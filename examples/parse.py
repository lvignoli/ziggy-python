import dataclasses
import datetime

import ziggy


@dataclasses.dataclass
class Message:
    sender: str
    content: str
    timestamp: int


data = """Message {
    .sender = "Allocgator",
    .content = "Hello World!",
    .timestamp = @date("2025-10-25T11:34")
}
"""


v = ziggy.parse(data)
print("Vanilla parsing:")
print("`Message` Ziggy struct is parsed as a Python dictionnary.")
print(v)
print()

print("Parsing with a struct declaration:")
print("`Message` Ziggy struct is parsed as a Python `Message` dataclass instance.")
v = ziggy.parse(
    data,
    structs={"Message": Message},
    literals={"date": datetime.datetime.fromisoformat},
)
print(v)
