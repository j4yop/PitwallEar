# Multi-stage build: Node builds the React app, then FastAPI serves it.
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --include=dev
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
RUN pip install --no-cache-dir -e ".[pace,audio]"

ENV PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
