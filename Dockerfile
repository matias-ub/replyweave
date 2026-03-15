FROM python:3.11-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

RUN pip install --no-cache-dir uv

COPY pyproject.toml /app/pyproject.toml

RUN uv lock
ARG ENABLE_SCRAPING=1
RUN if [ "$ENABLE_SCRAPING" = "1" ]; then \
		uv sync --no-dev --extra scraping; \
		uv run playwright install --with-deps chromium; \
	else \
		uv sync --no-dev; \
	fi

COPY . /app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
