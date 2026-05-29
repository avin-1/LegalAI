FROM python:3.10-slim-bookworm

# Install Redis and system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Set up user and working directory
# Hugging Face encourages running as non-root user (id 1000)
RUN useradd -m -u 1000 user
WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . /app/

# Setup permissions for HF persistent storage compatibility
RUN mkdir -p /data && chown -R user:user /data /app

# Give permissions to start.sh
RUN chmod +x /app/start.sh

# Switch to the non-root user
USER user

# Expose HF default port
EXPOSE 7860

# Command
CMD ["/app/start.sh"]
