"""Test streaming endpoint."""

import asyncio
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/test-stream")
async def test_stream():
    """
    Test SSE streaming to verify connection works.
    """
    async def event_generator():
        """Generate test events."""
        try:
            # Send initial message
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "status",
                    "message": "Stream starting..."
                })
            }

            # Stream some test data
            for i in range(10):
                await asyncio.sleep(0.5)  # Simulate processing
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "stream",
                        "text": f"Chunk {i + 1}/10\n"
                    })
                }

            # Send completion
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "complete",
                    "message": "Stream completed successfully!"
                })
            }

        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "error": str(e)
                })
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "none",
            "Access-Control-Allow-Origin": "*"
        },
        ping=15
    )
