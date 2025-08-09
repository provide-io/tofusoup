from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor, message as _message

DESCRIPTOR: _descriptor.FileDescriptor

class GetRequest(_message.Message):
    __slots__ = ("key",)
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: str
    def __init__(self, key: str | None = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    def __init__(self, value: int | None = ...) -> None: ...

class PutRequest(_message.Message):
    __slots__ = ("add_server", "key", "value")
    ADD_SERVER_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    add_server: int
    key: str
    value: int
    def __init__(
        self,
        add_server: int | None = ...,
        key: str | None = ...,
        value: int | None = ...,
    ) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SumRequest(_message.Message):
    __slots__ = ("a", "b")
    A_FIELD_NUMBER: _ClassVar[int]
    B_FIELD_NUMBER: _ClassVar[int]
    a: int
    b: int
    def __init__(self, a: int | None = ..., b: int | None = ...) -> None: ...

class SumResponse(_message.Message):
    __slots__ = ("r",)
    R_FIELD_NUMBER: _ClassVar[int]
    r: int
    def __init__(self, r: int | None = ...) -> None: ...
