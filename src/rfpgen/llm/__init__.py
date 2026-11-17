"""LLM 계층(설계서 8장)."""

from .context import Excerpt, keyword_excerpt, render_block
from .gateway import (
    LLMCall,
    LLMError,
    LLMGateway,
    LLMInvalidOutput,
    LLMPolicyError,
    LLMRefusal,
    Provider,
    ProviderReply,
    Usage,
)
from .schema import strict_schema
from .verify import BlockIndex, normalize_for_match, number_in_quote, verify_evidence

__all__ = [
    "BlockIndex", "Excerpt", "LLMCall", "LLMError", "LLMGateway", "LLMInvalidOutput", "LLMPolicyError",
    "LLMRefusal", "Provider", "ProviderReply", "Usage", "keyword_excerpt", "normalize_for_match",
    "number_in_quote", "render_block", "strict_schema", "verify_evidence",
]
