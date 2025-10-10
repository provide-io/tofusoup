#!/bin/bash
# Direct test of Go client → Python server

echo "Testing Go Client → Python Server"
echo "=================================="
echo ""

# Set up environment
export KV_STORAGE_DIR=/tmp
export LOG_LEVEL=INFO

# Path to executables
SOUP_GO="/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go"
SOUP=$(which soup)

echo "Go client: $SOUP_GO"
echo "Python server: $SOUP"
echo ""

# Test with soup as the server path
echo "Running: $SOUP_GO rpc client test $SOUP"
echo ""

timeout 45 "$SOUP_GO" rpc client test "$SOUP" 2>&1 | head -100
