"""
Define shared identifier primitives.

This module contains ID helpers and value objects used across domains.
"""

from __future__ import annotations

from typing import NewType
from uuid import uuid4

RequestId = NewType("RequestId", str)
UserId = NewType("UserId", str)


def new_id() -> str:
    return uuid4().hex
