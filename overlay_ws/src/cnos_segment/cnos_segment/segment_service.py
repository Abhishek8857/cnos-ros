import os
import glob
import subprocess
import tempfile
import threading 
import rclpy
import cv2
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

from pose_est_interface.srv import Segment

VENV_PYTHON = "/opt/cnos-venv/bin/python"
SERVER_SCRIPT = "src.scripts.inference_ros"
CNOS_DIR = "/root/cnos-ros/cnos/"

class CnosSegmentNode(Node):
    def __init__(self):
        super().__init__("cnos_segment_node")
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.latest_image = None
        self.cad_path = self.declare_parameter('cad_path', '/workspace/cnos/templates/cube.obj').value
        self.template_dir = self.declare_parameter('template_dir', '/root/cnos-ros/cnos/templates/').value
        self.obj_pose_path = self.declare_parameter('obj_pose_path', './src/poses/predefined_poses/obj_poses_level0.npy').value
        self.light_intensity = self.declare_parameter('light_intensity', 1.0).value
        self.radius = self.declare_parameter('radius', 0.4).value 
        self.save_dir = self.declare_parameter('save_dir', '/root/cnos-ros/cnos/segmaps').value
        
        if self.save_dir: 
            os.makedirs(self.save_dir, exist_ok=True)
        
        image_topic = self.declare_parameter('image_topic', '/front_stereo_camera/rgb/image_raw').value    
        
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        
        self.image_sub = self.create_subscription(Image, image_topic, self.image_callback, qos)
        self.get_logger().info(f"Subscribed to image topic: {image_topic}")

        self.ensure_templates_exist()
        
        self.get_logger().info("Starting CNOS inference subprocess (loading SAM + DINOv2)...")
        self.proc = subprocess.Popen(
            [VENV_PYTHON,"-m", SERVER_SCRIPT],
            cwd=CNOS_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        is_ready = False
        for line in self.proc.stdout:
            self.get_logger().info(f"[cnos-inference] {line.rstrip()}")
            if line.strip() == "READY":
                is_ready = True
                break
                
        if not is_ready:
            raise RuntimeError(f"Failed to load CNOS service, exit code: {self.proc.poll()}")
    
        self.srv = self.create_service(Segment, '/cnos/segment', self.handle_segment)

    def ensure_templates_exist(self):
        renders_dir = os.path.join(self.template_dir, "renders")
        existing_pngs = glob.glob(os.path.join(renders_dir, "*.png"))
        if existing_pngs:
            self.get_logger().info(
                f"Found {len(existing_pngs)} existing template PNGs in "
                f"{renders_dir}, skipping render."
            )
            return

        self.get_logger().info(f"No templates found in {renders_dir}. Rendering now...")
        os.makedirs(renders_dir, exist_ok=True)

        render_proc = subprocess.run(
            [
                VENV_PYTHON, "-m", "src.poses.pyrender",
                self.cad_path, self.obj_pose_path, self.template_dir,
                "0", "False", str(self.light_intensity), str(self.radius),
            ],
            cwd=CNOS_DIR,
            capture_output=True,
            text=True,
        )

        if render_proc.returncode != 0:
            self.get_logger().error(
                f"Template rendering failed:\n{render_proc.stdout}\n{render_proc.stderr}"
            )
            raise RuntimeError("Template rendering failed, see log above")

        rendered = glob.glob(os.path.join(renders_dir, "*.png"))
        self.get_logger().info(f"Rendered {len(rendered)} template PNGs into {renders_dir}.")
        
    def image_callback(self, msg):
        with self.lock:
            self.latest_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def handle_segment(self, request, response):
        with self.lock:
            if self.latest_image is None:
                response.success = False
                response.message = "No image received yet on image_topic"
                return response
            cv_img = self.latest_image.copy()

        rgb_f = tempfile.NamedTemporaryFile(suffix='.png', delete=False, dir='/tmp')
        mask_f = tempfile.NamedTemporaryFile(suffix='.png', delete=False, dir='/tmp')
        rgb_path, mask_path = rgb_f.name, mask_f.name
        rgb_f.close(); mask_f.close()

        cv2.imwrite(rgb_path, cv_img) 

        self.proc.stdin.write(f"{rgb_path}|{mask_path}\n")
        self.proc.stdin.flush()
        result_line = self.proc.stdout.readline().strip()
        os.remove(rgb_path)
        if result_line.startswith("OK|"):
            out_path = result_line.split("|", 1)[1]
            mask_img = cv2.imread(out_path, cv2.IMREAD_GRAYSCALE)
            os.remove(out_path)
                    
            if self.save_dir:
                cv2.imwrite(os.path.join(self.save_dir, f"segmap.png"), mask_img)
                cv2.imwrite(os.path.join(self.save_dir, f"rgb.png"), cv_img)
            
            response.mask = self.bridge.cv2_to_imgmsg(mask_img, encoding='mono8')
            response.success = True
            response.message = "OK"
        else:
            response.success = False
            response.message = result_line
            self.get_logger().warn(f"Segmentation failed: {result_line}")

        return response


def main():
    rclpy.init()
    node = CnosSegmentNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()