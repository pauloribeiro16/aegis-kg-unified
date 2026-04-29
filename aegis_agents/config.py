"""Configuration for AEGIS Agents."""

import os

NEO4J_CONFIG = {
    "http_url": os.getenv("NEO4J_URI", "http://localhost:7474"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", ""),
    "database": "neo4j",
}

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
