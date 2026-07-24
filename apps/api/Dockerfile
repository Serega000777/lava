FROM python:3.13-slim
WORKDIR /app
COPY apps/api/pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"
COPY apps/api .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

