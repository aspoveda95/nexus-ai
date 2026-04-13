FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements-all.txt /tmp/requirements-all.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements-all.txt

COPY apps/ai-ingestor /app

EXPOSE 8100

CMD ["uvicorn", "nexus_ingestor.main:app", "--host", "0.0.0.0", "--port", "8100"]
