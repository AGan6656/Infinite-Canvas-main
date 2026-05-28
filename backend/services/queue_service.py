from __future__ import annotations

from ..core import QUEUE, QUEUE_LOCK, app


@app.get("/api/queue_status")
async def get_queue_status(client_id: str):
    with QUEUE_LOCK:
        total = len(QUEUE)
        positions = [i + 1 for i, task in enumerate(QUEUE) if task["client_id"] == client_id]
        position = positions[0] if positions else 0
    return {"total": total, "position": position}
