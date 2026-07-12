# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# --- runtime ---
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Metaphors" \
      org.opencontainers.image.description="Infrastructure visualization through interchangeable metaphors" \
      org.opencontainers.image.source="https://github.com/Paslestrange/Metaphors"

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY server.py ./
COPY engine/ engine/
COPY static/ static/

RUN chown -R app:app /app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "server.py"]
