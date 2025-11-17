# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the dependencies file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app /code/app

# Expose the port the app runs on
EXPOSE 8000

# Default command to run the API (can be overridden)
# We won't run uvicorn here, as docker-compose will manage services
CMD ["bash", "-c", "echo 'Base image created'"]