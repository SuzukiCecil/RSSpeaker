#!/bin/bash
# RSSpeaker パイプライン実行
# 各ステップを順番に実行

set -e

echo "=================================="
echo "RSSpeaker Pipeline Starting..."
echo "=================================="

# Step 1: RSS記事取得
./pipeline/step1_fetch/run.sh || exit 1

# Step 2: Geminiで要約
./pipeline/step2_summarize/run.sh || exit 1

# Step 3: VOICEVOX起動確認
./pipeline/step3_voicevox/run.sh || exit 1

# Step 4: 音声ファイル生成
./pipeline/step4_audio/run.sh || exit 1

# Step 5: S3アップロード
./pipeline/step5_s3/run.sh || exit 1

# Step 6: Podcast RSSフィード生成
./pipeline/step6_rss/run.sh || exit 1

echo ""
echo "=================================="
echo "✓ Pipeline Completed!"
echo "=================================="

# 最新のoutputディレクトリを探す
LATEST_OUTPUT=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -n "$LATEST_OUTPUT" ]; then
    TIMESTAMP=$(basename "$LATEST_OUTPUT")
    FILE_COUNT=$(find "$LATEST_OUTPUT" -name "*.wav" 2>/dev/null | wc -l)

    echo "S3: https://rsspeaker-audio-files.s3.ap-southeast-2.amazonaws.com/${TIMESTAMP}/"
    echo "Total files: $FILE_COUNT"
fi

exit 0
