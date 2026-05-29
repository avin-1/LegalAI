#!/bin/bash
# Start script for Hugging Face Spaces (GraphAPI space)

# 1. Start Redis in the background (used for caching queries)
echo "Starting Redis..."
redis-server --daemonize yes

# Wait for redis to be ready
sleep 2

# 2. Configure persistent storage if running on HF
if [ -d "/data" ]; then
    echo "Hugging Face persistent storage detected."
else
    echo "Running in ephemeral storage mode."
fi

# 3. Start Gunicorn (WSGI) tightly bound to HF default port
echo "Starting Flask GraphAPI on Port 7860..."
export PORT=7860
exec gunicorn --bind 0.0.0.0:7860 --workers 2 --threads 4 --timeout 120 main:app
