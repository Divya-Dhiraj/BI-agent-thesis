# Use a modern Python base
FROM python:3.11-slim

# Set system-level environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# Set workspace
WORKDIR /app

# Install critical system tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- CRITICAL FIX: Copy requirements FIRST ---
COPY requirements.txt .

# Install dependencies from the file
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies (for Web Scraper)
RUN pip install playwright && playwright install --with-deps chromium

# Copy the actual thesis source code
COPY . .

# API entry point
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]