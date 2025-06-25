import time
import logging
from typing import Any, Dict

from xaibo.core.protocols import TextMessageHandlerProtocol, ResponseProtocol, LLMProtocol, ToolProviderProtocol, \
    ConversationHistoryProtocol
from xaibo.core.models.llm import LLMMessage, LLMOptions, LLMRole, LLMFunctionResult, LLMMessageContentType, LLMMessageContent
from .presentation_websocket_manager import PresentationWebSocketManager

import json

logger = logging.getLogger("concurrency-control-orchestrator")


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
        """
        self.config: Dict[str, Any] = config or {}
        self.system_prompt = self.config.get('system_prompt', '')
        self.max_thoughts = self.config.get('max_thoughts', 10)
        self.response: ResponseProtocol = response
        self.llm: LLMProtocol = llm
        self.tool_provider: ToolProviderProtocol = tool_provider
        self.history = history
        self.presentation_manager = presentation_manager
        
        # Local instance variable to track this invocation's time
        self._local_invocation_time: float = 0.0

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
        
        # Add slide context right after system prompt
        slide_context = await self._get_slide_context_message()
        if self.system_prompt:
            conversation.insert(1, LLMMessage.system(slide_context))
        else:
            conversation.insert(0, LLMMessage.system(slide_context))
        logger.debug("Added slide context to conversation")
        
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