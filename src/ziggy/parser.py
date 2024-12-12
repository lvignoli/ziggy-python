from __future__ import annotations

import dataclasses
import datetime
import pathlib
import sys
from typing import Callable, Mapping

import tree_sitter as ts
import tree_sitter_ziggy

_ts_ziggy_language = ts.Language(tree_sitter_ziggy.language())
_ts_ziggy_parser = ts.Parser(_ts_ziggy_language)


def parse(
    s: str | bytes | bytearray,
    *,
    literals: Mapping[str, Callable] | None = None,
    structs: Mapping[str, Callable] | None = None,
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
        >>> ziggy.parse('[1, 3.14, "pi", {"a": 0, "b": 1}])')
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
    interpreter = Parser(literals=literals, structs=structs)
    v = interpreter.interpret(tree.root_node)
    return v


class Parser:
    def __init__(
        self,
        *,
        literals: Mapping[str, Callable] | None = None,
        structs: Mapping[str, Callable] | None = None,
    ):
        self.literals: dict = dict(literals) if literals is not None else {}
        self.structs: dict = dict(structs) if structs is not None else {}

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
                return int(node.text)
            case "float":
                assert node.text is not None
                return float(node.text)
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
        lines = []
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
        map = {}
        for c in node.named_children:
            key_node = c.child_by_field_name("key")
            assert key_node is not None
            k = self.interpret_quoted_string(key_node)
            v = self.interpret(c.child_by_field_name("value"))
            map[k] = v
        return map

    def interpret_array(self, node: ts.Node) -> list[object]:
        arr = []
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
            if name is not None and name in self.structs:
                struct_constructor = self.structs[name]
                return struct_constructor(**fields)

        return fields


if __name__ == "__main__":
    language = ts.Language(tree_sitter_ziggy.language())
    parser = ts.Parser(language)
    data = pathlib.Path(sys.argv[1]).read_bytes()

    @dataclasses.dataclass
    class Message:
        sender: str
        content: str
        timestamp: int

    v = parse(data)
    print(v)

    v = parse(
        data,
        structs={"Message": Message},
        literals={"date": datetime.datetime.fromisoformat},
    )
    print(v)
