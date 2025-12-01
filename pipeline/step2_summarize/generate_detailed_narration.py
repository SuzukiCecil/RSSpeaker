#!/usr/bin/env python3
"""
ニュース概要から詳細なナレーション原稿を生成（並列処理対応）
"""
import os
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai

# プロジェクトルートの.envファイルを読み込む
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

# システムプロンプト
SYSTEM_PROMPT = """あなたは技術系ニュースを音声コンテンツ向けに解説する音声原稿ライターです。
与えられたニュース概要を元に、7-10分程度のナレーション原稿を自然な日本語で生成してください。

出力形式:
1行目: 内容を30字以内で表すタイトル
2行目: 空行
3行目以降: ナレーション本文

制約:
- 文章は話し言葉寄りにするが砕けすぎない
- TTSで滑らかに読めるよう、不要な改行・空白・箇条書きを使わない
- 不要なスペースを入れない（数字・英字の前後に空白を入れない）
- 導入（あいさつ）と締め（まとめ）は必ず含める
- ニュース概要の情報を基に、技術的背景や影響を詳しく解説する
- 補足説明が必要な場合は一般的に広く知られている範囲に限る
- 全体で7-10分の読み上げ（2000〜3000字）を想定する

音声読み上げ用の表記ルール（重要）:
- アルファベット略語は必ずカタカナで表記する
  例: S3 → エススリー、EC2 → イーシーツー、AI → エーアイ、API → エーピーアイ
- 数字を含む略語も同様にカタカナで表記する
  例: AWS → エーダブリューエス、GCP → ジーシーピー、HTML5 → エイチティーエムエルファイブ
- バージョン番号は「ばーじょん」を付けて表記する
  例: Python 3.13 → パイソン ばーじょん さんてんいちさん
- URLやファイルパスは読み上げに適した形に変換する
  例: github.com → ぎっとはぶ どっと こむ
- 固有名詞の正しい読み方（括弧による読み仮名付記は絶対に禁止）:
  Laravel → ララベル（「ラーベル」は誤り）
  Python → パイソン
  React → リアクト
  Vue → ビュー
  Docker → ドッカー
  Kubernetes → クーバネティス または クバネテス
- 固有名詞は必ず正しいカタカナ表記のみを使用し、括弧付きの読み仮名を付けてはいけない
  正しい例: ララベルイレブンの最新アップデート
  誤った例: Laravel（ララベル）イレブン ← 括弧で読み仮名を付けるのは禁止

絶対に禁止:
- 「承知しました」「かしこまりました」「以下の通りです」などのAIアシスタント特有の応答
- 「ナレーション原稿を作成します」などのメタ的な説明
- 「【タイトル】」「【本文】」などのマークダウン記号
- いかなる前置きや後置きのコメント

必ず守ること:
- 出力の1文字目は必ずタイトルの最初の文字であること
- タイトルの直後に本文を開始すること
- 音声コンテンツとして直接読み上げられる完成形の原稿のみを出力すること"""

def clean_narration(text):
    """
    前置き文言を自動削除する（フェイルセーフ）
    """
    import re

    unwanted_patterns = [
        r'^(はい、?)?承知(いたし|致し)ました。?\s*\n?',
        r'^(はい、?)?かしこまりました。?\s*\n?',
        r'^以下の?通りです。?\s*\n?',
        r'^ナレーション原稿を?(作成します|生成します)。?\s*\n?',
        r'^原稿を?(作成します|生成します)。?\s*\n?',
        r'^(それでは、?)?(ナレーション)?原稿です。?\s*\n?',
        r'^\【タイトル\】\s*\n?',
        r'^\【本文\】\s*\n?',
    ]

    for pattern in unwanted_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)

    # 冒頭の孤立したカタカナ1〜2文字を削除（前置き削除の残骸対策）
    # 条件: カタカナ1〜2文字の後に漢字・ひらがなで始まる文章が続く場合のみ
    text = re.sub(r'^[ァ-ヴ]{1,2}(?=[一-龯ぁ-ん])', '', text)

    text = text.lstrip()
    return text

def generate_narration_for_topic(topic, index, total, api_key):
    """
    1つのニュース概要について詳細ナレーションを生成

    Args:
        topic: ニュース概要 {"title": ..., "summary": ...}
        index: インデックス（1始まり）
        total: 全体の数
        api_key: Gemini API Key

    Returns:
        dict: 成功/失敗情報とナレーション原稿
    """
    print(f"[{index}/{total}] {topic['title']}")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        system_instruction=SYSTEM_PROMPT
    )

    user_prompt = f"""ニュース概要:
タイトル: {topic['title']}
概要: {topic['summary']}

上記のニュース概要を基に、詳細な技術解説を含む7-10分のナレーション原稿を作成してください。

重要: 1文字目からタイトルを開始してください。前置きコメントは絶対に出力しないでください。"""

    print(f"  📝 ナレーション原稿を生成中...")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=3000,
                )
            )

            narration = response.text
            narration = clean_narration(narration)

            print(f"  ✓ 生成完了 ({len(narration)} 文字)\n")

            return {
                'success': True,
                'index': index,
                'topic': topic,
                'narration': narration
            }

        except Exception as e:
            error_message = str(e)

            if "429" in error_message or "Resource exhausted" in error_message:
                if attempt < max_retries - 1:
                    print(f"  ⏳ レート制限。60秒待機... (試行 {attempt + 1}/{max_retries})")
                    time.sleep(60)
                    continue
                else:
                    print(f"  ✗ API エラー (リトライ失敗): {e}\n")
                    return {
                        'success': False,
                        'index': index,
                        'topic': topic,
                        'error': str(e)
                    }
            else:
                print(f"  ✗ API エラー: {e}\n")
                return {
                    'success': False,
                    'index': index,
                    'topic': topic,
                    'error': str(e)
                }

    return {
        'success': False,
        'index': index,
        'topic': topic,
        'error': '最大リトライ回数を超えました'
    }

def generate_narrations_from_topics(topics_file, output_file=None, api_key=None):
    """
    ニュース概要から詳細ナレーションを並列生成

    Args:
        topics_file: topics.jsonのパス
        output_file: 出力ファイルパス（Noneの場合は同じディレクトリにsummarized.json）
        api_key: Gemini API Key

    Returns:
        str: 出力ファイルパス
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini APIキーが設定されていません。")

    print(f"📖 ニュース概要を読み込み中: {topics_file}")

    with open(topics_file, 'r', encoding='utf-8') as f:
        topics = json.load(f)

    print(f"✓ {len(topics)} 件のニュース概要を読み込みました\n")

    # 環境変数から並列数を取得（デフォルトは5）
    max_workers = int(os.getenv('GEMINI_MAX_WORKERS', '5'))
    print(f"🔧 並列処理数: {max_workers}\n")

    results = []

    # 並列処理でナレーション生成
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_narration_for_topic, topic, i, len(topics), api_key): i
            for i, topic in enumerate(topics, 1)
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # インデックス順にソート
    results.sort(key=lambda x: x['index'])

    # 成功したナレーションのみを抽出
    narrations = []
    for result in results:
        if result['success']:
            narrations.append({
                'title': result['topic']['title'],
                'summary': result['topic']['summary'],
                'source': result['topic'].get('source', ''),
                'narration_script': result['narration']
            })
        else:
            print(f"⚠️  [{result['index']}] {result['topic']['title']} - 生成失敗: {result.get('error', 'Unknown')}")

    print(f"\n✓ 完了: {len(narrations)}/{len(topics)} 件のナレーションを生成しました")

    # 出力ファイルパスの決定
    if output_file is None:
        input_dir = Path(topics_file).parent
        output_file = input_dir / "summarized.json"

    # JSONファイルとして保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(narrations, f, ensure_ascii=False, indent=2)

    print(f"💾 ナレーション原稿を保存しました: {output_file}")

    return str(output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用法: python3 generate_detailed_narration.py <topics_json> [output_json]")
        print("例: python3 generate_detailed_narration.py data/20251201_120000/topics.json")
        sys.exit(1)

    topics_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print("RSSpeaker - 詳細ナレーション生成")
    print(f"入力ファイル: {topics_file}")
    print(f"出力ファイル: {output_file or '(自動生成)'}\n")

    try:
        generate_narrations_from_topics(topics_file, output_file)
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
