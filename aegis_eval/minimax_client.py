#!/usr/bin/env python3
"""
minimax_client.py — Minimax API client using LangChain MiniMaxChat.

Usage:
    from minimax_client import call_minimax

    response = call_minimax(
        messages=[{"role": "user", "content": "Your prompt here"}],
        system="Optional system prompt"
    )
"""

import os
import time
from typing import Optional

from langchain_community.chat_models import MiniMaxChat
from langchain_core.messages import HumanMessage, SystemMessage


def get_minimax_llm(temperature: float = 0.1, max_tokens: int = 4096) -> MiniMaxChat:
    """Get or create a MiniMaxChat instance."""
    return MiniMaxChat(
        model="MiniMax-M2.7",
        temperature=temperature,
        max_tokens=max_tokens
    )


def call_minimax(
    messages: list[dict],
    system: str = "",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """
    Call Minimax API via LangChain MiniMaxChat.

    Args:
        messages: List of message dicts with 'role' and 'content'
        system: Optional system prompt
        temperature: Override default temperature
        max_tokens: Override default max_tokens

    Returns:
        {
            "content": str,  # Response text
            "latency_ms": float,
            "error": str or None,
            "usage": dict  # Token usage info
        }
    """
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        return {
            "content": "",
            "latency_ms": 0,
            "error": "MINIMAX_API_KEY not configured",
            "usage": {}
        }

    try:
        llm = get_minimax_llm(temperature=temperature, max_tokens=max_tokens)

        # Build LangChain messages
        langchain_messages = []
        if system:
            langchain_messages.append(SystemMessage(content=system))

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage
                langchain_messages.append(AIMessage(content=content))

        start = time.time()
        response = llm.invoke(langchain_messages)
        elapsed = (time.time() - start) * 1000

        # Extract content
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)

        # Extract usage from metadata
        usage = {}
        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage", {})

        return {
            "content": content,
            "latency_ms": elapsed,
            "error": None,
            "usage": usage
        }

    except Exception as e:
        return {
            "content": "",
            "latency_ms": 0,
            "error": str(e),
            "usage": {}
        }


def call_minimax_simple(prompt: str, system: str = "", temperature: float = 0.1) -> dict:
    """
    Simple single-prompt interface for Minimax.

    Args:
        prompt: User prompt text
        system: Optional system prompt
        temperature: Temperature for generation

    Returns:
        Same as call_minimax
    """
    messages = [{"role": "user", "content": prompt}]
    return call_minimax(messages, system=system, temperature=temperature)


if __name__ == "__main__":
    print("Testing Minimax client via LangChain...")

    if not os.getenv("MINIMAX_API_KEY"):
        print("WARNING: MINIMAX_API_KEY not set")
    else:
        result = call_minimax_simple(
            prompt="Say 'Hello from Minimax via LangChain' in exactly those words.",
            system="You are a helpful assistant."
        )
        print(f"Response: {result['content']}")
        print(f"Latency: {result['latency_ms']:.0f}ms")
        if result['error']:
            print(f"Error: {result['error']}")