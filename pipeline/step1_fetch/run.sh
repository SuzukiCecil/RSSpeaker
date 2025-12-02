#!/bin/bash
# Step 1: Google Custom Search APIでニュース概要生成

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================="
echo "Step 1: Generating news topics..."
echo "=================================="

# 仮想環境の確認とアクティベート
if [ ! -d "venv" ]; then
    echo "✗ 仮想環境が見つかりません"
    echo "  ./setup.sh を実行してください"
    exit 1
fi

source venv/bin/activate

# dataディレクトリ作成
mkdir -p data

# Google Custom Search APIでニュース概要生成
python3 pipeline/step1_fetch/generate_news_topics_search.py || exit 1

# 最新のtopics.jsonを確認
LATEST_DIR=$(ls -td data/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_DIR" ]; then
    echo "✗ ニュース概要が見つかりません"
    exit 1
fi

LATEST_TOPICS="${LATEST_DIR}topics.json"
if [ ! -f "$LATEST_TOPICS" ]; then
    echo "✗ topics.jsonが見つかりません"
    exit 1
fi

echo "✓ News topics saved: $LATEST_TOPICS"

deactivate
exit 0
