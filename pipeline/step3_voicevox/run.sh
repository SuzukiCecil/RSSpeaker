#!/bin/bash
# Step 3: VOICEVOX起動確認

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================="
echo "Step 3: Checking VOICEVOX..."
echo "=================================="

# VOICEVOXの起動確認
if ! curl -s http://localhost:50021/version > /dev/null 2>&1; then
    echo "✗ VOICEVOX が起動していません"
    echo ""
    echo "以下のコマンドでVOICEVOXを起動してください:"
    echo "  docker run --rm -d -p 50021:50021 --name voicevox-engine voicevox/voicevox_engine:cpu-latest"
    echo ""
    exit 1
fi

# バージョン情報取得
VERSION=$(curl -s http://localhost:50021/version)
echo "✓ VOICEVOX is running"
echo "  Version: $VERSION"

exit 0
