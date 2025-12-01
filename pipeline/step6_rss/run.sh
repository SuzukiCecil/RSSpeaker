#!/bin/bash
# Step 6: Podcast RSSフィード生成

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================="
echo "Step 6: Generating Podcast RSS..."
echo "=================================="

# 仮想環境の確認とアクティベート
if [ ! -d "venv" ]; then
    echo "✗ 仮想環境が見つかりません"
    echo "  ./setup.sh を実行してください"
    exit 1
fi

source venv/bin/activate

# Podcast RSSフィード生成
python3 pipeline/step6_rss/generate_podcast_rss.py

echo "✓ Podcast RSS feed generated"

deactivate
exit 0
