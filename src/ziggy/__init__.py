"""Python support for the Ziggy data serialization language.

Leverage tree-sitter and the Ziggy tree-sitter grammar.
Ziggy schema is not supported.
"""

from ziggy.parser import Parser, parse
from ziggy.serializer import (
    AsMultilineStringFunc,
    AsQuotedStringFunc,
    AsTaggedLiteralFunc,
    Serializer,
    serialize,
)

__all__ = [
    "parse",
    "serialize",
    "Parser",
    "Serializer",
    "AsMultilineStringFunc",
    "AsQuotedStringFunc",
    "AsTaggedLiteralFunc",
]
