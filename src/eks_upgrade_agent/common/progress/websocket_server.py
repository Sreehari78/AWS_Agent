"""
WebSocket server for real-time progress streaming.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Set

from ..models.progress import ProgressEvent
from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for real-time progress updates.
    
    Features:
    - Real-time progress streaming
    - Client connection management
    - Automatic cleanup of disconnected clients
    """
    
    def __init__(
        self,
        port: int = 8765,
        host: str = "localhost",
        enabled: bool = True
    ):
        """
        Initialize WebSocket server.
        
        Args:
            port: Server port
            host: Server host
            enabled: Whether WebSocket server is enabled
        """
        self.port = port
        self.host = host
        self.enabled = enabled
        
        self._server = None
        self._clients: Set[Any] = set()
        self._progress_summary_provider: Optional[Callable[[], Dict[str, Any]]] = None
        
        logger.debug(f"WebSocketServer initialized on {host}:{port} (enabled: {enabled})")
    
    def set_progress_summary_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        """
        Set the function that provides progress summaries.
        
        Args:
            provider: Function that returns progress summary dict
        """
        self._progress_summary_provider = provider
    
    async def start(self) -> bool:
        """
        Start the WebSocket server.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("WebSocket server disabled, not starting")
            return False
        
        try:
            import websockets
            
            self._server = await websockets.serve(
                self._handle_client, self.host, self.port
            )
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            return True
            
        except ImportError:
            logger.warning("websockets package not available, WebSocket server disabled")
            return False
        except Exception as e:
            log_exception(logger, e, "Failed to start WebSocket server")
            return False
    
    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._clients.clear()
            logger.info("WebSocket server stopped")
    
    async def broadcast_event(self, event: ProgressEvent) -> None:
        """
        Broadcast a progress event to all connected clients.
        
        Args:
            event: Progress event to broadcast
        """
        if not self._clients:
            return
        
        message = json.dumps({
            "type": "progress_event",
            "data": {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "task_id": event.task_id,
                "task_type": event.task_type,
                "status": event.status,
                "message": event.message,
                "percentage": event.percentage,
                "details": event.details
            }
        })
        
        await self._broadcast_message(message)
    
    async def broadcast_summary(self, summary: Dict[str, Any]) -> None:
        """
        Broadcast a progress summary to all connected clients.
        
        Args:
            summary: Progress summary to broadcast
        """
        if not self._clients:
            return
        
        message = json.dumps({
            "type": "progress_summary",
            "data": summary
        })
        
        await self._broadcast_message(message)
    
    async def _handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        self._clients.add(websocket)
        client_address = getattr(websocket, 'remote_address', 'unknown')
        logger.info(f"WebSocket client connected: {client_address}")
        
        try:
            # Send current progress summary on connection
            if self._progress_summary_provider:
                summary = self._progress_summary_provider()
                await websocket.send(json.dumps({
                    "type": "progress_summary",
                    "data": summary
                }))
            
            # Keep connection alive and handle incoming messages
            async for message in websocket:
                # Handle client messages if needed
                await self._handle_client_message(websocket, message)
                
        except Exception as e:
            log_exception(logger, e, f"WebSocket client error for {client_address}")
        finally:
            self._clients.discard(websocket)
            logger.info(f"WebSocket client disconnected: {client_address}")
    
    async def _handle_client_message(self, websocket, message: str) -> None:
        """
        Handle messages from WebSocket clients.
        
        Args:
            websocket: Client websocket
            message: Message from client
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "ping":
                # Respond to ping with pong
                await websocket.send(json.dumps({"type": "pong"}))
            elif message_type == "get_summary":
                # Send current progress summary
                if self._progress_summary_provider:
                    summary = self._progress_summary_provider()
                    await websocket.send(json.dumps({
                        "type": "progress_summary",
                        "data": summary
                    }))
            else:
                logger.debug(f"Unknown message type from client: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from WebSocket client: {message}")
        except Exception as e:
            log_exception(logger, e, "Error handling WebSocket client message")
    
    async def _broadcast_message(self, message: str) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: JSON message to broadcast
        """
        if not self._clients:
            return
        
        disconnected_clients = set()
        
        for client in self._clients:
            try:
                await client.send(message)
            except Exception as e:
                log_exception(logger, e, "Failed to send WebSocket message")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self._clients -= disconnected_clients
        
        if disconnected_clients:
            logger.debug(f"Removed {len(disconnected_clients)} disconnected WebSocket clients")
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._clients)
    
    def is_running(self) -> bool:
        """Check if the WebSocket server is running."""
        return self._server is not None and not self._server.is_serving()
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the WebSocket server.
        
        Returns:
            Dictionary with server information
        """
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "running": self.is_running(),
            "client_count": self.get_client_count()
        }