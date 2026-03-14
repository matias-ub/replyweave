# Replyweave Backend

Run locally with Docker:

```bash
docker-compose up --build
```

Apply migrations:

```bash
docker-compose run --rm backend alembic upgrade head
```
