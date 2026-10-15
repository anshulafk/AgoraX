import asyncio
import websockets
import json
import logging
from typing import Callable, Awaitable, List

logger = logging.getLogger(__name__)

class TickWebsocketClient:
    """
    Async WebSocket consumer for real-time market data ticks.
    """
    def __init__(self, uri: str):
        self.uri = uri
        self.callbacks: List[Callable[[dict], Awaitable[None]]] = []

    def register_callback(self, callback: Callable[[dict], Awaitable[None]]):
        self.callbacks.append(callback)

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.uri) as ws:
                    logger.info(f"Connected to tick stream at {self.uri}")
                    await self._listen(ws)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Websocket closed. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Websocket error: {e}")
                await asyncio.sleep(5)

    async def _listen(self, ws):
        async for message in ws:
            data = json.loads(message)
            for callback in self.callbacks:
                # Ensure callback execution doesn't block the listener completely if they take long,
                # though usually ticks are handled fast enough.
                await callback(data)
