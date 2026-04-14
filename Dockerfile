# Dockerfile — Trip Planning Agent
# Builds a container image for Cloud Run deployment

# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Cloud Run sets PORT env variable — default to 8080
ENV PORT=8080

# Start the FastAPI server
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port $PORT"]
