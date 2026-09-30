FROM osrf/ros:humble-desktop

# Set Environments
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128,garbage_collection_threshold:0.8
ENV RGB_PATH=/root/cnos/images/
ENV OUTPUT_DIR=/root/cnos/results/
ENV CAD_PATH=/root/cnos/templates/  

# For Terminal bash 
SHELL ["/bin/bash", "-c"]

# Source ROS environments
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc \
 && echo "source /root/cnos-ros/colcon_ws/install/setup.bash" >> /root/.bashrc

# Get Dependancies
RUN apt-get update && apt-get install -y \
    build-essential cmake git wget unzip \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.9 python3.9-venv python3.9-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY /cnos/ /root/cnos-ros/cnos/

# Change working directory 
WORKDIR /root/cnos-ros/cnos/

# Build Conda Environment
RUN python3.9 -m venv /opt/cnos-venv
RUN /opt/cnos-venv/bin/pip install --upgrade pip
RUN /opt/cnos-venv/bin/pip install \
    numpy==1.26.4 torch torchvision omegaconf torchmetrics==0.10.3 \
    fvcore iopath xformers==0.0.18 opencv-python pycocotools matplotlib \
    onnxruntime onnx scipy hydra-colorlog hydra-core gdown scikit-image \
    pytorch-lightning==1.8.6 pandas ruamel.yaml pyrender wandb distinctipy \
    git+https://github.com/facebookresearch/hand_tracking_toolkit.git

# Install SAM
RUN /opt/cnos-venv/bin/pip install git+https://github.com/facebookresearch/segment-anything.git

# Install FastSAM
RUN /opt/cnos-venv/bin/pip install ultralytics==8.0.135

# Get DinoV2 (Getting this specific version because of missing 'from __future__ import annotations' error)
RUN wget -O /root/dinov2.zip https://github.com/facebookresearch/dinov2/archive/85a24602099d397264d5b30461ad7f3bfd726ca1.zip && \
    cd /root && unzip -q dinov2.zip && \
    mv dinov2-85a24602099d397264d5b30461ad7f3bfd726ca1 dinov2 && rm -rf dinov2.zip

# Download model checkpoints for DinoV2
RUN mkdir -p /root/.cache/torch/hub/checkpoints && \
    wget -q -O /root/.cache/torch/hub/checkpoints/dinov2_vitl14_pretrain.pth \
    https://dl.fbaipublicfiles.com/dinov2/dinov2_vitl14/dinov2_vitl14_pretrain.pth

# Copy Files 
COPY /colcon_ws/src/ /root/cnos-ros/colcon_ws/src/

# Change working directory
WORKDIR /root/cnos-ros/colcon_ws/
    
# Source ROS and build packages
RUN source /opt/ros/humble/setup.bash && colcon build

# Change working directory
WORKDIR /root/cnos-ros/