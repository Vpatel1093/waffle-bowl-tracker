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

# Expose port
EXPOSE 8080

# Startup script to initialize tokens then start gunicorn
CMD python init_tokens.py && gunicorn wsgi:app --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:8080
