#!/bin/bash

echo "🛑 Stopping all Syngenta Microservices..."
pkill -f uvicorn
echo "✅ All services stopped."
