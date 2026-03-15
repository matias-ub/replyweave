# Replyweave Backend

Run locally with Docker:

```bash
docker-compose up --build
```

Apply migrations:

```bash
docker-compose run --rm backend uv run alembic upgrade head
```

Install Playwright browsers for local (non-Docker) runs:

```bash
uv sync --extra scraping
uv run playwright install chromium
```

Disable scraping in Docker builds (skips Playwright install):

```bash
docker-compose build --build-arg ENABLE_SCRAPING=0 backend
```
