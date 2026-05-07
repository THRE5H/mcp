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

            # Call backend /api/chat endpoint with system prompt
            async with httpx.AsyncClient(timeout=RESPONSE_TIMEOUT) as client:
                logger.info(f"[MCP Tool] Sending request to backend...")
                
                response = await client.post(
                    BACKEND_CHAT_ENDPOINT,
                    json={
                        "message": query,
                        "session_id": "mcp_platform_support",
                    },
                    headers={"Content-Type": "application/json"},
                )

                logger.info(f"[MCP Tool] Backend response status: {response.status_code}")

                if response.status_code != 200:
                    logger.error(
                        f"[MCP Tool] Backend error: {response.status_code} - {response.text}"
                    )
                    return {
                        "answer": f"Backend error: {response.status_code}. Please check if the DNEXT backend is running."
                    }

                # Parse response - handle both streaming and regular JSON
                response_text = await self._parse_backend_response(response)

                logger.info(f"[MCP Tool] Response generated: {response_text[:100]}...")

                # Check if backend returned an error message
                if "suspended" in response_text.lower() or "error" in response_text.lower():
                    logger.warning(f"[MCP Tool] Backend returned error: {response_text}")
                    return {
                        "answer": "The backend service is not properly configured for MCP. Please ensure the backend is running with proper session management enabled."
                    }

                return {"answer": response_text}

        except asyncio.TimeoutError:
            logger.error("[MCP Tool] Request timeout")
            return {"answer": "Your question took too long to process. Please try again."}
        except Exception as e:
            logger.error(f"[MCP Tool] Unexpected error: {str(e)}", exc_info=True)
            return {
                "answer": f"Error: {str(e)}. Make sure the backend is running at {BACKEND_CHAT_ENDPOINT}"
            }

    async def _parse_backend_response(self, response: httpx.Response) -> str:
        """
        Parse response from backend.
        Handles both streaming (SSE) and regular JSON responses.
        """
        try:
            # First, try to parse as regular JSON (non-streaming)
            try:
                data = response.json()
                logger.info(f"[MCP Tool] Parsed JSON response: {str(data)[:200]}")
                
                if "response" in data:
                    return data["response"]
                if "message" in data:
                    return data["message"]
                if "answer" in data:
                    return data["answer"]
                if "content" in data:
                    return str(data["content"])
                    
                # If none of the above, return stringified JSON
                logger.warning("[MCP Tool] No recognized response field in JSON")
                return json.dumps(data)
                
            except json.JSONDecodeError:
                logger.info("[MCP Tool] Not JSON, trying to parse as streaming...")
                
                # Try to parse as streaming response (Server-Sent Events)
                full_response = ""
                latest_response = ""
                text_content = response.text
                
                logger.info(f"[MCP Tool] Raw response text: {text_content[:200]}")
                
                for line in text_content.split("\n"):
                    line = line.strip()
                    if line.startswith("data:"):
                        try:
                            event_data = json.loads(line[5:].strip())
                            if event_data.get("type") == "response" and "content" in event_data:
                                # The backend streams the full assistant message on each SSE event,
                                # so keep the latest version instead of concatenating duplicates.
                                latest_response = event_data["content"]
                            elif "content" in event_data:
                                full_response += event_data["content"]
                        except json.JSONDecodeError:
                            # Sometimes data is not JSON, just plain text
                            full_response += line[5:].strip()

                if latest_response:
                    logger.info(f"[MCP Tool] Parsed latest streaming response: {latest_response[:200]}")
                    return latest_response

                if full_response:
                    logger.info(f"[MCP Tool] Parsed streaming response: {full_response[:200]}")
                    return full_response
                    
                # If no data found, return the raw text
                if text_content:
                    logger.warning(f"[MCP Tool] Returning raw text: {text_content[:200]}")
                    return text_content
                    
                return "No response content found from backend."

        except Exception as e:
            logger.error(f"[MCP Tool] Response parsing error: {str(e)}", exc_info=True)
            return f"Error parsing response: {str(e)}"


# Tool instance
query_tool = QueryPlatformSupportingTool()
