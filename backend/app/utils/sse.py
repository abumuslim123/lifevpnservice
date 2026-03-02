import asyncio
from typing import Set


class StatusBroadcaster:
    """Рассылает события статуса серверов всем подключённым SSE-клиентам."""

    def __init__(self) -> None:
        self._queues: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    async def broadcast(self, data: dict) -> None:
        for q in list(self._queues):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass  # медленный клиент — пропускаем событие


broadcaster = StatusBroadcaster()
