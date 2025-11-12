"""
Supabase client helpers for consistent configuration across the project.

These helpers centralize Supabase client creation so that RLS-aware user
clients, anon clients, and service-role clients all share the same setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from supabase import Client, create_client

from ..config.settings import settings


class SupabaseClientError(RuntimeError):
    """Error raised when Supabase client creation fails."""


@dataclass(frozen=True)
class SessionTokens:
    """JWT session tokens used when binding a client to a user."""

    access_token: str
    refresh_token: Optional[str] = None


def _build_client(api_key: str) -> Client:
    """
    Create a Supabase client using the provided API key.

    Args:
        api_key: Supabase API key (anon or service-role).

    Returns:
        Supabase Client instance.

    Raises:
        SupabaseClientError: If the key or Supabase URL is missing.
    """
    if not settings.supabase_url:
        raise SupabaseClientError("Supabase URL is not configured.")

    if not api_key:
        raise SupabaseClientError("Supabase API key is missing.")

    try:
        return create_client(settings.supabase_url, api_key)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise SupabaseClientError(f"Failed to create Supabase client: {exc}") from exc


def get_anon_client() -> Client:
    """
    Return a Supabase client configured with the anon key.

    This client enforces RLS automatically; use it when a request should be
    scoped to an authenticated user's JWT.
    """
    return _build_client(settings.supabase_key)


def get_service_role_client() -> Client:
    """
    Return a Supabase client configured with the service-role key.

    Use this for backend jobs (cron, maintenance scripts) that must bypass RLS.
    """
    key = getattr(settings, "supabase_service_role_key", None)
    if not key:
        raise SupabaseClientError("Supabase service-role key is not configured.")
    return _build_client(key)


def get_user_client(tokens: SessionTokens | str) -> Client:
    """
    Return a Supabase client bound to an authenticated user's JWT.

    Args:
        tokens: Either a SessionTokens dataclass or a raw access token string.

    Returns:
        Supabase Client authorized for the user's RLS policies.
    """
    if isinstance(tokens, str):
        access_token = tokens
        refresh_token = None
    else:
        access_token = tokens.access_token
        refresh_token = tokens.refresh_token

    if not access_token:
        raise SupabaseClientError("Access token is required for user client.")

    client = get_anon_client()

    # Ensure PostgREST requests include the JWT for RLS.
    if hasattr(client, "postgrest"):
        client.postgrest.auth(access_token)

    # Attach the session to the auth subsystem when available.
    # Different supabase-py versions expose different helpers.
    auth = getattr(client, "auth", None)
    if auth is not None:
        try:
            # Newer supabase-py expects separate positional args
            auth.set_session(access_token, refresh_token or "")
        except AttributeError:
            try:
                auth._set_auth(access_token)  # type: ignore[attr-defined]
            except AttributeError:
                pass
        except TypeError:
            # Older versions accept a dict payload
            try:
                auth.set_session(
                    {"access_token": access_token, "refresh_token": refresh_token}
                )
            except TypeError:
                try:
                    auth._set_auth(access_token)  # type: ignore[attr-defined]
                except AttributeError:
                    pass

    return client
