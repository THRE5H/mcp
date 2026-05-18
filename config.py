import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load repo-level env first, then backend env when present.
for env_path in (BASE_DIR / ".env", BASE_DIR / "backend" / ".env"):
    if env_path.exists():
        load_dotenv(env_path)


def _resolve_path(path_value: str) -> str:
    """Resolve relative project paths against the repository root."""
    path = Path(path_value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path.resolve())


class Config:
    """Application configuration"""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # API metadata shared with the FastAPI backend
    API_TITLE = os.getenv("API_TITLE", "DNEXT Support Chatbot API")
    API_VERSION = os.getenv("API_VERSION", "2.0.0")
    API_DESCRIPTION = os.getenv(
        "API_DESCRIPTION",
        "REST API for the DNEXT Support Chatbot",
    )

    # Paths
    BASE_DIR = BASE_DIR
    DOCS_FOLDER = _resolve_path(os.getenv("DOCS_FOLDER", "docs_md"))
    CHROMA_DB_PATH = _resolve_path(os.getenv("CHROMA_DB_PATH", "data/chroma_db"))
    DATABASE_PATH = _resolve_path(os.getenv("DATABASE_PATH", "data/chatbot.db"))

    # Models
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
    GROQ_VISION_MODEL = os.getenv(
        "GROQ_VISION_MODEL",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    )

    # Server
    SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))
    SERVER_NAME = os.getenv("SERVER_NAME", "0.0.0.0")
    HOST = os.getenv("API_HOST", SERVER_NAME)
    PORT = int(os.getenv("API_PORT", os.getenv("PORT", str(SERVER_PORT))))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = ["*"]
    CORS_ALLOW_HEADERS = ["*"]

    # Chunking
    CHUNK_SIZE = 400
    CHUNK_OVERLAP = 50
    TOP_K_RESULTS = 5

    # LangSmith Configuration
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "dnext-support-chatbot")

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "â‌Œ OPENAI_API_KEY not found!\n"
                "Please set it in .env file or environment variables.\n"
                "Get your key from: https://platform.openai.com/account/api-keys"
            )

        docs_path = Path(cls.DOCS_FOLDER)
        if not docs_path.exists():
            docs_path.mkdir(parents=True)
            print(f"âœ… Created {cls.DOCS_FOLDER} folder")
