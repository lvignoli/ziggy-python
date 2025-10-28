import enum
from dataclasses import dataclass
from datetime import datetime

import ziggy


@dataclass
class Data:
    foo: list[object]
    bar: float


class Action(enum.StrEnum):
    Send = enum.auto()
    Clear = enum.auto()


r = ziggy.Serializer(
    indent="\t",
    with_dataclass_name=True,
    serialization_functions={
        Action: ziggy.AsTaggedLiteralFunc(lambda x: x.value, tag="user_action"),
        datetime: ziggy.AsTaggedLiteralFunc(lambda x: str(x), tag="timestamp"),
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
