# Backend runtime for hosted deployments (Render free tier).
# Deterministic backend stays the sole authority for all banking operations.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-hin \
      tesseract-ocr-tel \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bundled tessdata (eng/hin/tel) ships with the code; paths resolve relative
# to app/services/, so no extra config is needed.
ENV DEBUG=0 \
    OCR_LANGUAGES=eng,hin,tel

EXPOSE 8000

# SECRET_KEY defaults to a freshly generated random value per boot unless
# provided via the environment. Bindings to Dockerfile are written locally for readability.
CMD ["sh", "-c", "export SECRET_KEY=${SECRET_KEY:-$(python -c 'import secrets; print(secrets.token_hex(32))')} && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
