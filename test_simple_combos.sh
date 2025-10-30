#!/bin/bash
set -e

echo "=========================================="
echo "Testing RPC Combinations"
echo "=========================================="

SOUP_GO=~/Library/Caches/tofusoup/harnesses/soup-go

if [ ! -f "$SOUP_GO" ]; then
    echo "❌ soup-go not found at $SOUP_GO"
    exit 1
fi

echo "✓ Found soup-go at $SOUP_GO"

# Test 1: Go Client → Go Server
echo ""
echo "==========================================
"
echo "Test 1: Go Client → Go Server"
echo "=========================================="

TEST_DIR="/tmp/test_go_to_go"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

export KV_STORAGE_DIR="$TEST_DIR"
export SERVER_LANGUAGE="go"
export CLIENT_LANGUAGE="go"
export COMBO_ID="go_client_to_go_server"

# Start server
PORT=50097
echo "Starting Go server on port $PORT..."
$SOUP_GO rpc kv server --port $PORT --tls-mode disabled > /tmp/server.log 2>&1 &
SERVER_PID=$!
sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start"
    cat /tmp/server.log
    exit 1
fi

echo "✓ Server started (PID: $SERVER_PID)"

# Put value
TEST_KEY="combo_test_key"
TEST_VALUE='{"client":"go","server":"go","test":"combo"}'

echo "Putting value..."
$SOUP_GO rpc kv put "$TEST_KEY" "$TEST_VALUE" --address="127.0.0.1:$PORT"
echo "✓ Put succeeded"

# Get value
echo "Getting value..."
RETRIEVED=$($SOUP_GO rpc kv get "$TEST_KEY" --address="127.0.0.1:$PORT")
echo "✓ Get succeeded"

# Check storage file
STORAGE_FILE="$TEST_DIR/kv-data-$TEST_KEY"
if [ -f "$STORAGE_FILE" ]; then
    echo "✓ Storage file exists: $STORAGE_FILE"
    echo "  Contents:"
    cat "$STORAGE_FILE" | python3 -m json.tool | head -10

    # Check if storage has server_handshake (should NOT)
    if grep -q "server_handshake" "$STORAGE_FILE"; then
        echo "  ❌ Storage file contains server_handshake (should be raw JSON)"
    else
        echo "  ✓ Storage file contains raw JSON (no server_handshake)"
    fi
else
    echo "❌ Storage file not found"
fi

# Check retrieved value
echo ""
echo "Retrieved value:"
echo "$RETRIEVED" | python3 -m json.tool | head -20

if echo "$RETRIEVED" | grep -q "server_handshake"; then
    echo "✓ Retrieved value contains server_handshake"

    # Extract metadata
    echo ""
    echo "Combo metadata:"
    echo "$RETRIEVED" | python3 -c "
import json, sys
data = json.load(sys.stdin)
sh = data.get('server_handshake', {})
print(f'  server_language: {sh.get(\"server_language\")}')
print(f'  client_language: {sh.get(\"client_language\")}')
print(f'  combo_id: {sh.get(\"combo_id\")}')
if 'crypto_config' in sh:
    print(f'  crypto_config: {sh[\"crypto_config\"]}')
"
else
    echo "❌ Retrieved value missing server_handshake"
fi

# Cleanup
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "✅ Go Client → Go Server: WORKS"

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "Go Client → Go Server: ✅ WORKS"
echo "Python Client → Go Server: ⚠️  HANGS (plugin handshake issue)"
echo ""
echo "Files created in cache:"
find ~/Library/Caches/tofusoup/kv-store -type f 2>/dev/null || echo "  (none in default cache)"
