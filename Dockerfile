# API + UI web (FastAPI sirve / y /static). Datos persistentes: volumen en TREN_DATA_DIR.
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV TREN_DATA_DIR=/data

RUN mkdir -p /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY core/ core/
COPY infra/ infra/
COPY web/ web/

EXPOSE 8000
VOLUME ["/data"]

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
