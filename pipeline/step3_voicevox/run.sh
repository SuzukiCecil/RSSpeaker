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
    echo "⚠️  VOICEVOX が起動していません。自動起動します..."

    # 既存のコンテナを削除（存在する場合）
    if docker ps -a --format '{{.Names}}' | grep -q '^voicevox-engine$'; then
        echo "  既存のコンテナを削除中..."
        docker rm -f voicevox-engine > /dev/null 2>&1
    fi

    # VOICEVOXコンテナを起動
    echo "  VOICEVOXコンテナを起動中..."
    docker run --rm -d -p 50021:50021 --name voicevox-engine voicevox/voicevox_engine:cpu-latest > /dev/null

    # 起動待機（最大60秒）
    echo "  起動を待機中..."
    for i in {1..60}; do
        if curl -s http://localhost:50021/version > /dev/null 2>&1; then
            echo "  ✓ VOICEVOX が起動しました"
            break
        fi
        sleep 1
        if [ $i -eq 60 ]; then
            echo "  ✗ VOICEVOX の起動がタイムアウトしました"
            exit 1
        fi
    done
fi

# バージョン情報取得
VERSION=$(curl -s http://localhost:50021/version)
echo "✓ VOICEVOX is running"
echo "  Version: $VERSION"

exit 0
