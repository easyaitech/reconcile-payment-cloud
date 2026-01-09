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

# Make start script executable
RUN chmod +x /app/start.sh

# Create data directories
RUN mkdir -p /app/storage/uploads /app/storage/uploads/channels /app/storage/outputs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests, os; port=os.getenv('PORT', '8000'); requests.get(f'http://localhost:{port}/api/v1/health')" || exit 1

# Start command
CMD ["/app/start.sh"]
