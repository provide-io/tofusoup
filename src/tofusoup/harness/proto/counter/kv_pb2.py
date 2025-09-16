#
# tofusoup/harness/proto/counter/kv_pb2.py
#
"""Generated protocol buffer code."""

from google.protobuf import (
    descriptor as _descriptor,
    descriptor_pool as _descriptor_pool,
    runtime_version as _runtime_version,
    symbol_database as _symbol_database,
)
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 6, 31, 0, "", "kv.proto")
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x08kv.proto\x12\x05proto"\x19\n\nGetRequest\x12\x0b\n\x03key\x18\x01 \x01(\t"\x1c\n\x0bGetResponse\x12\r\n\x05value\x18\x01 \x01(\x03"<\n\nPutRequest\x12\x12\n\nadd_server\x18\x01 \x01(\r\x12\x0b\n\x03key\x18\x02 \x01(\t\x12\r\n\x05value\x18\x03 \x01(\x03"\x07\n\x05\x45mpty""\n\nSumRequest\x12\t\n\x01\x61\x18\x01 \x01(\x03\x12\t\n\x01\x62\x18\x02 \x01(\x03"\x18\n\x0bSumResponse\x12\t\n\x01r\x18\x01 \x01(\x03\x32_\n\x07\x43ounter\x12,\n\x03Get\x12\x11.proto.GetRequest\x1a\x12.proto.GetResponse\x12&\n\x03Put\x12\x11.proto.PutRequest\x1a\x0c.proto.Empty29\n\tAddHelper\x12,\n\x03Sum\x12\x11.proto.SumRequest\x1a\x12.proto.SumResponseB\tZ\x07./protob\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "kv_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals["DESCRIPTOR"]._loaded_options = None
    _globals["DESCRIPTOR"]._serialized_options = b"Z\007./proto"
    _globals["_GETREQUEST"]._serialized_start = 19
    _globals["_GETREQUEST"]._serialized_end = 44
    _globals["_GETRESPONSE"]._serialized_start = 46
    _globals["_GETRESPONSE"]._serialized_end = 74
    _globals["_PUTREQUEST"]._serialized_start = 76
    _globals["_PUTREQUEST"]._serialized_end = 136
    _globals["_EMPTY"]._serialized_start = 138
    _globals["_EMPTY"]._serialized_end = 145
    _globals["_SUMREQUEST"]._serialized_start = 147
    _globals["_SUMREQUEST"]._serialized_end = 181
    _globals["_SUMRESPONSE"]._serialized_start = 183
    _globals["_SUMRESPONSE"]._serialized_end = 207
    _globals["_COUNTER"]._serialized_start = 209
    _globals["_COUNTER"]._serialized_end = 304
    _globals["_ADDHELPER"]._serialized_start = 306
    _globals["_ADDHELPER"]._serialized_end = 363
# @@protoc_insertion_point(module_scope)


# 🍲🥄📄🪄
