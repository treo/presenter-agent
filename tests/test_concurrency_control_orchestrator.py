import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.concurrency_control_orchestrator import ConcurrencyControlOrchestrator
from modules.presentation_websocket_manager import PresentationWebSocketManager


@pytest.fixture
def mock_response():
    """Create a mock response protocol for testing"""
    response = MagicMock()
    response.respond_text = AsyncMock()
    return response


@pytest.fixture
def mock_llm():
    """Create a mock LLM protocol for testing"""
    llm = MagicMock()
    
    # Create a mock LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Test response from LLM"
    mock_llm_response.tool_calls = []
    
    llm.generate = AsyncMock(return_value=mock_llm_response)
    return llm


@pytest.fixture
def mock_tool_provider():
    """Create a mock tool provider for testing"""
    tool_provider = MagicMock()
    tool_provider.list_tools = AsyncMock(return_value=[])
    tool_provider.execute_tool = AsyncMock()
    return tool_provider


@pytest.fixture
def mock_history():
    """Create a mock conversation history for testing"""
    history = MagicMock()
    history.get_history = AsyncMock(return_value=[])
    return history


@pytest.fixture
def mock_presentation_manager():
    """Create a mock presentation manager for testing"""
    presentation_manager = MagicMock()
    presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route", "/another-route"])
    presentation_manager.get_route_content = AsyncMock(return_value="Test slide content")
    return presentation_manager


@pytest.fixture
def orchestrator(mock_response, mock_llm, mock_tool_provider, mock_history, mock_presentation_manager):
    """Create a concurrency control orchestrator for testing"""
    return ConcurrencyControlOrchestrator(
        response=mock_response,
        llm=mock_llm,
        tool_provider=mock_tool_provider,
        history=mock_history,
        presentation_manager=mock_presentation_manager
    )


@pytest.mark.asyncio
async def test_provides_protocol():
    """Test that the orchestrator provides the correct protocol"""
    protocols = ConcurrencyControlOrchestrator.provides()
    assert len(protocols) == 1
    # Import the protocol to check
    from xaibo.core.protocols import TextMessageHandlerProtocol
    assert TextMessageHandlerProtocol in protocols


@pytest.mark.asyncio
async def test_normal_execution_no_conflict(orchestrator, mock_response, mock_llm):
    """Test normal execution without concurrency conflicts"""
    await orchestrator.handle_text("Hello, world!")
    
    # Verify LLM was called
    mock_llm.generate.assert_called_once()
    
    # Verify response was sent (orchestrator always sends empty string - communication happens via tools)
    mock_response.respond_text.assert_called_once_with("")


@pytest.mark.asyncio
async def test_invocation_time_updates():
    """Test that invocation times are properly updated"""
    # Get initial global time
    initial_global_time = ConcurrencyControlOrchestrator._global_invocation_time
    
    # Create mock presentation manager
    mock_presentation_manager = MagicMock()
    mock_presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager.get_route_content = AsyncMock(return_value="Test content")
    
    # Create orchestrator and update times
    orchestrator = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager
    )
    
    orchestrator._update_invocation_times()
    
    # Verify times were updated
    assert ConcurrencyControlOrchestrator._global_invocation_time > initial_global_time
    assert orchestrator._local_invocation_time == ConcurrencyControlOrchestrator._global_invocation_time


@pytest.mark.asyncio
async def test_concurrency_conflict_detection():
    """Test that concurrency conflicts are properly detected"""
    # Create mock presentation manager
    mock_presentation_manager = MagicMock()
    mock_presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager.get_route_content = AsyncMock(return_value="Test content")
    
    orchestrator = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager
    )
    
    # Set initial times
    orchestrator._update_invocation_times()
    
    # Simulate another invocation by updating global time
    time.sleep(0.001)  # Small delay to ensure different timestamps
    ConcurrencyControlOrchestrator._global_invocation_time = time.time()
    
    # Check for conflict
    conflict_detected = orchestrator._check_concurrency_conflict()
    assert conflict_detected is True


@pytest.mark.asyncio
async def test_no_concurrency_conflict_detection():
    """Test that no conflict is detected when times are equal"""
    # Create mock presentation manager
    mock_presentation_manager = MagicMock()
    mock_presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager.get_route_content = AsyncMock(return_value="Test content")
    
    orchestrator = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager
    )
    
    # Set times to be equal
    orchestrator._update_invocation_times()
    
    # Check for conflict immediately (should be no conflict)
    conflict_detected = orchestrator._check_concurrency_conflict()
    assert conflict_detected is False


@pytest.mark.asyncio
async def test_concurrency_conflict_stops_execution(mock_response, mock_llm, mock_tool_provider, mock_history, mock_presentation_manager):
    """Test that execution stops and empty response is sent when conflict is detected"""
    orchestrator = ConcurrencyControlOrchestrator(
        response=mock_response,
        llm=mock_llm,
        tool_provider=mock_tool_provider,
        history=mock_history,
        presentation_manager=mock_presentation_manager
    )
    
    # Mock LLM to simulate delay and allow conflict to be injected
    async def mock_generate_with_conflict(*args, **kwargs):
        # Simulate another invocation happening during LLM call
        ConcurrencyControlOrchestrator._global_invocation_time = time.time() + 1
        
        # Return normal response
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_response.tool_calls = []
        return mock_response
    
    mock_llm.generate = AsyncMock(side_effect=mock_generate_with_conflict)
    
    await orchestrator.handle_text("Hello, world!")
    
    # Verify empty response was sent due to conflict
    mock_response.respond_text.assert_called_once_with("")


@pytest.mark.asyncio
async def test_global_time_tracking_across_instances():
    """Test that global time is properly tracked across multiple instances"""
    # Create mock presentation managers
    mock_presentation_manager1 = MagicMock()
    mock_presentation_manager1.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager1.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager1.get_route_content = AsyncMock(return_value="Test content")
    
    mock_presentation_manager2 = MagicMock()
    mock_presentation_manager2.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager2.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager2.get_route_content = AsyncMock(return_value="Test content")
    
    # Create first orchestrator and update time
    orchestrator1 = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager1
    )
    orchestrator1._update_invocation_times()
    time1 = ConcurrencyControlOrchestrator._global_invocation_time
    
    # Small delay
    time.sleep(0.001)
    
    # Create second orchestrator and update time
    orchestrator2 = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager2
    )
    orchestrator2._update_invocation_times()
    time2 = ConcurrencyControlOrchestrator._global_invocation_time
    
    # Verify global time increased
    assert time2 > time1
    
    # Verify first orchestrator detects conflict
    conflict = orchestrator1._check_concurrency_conflict()
    assert conflict is True


@pytest.mark.asyncio
async def test_initialization_with_config():
    """Test orchestrator initialization with configuration"""
    config = {
        'system_prompt': 'You are a test assistant',
        'max_thoughts': 5
    }
    
    # Create mock presentation manager
    mock_presentation_manager = MagicMock()
    mock_presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager.get_route_content = AsyncMock(return_value="Test content")
    
    orchestrator = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager,
        config=config
    )
    
    assert orchestrator.system_prompt == 'You are a test assistant'
    assert orchestrator.max_thoughts == 5


@pytest.mark.asyncio
async def test_initialization_without_config():
    """Test orchestrator initialization without configuration"""
    # Create mock presentation manager
    mock_presentation_manager = MagicMock()
    mock_presentation_manager.get_current_route = AsyncMock(return_value="/test-route")
    mock_presentation_manager.get_all_routes = AsyncMock(return_value=["/test-route"])
    mock_presentation_manager.get_route_content = AsyncMock(return_value="Test content")
    
    orchestrator = ConcurrencyControlOrchestrator(
        response=MagicMock(),
        llm=MagicMock(),
        tool_provider=MagicMock(),
        history=MagicMock(),
        presentation_manager=mock_presentation_manager
    )
    
    assert orchestrator.system_prompt == ''
    assert orchestrator.max_thoughts == 10
    assert orchestrator.config == {}


@pytest.mark.asyncio
async def test_handle_text_with_system_prompt(mock_response, mock_llm, mock_tool_provider, mock_history, mock_presentation_manager):
    """Test handle_text with system prompt configuration"""
    config = {'system_prompt': 'You are a helpful assistant'}
    
    orchestrator = ConcurrencyControlOrchestrator(
        response=mock_response,
        llm=mock_llm,
        tool_provider=mock_tool_provider,
        history=mock_history,
        presentation_manager=mock_presentation_manager,
        config=config
    )
    
    await orchestrator.handle_text("Hello")
    
    # Verify LLM was called
    mock_llm.generate.assert_called_once()
    
    # Get the conversation passed to LLM
    call_args = mock_llm.generate.call_args[0][0]  # First positional argument
    
    # Verify system prompt was added
    assert len(call_args) >= 2  # At least system message and user message
    assert call_args[0].role.value == 'system'  # First message should be system
    assert 'helpful assistant' in call_args[0].content[0].text