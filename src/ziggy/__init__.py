"""Python support for the Ziggy data serialization language.

Leverage tree-sitter and the Ziggy tree-sitter grammar.
Ziggy schema is not supported.
"""

from ziggy.parser import parse
from ziggy.serializer import serialize

__all__ = [
    "parse",
    "serialize",
]
