# Use an official Python runtime as a parent image
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY ./requirements.txt /app/requirements.txt
COPY ./requirements-dev.txt /app/requirements-dev.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir setuptools wheel
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# dev dependencies - do not run in deployment pipeline
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Start a shell instead of running the Python script
CMD ["/bin/bash"]
