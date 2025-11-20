"""
Laughter Detector and Counter - Secure Audio Processing System

A secure web application that processes audio from Limitless AI pendant to detect 
and count laughter using YAMNet, with encrypted storage and mobile-responsive UI.
"""

__version__ = "1.0.0"

# Ensure compatibility with Supabase client expectations when using newer httpx versions.
from .utils.httpx_patch import enable_proxy_keyword_compat

enable_proxy_keyword_compat()
