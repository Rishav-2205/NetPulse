# NetPulse Containerized Testing Environment
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

# Copy framework source code
COPY . .

# Install framework in editable mode
RUN pip install -e .

# Create unprivileged runner user (optional, can run as root for CAP_NET_RAW)
RUN mkdir -p reports logs

# Default entrypoint runs the automated test suite
CMD ["pytest", "-v", "--html=reports/report.html", "--self-contained-html", "--json-report", "--json-report-file=reports/results.json"]
