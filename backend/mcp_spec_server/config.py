"""Configuration for MCP Server."""
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "::")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", os.getenv("PORT", "8001")))


def _resolve_backend_url() -> str:
    """Resolve the API base URL used by the MCP server."""
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        return backend_url.rstrip("/")

    api_host = os.getenv("API_HOST", "localhost")
    if api_host in {"0.0.0.0", "::"}:
        api_host = "localhost"

    api_port = os.getenv("API_PORT", "8000")
    return f"http://{api_host}:{api_port}"


# Backend Configuration
BACKEND_URL = _resolve_backend_url()
BACKEND_CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat"

# Tool Configuration
TOOL_NAME = "query_platform_supporting"
TOOL_DESCRIPTION = """This agent answers platform-related questions about the DNEXT platform: module definitions, feature explanations, how-to guides, general troubleshooting, user documentation, and support email knowledge. It does NOT answer questions about specific datasets, data values, metadata, catalogue entries, or anything requiring SQL execution. Call this tool when the user asks how something works, what something means, or how to fix a general platform issue."""

# System Prompt for backend
SYSTEM_PROMPT = """You are the DNEXT platform support agent. Your role is to answer questions ONLY about:
- DNEXT platform modules and components
- Feature explanations and capabilities
- How-to guides and documentation
- General troubleshooting and support

You MUST REJECT and redirect the following types of questions:
- Questions about specific datasets or data values
- Questions about metadata or catalogue entries
- SQL queries or schema questions
- Domain-specific business logic

When you encounter these topics, respond with: "That's a [data/metadata/SQL] question. Please use the data-catalog tool or query_data tool instead."

Always be helpful, clear, and concise in your responses."""

# Response Configuration
RESPONSE_TIMEOUT = 60  # seconds
