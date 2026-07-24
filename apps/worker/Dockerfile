FROM python:3.13-slim
WORKDIR /worker
COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/worker .
CMD ["python", "worker.py"]

