FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── System deps + Node 20 ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ────────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── React: install packages first (layer cache) ────────────────────────────────
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# ── React: build (output → ./static_frontend/) ────────────────────────────────
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ── App code ───────────────────────────────────────────────────────────────────
COPY . .

# ── Hugging Face Spaces requires port 7860 ─────────────────────────────────────
EXPOSE 7860

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
