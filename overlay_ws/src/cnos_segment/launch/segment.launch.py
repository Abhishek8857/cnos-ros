from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='cnos_segment',
            executable='segment_service',
            name='cnos_segment_node',
            output='screen',
            parameters=[{
                'image_topic': '/front_stereo_camera/rgb/image_raw',
                'cad_path': '/workspace/cnos/templates/cube.obj',
                'template_dir': '/root/cnos-ros/cnos/templates',
                'obj_pose_path': './src/poses/predefined_poses/obj_poses_level0.npy',
                'light_intensity': 1.0,
                'radius': 0.4,
            }],
        )
    ])