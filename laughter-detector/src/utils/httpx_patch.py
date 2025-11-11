"""
Compatibility helpers for third-party libraries that expect legacy httpx arguments.

Supabase's Python client still instantiates httpx clients using the deprecated
``proxy`` keyword argument. Recent releases of httpx (>=0.25) removed that name
in favour of ``proxies`` which causes a TypeError when the Supabase client is
imported. This module patches the httpx initialisers at runtime to keep
backwards compatibility without downgrading httpx globally.
"""

from __future__ import annotations

import inspect
import httpx
from typing import Any


def _patch_client_init() -> None:
    """Patch ``httpx.Client.__init__`` so it accepts the legacy ``proxy`` kwarg."""
    signature = inspect.signature(httpx.Client.__init__)
    if "proxy" in signature.parameters:
        # Running on an older httpx version that still supports the keyword.
        return

    original_init = httpx.Client.__init__

    def patched_init(self, *args: Any, proxy: Any = None, proxies: Any = None, **kwargs: Any) -> None:
        if proxies is None and proxy is not None:
            proxies = proxy
        original_init(self, *args, proxies=proxies, **kwargs)

    httpx.Client.__init__ = patched_init  # type: ignore[assignment]


def _patch_async_client_init() -> None:
    """Patch ``httpx.AsyncClient.__init__`` to mirror the synchronous patch."""
    signature = inspect.signature(httpx.AsyncClient.__init__)
    if "proxy" in signature.parameters:
        return

    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args: Any, proxy: Any = None, proxies: Any = None, **kwargs: Any) -> None:
        if proxies is None and proxy is not None:
            proxies = proxy
        original_init(self, *args, proxies=proxies, **kwargs)

    httpx.AsyncClient.__init__ = patched_init  # type: ignore[assignment]


def enable_proxy_keyword_compat() -> None:
    """
    Apply runtime patches so httpx still accepts ``proxy=`` keyword arguments.

    This is safe to call multiple times and is executed during package import
    (see ``src/__init__.py``), ensuring all entrypoints benefit from the fix.
    """

    _patch_client_init()
    _patch_async_client_init()

