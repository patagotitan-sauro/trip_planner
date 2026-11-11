
# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12

# ---- base: runtime dependencies only ----
FROM python:${PYTHON_VERSION}-slim-trixie AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
ARG APP_UID=1000
RUN useradd --create-home --uid ${APP_UID} app \
    && mkdir -p /app /data \
    && chown app:app /app /data
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# ---- dev: adds test and lint tools; code comes from a bind mount ----
FROM base AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
USER app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- prod: code baked into the image ----
FROM base AS prod
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]