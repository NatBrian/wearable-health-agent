"""The dashboard's view of the shared wording. Every sentence lives in wha.wording so
the phone can say the same thing; this module exists so no screen import changes."""

from wha.wording import TEXT, level, rung, step, text

__all__ = ["TEXT", "level", "rung", "step", "text"]
