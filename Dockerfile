FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY scripts/ scripts/
COPY demo/cache.json demo/cache.json
RUN mkdir -p /data
ENV CARD_KHOLO_DB=/data/card_kholo.sqlite3
VOLUME ["/data"]
EXPOSE 8000
# Render injects $PORT; 8000 locally.
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
