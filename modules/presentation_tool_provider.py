import logging
from typing import Any, Dict, List

from xaibo.core.models.tools import Tool, ToolParameter, ToolResult
from xaibo.core.protocols.tools import ToolProviderProtocol
from xaibo.core.protocols import ResponseProtocol

from .presentation_websocket_manager import PresentationWebSocketManager

logger = logging.getLogger("presentation-tool-provider")


class PresentationToolProvider(ToolProviderProtocol):
    """Tool provider for presentation navigation functionality"""
    
    def __init__(self, presentation_manager: PresentationWebSocketManager, response: ResponseProtocol, config: Dict[str, Any] | None = None):
        """Initialize the presentation tool provider
        
        Args:
            presentation_manager: Instance of PresentationWebSocketManager for navigation
            response: Protocol for sending responses back to the user
            config: Optional configuration dictionary
        """
        self.presentation_manager = presentation_manager
        self.response = response
        self.config = config or {}
        
    async def list_tools(self) -> List[Tool]:
        """List all available presentation tools"""
        return [
            Tool(
                name="goto_slide",
                description="Navigate to a specific slide/route in the presentation",
                parameters={
                    "route": ToolParameter(
                        type="string",
                        description="The route/path of the slide to navigate to (e.g., '/00-cover', '/01-intro')",
                        required=True
                    )
                }
            ),
            Tool(
                name="next_slide",
                description="Navigate to the next slide in the presentation sequence",
                parameters={}
            ),
            Tool(
                name="previous_slide",
                description="Navigate to the previous slide in the presentation sequence",
                parameters={}
            ),
            Tool(
                name="say",
                description="Say something out loud. Only use this tool if the agent has been spoken to directly.",
                parameters={
                    "text": ToolParameter(
                        type="string",
                        description="The text to say out loud",
                        required=True
                    )
                }
            ),
            Tool(
                name="hint",
                description="Provide a hint to the user about content they should discuss",
                parameters={
                    "text": ToolParameter(
                        type="string",
                        description="The hint text to display",
                        required=True
                    )
                }
            ),
            Tool(
                name="get_all_slide_details",
                description="Retrieve the content/details of all slides in the presentation",
                parameters={}
            )
        ]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a presentation tool with the given parameters
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the tool execution
        """
        if tool_name == "goto_slide":
            return await self._execute_goto_slide(parameters)
        elif tool_name == "next_slide":
            return await self._execute_next_slide(parameters)
        elif tool_name == "previous_slide":
            return await self._execute_previous_slide(parameters)
        elif tool_name == "say":
            return await self._execute_say(parameters)
        elif tool_name == "hint":
            return await self._execute_hint(parameters)
        elif tool_name == "get_all_slide_details":
            return await self._execute_get_all_slide_details(parameters)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
    
    def _validate_required_parameter(self, parameters: Dict[str, Any], param_name: str, param_type: type) -> ToolResult | None:
        """Validate that a required parameter exists and has the correct type
        
        Args:
            parameters: Dictionary of parameters to validate
            param_name: Name of the required parameter
            param_type: Expected type of the parameter
            
        Returns:
            ToolResult with error if validation fails, None if validation passes
        """
        if param_name not in parameters:
            return ToolResult(
                success=False,
                error=f"Missing required parameter: {param_name}"
            )
        
        param_value = parameters[param_name]
        if not isinstance(param_value, param_type):
            type_name = param_type.__name__
            return ToolResult(
                success=False,
                error=f"Parameter '{param_name}' must be a {type_name}"
            )
        
        return None
    
    def _validate_websocket_connection(self) -> ToolResult | None:
        """Validate that WebSocket connection is available
        
        Returns:
            ToolResult with error if WebSocket not connected, None if connected
        """
        if not self.presentation_manager.websocket:
            return ToolResult(
                success=False,
                error="WebSocket not connected. Cannot navigate to slide."
            )
        return None
    
    async def _validate_routes_available(self) -> tuple[ToolResult | None, list[str]]:
        """Validate that routes are available and return them
        
        Returns:
            Tuple of (ToolResult with error if no routes available, list of available routes)
        """
        available_routes = await self.presentation_manager.get_all_routes()
        if not available_routes:
            return (ToolResult(
                success=False,
                error="No routes available. Presentation may not be connected."
            ), [])
        return (None, available_routes)
    
    def _handle_tool_exception(self, operation_name: str, exception: Exception) -> ToolResult:
        """Handle exceptions that occur during tool execution
        
        Args:
            operation_name: Name of the operation that failed
            exception: The exception that occurred
            
        Returns:
            ToolResult with standardized error message
        """
        logger.error(f"Error {operation_name}: {exception}")
        return ToolResult(
            success=False,
            error=f"Failed to {operation_name}: {str(exception)}"
        )
    
    def _create_success_result(self, message: str) -> ToolResult:
        """Create a standardized success result
        
        Args:
            message: Success message to include
            
        Returns:
            ToolResult indicating success
        """
        return ToolResult(
            success=True,
            result=message
        )
    
    async def _get_route_index_and_target(self, current_route: str, available_routes: list[str], direction: int) -> tuple[ToolResult | None, str]:
        """Get the current route index and calculate target route for navigation
        
        Args:
            current_route: Current route path
            available_routes: List of all available routes
            direction: Direction to navigate (1 for next, -1 for previous)
            
        Returns:
            Tuple of (ToolResult with error if navigation not possible, target route)
        """
        sorted_routes = sorted(available_routes)
        
        try:
            current_index = sorted_routes.index(current_route)
        except ValueError:
            return (ToolResult(
                success=False,
                error=f"Current route '{current_route}' not found in available routes."
            ), "")
        
        target_index = current_index + direction
        
        # Check bounds
        if direction > 0 and target_index >= len(sorted_routes):
            return (ToolResult(
                success=False,
                error="Already at the last slide. Cannot navigate to next slide."
            ), "")
        elif direction < 0 and target_index < 0:
            return (ToolResult(
                success=False,
                error="Already at the first slide. Cannot navigate to previous slide."
            ), "")
        
        return (None, sorted_routes[target_index])
    
    async def _execute_navigation(self, direction: int) -> ToolResult:
        """Execute navigation to next or previous slide
        
        Args:
            direction: Direction to navigate (1 for next, -1 for previous)
            
        Returns:
            Result of the navigation attempt
        """
        try:
            # Get current route and all available routes
            current_route = await self.presentation_manager.get_current_route()
            
            # Validate routes are available
            error_result, available_routes = await self._validate_routes_available()
            if error_result:
                return error_result
            
            if not current_route:
                direction_name = "next" if direction > 0 else "previous"
                return ToolResult(
                    success=False,
                    error=f"Current route is unknown. Cannot determine {direction_name} slide."
                )
            
            # Check WebSocket connection
            websocket_error = self._validate_websocket_connection()
            if websocket_error:
                direction_name = "next" if direction > 0 else "previous"
                return ToolResult(
                    success=False,
                    error=f"WebSocket not connected. Cannot navigate to {direction_name} slide."
                )
            
            # Get target route
            error_result, target_route = await self._get_route_index_and_target(current_route, available_routes, direction)
            if error_result:
                return error_result
            
            # Navigate to target slide
            direction_name = "next" if direction > 0 else "previous"
            logger.info(f"Navigating from '{current_route}' to {direction_name} slide '{target_route}'")
            await self.presentation_manager.goto_route(target_route)
            
            return self._create_success_result(f"Successfully navigated to {direction_name} slide: {target_route}")
            
        except Exception as e:
            direction_name = "next" if direction > 0 else "previous"
            return self._handle_tool_exception(f"navigate to {direction_name} slide", e)

    async def _execute_goto_slide(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the goto_slide tool
        
        Args:
            parameters: Tool parameters containing 'route'
            
        Returns:
            Result of the navigation attempt
        """
        # Validate required parameter
        validation_error = self._validate_required_parameter(parameters, "route", str)
        if validation_error:
            return validation_error
        
        route = parameters["route"]
        
        # Validate that routes are available
        error_result, available_routes = await self._validate_routes_available()
        if error_result:
            return error_result
        
        if route not in available_routes:
            return ToolResult(
                success=False,
                error=f"Route '{route}' not found. Available routes: {', '.join(available_routes)}"
            )
        
        # Check WebSocket connection
        websocket_error = self._validate_websocket_connection()
        if websocket_error:
            return websocket_error
        
        # Perform navigation
        try:
            current_route = await self.presentation_manager.get_current_route()
            logger.info(f"Navigating from '{current_route}' to '{route}'")
            
            await self.presentation_manager.goto_route(route)
            
            return self._create_success_result(f"Successfully navigated to slide: {route}")
        except Exception as e:
            return self._handle_tool_exception(f"navigate to slide {route}", e)
    
    async def _execute_next_slide(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the next_slide tool
        
        Args:
            parameters: Tool parameters (none required for this tool)
            
        Returns:
            Result of the navigation attempt
        """
        return await self._execute_navigation(1)
    
    async def _execute_previous_slide(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the previous_slide tool
        
        Args:
            parameters: Tool parameters (none required for this tool)
            
        Returns:
            Result of the navigation attempt
        """
        return await self._execute_navigation(-1)
    
    async def _execute_say(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the say tool
        
        Args:
            parameters: Tool parameters containing 'text'
            
        Returns:
            Result of the say operation
        """
        try:
            # Validate required parameter
            validation_error = self._validate_required_parameter(parameters, "text", str)
            if validation_error:
                return validation_error
            
            text = parameters["text"]
            
            # Send text to response protocol
            await self.response.respond_text(text)
            
            logger.info(f"Said: {text}")
            
            return self._create_success_result(f"Successfully said: {text}")
            
        except Exception as e:
            return self._handle_tool_exception("say text", e)
    
    async def _execute_hint(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the hint tool
        
        Args:
            parameters: Tool parameters containing 'text'
            
        Returns:
            Result of the hint operation
        """
        try:
            # Validate required parameter
            validation_error = self._validate_required_parameter(parameters, "text", str)
            if validation_error:
                return validation_error
            
            text = parameters["text"]
            
            # Check WebSocket connection
            websocket_error = self._validate_websocket_connection()
            if websocket_error:
                return ToolResult(
                    success=False,
                    error="WebSocket not connected. Cannot send hint."
                )
            
            # Send hint via presentation manager
            await self.presentation_manager.send_hint(text)
            
            logger.info(f"Sent hint: {text}")
            
            return self._create_success_result(f"Successfully sent hint: {text}")
            
        except Exception as e:
            return self._handle_tool_exception("send hint", e)
    
    async def _execute_get_all_slide_details(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the get_all_slide_details tool
        
        Args:
            parameters: Tool parameters (none required for this tool)
            
        Returns:
            Result containing all slide contents as a dictionary
        """
        try:
            # Get all slide contents from presentation manager
            slide_contents = await self.presentation_manager.get_all_slide_contents()
            
            if not slide_contents:
                return ToolResult(
                    success=False,
                    error="No slide contents available. Presentation may not be connected or no slides loaded."
                )
            
            logger.info(f"Retrieved details for {len(slide_contents)} slides")
            
            return ToolResult(
                success=True,
                result=slide_contents
            )
            
        except Exception as e:
            return self._handle_tool_exception("retrieve slide details", e)