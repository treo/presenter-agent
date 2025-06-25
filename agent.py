from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from pathlib import Path
import sys
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    Agent,
    AgentSession
)
from livekit.plugins import openai


load_dotenv(dotenv_path=".env.local")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)

from livekit.plugins import openai
from livekit.plugins import silero

from xaibo.integrations.livekit import XaiboAgentLoader
from modules.presentation_websocket_manager import PresentationWebSocketManager, periodic_navigation_task

# Create FastAPI app
app = FastAPI()

# Global manager instance
presentation_manager = PresentationWebSocketManager()

# Load agents from YAML configs with debug logging
loader = XaiboAgentLoader()
loader.load_agents_from_directory("./agents")
loader.enable_debug_logging()
loader.get_xaibo_instance().register_server_module('ws', presentation_manager)

# Get LLM for use in LiveKit VoiceAssistant
llm = loader.get_llm("example")

# Use in LiveKit agent
assistant = Agent(
        instructions="",
   vad=silero.VAD.load(),
   stt=openai.STT(),
   llm=llm,  # Xaibo agent as LLM
   tts=openai.TTS(),
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Set WebSocket reference in manager
    await presentation_manager.set_websocket(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            
            # Handle message through the manager
            await presentation_manager.handle_message(data)
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await presentation_manager.clear_websocket()
    
# Background task to run FastAPI server
fastapi_server_task = None

async def start_fastapi_server():
    """Start FastAPI server as a background task"""
    global fastapi_server_task
    if fastapi_server_task is None:
        logger.info("Starting FastAPI server on port 9002")
        config = uvicorn.Config(app, host="0.0.0.0", port=9002, log_level="info")
        server = uvicorn.Server(config)
        fastapi_server_task = asyncio.create_task(server.serve())
        logger.info("FastAPI server started as background task")

async def entrypoint(ctx: JobContext):
    # Start FastAPI server as background task
    await start_fastapi_server()
    
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession()

    await session.start(
        agent=assistant,
        room=ctx.room,
    )
    
    logger.info("agent started")


if __name__ == "__main__":

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
