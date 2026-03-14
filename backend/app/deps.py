import uuid
from typing import Annotated

from fastapi import Header, HTTPException, status


async def get_user_id_header(x_user_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id required")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-User-Id"
        ) from exc
