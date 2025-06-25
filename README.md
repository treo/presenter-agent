# Presenter Agent

An AI-powered presentation assistant system that combines LiveKit real-time communication, the Xaibo agent framework, and a SvelteKit frontend to provide intelligent presentation monitoring and guidance.

## Overview

The Presenter Agent is a sophisticated AI system designed to help presenters deliver more effective talks by providing real-time monitoring, contextual hints, and voice interaction capabilities. The system analyzes presentation content, tracks coverage of key topics, and offers gentle guidance when important content might be missed.

### Key Features

- **Real-time Presentation Monitoring**: Continuously tracks presentation flow and content coverage
- **Contextual Hints**: Provides subtle reminders when key topics are missed before slide transitions
- **Voice Interaction**: Responds to "Computer..." queries for direct presenter assistance
- **Slide Navigation Control**: Intelligent navigation based on content coverage and timing
- **Transcript Analysis**: Leverages previous presentation iterations for improved guidance
- **Concurrency Management**: Handles multiple concurrent operations efficiently

## Architecture

The system consists of three main components:

1. **AI Agents** (Python/LiveKit):
   - **Presentation Assistant**: Monitors presentation flow and provides contextual guidance
   - **Transcriber**: Logs conversations and maintains presentation transcripts

2. **Backend Server** (FastAPI):
   - WebSocket server running on port 9002
   - Real-time communication between agents and frontend
   - Integration with LiveKit for voice processing

3. **Frontend** (SvelteKit):
   - Interactive presentation interface with 35 slides (00-cover to 34-questions)
   - Real-time slide navigation and content display
   - Modern UI built with TailwindCSS and TypeScript

## Prerequisites

- **Python 3.13+** (required for the agent framework)
- **Node.js** and **pnpm** (for frontend development)
- **LiveKit Server** instance (for real-time communication)
- **OpenAI API Key** (for GPT-4.1-mini, STT, and TTS services)

## Installation

### 1. Python Environment Setup

Clone the repository and set up the Python environment:

```bash
# Using pip
pip install -e .

# Or using uv (recommended)
uv sync
```

### 2. Frontend Setup

Install frontend dependencies:

```bash
cd ui
pnpm install
```

## Environment Configuration

Create a `.env.local` file in the project root with the following variables:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key

# Optional: Additional Xaibo Integrations
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
```

## Usage

### Running the Backend

Start the presentation assistant agent:

```bash
python agent.py
```

Or run the transcriber agent separately:

```bash
python transcriber.py
```

### Running the Frontend

Start the SvelteKit development server:

```bash
cd ui
pnpm dev
```

The presentation interface will be available at `http://localhost:5173`

### Interacting with the System

1. **Presentation Monitoring**: The system automatically monitors your presentation flow
2. **Voice Commands**: Address the system with "Computer..." for direct interaction
3. **Contextual Hints**: Receive gentle reminders about missed content before slide transitions
4. **Navigation**: Use the interface or voice commands to navigate between slides

## Project Structure

```
presenter-agent/
├── agents/                          # Agent configuration files
│   ├── presentation-assistant.yml   # Main presentation assistant config
│   └── transcriber.yml             # Transcriber agent config
├── modules/                         # Core system modules
│   ├── concurrency_control_orchestrator.py
│   ├── presentation_tool_provider.py
│   ├── presentation_websocket_manager.py
│   └── simple_message_logger.py
├── tests/                          # Test suite
├── tools/                          # Additional tools and utilities
├── transcription/                  # Transcript storage
│   └── talk.jsonl                 # Conversation logs
├── ui/                            # SvelteKit frontend
│   ├── src/routes/               # Presentation slides (00-cover to 34-questions)
│   ├── static/                   # Static assets and images
│   └── package.json              # Frontend dependencies
├── agent.py                      # Main agent entry point
├── transcriber.py               # Transcriber agent entry point
└── pyproject.toml              # Python project configuration
```

## Key Dependencies

### Python Backend
- **livekit**: Real-time communication framework
- **livekit-agents**: Agent development toolkit with OpenAI and Silero plugins
- **xaibo**: Advanced agent framework with multiple integrations
- **websockets**: WebSocket communication
- **pytest**: Testing framework

### Frontend
- **SvelteKit**: Modern web framework
- **TailwindCSS**: Utility-first CSS framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and development server

## Development

### Running Tests

Execute the test suite:

```bash
pytest
```

### Development Server

For development with hot reload:

```bash
# Backend (with auto-reload)
python agent.py --dev

# Frontend (with hot reload)
cd ui && pnpm dev
```

### Building for Production

Build the frontend for production:

```bash
cd ui
pnpm build
```

## Configuration

### Agent Configuration

The system uses YAML configuration files for agent behavior:

- [`agents/presentation-assistant.yml`](agents/presentation-assistant.yml): Main presentation assistant configuration
- [`agents/transcriber.yml`](agents/transcriber.yml): Transcriber agent configuration

### WebSocket Communication

The system uses WebSocket connections on port 9002 for real-time communication between the backend agents and frontend interface.

### LiveKit Integration

LiveKit handles:
- Real-time audio processing
- Speech-to-text conversion
- Text-to-speech synthesis
- Room management for multi-participant scenarios

## Features in Detail

### Intelligent Content Monitoring

The presentation assistant uses advanced algorithms to:
- Track which topics are covered on each slide
- Compare current presentation with previous iterations
- Identify missed content before slide transitions
- Provide contextually appropriate hints

### Concurrency Control

The system manages multiple concurrent operations:
- Real-time audio processing
- Slide content analysis
- WebSocket communication
- Transcript logging

### Voice Interaction

Natural voice interaction capabilities:
- Wake word detection ("Computer...")
- Speech-to-text processing
- Contextual response generation
- Text-to-speech output

