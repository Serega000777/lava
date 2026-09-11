FROM python:3.13-slim AS base
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade --yes \
    && rm -rf /var/lib/apt/lists/*
COPY apps/api/pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --retries 5 --timeout 60 \
      "pip==26.2.1" "setuptools==84.0.0" \
    && pip install --retries 5 --timeout 60 "."
COPY apps/api .

FROM base AS test
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 5 --timeout 60 ".[dev]"

FROM base AS runtime
RUN pip uninstall --yes setuptools \
    && pip uninstall --yes pip
RUN useradd --create-home --uid 10001 lava
USER lava
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
