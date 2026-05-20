# Use Python 3.10 slim image (stdlib still includes audioop; avoids 3.13+ removals)
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set hardcoded environment variables
ENV ACCOUNT_SID=AC0492c8d3fcd15b0a2db82cc67edda495
ENV AUTH_TOKEN=43e2fd995c2137c8df24636fc79ac50c
ENV PHONE_NO=+17654030113
ENV GEMINI_API_KEY=AIzaSyDHRo3DNSXsMyEQg0vJgePxldozrIlLx4g

# Expose port
EXPOSE 8080

# Run the application with uvicorn
# Cloud Run will set PORT env var, default to 8080
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
