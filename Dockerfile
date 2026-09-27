FROM osrf/ros:humble-desktop

# Get Dependancies
RUN apt-get update && apt-get install -y \
    build-essential cmake git wget \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.9 python3.9-venv python3.9-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY /cnos/ /root/cnos/

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

WORKDIR /root/cnos