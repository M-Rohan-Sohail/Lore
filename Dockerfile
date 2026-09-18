# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS runtime
# CP-11: share-card rendering (app/services/card_render.py) launches this
# binary directly via CHROME_EXECUTABLE_PATH, same as the dev machine's
# /usr/bin/google-chrome — Debian's `chromium` package installs equivalently
# at /usr/bin/chromium. Not build-verified (no `docker` binary in this
# environment — same honest gap as CP-0's own Dockerfile; see PROGRESS.md).
RUN apt-get update && apt-get install -y --no-install-recommends chromium \
    && rm -rf /var/lib/apt/lists/*
ENV CHROME_EXECUTABLE_PATH=/usr/bin/chromium
RUN useradd --create-home --uid 1000 appuser
COPY --from=builder /install /usr/local
WORKDIR /app
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
