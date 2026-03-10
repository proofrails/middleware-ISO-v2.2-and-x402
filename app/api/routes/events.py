from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.sse import stream_events

router = APIRouter(tags=["events"])


@router.get("/v1/iso/events/{rid}")
async def sse_events(rid: str):
    return StreamingResponse(stream_events(rid), media_type="text/event-stream")
