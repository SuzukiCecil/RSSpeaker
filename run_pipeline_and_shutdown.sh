#!/bin/bash
set -e

echo "=================================="
echo "RSSpeaker Pipeline Starting..."
echo "=================================="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="pipeline_${TIMESTAMP}.log"

# stdbufでバッファリング無効化
stdbuf -oL -eL ./run_pipeline.sh 2>&1 | tee "$LOG_FILE"

echo "✓ Pipeline completed at $(date)"
echo "Shutting down EC2 instance in 3 minutes..."
sudo shutdown -h +3

