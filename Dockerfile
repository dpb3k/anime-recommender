FROM python:3.10-slim

# System dependencies for scikit-surprise
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose port and run the server
EXPOSE 5000
CMD ["python", "main.py"]
