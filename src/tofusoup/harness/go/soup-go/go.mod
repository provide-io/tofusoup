module github.com/provide-io/tofusoup/harness/soup-go

go 1.21

require (
	google.golang.org/grpc v1.64.0
	google.golang.org/protobuf v1.34.1
)

replace github.com/provide-io/tofusoup/proto/kv => ../../proto/kv