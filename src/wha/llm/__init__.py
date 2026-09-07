"""LLM client, provider abstraction, and prompts."""

from wha.llm.cassette import CassetteClient
from wha.llm.client import (
    LLMClient,
    LLMUsage,
    Prompt,
    get_llm_client,
)
from wha.llm.ollama import OllamaNativeClient
from wha.llm.openai_compat import OpenAICompatClient
from wha.llm.repair import build_repair_prompt, strip_markdown_fences

__all__ = [
    "CassetteClient",
    "LLMClient",
    "LLMUsage",
    "OllamaNativeClient",
    "OpenAICompatClient",
    "Prompt",
    "build_repair_prompt",
    "get_llm_client",
    "strip_markdown_fences",
]
