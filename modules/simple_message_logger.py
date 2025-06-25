import time
import logging
import json
from typing import Any, Dict
from datetime import datetime

from xaibo.core.protocols import TextMessageHandlerProtocol, ResponseProtocol, ConversationHistoryProtocol
from .presentation_websocket_manager import PresentationWebSocketManager

logger = logging.getLogger("simple-message-logger")

# Track startup time when module is first imported
_startup_time = time.time()


class SimpleMessageLogger(TextMessageHandlerProtocol):
    """
    A simplified text message handler that logs conversation data to a JSON lines file.
    
    This logger captures the last message in conversation history along with current slide
    information, elapsed time since startup, and timestamp, writing each entry as a single
    JSON line to a configurable output file.
    """
    
    @classmethod
    def provides(cls):
        """
        Specifies which protocols this class implements.
        
        Returns:
            list: List of protocols provided by this class
        """
        return [TextMessageHandlerProtocol]

    def __init__(self,
                 response: ResponseProtocol,
                 history: ConversationHistoryProtocol,
                 presentation_manager: PresentationWebSocketManager,
                 config: Dict[str, Any] | None = None):
        """
        Initialize the SimpleMessageLogger.
        
        Args:
            response: Protocol for sending responses back to the user
            history: A conversation History for accessing message history
            presentation_manager: Manager for presentation WebSocket functionality
            config: Configuration dictionary with required parameters:
                   - log_file: Path to the JSON lines output file
        """
        self.config: Dict[str, Any] = config or {}
        self.log_file = self.config.get('log_file', 'conversation_log.jsonl')
        self.response: ResponseProtocol = response
        self.history = history
        self.presentation_manager = presentation_manager

    def _get_elapsed_time_formatted(self) -> str:
        """
        Get elapsed time since startup in minutes and seconds format.
        
        Returns:
            str: Formatted elapsed time as "Xm Ys"
        """
        elapsed_seconds = int(time.time() - _startup_time)
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        return f"{minutes}m {seconds}s"

    async def _get_current_slide_info(self) -> Dict[str, Any]:
        """
        Get current slide information from the presentation manager.
        
        Returns:
            dict: Dictionary containing current slide information
        """
        try:
            current_route = await self.presentation_manager.get_current_route()
            all_routes = await self.presentation_manager.get_all_routes()
            
            return {
                "current_slide": current_route or "[Not set]",
                "total_slides": len(all_routes) if all_routes else 0,
                "position": all_routes.index(current_route or 'NOT SET') if all_routes else -1
            }
        except Exception as e:
            logger.error(f"Error getting slide information: {e}")
            return {
                "current_slide": "[Error]",
                "total_slides": 0,
                "position": -1,
                "error": str(e)
            }

    async def _get_last_message_text(self) -> str:
        """
        Get the text content of the last message in conversation history.
        
        Returns:
            str: Text content of the last message, or empty string if none found
        """
        try:
            history_messages = await self.history.get_history()
            if not history_messages:
                return ""
            
            last_message = history_messages[-1]
            
            # Extract text content from the message
            text_parts = []
            for content in last_message.content:
                if hasattr(content, 'text') and content.text:
                    text_parts.append(content.text.strip())
            
            return "\n".join(text_parts) if text_parts else ""
            
        except Exception as e:
            logger.error(f"Error getting last message text: {e}")
            return f"[Error retrieving message: {str(e)}]"

    async def _write_log_entry(self, message_text: str) -> None:
        """
        Write a log entry to the JSON lines file.
        
        Args:
            message_text: The text content of the message to log
        """
        try:
            # Gather all required data
            slide_info = await self._get_current_slide_info()
            elapsed_time = self._get_elapsed_time_formatted()
            timestamp = datetime.now().isoformat()
            
            # Create log entry
            log_entry = {
                "message_text": message_text,
                "slide_info": slide_info,
                "elapsed_time": elapsed_time,
                "timestamp": timestamp
            }
            
            # Write to JSON lines file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
            
            logger.debug(f"Logged message to {self.log_file}: {len(message_text)} characters")
            
        except Exception as e:
            logger.error(f"Error writing log entry to {self.log_file}: {e}")

    async def handle_text(self, text: str) -> None:
        """
        Process a user text message by logging it and responding with empty string.
        
        This method:
        1. Gets the last message from conversation history
        2. Gathers current slide information and elapsed time
        3. Writes the data as a JSON line to the configured log file
        4. Responds with an empty string
        
        Args:
            text: The user's input text message
        """
        try:
            # Get the last message text from history
            last_message_text = await self._get_last_message_text()
            
            # If no message in history, use the current input text
            if not last_message_text:
                last_message_text = text
            
            # Write log entry
            await self._write_log_entry(last_message_text)
            
            # Respond with empty string as specified
            await self.response.respond_text("")
            
        except Exception as e:
            logger.error(f"Error in handle_text: {e}")
            # Still respond with empty string even if logging fails
            await self.response.respond_text("")