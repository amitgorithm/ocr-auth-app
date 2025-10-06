# Use an official Python 3.12 image as the base
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Update package lists and install system dependencies (like Tesseract)
# This replaces apt.txt with a direct, guaranteed command
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

# Copy your Python requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project code into the container
COPY . .

# Define the command to run your app
# This replaces the Procfile and uses the gunicorn config we already made
CMD ["gunicorn", "--config", "gunicorn_config.py", "backend.app:app"]