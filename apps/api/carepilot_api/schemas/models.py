"""
Re-export API schema names for compatibility.

This module provides a backwards-compatible import surface that forwards
to the split schema modules in the core contracts package.
"""

from care_pilot.core.contracts.api.core import *  # noqa: F403
from care_pilot.core.contracts.api.meal_health import *  # noqa: F403
from care_pilot.core.contracts.api.notifications import *  # noqa: F403
from care_pilot.core.contracts.api.recommendations import *  # noqa: F403
from care_pilot.core.contracts.api.workflows import *  # noqa: F403
