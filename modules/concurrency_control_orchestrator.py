import time
import logging
from typing import Any, Dict, List
from datetime import datetime
import threading
import re

from xaibo.core.protocols import TextMessageHandlerProtocol, ResponseProtocol, LLMProtocol, ToolProviderProtocol, \
    ConversationHistoryProtocol
from xaibo.core.models.llm import LLMMessage, LLMOptions, LLMRole, LLMFunctionResult, LLMMessageContentType, LLMMessageContent
from .presentation_websocket_manager import PresentationWebSocketManager

import json

logger = logging.getLogger("concurrency-control-orchestrator")

# Track startup time when module is first imported
_startup_time = time.time()


class ConcurrencyControlOrchestrator(TextMessageHandlerProtocol):
    """
    A text message handler that implements concurrency control mechanism.
    
    This orchestrator sets the current time in a global class variable and a local instance variable
    on each invocation. After each interaction with the LLM, it checks if the global variable is 
    larger than the local variable (indicating a different invocation happened in the meantime).
    If that happens, it stops execution and sends an empty string as the response.
    """
    
    # Global class variable to track the latest invocation time
    _global_invocation_time: float = 0.0
    
    # Global class variable to track hint usage history
    _hint_usage_history: List[Dict[str, Any]] = []
    _hint_history_lock: threading.Lock = threading.Lock()
    
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
                 llm: LLMProtocol,
                 tool_provider: ToolProviderProtocol,
                 history: ConversationHistoryProtocol,
                 presentation_manager: PresentationWebSocketManager,
                 config: Dict[str, Any] | None = None):
        """
        Initialize the ConcurrencyControlOrchestrator.
        
        Args:
            response: Protocol for sending responses back to the user
            llm: Protocol for generating text using a language model
            tool_provider: Protocol for accessing and executing tools
            history: A conversation History for some context
            presentation_manager: Manager for presentation WebSocket functionality
            config: Configuration dictionary with optional parameters:
                   - system_prompt: Initial system prompt for the conversation
                   - max_thoughts: Maximum number of tool usage iterations
                   - transcription_file_path: Path to JSON lines file containing transcription data
        """
        self.config: Dict[str, Any] = config or {}
        self.system_prompt = self.config.get('system_prompt', '')
        self.max_thoughts = self.config.get('max_thoughts', 10)
        self.transcription_file_path = self.config.get('transcription_file_path', '')
        self.response: ResponseProtocol = response
        self.llm: LLMProtocol = llm
        self.tool_provider: ToolProviderProtocol = tool_provider
        self.history = history
        self.presentation_manager = presentation_manager
        
        # Local instance variable to track this invocation's time
        self._local_invocation_time: float = 0.0
        
        # Flag to track if transcription has been loaded to avoid loading it multiple times
        self._transcription_loaded: bool = False

    def _update_invocation_times(self) -> None:
        """Update both global and local invocation times to current time."""
        current_time = time.time()
        ConcurrencyControlOrchestrator._global_invocation_time = current_time
        self._local_invocation_time = current_time
        logger.debug(f"Updated invocation times to {current_time}")

    def _check_concurrency_conflict(self) -> bool:
        """
        Check if another invocation has occurred since this one started.
        
        Returns:
            bool: True if there's a concurrency conflict, False otherwise
        """
        conflict = ConcurrencyControlOrchestrator._global_invocation_time > self._local_invocation_time
        if conflict:
            logger.info(f"Concurrency conflict detected: global={ConcurrencyControlOrchestrator._global_invocation_time}, local={self._local_invocation_time}")
        return conflict

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

    def _add_hint_to_history(self, hint_text: str, slide_route: str | None = None) -> None:
        """
        Add a hint usage entry to the global hint history.
        
        Args:
            hint_text: The text content of the hint
            slide_route: The current slide route when the hint was given
        """
        try:
            current_time = time.time()
            timestamp = datetime.now().isoformat()
            
            hint_entry = {
                "text": hint_text,
                "timestamp": timestamp,
                "time": current_time,
                "slide": slide_route or "[Unknown]"
            }
            
            with self._hint_history_lock:
                self._hint_usage_history.append(hint_entry)
                # Keep only the last 50 hints to prevent memory issues
                if len(self._hint_usage_history) > 50:
                    self._hint_usage_history = self._hint_usage_history[-50:]
            
            logger.debug(f"Added hint to history: slide={slide_route}, text_length={len(hint_text)}")
            
        except Exception as e:
            logger.error(f"Error adding hint to history: {e}")

    def _get_hint_usage_context(self) -> str:
        """
        Generate a formatted hint usage history for the system prompt.
        
        Returns:
            str: Formatted hint usage history (last 10 hints)
        """
        try:
            with self._hint_history_lock:
                if not self._hint_usage_history:
                    return "HINT USAGE HISTORY: No hints have been provided yet."
                
                # Get the last 10 hints
                recent_hints = self._hint_usage_history[-10:]
                
                context_parts = ["HINT USAGE HISTORY:"]
                context_parts.append(f"Total hints provided: {len(self._hint_usage_history)}")
                context_parts.append("Recent hints (most recent first):")
                
                for hint in reversed(recent_hints):
                    timestamp = hint.get("timestamp", "Unknown time")
                    slide = hint.get("slide", "[Unknown]")
                    text = hint.get("text", "")
                    
                    # Truncate long hint text for readability
                    display_text = text[:100] + "..." if len(text) > 100 else text
                    context_parts.append(f"  - {timestamp} | Slide: {slide} | Hint: {display_text}")
                
                return "\n".join(context_parts)
                
        except Exception as e:
            logger.error(f"Error generating hint usage context: {e}")
            return "HINT USAGE HISTORY: Error retrieving hint history."

    def _load_transcription_content(self) -> str:
        """
        Load and format transcription content from a JSON lines file.
        
        Returns:
            str: Formatted transcription content with header, or empty string if no file or error
        """
        if not self.transcription_file_path:
            logger.debug("No transcription file path configured")
            return ""
        
        try:
            import os
            if not os.path.exists(self.transcription_file_path):
                logger.debug(f"Transcription file not found: {self.transcription_file_path}")
                return ""
            
            transcription_lines = []
            with open(self.transcription_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        message_text = entry.get('message_text', '').strip()
                        if not message_text:
                            continue
                        
                        # Extract slide information for context
                        slide_info = entry.get('slide_info', {})
                        current_slide = slide_info.get('current_slide', 'unknown-slide')
                        
                        # Extract elapsed time information
                        elapsed_time = entry.get('elapsed_time', '')
                        
                        # Format the transcription entry with timing information
                        if current_slide and current_slide != '[Not set]':
                            if elapsed_time:
                                formatted_entry = f"[{elapsed_time}] [Slide: {current_slide}] Speaker said: \"{message_text}\""
                            else:
                                formatted_entry = f"[Slide: {current_slide}] Speaker said: \"{message_text}\""
                        else:
                            if elapsed_time:
                                formatted_entry = f"[{elapsed_time}] Speaker said: \"{message_text}\""
                            else:
                                formatted_entry = f"Speaker said: \"{message_text}\""
                        
                        transcription_lines.append(formatted_entry)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num} in {self.transcription_file_path}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num} in {self.transcription_file_path}: {e}")
                        continue
            
            if not transcription_lines:
                logger.debug(f"No valid transcription entries found in {self.transcription_file_path}")
                return ""
            
            # Format the complete transcription with header
            transcription_content = "This is a transcription of the talk that was given previously:\n\n"
            transcription_content += "\n".join(transcription_lines)
            
            logger.info(f"Loaded transcription with {len(transcription_lines)} entries from {self.transcription_file_path}")
            return transcription_content
            
        except Exception as e:
            logger.error(f"Error loading transcription from {self.transcription_file_path}: {e}")
            return ""

    async def _get_slide_context_message(self) -> str:
        """
        Generate a formatted slide context message for the LLM.
        
        Returns:
            str: Formatted slide context information including current slide details and list of all slide IDs
        """
        try:
            current_route = await self.presentation_manager.get_current_route()
            all_routes = await self.presentation_manager.get_all_routes()
            
            if not all_routes:
                logger.debug("No slide routes available yet")
                return "PRESENTATION CONTEXT: No presentation slides are currently available."
            
            context_parts = ["PRESENTATION CONTEXT:"]
            
            # Current slide information
            if current_route:
                context_parts.append(f"Current slide: {current_route}")
            else:
                context_parts.append("Current slide: [Not set]")
            
            # All available slides
            context_parts.append(f"Available slides ({len(all_routes)} total):")
            for route in all_routes:
                context_parts.append(f"  - {route}")
            
            # Add detailed content only for the current slide
            if current_route:
                context_parts.append(f"\nCurrent slide content:")
                context_parts.append(f"\n--- SLIDE: {current_route} ---")
                content = await self.presentation_manager.get_route_content(current_route)
                if content:
                    context_parts.append(content)
                else:
                    context_parts.append("[No content available]")
                context_parts.append(f"--- END SLIDE: {current_route} ---")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error generating slide context: {e}")
            return "PRESENTATION CONTEXT: Error retrieving slide information."

    def _concatenate_consecutive_user_messages(self, messages: list[LLMMessage]) -> list[LLMMessage]:
        """
        Concatenate consecutive user messages into single messages.
        
        Args:
            messages: List of LLMMessage objects from conversation history
            
        Returns:
            list[LLMMessage]: Processed list with consecutive user messages concatenated
        """
        if not messages:
            return messages
            
        result = []
        current_user_messages = []
        
        for message in messages:
            if message.role == LLMRole.USER:
                # Collect consecutive user messages
                current_user_messages.append(message)
            else:
                # Non-user message encountered
                if current_user_messages:
                    # Concatenate all collected user messages
                    concatenated_message = self._create_concatenated_user_message(current_user_messages)
                    result.append(concatenated_message)
                    current_user_messages = []
                
                # Add the non-user message
                result.append(message)
        
        # Handle any remaining user messages at the end
        if current_user_messages:
            concatenated_message = self._create_concatenated_user_message(current_user_messages)
            result.append(concatenated_message)
        
        return result

    def _create_concatenated_user_message(self, user_messages: list[LLMMessage]) -> LLMMessage:
        """
        Create a single user message by concatenating the content of multiple user messages.
        
        Args:
            user_messages: List of consecutive user messages to concatenate
            
        Returns:
            LLMMessage: Single user message with concatenated content
        """
        if len(user_messages) == 1:
            return user_messages[0]
        
        # Extract text content from all messages and concatenate
        concatenated_texts = []
        for message in user_messages:
            for content in message.content:
                if content.type == LLMMessageContentType.TEXT and content.text:
                    concatenated_texts.append(content.text.strip())
        
        # Join with newlines to preserve message boundaries
        combined_text = "\n\n".join(concatenated_texts)
        
        # Create new user message with concatenated content
        return LLMMessage.user(combined_text)

    async def handle_text(self, text: str) -> None:
        """
        Process a user text message with concurrency control.
        
        This method:
        1. Sets the current time in both global and local variables
        2. Initializes a conversation with the system prompt and user message
        3. Retrieves available tools from the tool provider
        4. Iteratively generates responses and executes tools as needed
        5. After each LLM interaction, checks for concurrency conflicts
        6. If conflict detected, stops execution and sends empty response
        7. Otherwise, sends the final response back to the user
        
        Args:
            text: The user's input text message
        """
        # Set invocation times at the start
        self._update_invocation_times()
        
        # Initialize conversation with system prompt and concatenate consecutive user messages
        raw_conversation = [m for m in await self.history.get_history()]
        conversation = self._concatenate_consecutive_user_messages(raw_conversation)
        if self.system_prompt:
            conversation.insert(0, LLMMessage.system(self.system_prompt))
        
        # Add transcription content as first user message after system prompt (only once per conversation)
        transcription_added = False
        transcription_content = None
        if not self._transcription_loaded:
            transcription_content = self._load_transcription_content()
        if transcription_content:
            insert_position = 1 if self.system_prompt else 0
            conversation.insert(insert_position, LLMMessage.user(transcription_content))
            logger.debug("Added transcription content to conversation")
            transcription_added = True
            self._transcription_loaded = True
        
        # Add slide context after transcription (if present) or after system prompt
        slide_context = await self._get_slide_context_message()
        if self.system_prompt:
            insert_position = 2 if transcription_added else 1
        else:
            insert_position = 1 if transcription_added else 0
        conversation.insert(insert_position, LLMMessage.system(slide_context))
        logger.debug("Added slide context to conversation")
        
        # Add elapsed time information after slide context
        elapsed_time = self._get_elapsed_time_formatted()
        elapsed_time_context = f"CURRENT SESSION ELAPSED TIME: {elapsed_time} (time since this session started)"
        if self.system_prompt:
            insert_position = 3 if transcription_added else 2
        else:
            insert_position = 2 if transcription_added else 1
        conversation.insert(insert_position, LLMMessage.system(elapsed_time_context))
        logger.debug("Added elapsed time context to conversation")
        
        # Add hint usage history after elapsed time context
        hint_context = self._get_hint_usage_context()
        if self.system_prompt:
            insert_position = 4 if transcription_added else 3
        else:
            insert_position = 3 if transcription_added else 2
        conversation.insert(insert_position, LLMMessage.system(hint_context))
        logger.debug("Added hint usage context to conversation")
        
        # Add user message
        conversation.append(LLMMessage.user(text))
        
        # Get available tools
        tools = await self.tool_provider.list_tools()
        
        thoughts = 0
        
        while thoughts < self.max_thoughts:
            thoughts += 1
            
            # If max thoughts reached, disable tools
            if thoughts == self.max_thoughts:
                conversation.append(LLMMessage.system("Maximum tool usage reached. Tools Unavailable"))
            
            # Generate response
            options = LLMOptions(
                temperature=0.0,
                functions=tools if thoughts < self.max_thoughts else None
            )
            
            llm_response = await self.llm.generate(conversation, options)
            
            # Check for concurrency conflict after LLM interaction
            if self._check_concurrency_conflict():
                logger.info("Concurrency conflict detected after LLM interaction. Stopping execution.")
                await self.response.respond_text("")
                return
            
            # Add assistant response to conversation
            assistant_message = LLMMessage(
                role=LLMRole.FUNCTION if llm_response.tool_calls else LLMRole.ASSISTANT,
                content=[LLMMessageContent(
                    type=LLMMessageContentType.TEXT,
                    text=llm_response.content
                )],
                tool_calls=llm_response.tool_calls
            )
            conversation.append(assistant_message)
            
            # Check if tool was called and we haven't reached max thoughts
            if thoughts < self.max_thoughts and llm_response.tool_calls and len(llm_response.tool_calls) > 0:
                # Execute all tools and collect results
                tool_results = []
                
                for tool_call in llm_response.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments
                    
                    try:
                        tool_result = await self.tool_provider.execute_tool(tool_name, tool_args)
                        
                        # Track hint tool usage
                        if tool_name == "hint" and tool_result.success:
                            try:
                                # Extract hint text from tool arguments
                                hint_text = ""
                                if isinstance(tool_args, dict):
                                    hint_text = tool_args.get("text", "") or tool_args.get("hint", "") or tool_args.get("message", "")
                                elif isinstance(tool_args, str):
                                    hint_text = tool_args
                                
                                if hint_text:
                                    # Get current slide route
                                    current_slide = None
                                    try:
                                        current_slide = await self.presentation_manager.get_current_route()
                                    except Exception as e:
                                        logger.warning(f"Could not get current slide for hint tracking: {e}")
                                    
                                    # Add to hint history
                                    self._add_hint_to_history(hint_text, current_slide)
                                    logger.info(f"Tracked hint usage on slide '{current_slide}': {len(hint_text)} characters")
                                
                            except Exception as e:
                                logger.error(f"Error tracking hint usage: {e}")
                        
                        # Check for concurrency conflict after each tool execution
                        if self._check_concurrency_conflict():
                            logger.info("Concurrency conflict detected after tool execution. Stopping execution.")
                            await self.response.respond_text("")
                            return
                        
                        if tool_result.success:
                            tool_results.append({
                                "id": tool_call.id,
                                "name": tool_name,
                                "result": json.dumps(tool_result.result, default=repr)
                            })
                        else:
                            # Tool execution failed
                            tool_results.append({
                                "id": tool_call.id,
                                "name": tool_name,
                                "error": f"Error: {tool_result.error}"
                            })
                    except Exception as e:
                        # Handle any exceptions during tool execution
                        tool_results.append({
                            "id": tool_call.id,
                            "name": tool_name,
                            "error": f"Error: {str(e)}"
                        })

                conversation.append(LLMMessage(
                    role=LLMRole.FUNCTION,                        
                    tool_results=[
                        LLMFunctionResult(
                            id=tool_result.get("id"),
                            name=tool_result.get("name"),
                            content=tool_result.get("result", tool_result.get("error"))
                        ) for tool_result in tool_results
                    ]
                ))
                    
            else:
                # No tool call or max thoughts reached, end the conversation
                break
        
        # Final concurrency check before sending response
        if self._check_concurrency_conflict():
            logger.info("Concurrency conflict detected before final response. Stopping execution.")
            await self.response.respond_text("")
            return
        
        # Only say things with the say tool.
        await self.response.respond_text("")