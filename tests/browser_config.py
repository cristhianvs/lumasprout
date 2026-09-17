"""Shared environment for isolated browser tests (empty channel selects Playwright Chromium)."""
import os

BASE = os.environ.get('LUMA_BASE_URL', 'http://127.0.0.1:4173').rstrip('/')
BROWSER_CHANNEL = os.environ.get('LUMA_BROWSER_CHANNEL', 'chrome') or None
