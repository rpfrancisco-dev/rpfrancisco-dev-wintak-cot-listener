# TAK Device Monitor — Django/Channels backend served by daphne.
# Multi-stage: build wheels (mgrs needs a C compiler) then a slim runtime.

FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
# Install into an isolated prefix we copy into the runtime image. All deps
# (mgrs, cryptography, …) ship manylinux wheels, so no compiler is needed.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY --from=builder /install /usr/local

WORKDIR /app
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# settings.py derives FRONTEND_DIR from the repo root (/app); run from backend/.
WORKDIR /app/backend

EXPOSE 8000
# 0.0.0.0 so the published port is reachable from the host/LAN.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "takbridge.asgi:application"]
