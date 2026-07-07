# syntax=docker/dockerfile:1
#
# Multi-stage build for the golden-path Python service.
#   build stage   — copies source and installs dependencies into a virtualenv
#   runtime stage — distroless python3 + nonroot: no shell, no package manager,
#                   runs as UID 65532, only the virtualenv and source on disk
#
# The image is scanned by Trivy (fail on CRITICAL) and signed by cosign in the
# reusable workflow; keeping the runtime tiny keeps that surface tiny.

# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS build

WORKDIR /src

# Install dependencies in their own layer so source-only changes reuse the cache.
COPY requirements.txt ./
RUN pip install --no-cache-dir --target /out/deps -r requirements.txt

COPY . .

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

# Belt-and-suspenders: the base already defaults to nonroot; state it anyway.
USER nonroot:nonroot

# Copy installed dependencies to the distroless Python's site-packages.
COPY --from=build /out/deps /home/nonroot/.local/lib/python3.12/site-packages

# Copy source code.
COPY --from=build /src /app

WORKDIR /app

# Informational: the service listens here (override with PORT).
EXPOSE 8080

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/bin/python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
