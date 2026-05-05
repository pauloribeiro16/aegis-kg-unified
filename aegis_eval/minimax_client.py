#!/usr/bin/env python3
"""
minimax_client.py — Minimax API client using direct requests (no LangChain dependency).
"""

import os
import time
from pathlib import Path
from typing import Optional

import requests

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)


MINIMAX_API_URL = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
MINIMAX_MODEL = "MiniMax-M2.7"

_env_key = os.getenv("MINIMAX_API_KEY", "")
print(f"  [DEBUG minimax_client MODULE LOAD] MINIMAX_API_KEY first20={_env_key[:20]}... len={len(_env_key)}", flush=True)


def call_minimax(
    messages: list[dict],
    system: str = "",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """
    Call Minimax API via direct HTTP requests.
    """
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        return {"content": "", "latency_ms": 0, "error": "MINIMAX_API_KEY not configured", "usage": {}}

    print(f"  [DEBUG] call_minimax: key_first20={api_key[:20]}... len={len(api_key)}, url={MINIMAX_API_URL}", flush=True)

    api_messages = []
    if system:
        api_messages.append({"role": "system", "content": system})
    for msg in messages:
        api_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    payload = {
        "model": MINIMAX_MODEL,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.95,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"  [DEBUG] call_minimax: Authorization header set, Bearer prefix=sk-cp-{api_key[6:15]}...", flush=True)

    start = time.time()
    try:
        resp = requests.post(MINIMAX_API_URL, json=payload, headers=headers, timeout=60)
        elapsed = (time.time() - start) * 1000

        print(f"  [DEBUG] call_minimax: HTTP {resp.status_code}, body_len={len(resp.text)}", flush=True)
        print(f"  [DEBUG] call_minimax: response_body={resp.text[:300]}", flush=True)

        if resp.status_code != 200:
            return {"content": "", "latency_ms": elapsed, "error": f"HTTP {resp.status_code}: {resp.text[:500]}", "usage": {}}

        data = resp.json()

        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            status_msg = base_resp.get("status_msg", "unknown error")
            return {"content": "", "latency_ms": elapsed, "error": f"API error {base_resp.get('status_code')}: {status_msg}", "usage": {}}

        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage", {})

        return {"content": content, "latency_ms": elapsed, "error": None, "usage": usage}

    except requests.exceptions.Timeout:
        return {"content": "", "latency_ms": (time.time() - start) * 1000, "error": "Request timed out", "usage": {}}
    except requests.exceptions.RequestException as e:
        return {"content": "", "latency_ms": (time.time() - start) * 1000, "error": f"Request failed: {str(e)}", "usage": {}}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"  [DEBUG] Minimax exception: {e}", flush=True)
        print(f"  [DEBUG] Traceback:\n{tb}", flush=True)
        return {"content": "", "latency_ms": 0, "error": str(e), "usage": {}}


def call_minimax_simple(prompt: str, system: str = "", temperature: float = 0.1) -> dict:
    """Simple single-prompt interface for Minimax."""
    messages = [{"role": "user", "content": prompt}]
    return call_minimax(messages, system=system, temperature=temperature)


if __name__ == "__main__":
    print("Testing Minimax client via direct requests...")

    if not os.getenv("MINIMAX_API_KEY"):
        print("WARNING: MINIMAX_API_KEY not set")
    else:
        result = call_minimax_simple(
            prompt="Say 'Hello from Minimax direct' in exactly those words.",
            system="You are a helpful assistant."
        )
        print(f"Response: {result['content']}")
        print(f"Latency: {result['latency_ms']:.0f}ms")
        if result['error']:
            print(f"Error: {result['error']}")