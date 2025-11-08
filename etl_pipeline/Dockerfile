FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY etl_pipeline/requirements.txt ./etl_pipeline/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r etl_pipeline/requirements.txt

# Copy ETL pipeline code
COPY etl_pipeline/ ./etl_pipeline/

# Create logs directory
RUN mkdir -p /app/logs

# Set Python path (so imports work correctly)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python", "-m", "etl_pipeline.main", "--env", "local"]

