#!/bin/bash
# Step 5: S3アップロード

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# .envファイルから環境変数を読み込む
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# デフォルト値を設定
S3_BUCKET="${S3_BUCKET_NAME:-rsspeaker-audio-files}"
S3_REGION="${S3_REGION:-ap-southeast-2}"

echo "=================================="
echo "Step 5: Uploading to S3..."
echo "=================================="

# 最新のoutputディレクトリを探す
LATEST_OUTPUT=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_OUTPUT" ]; then
    echo "✗ 音声ファイルディレクトリが見つかりません"
    echo "  先に step4_generate_audio.sh を実行してください"
    exit 1
fi

# 末尾のスラッシュを削除
OUTPUT_DIR="${LATEST_OUTPUT%/}"
echo "Output directory: $OUTPUT_DIR"

# タイムスタンプを抽出（output/20251201_161058 → 20251201_161058）
TIMESTAMP=$(basename "$OUTPUT_DIR")

# AWS CLIの検索
AWS_CLI=""
for path in /usr/local/bin/aws /usr/bin/aws $(which aws 2>/dev/null); do
    if [ -f "$path" ] && [ -x "$path" ]; then
        AWS_CLI="$path"
        break
    fi
done

if [ -z "$AWS_CLI" ]; then
    echo "✗ AWS CLI not found"
    exit 1
fi

echo "Using AWS CLI: $AWS_CLI"

# 音声ファイル数を確認
FILE_COUNT=$(find "$OUTPUT_DIR" -name "*.wav" | wc -l)
echo "Found $FILE_COUNT audio files"

if [ $FILE_COUNT -eq 0 ]; then
    echo "✗ No audio files found"
    exit 1
fi

# S3にアップロード
echo "Uploading to S3..."
$AWS_CLI s3 sync "$OUTPUT_DIR" "s3://${S3_BUCKET}/${TIMESTAMP}/"
S3_EXIT_CODE=$?

if [ $S3_EXIT_CODE -eq 0 ]; then
    echo "✓ S3 upload completed"
    echo "S3 URL: https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/${TIMESTAMP}/"
else
    echo "✗ S3 upload failed (exit code: $S3_EXIT_CODE)"
    exit 1
fi

exit 0
