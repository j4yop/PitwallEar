# Multi-stage build: Node builds the React app, then FastAPI serves it.
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --include=dev
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# System deps for FastF1 / audio decoding.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
# CPU torch wheels: the default index resolves CUDA-bundled wheels (~2-3 GB
# extra) that a slim serving image never needs.
RUN pip install --no-cache-dir -e ".[pace,audio]" \
    --extra-index-url https://download.pytorch.org/whl/cpu

ENV PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
