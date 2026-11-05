# ── Base image ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── OS dependencies (needed by scikit-surprise C extensions) ───────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
COPY . .

# ── Hugging Face Spaces requires port 7860 ───────────────────────────────────
EXPOSE 7860

# ── Environment variables ────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Launch FastAPI via uvicorn ────────────────────────────────────────────────
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
