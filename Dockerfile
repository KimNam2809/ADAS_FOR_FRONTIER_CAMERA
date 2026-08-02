# Dockerfile for ADAS Object Detection on Jetson Nano and x86_64
# Multi-arch build for ARM64 (Jetson) and x86_64 (AWS/Laptop)

# Base image for ARM64 (Jetson Nano)
FROM nvcr.io/nvidia/l4t-base:r35.1.0 as arm64-base

# Base image for x86_64 (AWS/Laptop)
FROM nvcr.io/nvidia/cuda:11.8.0-base-ubuntu22.04 as x86_64-base

# Common setup for both architectures
FROM arm64-base as arm64-common
FROM x86_64-base as x86_64-common

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    git \
    wget \
    curl \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# For ARM64 (Jetson), install Jetson-specific packages
FROM arm64-common as arm64-final

# Install Jetson-specific dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnvinfer8 \
    libnvinfer-dev \
    libnvonnxparsers8 \
    libnvonnxparsers-dev \
    tensorrt \
    python3-libnvinfer-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyCUDA for TensorRT (ARM64)
RUN pip install --no-cache-dir pycuda

# Copy application code
COPY . /app
WORKDIR /app

# Set environment variables for Jetson
ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH

# For x86_64 (AWS/Laptop)
FROM x86_64-common as x86_64-final

# Install CUDA and TensorRT for x86_64
RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-driver-525 \
    nvidia-cuda-toolkit \
    libnvinfer8 \
    libnvinfer-dev \
    libnvonnxparsers8 \
    libnvonnxparsers-dev \
    tensorrt \
    && rm -rf /var/lib/apt/lists/*

# Install PyCUDA for TensorRT (x86_64)
RUN pip install --no-cache-dir pycuda

# Copy application code
COPY . /app
WORKDIR /app

# Set environment variables for x86_64
ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Final stage - multi-arch build
FROM arm64-final as final-arm64
FROM x86_64-final as final-x86_64

# For ARM64
FROM final-arm64

# Set entry point
ENTRYPOINT ["python", "-m", "src.detection.yolo_detector"]
CMD ["--help"]

# Expose port for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import src.detection; print('OK')" || exit 1
