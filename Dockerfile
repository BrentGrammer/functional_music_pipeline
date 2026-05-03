# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Default command to start a shell
CMD ["/bin/bash"]
