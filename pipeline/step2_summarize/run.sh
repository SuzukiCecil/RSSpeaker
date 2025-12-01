#!/bin/bash
# Step 2: 詳細ナレーション生成

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================="
echo "Step 2: Generating narrations..."
echo "=================================="

# 仮想環境の確認とアクティベート
if [ ! -d "venv" ]; then
    echo "✗ 仮想環境が見つかりません"
    echo "  ./setup.sh を実行してください"
    exit 1
fi

source venv/bin/activate

# 最新のニュース概要ディレクトリを探す
LATEST_DIR=$(ls -td data/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_DIR" ]; then
    echo "✗ ニュース概要ディレクトリが見つかりません"
    echo "  先に step1を実行してください"
    exit 1
fi

LATEST_TOPICS="${LATEST_DIR}topics.json"
if [ ! -f "$LATEST_TOPICS" ]; then
    echo "✗ topics.jsonが見つかりません"
    exit 1
fi

SUMMARIZED_JSON="${LATEST_DIR}summarized.json"

echo "Input: $LATEST_TOPICS"
echo "Output: $SUMMARIZED_JSON"

# 詳細ナレーション生成
python3 pipeline/step2_summarize/generate_detailed_narration.py "$LATEST_TOPICS" "$SUMMARIZED_JSON" || exit 1

echo "✓ Narration generation completed: $SUMMARIZED_JSON"

deactivate
exit 0
