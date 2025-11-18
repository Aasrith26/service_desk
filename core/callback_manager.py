"""
Callback Chain Management System
Manages multiple handlers for a single event to prevent callback collision.
Fixes the issue where engine.start() was overwriting main.py's callbacks.
"""

import asyncio
import logging
from typing import Callable, List, Optional, Any

logger = logging.getLogger(__name__)


class CallbackChain:
    """Manages multiple callbacks for a single event."""

    def __init__(self, name: str = "CallbackChain"):
        """Initialize callback chain.

        Args:
            name: Name for logging purposes
        """
        self.handlers: List[Callable] = []
        self.name = name
        logger.debug(f"[CALLBACK CHAIN] Created: {name}")

    def register(self, handler: Callable, priority: int = 0) -> None:
        """Register a callback handler.

        Args:
            handler: Async or sync callable
            priority: Higher priority handlers called first
        """
        if handler is None:
            logger.warning(f"[CALLBACK CHAIN] {self.name}: Attempting to register None handler")
            return

        if handler in [h for h, _ in self.handlers]:
            logger.debug(f"[CALLBACK CHAIN] {self.name}: Handler already registered: {handler.__name__}")
            return

        self.handlers.append((handler, priority))
        # Sort by priority (highest first)
        self.handlers.sort(key=lambda x: x[1], reverse=True)

        logger.debug(f"[CALLBACK CHAIN] {self.name}: Registered handler: {handler.__name__} (priority={priority})")

    def unregister(self, handler: Callable) -> None:
        """Unregister a callback handler.

        Args:
            handler: Handler to remove
        """
        before_count = len(self.handlers)
        self.handlers = [(h, p) for h, p in self.handlers if h != handler]
        after_count = len(self.handlers)

        if before_count > after_count:
            logger.debug(f"[CALLBACK CHAIN] {self.name}: Unregistered handler: {handler.__name__}")
        else:
            logger.warning(f"[CALLBACK CHAIN] {self.name}: Handler not found: {handler.__name__}")

    async def call(self, *args, **kwargs) -> None:
        """Call all registered handlers in order.

        Args:
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        if not self.handlers:
            logger.debug(f"[CALLBACK CHAIN] {self.name}: No handlers registered")
            return

        for handler, priority in self.handlers:
            handler_name = getattr(handler, '__name__', str(handler))
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
                logger.debug(f"[CALLBACK CHAIN] {self.name}: ✓ Called {handler_name}")
            except Exception as e:
                logger.error(f"[CALLBACK CHAIN] {self.name}: ✗ Error in {handler_name}: {e}", exc_info=True)

    async def __call__(self, *args, **kwargs):
        """Make the chain callable as an async function."""
        await self.call(*args, **kwargs)

    def __repr__(self):
        handlers_str = ", ".join([h.__name__ for h, _ in self.handlers])
        return f"CallbackChain({self.name}, handlers=[{handlers_str}])"


class RealtimeClientCallbackManager:
    """Manages callbacks for RealtimeClient to support multiple handlers."""

    def __init__(self, realtime_client):
        """Initialize callback manager for realtime client.

        Args:
            realtime_client: The RealtimeClient instance to manage
        """
        self.client = realtime_client

        # Create callback chains
        self._on_text_received_chain = CallbackChain("on_text_received")
        self._on_audio_received_chain = CallbackChain("on_audio_received")
        self._on_connection_closed_chain = CallbackChain("on_connection_closed")

        # Wire the chains to the client
        self.client.on_text_received = self._on_text_received_chain
        self.client.on_audio_received = self._on_audio_received_chain

        if hasattr(self.client, 'on_connection_closed'):
            self.client.on_connection_closed = self._on_connection_closed_chain

        logger.info("[CALLBACK MANAGER] Initialized for RealtimeClient")

    def add_text_handler(self, handler: Callable, priority: int = 0) -> None:
        """Add a text received handler.

        Args:
            handler: Async or sync callable that receives text
            priority: Higher priority = called first
        """
        logger.debug(f"[CALLBACK MANAGER] Adding text handler: {handler.__name__}")
        self._on_text_received_chain.register(handler, priority)

    def add_audio_handler(self, handler: Callable, priority: int = 0) -> None:
        """Add an audio received handler.

        Args:
            handler: Async or sync callable that receives audio
            priority: Higher priority = called first
        """
        logger.debug(f"[CALLBACK MANAGER] Adding audio handler: {handler.__name__}")
        self._on_audio_received_chain.register(handler, priority)

    def add_connection_closed_handler(self, handler: Callable, priority: int = 0) -> None:
        """Add a connection closed handler.

        Args:
            handler: Async or sync callable
            priority: Higher priority = called first
        """
        logger.debug(f"[CALLBACK MANAGER] Adding connection closed handler: {handler.__name__}")
        self._on_connection_closed_chain.register(handler, priority)

    def remove_text_handler(self, handler: Callable) -> None:
        """Remove a text received handler.

        Args:
            handler: Handler to remove
        """
        logger.debug(f"[CALLBACK MANAGER] Removing text handler: {handler.__name__}")
        self._on_text_received_chain.unregister(handler)

    def remove_audio_handler(self, handler: Callable) -> None:
        """Remove an audio received handler.

        Args:
            handler: Handler to remove
        """
        logger.debug(f"[CALLBACK MANAGER] Removing audio handler: {handler.__name__}")
        self._on_audio_received_chain.unregister(handler)

    def remove_connection_closed_handler(self, handler: Callable) -> None:
        """Remove a connection closed handler.

        Args:
            handler: Handler to remove
        """
        logger.debug(f"[CALLBACK MANAGER] Removing connection closed handler: {handler.__name__}")
        self._on_connection_closed_chain.unregister(handler)

    def get_status(self) -> dict:
        """Get status of all callback chains.

        Returns:
            Dict with handler counts
        """
        return {
            "on_text_received": len(self._on_text_received_chain.handlers),
            "on_audio_received": len(self._on_audio_received_chain.handlers),
            "on_connection_closed": len(self._on_connection_closed_chain.handlers),
        }