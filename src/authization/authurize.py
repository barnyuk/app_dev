"""Compatibility import; use src.authization.authorize in new code."""

from src.authization.authorize import get_token

__all__ = ['get_token']