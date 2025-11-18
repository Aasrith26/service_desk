"""
COMPLETE WORKING: core/callback_manager.py
Python 3.9 compatible with proper callback chain
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
        
        # Wire up the realtime client to use these chains
        self._wire_callbacks()
        
        logger.info("[CALLBACK MANAGER] Initialized and wired to RealtimeClient")
    
    def _wire_callbacks(self):
        """Wire callback chains to realtime client."""
        # Set the realtime client's callbacks to invoke our chains
        self.realtime_client.on_audio_received = self._on_audio_callback
        self.realtime_client.on_text_received = self._on_text_callback
        
        logger.debug("[CALLBACK MANAGER] Wired callbacks to RealtimeClient")
    
    async def _on_audio_callback(self, audio_data: bytes, **kwargs):
        """Internal callback that invokes the audio chain."""
        await self.on_audio_received.invoke(audio_data, **kwargs)
    
    async def _on_text_callback(self, text: str, **kwargs):
        """Internal callback that invokes the text chain."""
        await self.on_text_received.invoke(text, **kwargs)
    
    def add_audio_handler(self, handler: Callable, priority: int = 10):
        """Register an audio handler."""
        self.on_audio_received.add_handler(handler, priority)
        logger.debug(f"[CALLBACK MANAGER] Adding audio handler: {handler.__name__}")
    
    def add_text_handler(self, handler: Callable, priority: int = 10):
        """Register a text handler."""
        self.on_text_received.add_handler(handler, priority)
        logger.debug(f"[CALLBACK MANAGER] Adding text handler: {handler.__name__}")
    
    def add_connection_closed_handler(self, handler: Callable, priority: int = 10):
        """Register a connection closed handler."""
        self.on_connection_closed.add_handler(handler, priority)
        logger.debug(f"[CALLBACK MANAGER] Adding connection closed handler: {handler.__name__}")
    
    def get_status(self) -> Dict[str, int]:
        """Get count of registered handlers for each callback type."""
        return {
            'on_text_received': self.on_text_received.count(),
            'on_audio_received': self.on_audio_received.count(),
            'on_connection_closed': self.on_connection_closed.count()
        }
