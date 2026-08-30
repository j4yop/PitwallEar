# Multi-stage build: Node builds the React app, then FastAPI serves it.
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --include=dev --legacy-peer-deps
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

# Bake the text-emotion model into the image: free-tier hosts have ephemeral
# disks, so without this every restart re-downloads ~500 MB from the HF hub
# and the first analysis after each deploy pays a multi-minute penalty.
# Kept to the text model — the audio models would push the image past ~2 GB
# and their RAM footprint exceeds the 512 MB tier anyway.
ENV HF_HUB_DISABLE_TELEMETRY=1
RUN python -c "from transformers import pipeline; pipeline('text-classification', model='cardiffnlp/twitter-roberta-base-emotion', top_k=None)" \
    && python -c "from transformers import __version__ as v; print('transformers', v)"

ENV PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
