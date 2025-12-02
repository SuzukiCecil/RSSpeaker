# RSSpeaker

Gemini AIでユーザーの興味に合わせた最新技術ニュースを生成し、ポッドキャスト音声を自動作成するシステム

## システム構成

```
ホストOS（EC2 Ubuntu）
├── Python仮想環境（venv/）
│   ├── Google Custom Search API（最新ニュース検索）
│   ├── Gemini（要約・ナレーション生成、並列処理）
│   ├── 音声生成（HTTPでVOICEVOXに接続）
│   ├── S3アップロード
│   └── Podcast RSS生成
│
└── Docker
    └── VOICEVOXコンテナ（音声合成エンジン、ポート50021）
```

## 環境セットアップ

### 1. 初回セットアップ

```bash
# リポジトリをクローンまたは配置
cd /path/to/RSSpeaker

# セットアップスクリプトを実行（初回のみ）
./setup.sh
```

`setup.sh` は以下を実行します：
- Python仮想環境（venv）の作成
- pipのアップグレード
- 依存パッケージのインストール（requirements.txtから）

**注意**: EC2では初回セットアップ後、インスタンスを停止・起動しても仮想環境は保持されます（EBSボリュームに保存）。インスタンスをterminateしない限り、`setup.sh`の再実行は不要です。

### 2. ユーザー設定（user_preferences.json）

初回は`user_preferences.json.example`をコピーして`user_preferences.json`を作成してください：

```bash
cp user_preferences.json.example user_preferences.json
```

`user_preferences.json`でニュース生成の設定をカスタマイズできます：

```json
{
  "interests": [
    "人工知能（AI）",
    "機械学習",
    "大規模言語モデル（LLM）",
    "開発者ツール",
    "PHP言語",
    "Laravel",
    "ソフトウェア開発手法",
    "クラウドサービス",
    "Web開発",
    "オープンソース",
    "セキュリティ",
    "データベース技術",
    "DevOps",
    "React",
    "Node.js"
  ],
  "language": "日本語",
  "news_count": 10,
  "search_query_count": 10,
  "target_audience": "エンジニア・技術者",
  "content_depth": "詳細な技術解説を含む"
}
```

- **interests**: 興味のある技術分野（配列で複数指定可能）
- **news_count**: 生成するニュース数（デフォルト: 10）
- **search_query_count**: Google検索クエリ数（デフォルト: 10）
- **target_audience**: 対象読者層
- **content_depth**: コンテンツの詳細度

**注意**: `user_preferences.json`は`.gitignore`に含まれており、個人設定として管理されます。

### 3. 環境変数設定（.envファイル）

`.env.example`をコピーして`.env`ファイルを作成し、必要な設定を記入します：

```bash
cp .env.example .env
```

`.env`ファイルを編集して、以下の必須項目を設定してください：

```bash
# Gemini API Key（必須）
GEMINI_API_KEY=your-gemini-api-key-here

# Google Custom Search API（必須）
GOOGLE_SEARCH_API_KEY=your-google-search-api-key-here
GOOGLE_SEARCH_CX=your-custom-search-engine-id-here

# S3 Bucket（デフォルト値が設定済み、変更可能）
S3_BUCKET_NAME=rsspeaker-audio-files
S3_REGION=ap-southeast-2

# Podcast設定（任意、デフォルト値が設定済み）
PODCAST_TITLE=RSSpeaker Tech News
PODCAST_DESCRIPTION=AI技術ニュースを音声でお届けします
PODCAST_AUTHOR=RSSpeaker
PODCAST_EMAIL=podcast@example.com

# 並列処理設定
GEMINI_MAX_WORKERS=5          # Geminiナレーション生成の並列数（デフォルト: 5）
VOICEVOX_MAX_WORKERS=3        # 音声生成の並列数（推奨: 3）
# t3.medium (2 vCPU, 4GB RAM): VOICEVOX_MAX_WORKERS=1（メモリ不足のため2並列は不可）
# c7i.xlarge (4 vCPU, 8GB RAM): VOICEVOX_MAX_WORKERS=3推奨（安全マージン考慮）
```

**重要**: `.env`ファイルは`.gitignore`に含まれており、Gitで管理されません。APIキーなどの機密情報は安全に保管されます。

**AWS認証**: EC2ではIAMロールを使用するため、AWS認証情報の設定は不要です。

### 4. VOICEVOX起動（Dockerコンテナ）

```bash
docker run --rm -d -p 50021:50021 --name voicevox-engine voicevox/voicevox_engine:cpu-latest
```

VOICEVOXは音声合成エンジンで、HTTPリクエストで音声生成を行います。

## パイプライン実行

### 全ステップを一括実行

```bash
./run_pipeline.sh
```

### ステップごとに実行（テスト・デバッグ用）

```bash
# Step 1: Google Custom Search APIでニュース検索
./pipeline/step1_fetch/run.sh

# Step 2: Geminiで詳細ナレーション生成
./pipeline/step2_summarize/run.sh

# Step 3: VOICEVOX起動確認
./pipeline/step3_voicevox/run.sh

# Step 4: 音声ファイル生成
./pipeline/step4_audio/run.sh

# Step 5: S3アップロード
./pipeline/step5_s3/run.sh

# Step 6: Podcast RSSフィード生成
./pipeline/step6_rss/run.sh
```

## パイプライン処理フロー

1. **Google Custom Search API** (`pipeline/step1_fetch/run.sh`)
   - **検索クエリ生成**: Gemini API (gemini-2.5-flash) で`user_preferences.json`の興味分野から10個の検索クエリを生成
   - **最新ニュース検索**: Google Custom Search APIで過去24時間以内のニュースを検索（`dateRestrict=d1`パラメータ使用）
   - **要約生成**: 検索結果のsnippetを基にGeminiが200-300字の要約を生成（幻覚を防止）
   - **重複防止**: 同一ニュースの重複を自動的に排除
   - **日付フィルタリング**: 24時間以内のニュースのみを厳密にフィルタリング
   - 出力: `data/YYYYMMDD_HHMMSS/topics.json`（10件のニュース概要）

   **重要**: Google Custom Search APIは1日100クエリまで無料。10クエリ × 各10件 = 最大100件の検索結果から10件を選定。

2. **Gemini詳細ナレーション生成** (`pipeline/step2_summarize/run.sh`)
   - **並列処理**: 10件のニュース概要を同時に処理（デフォルト5並列、GEMINI_MAX_WORKERSで調整可能）
   - 各ニュースについて7-10分のナレーション原稿を生成（2000-3000文字）
   - **TTS最適化**: 技術用語の読み方を最適化（AWS→エーダブリューエス、Laravel→ララベルなど）
   - 固有名詞の正しいカタカナ表記、括弧付き読み仮名の禁止
   - プロンプトに厳格な制約を設定し、不要な前置き文言を防止
   - フェイルセーフとして正規表現で前置き文言を自動削除
   - 出力: `data/YYYYMMDD_HHMMSS/summarized.json`

3. **VOICEVOX確認** (`pipeline/step3_voicevox/run.sh`)
   - VOICEVOXエンジンの起動確認
   - `http://localhost:50021`で接続確認

4. **音声生成** (`pipeline/step4_audio/run.sh`)
   - **並列処理対応**: 複数記事を同時に音声生成（デフォルト2並列、VOICEVOX_MAX_WORKERSで調整可能）
   - ナレーション原稿をチャンクに分割（300文字単位）
   - VOICEVOXで各チャンクを音声化
   - WAVファイルを正しく結合（ヘッダー処理）
   - 出力: `output/YYYYMMDD_HHMMSS/*.wav`
   - **パフォーマンス**: ローカル環境で約2.5倍高速化、本番環境（t3.medium）で約50%短縮見込み

5. **S3アップロード** (`pipeline/step5_s3/run.sh`)
   - 生成された音声ファイルをS3にアップロード
   - バケット: `s3://rsspeaker-audio-files/YYYYMMDD_HHMMSS/`

6. **Podcast RSS生成** (`pipeline/step6_rss/run.sh`)
   - Podcast用のRSSフィードを生成
   - S3上の音声ファイルを参照

## ファイル構成

```
RSSpeaker/
├── README.md                          # このファイル
├── requirements.txt                   # Python依存パッケージ
├── setup.sh                           # 初回セットアップスクリプト
├── .gitignore                         # Git除外設定
├── .env.example                       # 環境変数テンプレート
├── .env                               # 環境変数（.gitignoreで除外）
├── user_preferences.json              # ユーザー設定（興味分野など）
│
├── run_pipeline.sh                    # 全パイプライン実行
│
├── pipeline/                          # パイプラインステップディレクトリ
│   ├── step1_fetch/
│   │   ├── run.sh                     # ニュース検索実行スクリプト
│   │   └── generate_news_topics_search.py  # Google Custom Search APIでニュース検索
│   │
│   ├── step2_summarize/
│   │   ├── run.sh                     # ナレーション生成実行スクリプト
│   │   └── generate_detailed_narration.py  # Gemini詳細ナレーション生成（並列処理）
│   │
│   ├── step3_voicevox/
│   │   └── run.sh                     # VOICEVOX起動確認スクリプト
│   │
│   ├── step4_audio/
│   │   ├── run.sh                     # 音声生成実行スクリプト
│   │   └── generate_audio_from_json.py # 音声生成スクリプト（並列処理対応）
│   │
│   ├── step5_s3/
│   │   └── run.sh                     # S3アップロードスクリプト
│   │
│   └── step6_rss/
│       ├── run.sh                     # Podcast RSS生成実行スクリプト
│       └── generate_podcast_rss.py    # Podcast RSS生成スクリプト
│
├── venv/                              # Python仮想環境（自動生成）
├── data/                              # ニュースデータ（自動生成）
│   └── YYYYMMDD_HHMMSS/               # タイムスタンプごとのディレクトリ
│       ├── topics.json                # Google Custom Search API検索結果
│       └── summarized.json            # Gemini詳細ナレーション結果
└── output/                            # 音声ファイル（自動生成）
    └── YYYYMMDD_HHMMSS/               # タイムスタンプごとのディレクトリ
        └── *.wav                      # 生成された音声ファイル
```

## 依存パッケージ

`requirements.txt`:
```
requests==2.31.0
google-generativeai==0.8.5
boto3==1.34.0
python-dotenv==1.0.0
```

## 技術的特徴

### Google Custom Search API統合
- **過去24時間限定検索**: `dateRestrict=d1`パラメータで確実に最新ニュースのみ取得
- **幻覚防止アーキテクチャ**: 検索結果snippetのみから要約生成し、Geminiの幻覚を防止
- **2段階処理**: Geminiで検索クエリ生成 → Custom Search APIで検索 → Geminiで要約生成
- **RSSフィード不要**: 直接Google検索から最新情報を取得
- **ユーザーカスタマイズ**: `user_preferences.json`で興味分野を自由に設定可能
- **無料枠内運用**: 1日100クエリまで無料（1日1回実行で10クエリ使用）

### 並列処理による高速化
- **Step2**: 10件のナレーション生成を5並列で処理（Gemini API）
- **Step4**: 音声生成を2並列で処理（VOICEVOX）
- リトライ機能付きでレート制限にも対応

### TTS最適化
- 技術用語の正しい読み方を自動変換
  - AWS → エーダブリューエス
  - S3 → エススリー
  - Laravel → ララベル
  - Python → パイソン
- 括弧付き読み仮名の自動削除で二重読み防止
- バージョン番号の適切な表記（Python 3.13 → パイソン ばーじょん さんてんいちさん）

### 完全無料運用
- Gemini API無料枠内で動作（gemini-2.5-flash使用）
- S3とCloudFrontの無料枠活用
- EC2 Spotインスタンスで低コスト実現

## トラブルシューティング

### 仮想環境が見つからない

```bash
✗ 仮想環境が見つかりません
  ./setup.sh を実行してください
```

→ `./setup.sh`を実行して仮想環境を作成してください。

### VOICEVOXが起動していない

```bash
✗ VOICEVOX が起動していません
```

→ 以下のコマンドでVOICEVOXを起動してください：
```bash
docker run --rm -d -p 50021:50021 --name voicevox-engine voicevox/voicevox_engine:cpu-latest
```

### Gemini APIレート制限

```bash
⏳ レート制限に達しました。60秒待機してリトライします...
```

→ 自動リトライが実行されます。`GEMINI_MAX_WORKERS`を減らすことで並列数を調整できます。

### 音声ファイルが40秒で切れる

→ `generate_audio_from_json.py`でWAVファイル結合が正しく行われているか確認してください。`concatenate_wav_files()`関数を使用している必要があります。

### S3アップロードに失敗

→ AWS認証情報を確認してください。EC2の場合はIAMロールが正しく設定されているか確認してください。

## 本番環境（EC2）での運用

### EventBridgeスケジュール設定

毎日9:00 JSTに自動実行する設定：

```bash
# SSM経由でコマンド実行
cd /home/ubuntu/rsspeaker && ./run_pipeline.sh
```

### 自動シャットダウン

パイプライン実行後にEC2を自動停止する場合は`run_pipeline_and_shutdown.sh`を使用してください。

## ライセンス

（ライセンス情報を追加してください）

## 作者

（作者情報を追加してください）
