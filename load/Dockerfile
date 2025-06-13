FROM python:3.9-slim

# Install system dependencies (TAMBAHAN: curl untuk health check)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY ./load/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy load scripts
COPY ./load/yfinance-load.py .

# Create volume mount point for output data
RUN mkdir -p /app/output
RUN mkdir -p /app/logs

# Set environment variables untuk database yfinance_data
ENV MONGO_URI="mongodb+srv://coffeelatte:secretdata3@luna.sryzase.mongodb.net/"
ENV MONGO_DB="yfinance_data"
ENV INPUT_PATH="/app/output/tickers_data.json"
ENV PYTHONUNBUFFERED=1

# TAMBAHAN: Health check untuk memastikan input file ada sebelum running
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD test -f /app/output/tickers_data.json || exit 1

# Run the yfinance loader script
CMD ["python", "yfinance-load.py"]