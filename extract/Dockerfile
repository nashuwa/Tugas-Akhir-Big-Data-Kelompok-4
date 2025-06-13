FROM python:3.11

# Install system dependencies (TAMBAHAN: curl untuk health check)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Setup working directory
WORKDIR /app

# Create output directory and logs directory
RUN mkdir -p /app/output && chmod -R 777 /app/output
RUN mkdir -p /app/logs && chmod -R 777 /app/logs

# Copy requirements first for better caching
COPY ./extract/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy input file (tickers.xlsx) - PENTING!
COPY ./extract/tickers.xlsx .

# Copy yfinance extraction script (NAMA FILE BARU)
COPY ./extract/yfinance_data_fetcher_5years.py ./yfinance_data_fetcher_5years.py

# Set permissions
RUN chmod +x yfinance_data_fetcher_5years.py

# Environment variables
ENV EXCEL_FILE_PATH=/app/tickers.xlsx
ENV YFINANCE_OUTPUT_PATH=/app/output/tickers_data.json
ENV PYTHONUNBUFFERED=1

# TAMBAHAN: Health check untuk memastikan file output berhasil dibuat
HEALTHCHECK --interval=60s --timeout=30s --start-period=300s --retries=3 \
    CMD test -f /app/output/tickers_data.json || exit 1

# Default command (NAMA FILE BARU)
CMD ["python", "yfinance_data_fetcher_5years.py"]