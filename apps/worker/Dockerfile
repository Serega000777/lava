FROM python:3.13-slim
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade --yes \
    && rm -rf /var/lib/apt/lists/*
COPY apps/worker/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 5 --timeout 60 -r requirements.txt
RUN useradd --create-home --uid 10001 lava
COPY --chown=lava:lava apps/api/app ./app
COPY --chown=lava:lava apps/worker/worker.py ./worker.py
USER lava
CMD ["python", "worker.py"]
