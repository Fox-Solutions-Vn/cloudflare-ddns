# ---- Base ----
FROM python:alpine AS base
# install dependencies
RUN apk add --no-cache gcc musl-dev linux-headers supervisor

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Final ----
FROM base AS final

# copy installed dependencies and project source file(s)
WORKDIR /app

COPY cloudflare-ddns.py .
COPY api api/
COPY web web/

# Set environment variables with defaults
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV ASSET_VERSION=1.0.0

# Create directories for supervisor
RUN mkdir -p /var/log/supervisor

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the FastAPI port
EXPOSE ${API_PORT}

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
