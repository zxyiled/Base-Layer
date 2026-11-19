FROM python:3.12.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
# Runtime dependencies only: skips the dev (pytest) and train (scikit-learn,
# matplotlib) groups. UV_NO_CACHE keeps the uv download cache out of the layer.
RUN uv sync --locked --no-default-groups --no-install-project

# Selective COPY: never the whole context (it may hold datasets or tool folders).
COPY app ./app
COPY migrations ./migrations
COPY ml_training/reports/metrics.json ./ml_training/reports/metrics.json
COPY wsgi.py entrypoint.sh README.md ./

# The code stays owned by root (read-only for the app); only logs/ is writable.
# A recursive chown of /app would copy the whole .venv into a new layer.
RUN chmod +x entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/logs \
    && chown appuser:appuser /app/logs

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
# Keep one worker: RotatingFileHandler and the lazy model-version registration
# are not safe across several processes. Threads give concurrency instead.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", "wsgi:app"]
