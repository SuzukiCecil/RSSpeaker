#!/bin/bash
# Step 4: 音声ファイル生成

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================="
echo "Step 4: Generating audio..."
echo "=================================="

# 仮想環境の確認とアクティベート
if [ ! -d "venv" ]; then
    echo "✗ 仮想環境が見つかりません"
    echo "  ./setup.sh を実行してください"
    exit 1
fi

source venv/bin/activate

# .envファイルを読み込む
if [ -f ".env" ]; then
    set -a
    source <(cat .env | sed 's/#.*$//' | grep -v '^$')
    set +a
fi

# 最新の記事ディレクトリを探す
LATEST_DIR=$(ls -td data/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_DIR" ]; then
    echo "✗ 記事ディレクトリが見つかりません"
    echo "  先に step1_fetch_rss.sh を実行してください"
    exit 1
fi

SUMMARIZED_JSON="${LATEST_DIR}summarized.json"
if [ ! -f "$SUMMARIZED_JSON" ]; then
    echo "✗ summarized.jsonが見つかりません"
    echo "  先に step2_summarize.sh を実行してください"
    exit 1
fi

echo "Input: $SUMMARIZED_JSON"

# タイムスタンプを抽出（data/20251201_154625/ → 20251201_154625）
TIMESTAMP=$(basename "$LATEST_DIR")
OUTPUT_DIR="output/${TIMESTAMP}"

mkdir -p "$OUTPUT_DIR"
echo "Output directory: $OUTPUT_DIR"

# 音声生成
python3 -u pipeline/step4_audio/generate_audio_from_json.py "$SUMMARIZED_JSON" "$OUTPUT_DIR"
AUDIO_EXIT_CODE=$?

echo ""
echo "✓ Audio generation completed (exit code: $AUDIO_EXIT_CODE)"
echo "Generated files:"
ls -lh "$OUTPUT_DIR/" || echo "No files found"

if [ $AUDIO_EXIT_CODE -ne 0 ]; then
    deactivate
    exit $AUDIO_EXIT_CODE
fi

deactivate
exit 0
