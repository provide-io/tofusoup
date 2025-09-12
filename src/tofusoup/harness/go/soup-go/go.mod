module github.com/provide-io/tofusoup/harness/soup-go

go 1.21

require (
	github.com/hashicorp/go-hclog v1.6.3
	github.com/spf13/cobra v1.10.1
)

require (
	github.com/fatih/color v1.13.0 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/mattn/go-colorable v0.1.12 // indirect
	github.com/mattn/go-isatty v0.0.14 // indirect
	github.com/spf13/pflag v1.0.9 // indirect
	golang.org/x/sys v0.18.0 // indirect
)

replace github.com/provide-io/tofusoup/proto/kv => ../../proto/kv
