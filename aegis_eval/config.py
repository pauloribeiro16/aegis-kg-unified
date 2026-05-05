import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_result = load_dotenv(env_path)

print(f"[DEBUG eval_config] load_dotenv({env_path}) returned: {load_result}", flush=True)
print(f"[DEBUG eval_config] NEO4J_PASSWORD set: {bool(os.getenv('NEO4J_PASSWORD'))}", flush=True)
print(f"[DEBUG eval_config] MINIMAX_API_KEY set: {bool(os.getenv('MINIMAX_API_KEY'))}", flush=True)
print(f"[DEBUG eval_config] MINIMAX_API_KEY len: {len(os.getenv('MINIMAX_API_KEY', ''))}", flush=True)
print(f"[DEBUG eval_config] LANGFUSE_PUBLIC_KEY set: {bool(os.getenv('LANGFUSE_PUBLIC_KEY'))}", flush=True)
print(f"[DEBUG eval_config] OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL')}", flush=True)

NEO4J = {
    "http_url": os.getenv("NEO4J_URI", "http://localhost:7474"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", ""),
    "database": "neo4j",
}
print(f"[DEBUG eval_config] NEO4J password length: {len(NEO4J['password'])}", flush=True)

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
print(f"[DEBUG eval_config] MINIMAX api_key loaded: {MINIMAX['api_key'][:15]}... len={len(MINIMAX['api_key'])}", flush=True)

PROJECT_NAME = "aegis-kg-eval"
TRACE_NAME = "aegis-kg-unified-eval"
