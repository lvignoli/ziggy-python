from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from typing import (
    Callable,
    Final,
    Iterable,
    Mapping,
    Sequence,
    TypeVar,
    get_args,
    get_type_hints,
)

T = TypeVar("T")


def annotated_by(
    annotated: object,
    kind: type[T],
) -> Iterable[tuple[str, T, type]]:
    for k, v in get_type_hints(annotated, include_extras=True).items():
        all_args = get_args(v)
        if not all_args:
            continue
        actual, *rest = all_args
        for arg in rest:
            if isinstance(arg, kind):
                yield k, arg, actual


class SerializeFunction(ABC):
    @abstractmethod
    def __call__(self, x: object) -> str: ...


class AsQuotedStringFunc(SerializeFunction):
    def __init__(self, f: Callable[..., str]):
        self.f = f

    def __call__(self, x: object) -> str:
        s = self.f(x)
        return serialize_quoted_string(s)


class AsMultilineStringFunc(SerializeFunction):
    def __init__(self, f: Callable[..., str]):
        self.f = f

    def __call__(self, x: object) -> str:
        s = self.f(x)
        return serialize_multiline_string(s)


class AsTaggedLiteralFunc(SerializeFunction):
    def __init__(self, f: Callable[..., str], *, tag: str):
        self.f = f
        self.tag = tag

    def __call__(self, x: object) -> str:
        s = self.f(x)
        return serialize_tagged_literal(s, tag=self.tag)


@dataclass(frozen=True)
class TaggedLiteralAnnotation:
    name: Final[str]
    serialize_function: Final[Callable[..., str]] | None = None


@dataclass(frozen=True)
class QuotedString:
    value: str


@dataclass(frozen=True)
class MultilineString:
    value: str


@dataclass(frozen=True, kw_only=True)
class TaggedLiteral:
    value: str
    tag: str


class ZiggySerializer[T](ABC):
    """Abstract class to define the Ziggy string representation of an object.

    Any subclass of ZiggySerializer is serialized as a quoted string, as returned by the `ziggy_serialize`
    method implemeted by the user.
    """

    @abstractmethod
    def ziggy_serialize(self) -> QuotedString | MultilineString | TaggedLiteral: ...


def serialize(
    obj: object,
    *,
    serializer: Serializer | None = None,
) -> str:
    """Serialize `obj` into a Ziggy document.

    Serialization supports any objects composed with Sequences, Mappings, dataclasses and literals
    (string, numbers, booleans) or None values.

    Args:
        obj: the object to serialize.
        indent: a string to preprend before each line. None by default. If None, the output
            document is minified.
        with_dataclass_name: if True, preprend each output struct by the dataclass name.

    Examples:
        >>> import ziggy
        >>> ziggy.serialize([None, True, 1, 3.14, "hello", {"name": "Apple", "type": "fruit"}])
        '[null, true, 1, 3.14, "hello", {"name": "Apple", "type": "fruit"}]'

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Message:
        ...     id: int
        ...     content: str
        >>> ziggy.serialize(Message(id=1, content="Hello, World!"), with_dataclass_name = False)
        '{.id = 1, .content = "Hello, World!"}'

        >>> ziggy.serialize(Message(id=1, content="Hello, World!"))
        'Message {.id = 1, .content = "Hello, World!"}'

        >>> s = ziggy.serialize(Message(id=1, content="Hello, World!"), indent="    ")
        >>> print(s)
        Message {
            .id = 1,
            .content = "Hello, World!",
        }
    """
    if serializer is None:
        serializer = Serializer()
    return serializer.serialize(obj, depth=0)


def enclose_indent_comma_sep(
    left: str,
    values: Iterable[str],
    right: str,
    indent: str | None,
    depth: int,
) -> str:
    if indent is None:
        return left + ", ".join(values) + right
    lines = [indent * (depth + 1) + x for x in values]
    body = (",\n").join(lines) + ","
    return left + "\n" + body + "\n" + depth * indent + right


class Serializer:
    def __init__(
        self,
        indent: str | None = None,
        with_dataclass_name: bool = True,
        serialization_functions: dict[type, SerializeFunction] | None = None,
    ):
        self.indent = indent
        self.with_dataclass_name = with_dataclass_name
        self.serialization_functions = (
            serialization_functions if serialization_functions is not None else {}
        )

    def serialize(self, v: object, depth: int) -> str:
        # If we have a custom serialization function for this type, use it.
        if func := self.serialization_functions.get(type(v)):
            return func(v)

        # If the type encountered is a ZiggySerializer, we let it serialize itself and output the
        # required Ziggy string literal.
        if isinstance(v, ZiggySerializer):
            s = v.ziggy_serialize()
            match s:
                case QuotedString():
                    return serialize_quoted_string(s.value)
                case MultilineString():
                    return serialize_multiline_string(s.value)
                case TaggedLiteral():
                    return serialize_tagged_literal(s.value, tag=s.tag)
                case _:
                    raise ValueError()

        # Otherwise, we do default serialization of the object according to its runtime type.
        # Beginning with the literal case. Stateless functions are enough.
        match v:
            case None:
                return "null"
            case bool():
                return "true" if v else "false"
            case str():
                return serialize_quoted_string(v)
            case bytes():
                return serialize_quoted_string(v.decode())
            case bytearray():
                return serialize_quoted_string(bytes(v).decode())
            case int():
                return serialize_integer(v)
            case float():
                return serialize_float(v)

        # Container case. We track the depth for indentation purpose.
        if isinstance(v, Sequence):
            return self.serialize_sequence(v, depth)
        elif isinstance(v, Mapping):
            return self.serialize_mapping(v, depth)
        elif is_dataclass(v):
            return self.serialize_dataclass(v, depth)

        raise ValueError("unsupported type", type(v))

    def serialize_sequence(self, seq: Sequence, depth: int) -> str:
        vals = [self.serialize(x, depth + 1) for x in seq]
        return enclose_indent_comma_sep("[", vals, "]", self.indent, depth)

    def serialize_mapping(self, d: Mapping, depth: int) -> str:
        vals = []
        for k, v in d.items():
            vals.append(f'"{k:s}": {self.serialize(v, depth+1)}')
        return enclose_indent_comma_sep("{", vals, "}", self.indent, depth)

    def serialize_dataclass(self, dc, depth: int) -> str:
        if not is_dataclass(dc):
            raise ValueError

        # We check for annotated field.
        fields_as_tagged_literal: dict[str, TaggedLiteralAnnotation] = {}
        for field_name, annotation, parent_type in annotated_by(
            dc, TaggedLiteralAnnotation
        ):
            fields_as_tagged_literal[field_name] = annotation

        vals = []
        for f in fields(dc):
            if (annotation := fields_as_tagged_literal.get(f.name)) is not None:
                tag = annotation.name
                serialize_function = annotation.serialize_function
                if serialize_function is None:
                    serialize_function = str
                value = getattr(dc, f.name)
                vals.append(f'@{tag}("{serialize_function(value)}")')
                continue
            vals.append(f".{f.name} = {self.serialize(getattr(dc, f.name), depth+1)}")

        s = enclose_indent_comma_sep("{", vals, "}", self.indent, depth)
        if self.with_dataclass_name:
            class_name = type(dc).__name__
            s = class_name + " " + s
        return s


def serialize_quoted_string(s: str) -> str:
    s = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{s}"'


def serialize_multiline_string(s: str) -> str:
    lines = s.split("\n")
    s = "\n".join(["\\\\" + l for l in lines])
    return s


def serialize_tagged_literal(s: str, *, tag: str) -> str:
    s = serialize_quoted_string(s)
    return f"@{tag}({s})"


def serialize_integer(x: int) -> str:
    return str(x)


def serialize_float(x: float) -> str:
    return str(x)


if __name__ == "__main__":

    @dataclass
    class Data:
        foo: list
        bar: float

    class Action(enum.StrEnum):
        Send = enum.auto()
        Clear = enum.auto()

    r = Serializer(
        indent="\t",
        with_dataclass_name=True,
        serialization_functions={
            Action: AsTaggedLiteralFunc(lambda x: x.value, tag="user_action"),
            datetime: AsTaggedLiteralFunc(lambda x: str(x), tag="timestamp"),
        },
    ).serialize(
        [
            1,
            2,
            {
                "command": Action.Send,
                "datetime": datetime.fromisoformat("2024-11-27T22:32:25"),
            },
            {"a": 'OK"you" lucky \n\tboy\'s', "b": [True, False, None, 1]},
            Data(foo=[True, "A", 1], bar=3.14),
        ],
        depth=0,
    )
    print(r)
