module github.com/provide-io/tofusoup/harness/soup-go

go 1.21

require (
	github.com/hashicorp/go-hclog v1.6.3
	github.com/hashicorp/hcl/v2 v2.19.1
	github.com/spf13/cobra v1.10.1
	github.com/vmihailenco/msgpack/v5 v5.4.1
	github.com/zclconf/go-cty v1.14.1
)

require (
	github.com/agext/levenshtein v1.2.1 // indirect
	github.com/apparentlymart/go-textseg/v15 v15.0.0 // indirect
	github.com/fatih/color v1.13.0 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/mattn/go-colorable v0.1.12 // indirect
	github.com/mattn/go-isatty v0.0.14 // indirect
	github.com/mitchellh/go-wordwrap v0.0.0-20150314170334-ad45545899c7 // indirect
	github.com/spf13/pflag v1.0.9 // indirect
	github.com/vmihailenco/tagparser/v2 v2.0.0 // indirect
	golang.org/x/sys v0.18.0 // indirect
	golang.org/x/text v0.11.0 // indirect
)

replace github.com/provide-io/tofusoup/proto/kv => ../../proto/kv
