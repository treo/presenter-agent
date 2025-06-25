import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.presentation_tool_provider import PresentationToolProvider
from modules.presentation_websocket_manager import PresentationWebSocketManager


@pytest.fixture
def mock_presentation_manager():
    """Create a mock presentation manager for testing"""
    manager = MagicMock(spec=PresentationWebSocketManager)
    manager.get_all_routes = AsyncMock(return_value=["/00-cover", "/01-intro", "/02-content"])
    manager.get_current_route = AsyncMock(return_value="/00-cover")
    manager.goto_route = AsyncMock()
    manager.send_hint = AsyncMock()
    manager.websocket = MagicMock()  # Mock websocket connection
    return manager


@pytest.fixture
def mock_response():
    """Create a mock response protocol for testing"""
    response = MagicMock()
    response.respond_text = AsyncMock()
    return response


@pytest.fixture
def tool_provider(mock_presentation_manager, mock_response):
    """Create a presentation tool provider for testing"""
    return PresentationToolProvider(mock_presentation_manager, mock_response)


# Test data fixtures for parametrized tests
@pytest.fixture
def missing_parameter_test_data():
    """Test data for missing parameter tests"""
    return [
        ("goto_slide", "route"),
        ("say", "text"),
        ("hint", "text"),
    ]


@pytest.fixture
def invalid_parameter_type_test_data():
    """Test data for invalid parameter type tests"""
    return [
        ("goto_slide", "route", 123),
        ("say", "text", 123),
        ("hint", "text", 123),
    ]


@pytest.fixture
def websocket_connection_test_data():
    """Test data for WebSocket connection tests"""
    return [
        ("goto_slide", {"route": "/01-intro"}),
        ("hint", {"text": "This is a helpful hint"}),
        ("next_slide", {}),
        ("previous_slide", {}),
    ]


@pytest.fixture
def exception_handling_test_data():
    """Test data for exception handling tests"""
    return [
        ("goto_slide", {"route": "/01-intro"}, "goto_route", Exception("Network error"), "Failed to navigate to slide /01-intro: Network error"),
        ("say", {"text": "Hello, world!"}, "respond_text", Exception("Response error"), "Failed to say text: Response error"),
        ("hint", {"text": "This is a helpful hint"}, "send_hint", Exception("WebSocket error"), "Failed to send hint: WebSocket error"),
        ("next_slide", {}, "goto_route", Exception("Navigation error"), "Failed to navigate to next slide: Navigation error"),
        ("previous_slide", {}, "goto_route", Exception("Navigation error"), "Failed to navigate to previous slide: Navigation error"),
        ("get_all_slide_details", {}, "get_all_slide_contents", Exception("Database error"), "Failed to retrieve slide details: Database error"),
    ]


# Helper functions for common test scenarios
async def setup_navigation_mocks(mock_presentation_manager, current_route, all_routes):
    """Helper to setup navigation-related mocks"""
    mock_presentation_manager.get_current_route = AsyncMock(return_value=current_route)
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=all_routes)


@pytest.mark.asyncio
async def test_list_tools(tool_provider):
    """Test that list_tools returns the expected tools"""
    tools = await tool_provider.list_tools()
    
    assert len(tools) == 6
    
    # Test goto_slide tool
    goto_slide_tool = next(tool for tool in tools if tool.name == "goto_slide")
    assert goto_slide_tool.description == "Navigate to a specific slide/route in the presentation"
    assert "route" in goto_slide_tool.parameters
    assert goto_slide_tool.parameters["route"].required is True
    assert goto_slide_tool.parameters["route"].type == "string"
    
    # Test next_slide tool
    next_slide_tool = next(tool for tool in tools if tool.name == "next_slide")
    assert next_slide_tool.description == "Navigate to the next slide in the presentation sequence"
    assert len(next_slide_tool.parameters) == 0  # No parameters required
    
    # Test previous_slide tool
    previous_slide_tool = next(tool for tool in tools if tool.name == "previous_slide")
    assert previous_slide_tool.description == "Navigate to the previous slide in the presentation sequence"
    assert len(previous_slide_tool.parameters) == 0  # No parameters required
    
    # Test say tool
    say_tool = next(tool for tool in tools if tool.name == "say")
    assert say_tool.description == "Say something out loud. Only use this tool if the agent has been spoken to directly."
    assert "text" in say_tool.parameters
    assert say_tool.parameters["text"].required is True
    assert say_tool.parameters["text"].type == "string"
    
    # Test hint tool
    hint_tool = next(tool for tool in tools if tool.name == "hint")
    assert hint_tool.description == "Provide a hint to the user about content they should discuss"
    assert "text" in hint_tool.parameters
    assert hint_tool.parameters["text"].required is True
    assert hint_tool.parameters["text"].type == "string"
    
    # Test get_all_slide_details tool
    get_all_slide_details_tool = next(tool for tool in tools if tool.name == "get_all_slide_details")
    assert get_all_slide_details_tool.description == "Retrieve the content/details of all slides in the presentation"
    assert len(get_all_slide_details_tool.parameters) == 0  # No parameters required


# Parametrized tests for repetitive patterns
@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,param_name", [
    ("goto_slide", "route"),
    ("say", "text"),
    ("hint", "text"),
])
async def test_missing_parameter(tool_provider, tool_name, param_name):
    """Test tools with missing required parameters"""
    parameters = {}
    
    result = await tool_provider.execute_tool(tool_name, parameters)
    
    assert result.success is False
    assert f"Missing required parameter: {param_name}" in result.error


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,param_name,invalid_value", [
    ("goto_slide", "route", 123),
    ("say", "text", 123),
    ("hint", "text", 123),
])
async def test_invalid_parameter_type(tool_provider, tool_name, param_name, invalid_value):
    """Test tools with invalid parameter types"""
    parameters = {param_name: invalid_value}
    
    result = await tool_provider.execute_tool(tool_name, parameters)
    
    assert result.success is False
    assert f"Parameter '{param_name}' must be a str" in result.error


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,parameters", [
    ("goto_slide", {"route": "/01-intro"}),
    ("hint", {"text": "This is a helpful hint"}),
    ("next_slide", {}),
    ("previous_slide", {}),
])
async def test_no_websocket_connection(tool_provider, mock_presentation_manager, tool_name, parameters):
    """Test tools when websocket is not connected"""
    mock_presentation_manager.websocket = None
    
    # Setup additional mocks for navigation tools
    if tool_name in ["next_slide", "previous_slide"]:
        await setup_navigation_mocks(mock_presentation_manager, "/00-cover", ["/00-cover", "/02-sci-fi-inspiration"])
    
    result = await tool_provider.execute_tool(tool_name, parameters)
    
    assert result.success is False
    assert "WebSocket not connected" in result.error


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,parameters,mock_method,exception,expected_error", [
    ("goto_slide", {"route": "/01-intro"}, "goto_route", Exception("Network error"), "Failed to navigate to slide /01-intro: Network error"),
    ("say", {"text": "Hello, world!"}, "respond_text", Exception("Response error"), "Failed to say text: Response error"),
    ("hint", {"text": "This is a helpful hint"}, "send_hint", Exception("WebSocket error"), "Failed to send hint: WebSocket error"),
    ("next_slide", {}, "goto_route", Exception("Navigation error"), "Failed to navigate to next slide: Navigation error"),
    ("previous_slide", {}, "goto_route", Exception("Navigation error"), "Failed to navigate to previous slide: Navigation error"),
    ("get_all_slide_details", {}, "get_all_slide_contents", Exception("Database error"), "Failed to retrieve slide details: Database error"),
])
async def test_exception_handling(tool_provider, mock_presentation_manager, mock_response, tool_name, parameters, mock_method, exception, expected_error):
    """Test exception handling for all tools"""
    # Setup navigation mocks for navigation tools
    if tool_name == "next_slide":
        await setup_navigation_mocks(mock_presentation_manager, "/00-cover", ["/00-cover", "/02-sci-fi-inspiration"])
    elif tool_name == "previous_slide":
        # For previous_slide exception test, set current route to second slide so navigation is attempted
        await setup_navigation_mocks(mock_presentation_manager, "/02-sci-fi-inspiration", ["/00-cover", "/02-sci-fi-inspiration"])
    
    # Setup the exception on the appropriate mock object
    if mock_method == "respond_text":
        getattr(mock_response, mock_method).side_effect = exception
    else:
        getattr(mock_presentation_manager, mock_method).side_effect = exception
    
    result = await tool_provider.execute_tool(tool_name, parameters)
    
    assert result.success is False
    assert expected_error in result.error


# Individual tool success tests
@pytest.mark.asyncio
async def test_execute_goto_slide_success(tool_provider, mock_presentation_manager):
    """Test successful execution of goto_slide tool"""
    parameters = {"route": "/01-intro"}
    
    result = await tool_provider.execute_tool("goto_slide", parameters)
    
    assert result.success is True
    assert "Successfully navigated to slide: /01-intro" in result.result
    mock_presentation_manager.goto_route.assert_called_once_with("/01-intro")


@pytest.mark.asyncio
async def test_execute_goto_slide_invalid_route(tool_provider, mock_presentation_manager):
    """Test goto_slide with invalid route"""
    parameters = {"route": "/invalid-route"}
    
    result = await tool_provider.execute_tool("goto_slide", parameters)
    
    assert result.success is False
    assert "Route '/invalid-route' not found" in result.error
    mock_presentation_manager.goto_route.assert_not_called()


@pytest.mark.asyncio
async def test_execute_goto_slide_no_routes_available(tool_provider, mock_presentation_manager):
    """Test goto_slide when no routes are available"""
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=[])
    parameters = {"route": "/01-intro"}
    
    result = await tool_provider.execute_tool("goto_slide", parameters)
    
    assert result.success is False
    assert "No routes available" in result.error


@pytest.mark.asyncio
async def test_execute_say_success(tool_provider, mock_response):
    """Test successful execution of say tool"""
    parameters = {"text": "Hello, world!"}
    
    result = await tool_provider.execute_tool("say", parameters)
    
    assert result.success is True
    assert "Successfully said: Hello, world!" in result.result
    mock_response.respond_text.assert_called_once_with("Hello, world!")


@pytest.mark.asyncio
async def test_execute_hint_success(tool_provider, mock_presentation_manager):
    """Test successful execution of hint tool"""
    parameters = {"text": "This is a helpful hint"}
    
    result = await tool_provider.execute_tool("hint", parameters)
    
    assert result.success is True
    assert "Successfully sent hint: This is a helpful hint" in result.result
    mock_presentation_manager.send_hint.assert_called_once_with("This is a helpful hint")


@pytest.mark.asyncio
async def test_execute_next_slide_success(tool_provider, mock_presentation_manager):
    """Test successful execution of next_slide tool"""
    # Setup mock to simulate being on first slide
    await setup_navigation_mocks(mock_presentation_manager, "/00-cover", ["/00-cover", "/02-sci-fi-inspiration", "/03-image-slide"])
    
    result = await tool_provider.execute_tool("next_slide", {})
    
    assert result.success is True
    assert "Successfully navigated to next slide: /02-sci-fi-inspiration" in result.result
    mock_presentation_manager.goto_route.assert_called_once_with("/02-sci-fi-inspiration")


@pytest.mark.asyncio
async def test_execute_next_slide_at_last_slide(tool_provider, mock_presentation_manager):
    """Test next_slide when already at the last slide"""
    # Setup mock to simulate being on last slide
    await setup_navigation_mocks(mock_presentation_manager, "/03-image-slide", ["/00-cover", "/02-sci-fi-inspiration", "/03-image-slide"])
    
    result = await tool_provider.execute_tool("next_slide", {})
    
    assert result.success is False
    assert "Already at the last slide" in result.error
    mock_presentation_manager.goto_route.assert_not_called()


@pytest.mark.asyncio
async def test_execute_next_slide_no_routes(tool_provider, mock_presentation_manager):
    """Test next_slide when no routes are available"""
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=[])
    
    result = await tool_provider.execute_tool("next_slide", {})
    
    assert result.success is False
    assert "No routes available" in result.error


@pytest.mark.asyncio
async def test_execute_next_slide_no_current_route(tool_provider, mock_presentation_manager):
    """Test next_slide when current route is unknown"""
    await setup_navigation_mocks(mock_presentation_manager, None, ["/00-cover", "/02-sci-fi-inspiration"])
    
    result = await tool_provider.execute_tool("next_slide", {})
    
    assert result.success is False
    assert "Current route is unknown" in result.error


@pytest.mark.asyncio
async def test_execute_next_slide_current_route_not_found(tool_provider, mock_presentation_manager):
    """Test next_slide when current route is not in available routes"""
    await setup_navigation_mocks(mock_presentation_manager, "/unknown-route", ["/00-cover", "/02-sci-fi-inspiration"])
    
    result = await tool_provider.execute_tool("next_slide", {})
    
    assert result.success is False
    assert "Current route '/unknown-route' not found in available routes" in result.error


@pytest.mark.asyncio
async def test_execute_previous_slide_success(tool_provider, mock_presentation_manager):
    """Test successful execution of previous_slide tool"""
    # Setup mock to simulate being on second slide
    await setup_navigation_mocks(mock_presentation_manager, "/02-sci-fi-inspiration", ["/00-cover", "/02-sci-fi-inspiration", "/03-image-slide"])
    
    result = await tool_provider.execute_tool("previous_slide", {})
    
    assert result.success is True
    assert "Successfully navigated to previous slide: /00-cover" in result.result
    mock_presentation_manager.goto_route.assert_called_once_with("/00-cover")


@pytest.mark.asyncio
async def test_execute_previous_slide_at_first_slide(tool_provider, mock_presentation_manager):
    """Test previous_slide when already at the first slide"""
    # Setup mock to simulate being on first slide
    await setup_navigation_mocks(mock_presentation_manager, "/00-cover", ["/00-cover", "/02-sci-fi-inspiration", "/03-image-slide"])
    
    result = await tool_provider.execute_tool("previous_slide", {})
    
    assert result.success is False
    assert "Already at the first slide" in result.error
    mock_presentation_manager.goto_route.assert_not_called()


@pytest.mark.asyncio
async def test_execute_previous_slide_no_routes(tool_provider, mock_presentation_manager):
    """Test previous_slide when no routes are available"""
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=[])
    
    result = await tool_provider.execute_tool("previous_slide", {})
    
    assert result.success is False
    assert "No routes available" in result.error


@pytest.mark.asyncio
async def test_execute_previous_slide_no_current_route(tool_provider, mock_presentation_manager):
    """Test previous_slide when current route is unknown"""
    await setup_navigation_mocks(mock_presentation_manager, None, ["/00-cover", "/02-sci-fi-inspiration"])
    
    result = await tool_provider.execute_tool("previous_slide", {})
    
    assert result.success is False
    assert "Current route is unknown" in result.error


@pytest.mark.asyncio
async def test_execute_previous_slide_current_route_not_found(tool_provider, mock_presentation_manager):
    """Test previous_slide when current route is not in available routes"""
    await setup_navigation_mocks(mock_presentation_manager, "/unknown-route", ["/00-cover", "/02-sci-fi-inspiration"])
    
    result = await tool_provider.execute_tool("previous_slide", {})
    
    assert result.success is False
    assert "Current route '/unknown-route' not found in available routes" in result.error


@pytest.mark.asyncio
async def test_execute_get_all_slide_details_success(tool_provider, mock_presentation_manager):
    """Test successful execution of get_all_slide_details tool"""
    expected_slide_contents = {
        "/00-cover": "<h1>Cover Slide</h1>",
        "/01-intro": "<h1>Introduction</h1><p>Welcome to the presentation</p>",
        "/02-content": "<h1>Content</h1><p>Main content here</p>"
    }
    mock_presentation_manager.get_all_slide_contents = AsyncMock(return_value=expected_slide_contents)
    
    result = await tool_provider.execute_tool("get_all_slide_details", {})
    
    assert result.success is True
    assert result.result == expected_slide_contents
    mock_presentation_manager.get_all_slide_contents.assert_called_once()


@pytest.mark.asyncio
async def test_execute_get_all_slide_details_no_slides(tool_provider, mock_presentation_manager):
    """Test get_all_slide_details when no slides are available"""
    mock_presentation_manager.get_all_slide_contents = AsyncMock(return_value={})
    
    result = await tool_provider.execute_tool("get_all_slide_details", {})
    
    assert result.success is False
    assert "No slide contents available" in result.error


@pytest.mark.asyncio
async def test_execute_get_all_slide_details_none_returned(tool_provider, mock_presentation_manager):
    """Test get_all_slide_details when None is returned"""
    mock_presentation_manager.get_all_slide_contents = AsyncMock(return_value=None)
    
    result = await tool_provider.execute_tool("get_all_slide_details", {})
    
    assert result.success is False
    assert "No slide contents available" in result.error


@pytest.mark.asyncio
async def test_execute_unknown_tool(tool_provider):
    """Test execution of unknown tool"""
    result = await tool_provider.execute_tool("unknown_tool", {})
    
    assert result.success is False
    assert "Unknown tool: unknown_tool" in result.error