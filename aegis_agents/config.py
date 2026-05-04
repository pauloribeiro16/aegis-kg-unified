"""Configuration for AEGIS Agents."""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_result = load_dotenv(env_path)

print(f"[DEBUG config] load_dotenv({env_path}) returned: {load_result}", flush=True)
print(f"[DEBUG config] NEO4J_PASSWORD set: {bool(os.getenv('NEO4J_PASSWORD'))}", flush=True)
print(f"[DEBUG config] MINIMAX_API_KEY set: {bool(os.getenv('MINIMAX_API_KEY'))}", flush=True)
print(f"[DEBUG config] MINIMAX_API_KEY len: {len(os.getenv('MINIMAX_API_KEY', ''))}", flush=True)
print(f"[DEBUG config] LANGFUSE_PUBLIC_KEY set: {bool(os.getenv('LANGFUSE_PUBLIC_KEY'))}", flush=True)
print(f"[DEBUG config] OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL')}", flush=True)

NEO4J_CONFIG = {
    "http_url": os.getenv("NEO4J_URI", "http://localhost:7474"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", ""),
    "database": "neo4j",
}
print(f"[DEBUG config] NEO4J_CONFIG password length: {len(NEO4J_CONFIG['password'])}", flush=True)

OLLAMA_CONFIG = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "model": os.getenv("OLLAMA_MODEL", "ministral-3:latest"),
    "timeout": int(os.getenv("OLLAMA_TIMEOUT", "120")),
}

LANGCHAIN_CONFIG = {
    "model": os.getenv("OLLAMA_MODEL", "gemma3:1b"),
    "temperature": float(os.getenv("LANGCHAIN_TEMPERATURE", "0.0")),
}

LANGFUSE_CONFIG = {
    "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    "secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
    "host": os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
}

PROJECT_NAME = "aegis-kg-agents"
TRACE_NAME = "aegis-kg-unified-agents"
