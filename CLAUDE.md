# RSSpeaker プロジェクト

このプロジェクトは、窓の杜の技術ニュースを毎日自動取得し、GPTで要約、XTTS-v2で音声生成してApple Podcastに配信するシステムです。

## 設計ドキュメント

詳細な設計情報は `.claude/DESIGN.md` を参照してください。

### システム概要

```
EventBridge（1日1回）
        ↓
Lambda（RSS取得 → GPT記事選別＆要約 → テキスト保存）
        ↓
S3（要約テキスト保存）
        ↓
EC2 Spot（XTTS-v2実行：テキスト→音声生成）
        ↓
S3（音声保存）
        ↓
Lambda（Podcast RSSフィード自動生成）
        ↓
S3 + CloudFront（feed.xml公開）
        ↓
Apple Podcast（購読）
```

### 月額コスト: 約150〜300円

- ChatGPT API: 100〜200円
- EC2 Spot: 30〜60円
- S3: 5〜10円
- Lambda + EventBridge: 約15円
- CloudFront: 無料枠内

### 現在のステータス

**フェーズ**: 設計・検討中

**完成している部分**:
- XTTS-v2のローカルテスト環境（Dockerfile, generate.py）

**次に実装すること**:
- Lambda関数（RSS取得・GPT要約）
- EC2音声生成スクリプト
- Podcast RSS生成Lambda
- Terraformインフラ定義

### プロジェクト構成

```
RSSpeaker/
├── .claude/
│   └── DESIGN.md          # 詳細設計ドキュメント
├── Dockerfile             # XTTS-v2テスト環境
├── generate.py            # XTTS-v2テストスクリプト
└── CLAUDE.md              # このファイル（セッション自動読込）
```

## 検討中の課題

1. EC2の自動起動方法（Lambda→EC2 or EventBridge）
2. エラー通知の実装方法
3. 音声品質の調整パラメータ
4. 複数ニュースソース対応

## 参考情報

- 窓の杜RSS: https://forest.watch.impress.co.jp/data/rss/1.0/wf/feed.rdf
- Coqui TTS: https://github.com/coqui-ai/TTS
- Apple Podcast Connect: https://podcastsconnect.apple.com/
