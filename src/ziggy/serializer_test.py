from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from ziggy.serializer import (
    AsQuotedStringFunc,
    AsTaggedLiteralFunc,
    MultilineString,
    QuotedString,
    Serializer,
    TaggedLiteral,
    ZiggySerializer,
    serialize,
)


@dataclass
class Book(ZiggySerializer):
    title: str
    author: str

    def ziggy_serialize(self) -> QuotedString:
        return QuotedString(f"{self.title}, by {self.author}")


@dataclass
class BookMultiline(ZiggySerializer):
    title: str
    author: str

    def ziggy_serialize(self) -> MultilineString:
        return MultilineString(f"{self.title}\nby {self.author}")


@dataclass
class BookWithTag(ZiggySerializer):
    title: str
    author: str

    def ziggy_serialize(self) -> TaggedLiteral:
        return TaggedLiteral(value=f"{self.title}, by {self.author}", tag="book")


@dataclass
class Data:
    foo: list
    bar: float


def my_date_func(x: datetime) -> str:
    return f"{x.time().hour}:{x.time().minute} on the {x.date()}"


@pytest.mark.parametrize(
    "case_name, input, serializer, expected",
    [
        (
            "complex object",
            [
                1,
                2,
                {"a": 'OK"you" lucky \n\tboy\'s', "b": [True, False, None, 1]},
                Data(foo=[True, "A", 1], bar=3.14),
                BookWithTag("Ruy Blas", "Victor Hugo"),
                datetime.fromisoformat("2024-11-30 17:26"),
            ],
            Serializer(
                indent="\t",
                serialization_functions={
                    datetime: AsTaggedLiteralFunc(my_date_func, tag="date")
                },
            ),
            """[
	1,
	2,
	{
		"a": "OK\\\"you\\\" lucky \\n\\tboy's",
		"b": [
			true,
			false,
			null,
			1,
		],
	},
	Data {
		.foo = [
			true,
			"A",
			1,
		],
		.bar = 3.14,
	},
	@book("Ruy Blas, by Victor Hugo"),
	@date("17:26 on the 2024-11-30"),
]""",
        ),
        (
            "custom serializer, quoted string",
            Book(title="Ruy Blas", author="Victor Hugo"),
            Serializer(),
            '"Ruy Blas, by Victor Hugo"',
        ),
        (
            "custom serializer, multiline",
            BookMultiline(title="Ruy Blas", author="Victor Hugo"),
            Serializer(),
            """\\\\Ruy Blas
\\\\by Victor Hugo""",
        ),
        (
            "custom serializer, tagged literal",
            BookWithTag(title="Ruy Blas", author="Victor Hugo"),
            Serializer(),
            '@book("Ruy Blas, by Victor Hugo")',
        ),
        (
            "serialization function with tag",
            BookWithTag(title="Ruy Blas", author="Victor Hugo"),
            Serializer(
                serialization_functions={
                    BookWithTag: AsTaggedLiteralFunc(
                        lambda x: f"{x.title}, by {x.author}",
                        tag="book",
                    )
                },
            ),
            '@book("Ruy Blas, by Victor Hugo")',
        ),
        (
            "override with serialization function",
            Book(title="Ruy Blas", author="Victor Hugo"),
            Serializer(
                serialization_functions={
                    Book: AsQuotedStringFunc(
                        lambda x: f"{x.title}, by {" ".join(
                                [f'{f[0]}.' for f in x.author.split(' ')]
                            )}"
                    )
                },
            ),
            '"Ruy Blas, by V. H."',
        ),
    ],
)
def test_serialize(case_name, input, serializer, expected):
    actual = serialize(input, serializer=serializer)
    assert actual == expected
