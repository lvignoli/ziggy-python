from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from ziggy.parser import parse


@dataclass
class Message:
    sender: str
    payload: Picture
    location: Location
    next: str | None


@dataclass
class Picture:
    width: int
    height: int
    data: str


@dataclass
class Location:
    latitude: float
    longitude: float


@pytest.mark.parametrize(
    "case_name, input, parser_options, expected",
    [
        (
            "Nested arrays, maps, structs",
            """[1, [2, [3, { "a": 1, "b": ["alpha", "beta"], "c": { .name = "Louis", .age = 29 } }]]]""",
            {},
            [
                1,
                [
                    2,
                    [
                        3,
                        {
                            "a": 1,
                            "b": ["alpha", "beta"],
                            "c": {"name": "Louis", "age": 29},
                        },
                    ],
                ],
            ],
        ),
        (
            "With literals",
            '{"today": @date("2024-11-24"), "now": @time("1732479081")}',
            {
                "literals": {
                    "date": lambda x: tuple(x.split("-")),
                    "time": lambda x: datetime.fromtimestamp(int(x)),
                }
            },
            {"today": ("2024", "11", "24"), "now": datetime.fromtimestamp(1732479081)},
        ),
        (
            "Top level struct",
            """.title = "Post",
            .author = "Louis Vignoli",
            .draft = "true",
            """,
            {},
            {"title": "Post", "author": "Louis Vignoli", "draft": "true"},
        ),
        (
            "A complex top level struct.",
            """
            .louis = {
                .name = "Louis",
                .age = 29,
                .description =
                    \\\\Je m'appelle Louis.
                    \\\\J'aime coder en Zig.
                ,
                .friends = [
                    // Ma nana.
                    "Noémie",

                    // Mon chat.
                    "Piana",
                    "Louis",
            ],
                .data = { "a": 1, "b": 2, "c": "abc", "d": [1, 2, 3] },
                .title = "Hot Startup wants Senior Zig Engineer",
                .creation_date = @date("2024-01-01"),
                .publish_date = @date("2024-01-10"),
                .expiry_date = @date("2024-02-10"),
                .text = "Hot Startup...",
            },
            """,
            {},
            {
                "louis": {
                    "name": "Louis",
                    "age": 29,
                    "description": "Je m'appelle Louis.\nJ'aime coder en Zig.",
                    "friends": ["Noémie", "Piana", "Louis"],
                    "data": {"a": 1, "b": 2, "c": "abc", "d": [1, 2, 3]},
                    "title": "Hot Startup wants Senior Zig Engineer",
                    "creation_date": "2024-01-01",
                    "publish_date": "2024-01-10",
                    "expiry_date": "2024-02-10",
                    "text": "Hot Startup...",
                }
            },
        ),
        (
            "Several dataclasses",
            """Message {
                .sender = "Louis",
                .payload = Picture {
                    .width = 480,
                    .height = 640,
                    .data = "abcdefghij"
                },
                .location = Location {
                    .latitude = 21.01,
                    .longitude = 142.9,
                },
                .next = null
            }
            """,
            {
                "structs": {
                    "Message": Message,
                    "Picture": Picture,
                    "Location": Location,
                }
            },
            Message(
                sender="Louis",
                payload=Picture(width=480, height=640, data="abcdefghij"),
                location=Location(latitude=21.01, longitude=142.9),
                next=None,
            ),
        ),
    ],
)
def test_simple(
    case_name: str,
    input: str,
    parser_options: dict,
    expected,
):
    actual = parse(input, **parser_options)
    assert actual == expected
