"""
Stockei - Fila de processamento de frames
Fila assíncrona em memória com workers, priorização e timeout.
Produção: substituir por Redis (mesma interface).
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("stockei.queue")

DEFAULT_TIMEOUT = 5.0  # segundos
MAX_QUEUE_SIZE = 100


@dataclass(order=True)
class FrameJob:
    priority: int
    enqueued_at: float = field(compare=False)
    job_id: str = field(compare=False)
    data: bytes = field(compare=False, repr=False)
    future: asyncio.Future = field(compare=False, repr=False)


class FrameQueue:
    """Fila de frames com prioridade (menor = mais urgente) e workers."""

    def __init__(
        self,
        processor: Callable[[bytes], Awaitable[Any]],
        workers: int = 2,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._queue: asyncio.PriorityQueue[FrameJob] = asyncio.PriorityQueue(MAX_QUEUE_SIZE)
        self._processor = processor
        self._timeout = timeout
        self._worker_count = workers
        self._tasks: list[asyncio.Task] = []
        self.processed = 0
        self.dropped = 0

    async def start(self):
        # Recria a fila: asyncio.Queue fica vinculada ao event loop do primeiro
        # uso, e o loop muda entre ciclos de vida (ex.: reinícios, testes).
        self._queue = asyncio.PriorityQueue(MAX_QUEUE_SIZE)
        self._tasks = [
            asyncio.create_task(self._worker(i)) for i in range(self._worker_count)
        ]
        logger.info("FrameQueue: %d workers iniciados", self._worker_count)

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        self._tasks = []

    async def submit(self, data: bytes, priority: int = 10) -> Any:
        """Enfileira um frame e aguarda o resultado (ou TimeoutError)."""
        loop = asyncio.get_running_loop()
        job = FrameJob(
            priority=priority,
            enqueued_at=time.time(),
            job_id=uuid.uuid4().hex[:8],
            data=data,
            future=loop.create_future(),
        )
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            self.dropped += 1
            raise RuntimeError("Frame queue full")
        return await asyncio.wait_for(job.future, timeout=self._timeout)

    async def _worker(self, worker_id: int):
        while True:
            job = await self._queue.get()
            try:
                if time.time() - job.enqueued_at > self._timeout:
                    self.dropped += 1
                    if not job.future.done():
                        job.future.set_exception(TimeoutError("Frame expired in queue"))
                    continue
                result = await self._processor(job.data)
                self.processed += 1
                if not job.future.done():
                    job.future.set_result(result)
            except Exception as exc:
                if not job.future.done():
                    job.future.set_exception(exc)
            finally:
                self._queue.task_done()

    def stats(self) -> dict:
        return {
            "pending": self._queue.qsize(),
            "processed": self.processed,
            "dropped": self.dropped,
            "workers": self._worker_count,
        }
