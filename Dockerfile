FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=20

WORKDIR /app

# ── System deps ────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ────────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── React build ────────────────────────────────────────────────────────────────
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci --prefer-offline

COPY frontend/ ./frontend/
RUN cd frontend && npm run build
# Output lands in ./static_frontend/ (configured in vite.config.js)

# ── App code ───────────────────────────────────────────────────────────────────
COPY . .

# ── Hugging Face Spaces requires port 7860 ─────────────────────────────────────
EXPOSE 7860

HEALTHCHECK CMD curl --fail http://localhost:7860/api/health || exit 1

# FastAPI serves React static files + /api endpoints on the single exposed port.
# Streamlit admin panel is available internally on port 7861 via start.sh.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
