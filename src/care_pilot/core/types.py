"""
Define shared type aliases.

This module hosts simple type aliases used across features and adapters.
"""

from __future__ import annotations

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | dict[str, "JSONValue"] | list["JSONValue"]
type JSONDict = dict[str, JSONValue]
