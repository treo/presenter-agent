import asyncio
import json
import logging
import random
from pathlib import Path

from fastapi import WebSocket

logger = logging.getLogger("my-worker")


class PresentationWebSocketManager:
    """Manages WebSocket functionality for presentation navigation"""
    
    def __init__(self):
        self.routes = []
        self.route_data = []  # List of dictionaries with route and content
        self.current_route = None
        self.websocket = None
        
    async def handle_message(self, message_data: str):
        """Handle incoming WebSocket messages"""
        try:
            # Parse JSON message
            message = json.loads(message_data)
            
            # Handle connection message with routes
            if message.get("type") == "connection":
                routes = message.get("routes", [])
                current_route = message.get("currentRoute")
                
                # Store the routes
                self.routes = routes
                self.current_route = current_route
                
                # Load route file contents
                logger.info(f"Loading content for {len(routes)} routes...")
                self.route_data = await load_route_contents(routes)
                
                logger.info(f"Stored {len(routes)} routes from connection message")
                logger.info(f"Current route: {current_route}")
                logger.debug(f"Routes: {routes}")
                
                # Log summary of loaded content
                routes_with_content = sum(1 for route_info in self.route_data if route_info["content"] is not None)
                routes_without_content = len(self.route_data) - routes_with_content
                logger.info(f"Route content summary: {routes_with_content} files loaded, {routes_without_content} files failed")
                
            elif message.get("type") == "route_change":
                # Update current route when route changes
                new_route = message.get("currentRoute")
                if new_route:
                    self.current_route = new_route
                    logger.info(f"Route changed to: {new_route}")
                else:
                    logger.warning(f"Unexpected message contents: {message_data}")
                    
            elif message.get("type") == "heartbeat":
                # Handle heartbeat messages if needed
                logger.debug("Received heartbeat message")
                
            else:
                logger.info(f"Received message of type: {message.get('type', 'unknown')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            logger.error(f"Raw message: {message_data}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def get_current_route(self) -> str | None:
        """Returns the currently displayed route"""
        return self.current_route
    
    async def get_current_route_content(self) -> str | None:
        """Returns the content of the current route"""
        if not self.current_route:
            return None
            
        for route_info in self.route_data:
            if route_info["route"] == self.current_route:
                return route_info["content"]
        return None
    
    async def get_all_routes(self) -> list[str]:
        """Returns list of all available routes"""
        return self.routes.copy()
    
    async def get_route_content(self, route: str) -> str | None:
        """Returns content for a specific route"""
        for route_info in self.route_data:
            if route_info["route"] == route:
                return route_info["content"]
        return None
    
    async def get_all_slide_contents(self) -> dict[str, str | None]:
        """Returns a dictionary mapping slide routes to their content"""
        slide_contents = {}
        
        for route_info in self.route_data:
            route = route_info["route"]
            content = route_info["content"]
            slide_contents[route] = content
            
        return slide_contents
    
    async def goto_route(self, route: str):
        """Sends goto command to navigate to specified route"""
        if not self.websocket:
            logger.error("WebSocket not connected, cannot send goto command")
            return
            
        if route not in self.routes:
            logger.warning(f"Route {route} not in available routes")
            return
            
        goto_message = {
            "type": "goto",
            "route": route
        }
        
        try:
            await self.websocket.send_text(json.dumps(goto_message))
            logger.info(f"Sent goto command for route: {route}")
        except Exception as e:
            logger.error(f"Error sending goto command: {e}")
    
    async def send_hint(self, hint_text: str):
        """Sends hint message to the presentation UI"""
        if not self.websocket:
            logger.error("WebSocket not connected, cannot send hint")
            return
            
        hint_message = {
            "type": "hint",
            "text": hint_text
        }
        
        try:
            await self.websocket.send_text(json.dumps(hint_message))
            logger.info(f"Sent hint message: {hint_text}")
        except Exception as e:
            logger.error(f"Error sending hint message: {e}")
    
    async def set_websocket(self, websocket: WebSocket):
        """Set the WebSocket connection reference"""
        self.websocket = websocket
    
    async def clear_websocket(self):
        """Clear the WebSocket connection reference"""
        self.websocket = None


async def read_route_file_content(route: str) -> str | None:
    """
    Read the content of a route file.
    
    Args:
        route: Route path like '/00-cover'
    
    Returns:
        File content as string or None if file doesn't exist/can't be read
    """
    try:
        # Remove leading slash and construct file path
        route_name = route.lstrip('/')
        file_path = Path("ui/src/routes") / route_name / "+page.svelte"
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Route file does not exist: {file_path}")
            return None
            
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.debug(f"Successfully read route file: {file_path} ({len(content)} characters)")
        return content
        
    except PermissionError:
        logger.error(f"Permission denied reading route file: {file_path}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading route file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading route file {file_path}: {e}")
        return None


async def load_route_contents(routes: list[str]) -> list[dict]:
    """
    Load content for all routes.
    
    Args:
        routes: List of route paths
        
    Returns:
        List of dictionaries with route and content keys
    """
    route_data = []
    successful_reads = 0
    failed_reads = 0
    
    for route in routes:
        content = await read_route_file_content(route)
        
        route_info = {
            "route": route,
            "content": content
        }
        
        if content is not None:
            successful_reads += 1
            # Log content summary for debugging
            content_lines = len(content.splitlines())
            logger.debug(f"Route {route}: {len(content)} chars, {content_lines} lines")
        else:
            failed_reads += 1
            
        route_data.append(route_info)
    
    logger.info(f"Route file loading complete: {successful_reads} successful, {failed_reads} failed")
    
    return route_data


async def periodic_navigation_task(presentation_manager):
    """External navigation control - sends random navigation commands every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            
            # Get available routes from manager
            available_routes = await presentation_manager.get_all_routes()
            if available_routes:
                # Select a random route
                random_route = random.choice(available_routes)
                # Use manager to navigate
                await presentation_manager.goto_route(random_route)
                # Send hint message after navigation
                await presentation_manager.send_hint("Hello World! 👋")
            else:
                logger.debug("No routes available yet for navigation")
                
        except asyncio.CancelledError:
            logger.info("Periodic navigation task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic navigation task: {e}")
            break