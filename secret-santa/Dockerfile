# Family Secret Santa — one small container. Mount a persistent volume at /data.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV SANTA_DB=/data/santa.db \
    SANTA_OUTBOX=/data/outbox \
    PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8080
# one worker on purpose: sessions and the daily digest scheduler live in this process
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
