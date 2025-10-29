"""Python support for the [Ziggy](https://ziggy-lang.io) data serialization language.

Leverage tree-sitter and the [Ziggy tree-sitter grammar](https://github.com/lvignoli/tree-sitter-ziggy).
Ziggy schema is not supported.

This is work in progress, especially the public API of the package, that is at present
quite heterogeneous.
"""

from ziggy.parser import Parser, parse
from ziggy.serializer import (
    AsMultilineStringFunc,
    AsQuotedStringFunc,
    AsTaggedLiteralFunc,
    Serializer,
    TaggedLiteralAnnotation,
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
    "TaggedLiteralAnnotation",
]
