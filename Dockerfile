FROM python:3.12-slim

WORKDIR /app

# Copy application files
COPY . /app

# Expose server port
EXPOSE 8085

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8085

# Run the server
CMD ["python", "server.py"]
