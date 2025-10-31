from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Callable

import pytest
import tree_sitter as ts
import tree_sitter_ziggy

_ts_ziggy_language = ts.Language(tree_sitter_ziggy.language())
_ts_ziggy_parser = ts.Parser(_ts_ziggy_language)


def parse(
    s: str | bytes | bytearray,
    *,
    literals: Mapping[str, Callable[[str], object]] | None = None,
    structs: Mapping[str, Callable[..., object]] | None = None,
) -> object:
    """Deserialize `s` to a Python object.

    From a ziggy document:
    - the null value is parsed as `None`
    - booleans, integers, floats are parsed as python equivalent
    - bytes and multiline bytes literals are parsed as python strings
    - an array is parsed as a python list
    - a map is parsed as a python dictionnary
    - a struct is parsed as a python dataclass. If the struct is named and the name is found as a
        key in the `structs` argument, the parsed fields and their values are passed as keyword
        arguments to the corresponding function, which may instantiate any python object.
        Typically, such functions are dataclasses.
    - a tagged literal is parsed as a string. If the tag name is found as a key in the `literals`
        argument, the parsed string is passed to the corresponding function, which may instantiate
        any python object.

    Args:
        s: The input to be interpreted, which can be a string, bytes, or bytearray.
        literals: Default is None. An optional mapping of literal names to functions that can
            process them.
        structs: Default is None. An optional mapping of struct names to functions that define
            their structure.

    Returns:
        A Python object corresponding to the input Ziggy document.

        >>> import ziggy
        >>> ziggy.parse('[1, 3.14, "pi", {"a": 0, "b": 1}]')
        [1, 3.14, 'pi', {'a': 0, 'b': 1}]

        >>> ziggy.parse('.title = "Ruy Blas", .author = "Victor Hugo"')
        {'title': 'Ruy Blas', 'author': 'Victor Hugo'}

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Book:
        ...     title: str
        ...     author: str
        >>> ziggy.parse('Book {.title = "Ruy Blas", .author = "Victor Hugo"}', structs={"Book": Book})
        Book(title='Ruy Blas', author='Victor Hugo')
    """
    if isinstance(s, str):
        s = s.encode()
    elif isinstance(s, bytearray):
        s = bytes(s)
    tree = _ts_ziggy_parser.parse(s)

    # Find all error nodes in the tree
    error_nodes: list[ts.Node] = []

    def find_errors(node: ts.Node):
        if node.type == "ERROR":
            error_nodes.append(node)
        for child in node.children:
            find_errors(child)

    find_errors(tree.root_node)

    if error_nodes:
        error_messages: list[str] = []
        # Split source into lines for error display
        source_lines = s.decode("utf-8").splitlines()

        for error_node in error_nodes:
            start_point = error_node.start_point
            line_num = start_point.row + 1  # Convert 0-based to 1-based
            column_num = start_point.column + 1  # Convert 0-based to 1-based

            error_msg = f"Error at line {line_num}, column {column_num}:"

            # Add the source line if it exists
            if 0 <= start_point.row < len(source_lines):
                source_line = source_lines[start_point.row]
                error_msg += f"\n  {source_line}"
                # Add caret indicator pointing to the error column
                pointer = " " * (start_point.column + 2) + "^"
                error_msg += f"\n{pointer}"

            error_messages.append(error_msg)
        error_msg = "Parse error:\n" + "\n".join(error_messages)
        raise ValueError(error_msg)

    interpreter = Parser(literals=literals, structs=structs)
    v = interpreter.interpret(tree.root_node)
    return v


class Parser:
    def __init__(
        self,
        *,
        literals: Mapping[str, Callable[[str], object]] | None = None,
        structs: Mapping[str, Callable[[], object]] | None = None,
    ):
        self.literals: dict[str, Callable[[str], object]] = (
            dict(literals) if literals is not None else {}
        )
        self.structs: dict[str, Callable[[], object]] = dict(structs) if structs is not None else {}

    def interpret(self, node: ts.Node | None) -> object:
        if node is None:
            return None
        match node.type:
            case "document":
                return self.interpret(node.child(0))
            case "true":
                return True
            case "false":
                return False
            case "null":
                return None
            case "integer":
                assert node.text is not None
                return interpret_integer(node.text.decode())
            case "float":
                assert node.text is not None
                return interpret_float(node.text.decode())
            case "identifier":
                return self.interpret_identifier(node)
            case "string":
                return self.interpret_string(node)
            case "quoted_string":
                return self.interpret_quoted_string(node)
            case "tag_string":
                return self.interpret_tag_string(node)
            case "map":
                return self.interpret_map(node)
            case "array":
                return self.interpret_array(node)
            case "struct":
                return self.interpret_struct(node)
            case "top_level_struct":
                return self.interpret_struct(node)
            case _:
                raise ValueError(f"unsupported: {node.type}")

    def interpret_identifier(self, node: ts.Node) -> str:
        assert (txt := node.text) is not None
        return txt.decode("utf-8")

    def interpret_string(self, node: ts.Node) -> str:
        if len(node.children) == 1:
            return self.interpret_quoted_string(node)
        else:
            return self.interpret_multiline_string(node)

    def interpret_quoted_string(self, node: ts.Node) -> str:
        assert (txt := node.text) is not None
        return txt.decode("utf-8").strip('"')

    def interpret_multiline_string(self, node: ts.Node) -> str:
        lines: list[str] = []
        for c in node.named_children:
            assert c.text is not None
            line = c.text.decode("utf-8").lstrip("\\\\")
            lines.append(line)
        return "\n".join(lines)

    def interpret_tag_string(self, node: ts.Node) -> object:
        name = node.named_children[0].text
        assert name is not None
        name = name.decode("utf-8")
        v = self.interpret_quoted_string(node.named_children[1])
        if name in self.literals:
            f = self.literals[name]
            return f(v)
        return v

    def interpret_map(self, node: ts.Node) -> dict[str, object]:
        map: dict[str, object] = {}
        for c in node.named_children:
            key_node = c.child_by_field_name("key")
            assert key_node is not None
            k = self.interpret_quoted_string(key_node)
            v = self.interpret(c.child_by_field_name("value"))
            map[k] = v
        return map

    def interpret_array(self, node: ts.Node) -> list[object]:
        arr: list[object] = []
        for c in node.named_children:
            x = self.interpret(c.children[-1])
            arr.append(x)
        return arr

    def interpret_struct(self, node: ts.Node) -> dict[str, object] | object:
        fields: dict[str, object] = {}

        for c in node.named_children:
            if c.type != "struct_field":
                continue
            key_node = c.child_by_field_name("key")
            assert key_node is not None
            k = self.interpret_identifier(key_node)
            v = self.interpret(c.child_by_field_name("value"))
            fields[k] = v

        name_node = node.child_by_field_name("name")
        struct_is_named = name_node is not None

        if struct_is_named:
            name = name_node.text
            assert name is not None
            name = name.decode("utf-8")
            if name in self.structs:
                struct_constructor = self.structs[name]
                return struct_constructor(**fields)

        return fields


def interpret_integer(s: str) -> int:
    # Extract base prefix, if existing.
    base = 10
    if s.startswith("0x"):
        base = 16
    elif s.startswith("0o"):
        base = 8
    elif s.startswith("0b"):
        base = 2
    if base != 10:
        s = s[2:]
    return int(s, base=base)


def interpret_float(s: str) -> float:
    s = s.lower().strip("_")

    if not s.startswith("0x"):
        return float(s)

    # Must be hexadecimal.
    # We interpret the integer and "decimal" part separately.
    x = s[2:]

    base, idec, exp = 0, 0, 0
    if "p" in x:
        x, e = s.split("p")
        exp = int(e)
    else:
        x = s

    if "." in x:
        b, d = x.split(".")
        base = int(b, base=16)
        idec = int(d, base=16)
    else:
        base = int(x, base=16)

    if idec == 0:
        dec = 0
    else:
        k = round(math.log10(idec)) + 1
        dec = idec * 10**-k

    return (base + dec) * 10**exp


@pytest.mark.parametrize(
    "input,expected",
    [
        # Base 10.
        ("0", 0),
        ("123", 123),
        ("123_456", 123456),
        # Base 2.
        ("0b0", 0),
        ("0o0", 0),
        ("0b0_0", 0),
        ("0b10", 2),
        ("0b1010", 10),
        # Base 8.
        ("0o0", 0),
        ("0o7", 7),
        ("0o10", 8),
        ("0o12", 10),
        # Base 16.
        ("0x0", 0),
        ("0xa", 10),
        ("0xf", 15),
        ("0x10", 16),
        ("0xff", 255),
        ("0xFF", 255),
        ("0xFF_FF_FF", 16777215),
    ],
)
def test_interpret_integer(input: str, expected: int):
    actual = interpret_integer(input)
    assert actual == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        # Base 10.
        ("0", 0),
        ("123", 123),
        ("0.123", 0.123),
        ("123_456", 123456),
        ("123.456", 123.456),
        ("123e456", 123e456),
        ("12_3.45_6E1_2", 123.456e12),
        ("123.0", 123.0),
        ("123_000.456_000", 123_000.456_000),
        ("123.0e+77", 123.0e77),
        ("123.0E+77", 123.0e77),
        # Base 16.
        ("0x0", 0),
        ("0xa", 10),
        ("0xf", 15),
        ("0x10", 16),
        ("0xff", 255),
        ("0xFF", 255),
        ("0xFF_FF_FF", 16777215),
        ("0x0.0", 0),
        ("0x0.0p0", 0),
        ("0x0.0p1", 0),
        ("0xef.abp12", 239.171e12),
        ("0xEF.ABp12", 239.171e12),
        ("0x103.70p-5", 259.112e-5),
        ("0x103.70", 259.112),
        ("0x1234_5678.9ABC_CDEFp-10", 305419896.2596064751e-10),
    ],
)
def test_interpret_float(input: str, expected: int):
    actual = interpret_float(input)
    assert math.isclose(actual, expected, abs_tol=1e-10)
