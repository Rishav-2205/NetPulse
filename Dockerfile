# NetPulse Containerized Testing & Web Control Center Environment
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install essential network diagnostic tools and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    tcpdump \
    curl \
    gcc \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /netpulse

# Install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy framework source code and built frontend assets
COPY . .

# Install framework in editable mode
RUN pip install -e .

# Create output directories
RUN mkdir -p reports logs

# Expose Web Control Center port
EXPOSE 8000

# Default entrypoint runs test suite and report generation
CMD ["pytest", "-v", "--html=reports/report.html", "--self-contained-html", "--json-report", "--json-report-file=reports/results.json"]
