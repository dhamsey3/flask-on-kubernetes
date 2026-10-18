# ---------- build stage ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies in a throw-away layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- runtime stage ----------
FROM python:3.12-slim AS runtime

LABEL maintainer="contact@dijato-geoservices.com" \
      description="Dijato Geoservices Flask application"

WORKDIR /app

# Copy only the installed packages from the builder stage (no build-essential in final image)
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create and switch to a non-root user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
