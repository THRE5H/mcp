"""Tool implementations for MCP server."""
import asyncio
import json
import logging
from typing import Any, Dict

import httpx

from config import (
    BACKEND_CHAT_ENDPOINT,
    SYSTEM_PROMPT,
    RESPONSE_TIMEOUT,
    TOOL_NAME,
    TOOL_DESCRIPTION,
)

logger = logging.getLogger(__name__)


class QueryPlatformSupportingTool:
    """Implementation of query_platform_supporting tool."""

    def __init__(self):
        self.name = TOOL_NAME
        self.description = TOOL_DESCRIPTION
        self.input_schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute the query against the platform support agent.

        Args:
            query: The user's question about DNEXT platform

        Returns:
            Dict with "answer" key containing the response
        """
        try:
            logger.info(f"[MCP Tool] Processing query: {query[:100]}...")
            logger.info(f"[MCP Tool] Backend URL: {BACKEND_CHAT_ENDPOINT}")

            response_text = ""
            metadata: Dict[str, Any] = {}

            # Call backend /api/chat endpoint and consume the SSE stream directly.
            async with httpx.AsyncClient(timeout=RESPONSE_TIMEOUT) as client:
                logger.info(f"[MCP Tool] Sending request to backend...")
                async with client.stream(
                    "POST",
                    BACKEND_CHAT_ENDPOINT,
                    json={
                        "message": query,
                        "session_id": "mcp_platform_support",
                    },
                    headers={"Content-Type": "application/json"},
                ) as response:
                    logger.info(f"[MCP Tool] Backend response status: {response.status_code}")

                    if response.status_code != 200:
                        error_content = await response.aread()
                        logger.error(
                            f"[MCP Tool] Backend error: {response.status_code} - {error_content!r}"
                        )
                        return {
                            "answer": (
                                f"Backend error: {response.status_code}. "
                                "Please check if the DNEXT backend is running."
                            )
                        }

                    response_text, metadata = await self._parse_backend_stream(response)

                logger.info(f"[MCP Tool] Response generated: {response_text[:100]}...")
                if metadata:
                    logger.info(f"[MCP Tool] Metadata: {metadata}")

                normalized = response_text.strip().lower()
                if not normalized or normalized == "no response content found from backend.":
                    logger.warning("[MCP Tool] Backend returned no usable content")
                    return {
                        "answer": (
                            "The backend did not return a usable answer. "
                            "Please check the backend chat endpoint and session handling."
                        )
                    }

                if normalized.startswith("error parsing response:") or normalized.startswith("backend error:"):
                    logger.warning(f"[MCP Tool] Backend returned an error payload: {response_text}")
                    return {"answer": response_text}

                return {"answer": response_text}

        except asyncio.TimeoutError:
            logger.error("[MCP Tool] Request timeout")
            return {"answer": "Your question took too long to process. Please try again."}
        except Exception as e:
            logger.error(f"[MCP Tool] Unexpected error: {str(e)}", exc_info=True)
            return {
                "answer": f"Error: {str(e)}. Make sure the backend is running at {BACKEND_CHAT_ENDPOINT}"
            }

    async def _parse_backend_stream(self, response: httpx.Response) -> tuple[str, Dict[str, Any]]:
        """
        Parse the backend SSE response.

        The backend emits cumulative assistant text on each `response` event,
        so we keep the latest response content rather than concatenating all events.
        """
        try:
            latest_response = ""
            metadata: Dict[str, Any] = {}

            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue

                payload = line[5:].strip()
                if not payload:
                    continue

                try:
                    event_data = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"[MCP Tool] Non-JSON SSE payload: {payload[:200]}")
                    continue

                event_type = event_data.get("type")
                if event_type == "response":
                    latest_response = event_data.get("content", "") or latest_response
                elif event_type == "metadata":
                    metadata = event_data.get("data", {}) or metadata
                elif event_type == "error":
                    error_message = event_data.get("content", "Unknown backend error")
                    logger.warning(f"[MCP Tool] Backend SSE error: {error_message}")
                    return error_message, metadata

            if latest_response:
                logger.info(f"[MCP Tool] Parsed latest streaming response: {latest_response[:200]}")
                return latest_response, metadata

            return "No response content found from backend.", metadata
        except Exception as e:
            logger.error(f"[MCP Tool] Response parsing error: {str(e)}", exc_info=True)
            return f"Error parsing response: {str(e)}", {}


# Tool instance
query_tool = QueryPlatformSupportingTool()
