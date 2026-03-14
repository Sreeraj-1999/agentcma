"""
Azure OpenAI client wrapper.
Single place to initialize and access the LLM.
"""

from openai import AzureOpenAI
from config.settings import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OPENAI_API_VERSION,
    AZURE_OPENAI_MODEL,
)

_client = None


def get_client() -> AzureOpenAI:
    """Get the Azure OpenAI client. Reuses same instance."""
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=OPENAI_API_VERSION,
        )
    return _client


def chat(messages: list[dict], temperature: float = 0.0) -> str:
    """
    Simple chat completion call.
    
    Args:
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        temperature: 0.0 for deterministic (SQL gen), higher for creative tasks
    
    Returns:
        The assistant's response text.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
