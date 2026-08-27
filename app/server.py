"""
FastAPI backend that exposes the agent as an HTTP API.
Provides endpoints for chat, session management, and health checks.
"""

import logging
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import config
from app.agent import Agent, AgentResponse
from app.llm.base import LLMProvider
from app.rag.retriever import Retriever
from app.tools.order_lookup import OrderLookup

logger = logging.getLogger(__name__)

app = FastAPI(title="Aster & Row Support Agent", version="1.0.0")

# Allow CORS for the frontend dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance, initialized on startup.
_agent: Agent | None = None


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    message: str
    session_id: str | None = None


class SourceResponse(BaseModel):
    """A single source citation in the response."""
    filename: str
    heading: str


class ChatResponse(BaseModel):
    """Response body from the chat endpoint."""
    answer: str
    sources: list[SourceResponse] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    handoff_recommended: bool = False
    session_id: str = ""
    debug_trace: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Response body for new session creation."""
    session_id: str


# Creates the LLM provider based on configuration.
def _create_llm() -> LLMProvider:
    if config.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        return OllamaProvider(base_url=config.ollama_base_url, model=config.ollama_model)
    elif config.llm_provider == "mock":
        from app.llm.mock_provider import MockProvider
        return MockProvider()
    else:
        if not config.mistral_api_key:
            logger.warning("MISTRAL_API_KEY not configured. Using deterministic MockProvider for zero-cost execution.")
            from app.llm.mock_provider import MockProvider
            return MockProvider()
        from app.llm.mistral_provider import MistralProvider
        return MistralProvider(api_key=config.mistral_api_key, model=config.mistral_model)


# Initializes the agent with all its dependencies on application startup.
@app.on_event("startup")
async def startup():
    global _agent

    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting Aster & Row Support Agent")
    logger.info("LLM Provider: %s", config.llm_provider)
    logger.info("Debug mode: %s", config.debug)

    llm = _create_llm()
    logger.info("LLM initialized: %s", llm.name())

    retriever = Retriever(config.index_dir)
    logger.info("Retriever initialized")

    order_lookup = OrderLookup(config.orders_file)
    logger.info("Order lookup initialized")

    _agent = Agent(llm=llm, retriever=retriever, order_lookup=order_lookup)
    logger.info("Agent ready")


# Chat endpoint: processes a user message and returns the agent's response
# with answer, sources, tool activity, and handoff signals.
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if _agent is None:
        return ChatResponse(answer="Agent not initialized. Please try again.", session_id="")

    session_id = request.session_id or str(uuid.uuid4())

    try:
        response: AgentResponse = _agent.chat(request.message, session_id)

        return ChatResponse(
            answer=response.answer,
            sources=[SourceResponse(filename=s.filename, heading=s.heading) for s in response.sources],
            tool_calls=response.tool_calls,
            tool_results=response.tool_results,
            handoff_recommended=response.handoff_recommended,
            session_id=session_id,
            debug_trace=response.debug_trace,
        )
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return ChatResponse(
            answer="I'm sorry, I encountered an error processing your request. Please try again.",
            session_id=session_id,
            handoff_recommended=True,
        )


# Creates a new conversation session and returns the session ID.
@app.post("/api/new-session", response_model=SessionResponse)
async def new_session():
    session_id = str(uuid.uuid4())
    if _agent:
        _agent.clear_session(session_id)
    return SessionResponse(session_id=session_id)


# Health check endpoint for verifying the server is running.
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "provider": config.llm_provider,
        "debug": config.debug,
    }


# Mount compiled React frontend files for full-stack single-command hosting.
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

