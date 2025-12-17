FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# copy the entrypoint into the image and make it executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Use the entrypoint to initialize token files and start the server
ENTRYPOINT ["/docker-entrypoint.sh"]
# Default command when no command is provided (matches entrypoint fallback)
CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120"]

# Expose port
EXPOSE 8080
