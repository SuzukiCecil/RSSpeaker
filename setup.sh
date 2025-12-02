#!/bin/bash
# RSSpeaker環境セットアップスクリプト

set -e

echo "RSSpeaker環境セットアップを開始します"
echo "=========================================="

# システムパッケージのインストール（Ubuntu/Debian）
if [ -f /etc/debian_version ]; then
    echo "システムパッケージをインストール中..."
    sudo apt update
    sudo apt install -y python3-venv python3-pip unzip curl
    echo "✓ システムパッケージをインストールしました"
fi

# AWS CLI v2のインストール確認
if ! command -v aws &> /dev/null; then
    echo "AWS CLI v2をインストール中..."
    cd /tmp
    curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
    cd - > /dev/null
    echo "✓ AWS CLI v2をインストールしました"
else
    echo "✓ AWS CLI は既にインストールされています ($(aws --version))"
fi

# Python3のバージョン確認
echo "Python3のバージョン確認..."
python3 --version

# 仮想環境の作成
if [ ! -d "venv" ]; then
    echo "仮想環境を作成中..."
    python3 -m venv venv
    echo "✓ 仮想環境を作成しました"
else
    echo "✓ 仮想環境は既に存在します"
fi

# 仮想環境のアクティベート
echo "仮想環境をアクティベート中..."
source venv/bin/activate

# pipのアップグレード
echo "pipをアップグレード中..."
pip install --upgrade pip

# 依存パッケージのインストール
echo "依存パッケージをインストール中..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✓ セットアップが完了しました"
echo ""
echo "使用方法:"
echo "  1. 仮想環境をアクティベート: source venv/bin/activate"
echo "  2. パイプライン実行: ./run_pipeline.sh"
echo "  3. 仮想環境を終了: deactivate"
echo "=========================================="
