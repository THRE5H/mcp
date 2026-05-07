"""Chat endpoint with streaming support"""

import logging
import json
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional, List, Union

from schemas.messages import ChatRequest, ErrorResponse
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()
chat_service: ChatService | None = None
TEMP_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "temp_uploads"


def get_chat_service() -> ChatService:
    """Initialize the chat service lazily so health checks stay lightweight."""
    global chat_service
    if chat_service is None:
        try:
            chat_service = ChatService()
        except Exception as exc:
            logger.error("Chat service initialization failed", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"Chat service is unavailable: {exc}",
            ) from exc
    return chat_service


async def generate_sse_stream(
    message: str,
    session_id: Optional[str] = None,
    files: list = None,
    cleanup_paths: list[str] = None,
):
    """Generate Server-Sent Events stream for chat response"""
    try:
        service = get_chat_service()
        async for chunk in service.stream_chat_response(message, session_id, files):
            # Format as SSE
            yield f"data: {json.dumps(chunk)}\n\n"
    except Exception as e:
        logger.error(f"Error in SSE stream: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    finally:
        for path_str in cleanup_paths or []:
            path = Path(path_str)
            try:
                if path.exists():
                    path.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {path}: {cleanup_error}")


async def save_uploaded_files(files: list[UploadFile]) -> list[str]:
    """Persist multipart uploads so the V1 file pipeline can read them by path."""
    TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_paths: list[str] = []
    for file in files:
        suffix = Path(file.filename or "").suffix
        file_path = TEMP_UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
        logger.info(f"Saving file {file.filename} to {file_path.resolve()}")
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(str(file_path.resolve()))
        logger.info(f"Saved uploaded file: {file_path.resolve()}, exists: {file_path.exists()}")
        await file.close()

    return file_paths


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint with streaming response.
    
    Returns Server-Sent Events stream of response chunks.
    """
    try:
        logger.info(f"Processing chat request: {request.message[:50]}...")
        get_chat_service()
        
        # Generate SSE stream
        return StreamingResponse(
            generate_sse_stream(
                message=request.message,
                session_id=request.session_id,
                files=None,  # File upload via multipart in separate endpoint
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.post("/chat/with-files")
async def chat_with_files(
    files: List[UploadFile] = File(default_factory=list),
    message: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Chat endpoint with file upload support.
    
    Accepts multipart/form-data with optional files.
    """
    try:
        if not message and (not files or len(files) == 0):
            raise HTTPException(
                status_code=400,
                detail="Either message or files must be provided",
            )
        
        logger.info(f"Processing chat with files: {message[:50] if message else 'no text'}... ({len(files or [])} files)")
        get_chat_service()

        # Save uploaded files to a stable temp directory before passing them to V1.
        file_paths = await save_uploaded_files(files or [])
        logger.info(f"Generated file paths: {file_paths}")
        
        # Generate SSE stream
        return StreamingResponse(
            generate_sse_stream(
                message=message or "",
                session_id=session_id,
                files=file_paths,
                cleanup_paths=file_paths,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_with_files endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    service = get_chat_service()
    session = service.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "created_at": session.created_at,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Clear a session"""
    service = get_chat_service()
    if service.clear_session(session_id):
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")
