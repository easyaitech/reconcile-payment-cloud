FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create data directories
RUN mkdir -p /app/storage/uploads /app/storage/uploads/channels /app/storage/outputs

# Railway expects the app to bind to the PORT env var
# We use a small wrapper script to handle this
ENV PORT=8000

# Expose port
EXPOSE 8000

# Create a simple entrypoint that handles PORT
RUN echo '#!/bin/sh\nexec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
