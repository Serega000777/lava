FROM python:3.13-slim
WORKDIR /app
COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./app
COPY apps/worker/worker.py ./worker.py
CMD ["python", "worker.py"]
