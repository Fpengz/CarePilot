"""
Re-export legacy API schema names for compatibility.

This module provides a backwards-compatible import surface that forwards
to the split schema modules.
"""

from .core import *  # noqa: F403
from .meal_health import *  # noqa: F403
from .notifications import *  # noqa: F403
from .recommendations import *  # noqa: F403
from .workflows import *  # noqa: F403
