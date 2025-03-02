FROM python:3.10-slim

# Install Apache Beam SDK
RUN pip install --no-cache-dir apache-beam[gcp]==2.63.0

# Verify that the image does not have conflicting dependencies
RUN pip check

# Copy necessary files from the Apache Beam SDK image
COPY --from=apache/beam_python3.10_sdk:2.63.0 /opt/apache/beam /opt/apache/beam

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install minimal CPU-only PyTorch
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch torchvision

# Install remaining dependencies
RUN pip install --no-cache-dir \
    jupyterlab \
    notebook \
    voila \
    timm \
    opencv-python-headless \
    pillow \
    ultralytics \
    requests

# Copy the pipeline script into the container
COPY pipeline.py /pipeline.py

# Ensure the expected Dataflow directory exists
RUN mkdir -p /opt/google/dataflow/

# Ensure the correct Python version is used
ENV PYTHON_VERSION=3.10
ENV PYTHONPATH=/usr/local/lib/python3.10/site-packages

# Create python_template_launcher that runs our pipeline
RUN echo '#!/bin/bash\nexec python /pipeline.py' > /opt/google/dataflow/python_template_launcher && chmod +x /opt/google/dataflow/python_template_launcher

# Set the entrypoint to mimic the expected behavior
ENTRYPOINT ["/opt/google/dataflow/python_template_launcher"]
