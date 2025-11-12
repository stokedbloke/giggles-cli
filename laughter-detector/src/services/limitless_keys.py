"""
Helpers for retrieving and decrypting Limitless API keys.
"""

from __future__ import annotations

from typing import Optional

from supabase import Client

from ..auth.encryption import encryption_service
from .supabase_client import get_service_role_client


class LimitlessKeyError(RuntimeError):
    """Raised when Limitless key retrieval fails."""


def _ensure_client(client: Optional[Client]) -> Client:
    """Return the provided client or fall back to the service-role client."""
    return client or get_service_role_client()


def fetch_encrypted_limitless_key(
    user_id: str, *, supabase: Optional[Client] = None
) -> str:
    """
    Fetch the encrypted Limitless API key for a user.

    Args:
        user_id: Supabase user identifier.
        supabase: Optional Supabase client (RLS-aware or service-role).

    Returns:
        Encrypted API key as stored in the database.

    Raises:
        LimitlessKeyError: If no active key is found.
    """
    client = _ensure_client(supabase)
    response = (
        client.table("limitless_keys")
        .select("encrypted_api_key")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise LimitlessKeyError(f"No active Limitless API key for user {user_id}")

    return response.data[0]["encrypted_api_key"]


def fetch_decrypted_limitless_key(
    user_id: str, *, supabase: Optional[Client] = None
) -> str:
    """
    Fetch and decrypt the Limitless API key for a user.

    Args:
        user_id: Supabase user identifier.
        supabase: Optional Supabase client (RLS-aware or service-role).

    Returns:
        Decrypted API key string.
    """
    encrypted_key = fetch_encrypted_limitless_key(user_id, supabase=supabase)
    return encryption_service.decrypt(
        encrypted_key, associated_data=user_id.encode("utf-8")
    )
