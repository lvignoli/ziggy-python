from __future__ import annotations

import ziggy

msg = """.id = @uuid("..."),
.time = 1710085168,
.payload = Command {
  .do = @action("clear_chat"),
  .sender = "kristoff-it",
  .roles = ["admin", "mod"],
  .extra = {
    "agent": "Mozilla/5.0",
    "os": "Linux/x64",
  },
}
"""

o = ziggy.parse(msg)
print(o)


# Let us now define some object into which we would like to parse, following the schema.
#
#   root = Message
#
#   /// A UUIDv5 value.
#   @uuid = bytes,
#   @action = enum { clear_chat, ban_user },
#
#   struct Message {
#     id: @uuid,
#     time: int,
#     payload: Command | Notification,
#   }
#
#   struct Command {
#     do: @action,
#     sender: bytes,
#     roles: [bytes],
#     /// Optional metadata.
#     extra: ?map[bytes],
#   }
#
#   struct Notification { text: bytes, lvl: int }


from dataclasses import dataclass
from enum import StrEnum


@dataclass
class Command:
    do: Action
    sender: str
    roles: list[str]
    extra: dict[str, str]


@dataclass
class Notification:
    text: str
    lvl: int


type UUID = str


class Action(StrEnum):
    ClearChat = "clear_chat"
    BanUser = "ban_user"


def parse_uuid_literal(s: str) -> UUID:
    return s


def parse_action_literal(s: str) -> Action:
    match s:
        case "clear_chat":
            return Action.ClearChat
        case "ban_user":
            return Action.BanUser
        case _:
            raise ValueError(f"unknown action: {s}")


o_with_message = ziggy.parse(
    msg,
    literals={
        "uuid": parse_uuid_literal,
        "action": parse_action_literal,
    },
    structs={"Command": Command},
)
print(o_with_message)

s = ziggy.serialize(o_with_message, serializer=ziggy.Serializer(indent="    "))
print(s)
