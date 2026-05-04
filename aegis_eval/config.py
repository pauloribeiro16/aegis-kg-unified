import os
from dotenv import load_dotenv
load_dotenv()

NEO4J = {
    "http_url": os.getenv("NEO4J_URI", "http://localhost:7474"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", ""),
    "database": "neo4j",
}

OLLAMA = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "model": os.getenv("OLLAMA_MODEL", "ministral-3:latest"),
    "timeout": int(os.getenv("OLLAMA_TIMEOUT", "120")),
}

LANGFUSE = {
    "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    "secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
    "host": os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
}

MINIMAX = {
    "api_key": os.getenv("MINIMAX_API_KEY", ""),
    "model": "MiniMax-M2.7",
    "base_url": "https://api.minimaxi.chat/v1/text/chatcompletion_v2",
    "max_tokens": 4096,
    "temperature": 0.1,
}

PROJECT_NAME = "aegis-kg-eval"
TRACE_NAME = "aegis-kg-unified-eval"