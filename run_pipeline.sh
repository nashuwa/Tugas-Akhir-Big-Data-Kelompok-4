#!/bin/bash

echo "🚀 Building YFinance Pipeline Images..."
echo "========================================"

# Build extract image
echo "📈 Building extraction image..."
docker build -f extract/Dockerfile -t yfinance_extraction:latest .
if [ $? -eq 0 ]; then
    echo "✅ Extraction image built successfully"
else
    echo "❌ Failed to build extraction image"
    exit 1
fi

# Build load image  
echo "💾 Building load image..."
docker build -f load/Dockerfile -t yfinance-load:latest .
if [ $? -eq 0 ]; then
    echo "✅ Load image built successfully"
else
    echo "❌ Failed to build load image"
    exit 1
fi

echo ""
echo "🎉 All images built successfully!"
echo "📋 Images created:"
echo "   - yfinance_extraction:latest"
echo "   - yfinance-load:latest"
echo ""
echo "🚀 You can now run: docker-compose up -d"