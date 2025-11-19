"""
COMPLETE WORKING: core/callback_manager.py
Updated with 'on_response_done' chain for event-driven playback
"""

import asyncio
import logging
from typing import Callable, List, Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class CallbackChain:
    """Manages a chain of callbacks with priority ordering."""
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[Tuple[int, Callable]] = []
        logger.debug(f"[CALLBACK CHAIN] Created: {name}")
    
    def add_handler(self, handler: Callable, priority: int = 10):
        """Add a handler with priority (lower = higher priority)."""
        self.handlers.append((priority, handler))
        self.handlers.sort(key=lambda x: x[0])
        logger.debug(f"[CALLBACK CHAIN] {self.name}: Registered handler: {handler.__name__} (priority={priority})")
    
    async def invoke(self, *args, **kwargs):
        """Invoke all handlers in priority order."""
        for priority, handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"[CALLBACK CHAIN] {self.name}: Error in handler {handler.__name__}: {e}", exc_info=True)
    
    def count(self) -> int:
        """Return number of registered handlers."""
        return len(self.handlers)


class CallbackManager:
    """Central callback manager for audio, text, and connection events."""
    
    def __init__(self, realtime_client):
        """Initialize callback manager with reference to realtime client."""
        self.realtime_client = realtime_client
        
        # Create callback chains
        self.on_audio_received = CallbackChain("on_audio_received")
        self.on_text_received = CallbackChain("on_text_received")
        self.on_connection_closed = CallbackChain("on_connection_closed")
        # --- NEW CHAIN ---
        self.on_response_done = CallbackChain("on_response_done")
        
        # Wire up the realtime client to use these chains
        self._wire_callbacks()
        
        logger.info("[CALLBACK MANAGER] Initialized and wired to RealtimeClient")
    
    def _wire_callbacks(self):
        """Wire callback chains to realtime client."""
        # Set the realtime client's callbacks to invoke our chains
        self.realtime_client.on_audio_received = self._on_audio_callback
        self.realtime_client.on_text_received = self._on_text_callback
        self.realtime_client.on_response_done = self._on_response_done_callback
        
        logger.debug("[CALLBACK MANAGER] Wired callbacks to RealtimeClient")
    
    async def _on_audio_callback(self, audio_data: bytes, **kwargs):
        await self.on_audio_received.invoke(audio_data, **kwargs)
    
    async def _on_text_callback(self, text: str, **kwargs):
        await self.on_text_received.invoke(text, **kwargs)
        
    async def _on_response_done_callback(self, **kwargs):
        await self.on_response_done.invoke(**kwargs)
    
    def add_audio_handler(self, handler: Callable, priority: int = 10):
        self.on_audio_received.add_handler(handler, priority)
    
    def add_text_handler(self, handler: Callable, priority: int = 10):
        self.on_text_received.add_handler(handler, priority)
        
    def add_response_done_handler(self, handler: Callable, priority: int = 10):
        """Register a response done handler."""
        self.on_response_done.add_handler(handler, priority)
        logger.debug(f"[CALLBACK MANAGER] Adding response_done handler: {handler.__name__}")
    
    def get_status(self) -> Dict[str, int]:
        return {
            'on_text_received': self.on_text_received.count(),
            'on_audio_received': self.on_audio_received.count(),
            'on_connection_closed': self.on_connection_closed.count(),
            'on_response_done': self.on_response_done.count()
        }