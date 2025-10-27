"""Python support for the Ziggy data serialization language.

Leverage tree-sitter and the Ziggy tree-sitter grammar.
Ziggy schema is not supported.

This is work in progress, especially the public API of the package, that is a
heterogeneous.
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
