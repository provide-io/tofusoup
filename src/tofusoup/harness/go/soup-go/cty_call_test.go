package main

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/function/stdlib"
)

// The oracle is ground truth for a second implementation in another repository,
// so a fault here does not merely fail -- it accuses the code under test. These
// cover the parts that are this harness's own logic rather than go-cty's.

func TestStdlibFunctionsCoversTheWholeStdlib(t *testing.T) {
	// go-cty has no runtime registry to enumerate, so the count is asserted
	// against the number of distinct functions its stdlib declares. Adding one
	// upstream should fail here rather than silently narrow the oracle: that
	// gap is exactly how seven implemented functions ended up with no
	// differential verification at all.
	const wantCount = 83

	if got := len(stdlibFunctions); got != wantCount {
		t.Errorf("oracle exposes %d functions, want %d", got, wantCount)
	}

	for _, name := range []string{
		"assertnotnull", "byteslen", "bytesslice", "sethaselement",
		"setsymmetricdifference", "strlen", "tobool", "tonumber", "tostring",
	} {
		if _, ok := stdlibFunctions[name]; !ok {
			t.Errorf("%s is not reachable from `cty call`", name)
		}
	}
}

func TestBytesRoundTripsThroughBase64(t *testing.T) {
	// "hello world" -- the capsule type has no JSON spelling of its own, so
	// this checks the one the harness invents for it, in both directions.
	arg := json.RawMessage(`{"type":"bytes","value":"aGVsbG8gd29ybGQ="}`)

	val, err := decodeCallArg(arg)
	if err != nil {
		t.Fatalf("decodeCallArg: %v", err)
	}
	if !val.Type().Equals(stdlib.Bytes) {
		t.Fatalf("decoded type is %s, want the Bytes capsule", val.Type().FriendlyName())
	}
	if got := string(*val.EncapsulatedValue().(*[]byte)); got != "hello world" {
		t.Fatalf("decoded buffer is %q", got)
	}

	result := describeResult("byteslen", val, nil)
	if !result.OK {
		t.Fatalf("describeResult reported %q", result.Error)
	}
	if string(result.Type) != `"bytes"` {
		t.Errorf("result type is %s, want \"bytes\"", result.Type)
	}
	if string(result.Value) != `"aGVsbG8gd29ybGQ="` {
		t.Errorf("result value is %s, want the base64 it came from", result.Value)
	}
}

func TestBytesAcceptsAnEmptyBuffer(t *testing.T) {
	// BytesVal panics on a nil slice, and decoding "" can produce one.
	if _, err := decodeCallArg(json.RawMessage(`{"type":"bytes","value":""}`)); err != nil {
		t.Fatalf("decodeCallArg on an empty buffer: %v", err)
	}
}

func TestBytesRejectsInvalidBase64(t *testing.T) {
	if _, err := decodeCallArg(json.RawMessage(`{"type":"bytes","value":"not base64!"}`)); err == nil {
		t.Fatal("invalid base64 was accepted")
	}
}

func TestAnUnrepresentableResultIsReportedRatherThanOmitted(t *testing.T) {
	// A capsule other than Bytes cannot be marshalled at all. Reporting an
	// error is the point: a caller comparing `{"ok":true}` with no value
	// against its own answer would read agreement out of silence.
	other := cty.Capsule("other", reflect.TypeOf(struct{}{}))
	value := cty.CapsuleVal(other, &struct{}{})

	result := describeResult("hypothetical", value, nil)

	if result.OK {
		t.Fatal("an unmarshalable result was reported as a successful call")
	}
	if result.Error == "" {
		t.Fatal("an unmarshalable result carried no error")
	}
}

func TestBytesSliceTakesALengthNotAnEndIndex(t *testing.T) {
	// Pinned because it is the distinction a reading of the source is most
	// likely to get backwards, and did: `end := offset + length`.
	buf := stdlib.BytesVal([]byte("hello world"))
	offset := cty.NumberIntVal(1)
	length := cty.NumberIntVal(3)

	got, err := stdlibFunctions["bytesslice"].Call([]cty.Value{buf, offset, length})
	if err != nil {
		t.Fatalf("bytesslice: %v", err)
	}

	if sliced := string(*got.EncapsulatedValue().(*[]byte)); sliced != "ell" {
		t.Errorf("bytesslice(buf, 1, 3) is %q, want \"ell\"", sliced)
	}
}
