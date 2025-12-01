#!/usr/bin/env python3
"""
Geminiグラウンディング機能でニュース概要を生成
"""
import os
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# プロジェクトルートの.envファイルを読み込む
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

def load_user_preferences(preferences_path="user_preferences.json"):
    """ユーザー属性設定を読み込む"""
    prefs_file = project_root / preferences_path

    if not prefs_file.exists():
        print(f"⚠️  {preferences_path}が見つかりません。デフォルト設定を使用します。")
        return {
            "interests": ["AI", "機械学習", "クラウド"],
            "language": "日本語",
            "news_count": 10,
            "target_audience": "エンジニア",
            "content_depth": "詳細",
            "date_range": "過去1週間以内"
        }

    with open(prefs_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_news_topics_with_grounding(api_key=None):
    """
    Geminiグラウンディング機能でニュース概要を生成

    Returns:
        list: ニュース概要のリスト [{"title": ..., "summary": ...}, ...]
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini APIキーが設定されていません。")

    # ユーザー設定を読み込む
    prefs = load_user_preferences()

    print(f"📋 ユーザー設定:")
    print(f"  興味のある分野: {', '.join(prefs['interests'])}")
    print(f"  対象読者: {prefs['target_audience']}")
    print(f"  ニュース数: {prefs['news_count']}")
    print()

    genai.configure(api_key=api_key)

    # グラウンディング機能付きモデルを設定
    # gemini-2.5-flashでGoogle検索グラウンディングを使用
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash'
    )

    # プロンプトを構築
    interests_str = "、".join(prefs['interests'])

    prompt = f"""あなたは技術ニュースキュレーターです。
以下の条件に基づいて、最新の技術ニュースを{prefs['news_count']}個選定してください。

**対象読者**: {prefs['target_audience']}
**興味のある分野**: {interests_str}
**期間**: {prefs['date_range']}
**言語**: {prefs['language']}

**重要な指示**:
1. Google検索を使って、上記の分野に関する最新ニュースを調査してください
2. ニュースは重複しないようにしてください
3. それぞれのニュースについて、30-50字程度のタイトルと100-150字程度の概要を提供してください
4. 技術的な深さと正確性を重視してください

**出力形式**:
以下のJSON形式で出力してください。JSON以外の文字は一切含めないでください。

{{
  "news": [
    {{
      "title": "ニュースのタイトル（30-50字）",
      "summary": "ニュースの概要（100-150字）",
      "source": "情報源（URLまたはメディア名）"
    }}
  ]
}}

注意: 出力はJSONのみとし、前置きや説明文は一切含めないでください。"""

    print("🔍 Geminiグラウンディングでニュースを検索中...")
    print("   (Google検索を使用して最新情報を取得します)")
    print()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # gemini-2.5系でのグラウンディング設定
            # SDKアップグレード後、google_searchフィールドを使用
            from google.ai.generativelanguage_v1beta.types import Tool

            # Google検索を使ったグラウンディング設定
            # google_searchフィールドに空のdictを渡すことで有効化
            google_search_tool = Tool(google_search={})

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8000,  # ニュース10件のJSON生成に十分な容量
                ),
                tools=[google_search_tool]
            )

            # レスポンスの確認
            if not response.candidates:
                print(f"⚠️  レスポンスにcandidatesが含まれていません")
                print(f"    response: {response}")
                raise ValueError("レスポンスが空です")

            # finish_reasonを確認
            finish_reason = response.candidates[0].finish_reason
            if finish_reason != 1:  # 1 = STOP (正常終了)
                print(f"⚠️  異常な終了理由: finish_reason = {finish_reason}")
                print(f"    (1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER)")
                if finish_reason == 3:  # SAFETY
                    print(f"    安全フィルターによりブロックされました")
                    if hasattr(response.candidates[0], 'safety_ratings'):
                        print(f"    safety_ratings: {response.candidates[0].safety_ratings}")

            # レスポンスからテキストを取得
            response_text = response.text.strip()

            # JSON部分を抽出（前後の余分なテキストを除去）
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # JSONをパース
            result = json.loads(response_text)

            if "news" not in result:
                raise ValueError("レスポンスに'news'キーが含まれていません")

            news_list = result["news"]

            print(f"✓ {len(news_list)} 件のニュースを取得しました\n")

            # 取得したニュースを表示
            for i, news in enumerate(news_list, 1):
                print(f"[{i}] {news['title']}")
                print(f"    {news['summary']}")
                if 'source' in news and news['source']:
                    print(f"    出典: {news['source']}")
                print()

            return news_list

        except json.JSONDecodeError as e:
            print(f"⚠️  JSONパースエラー (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"   5秒後にリトライします...")
                time.sleep(5)
                continue
            else:
                print(f"✗ リトライ失敗。レスポンス内容:")
                print(response_text[:500])
                raise

        except Exception as e:
            error_message = str(e)

            if "429" in error_message or "Resource exhausted" in error_message:
                if attempt < max_retries - 1:
                    print(f"⏳ レート制限に達しました。60秒待機してリトライします... (試行 {attempt + 1}/{max_retries})")
                    time.sleep(60)
                    continue
                else:
                    print(f"✗ Gemini API エラー (リトライ失敗): {e}")
                    raise
            else:
                print(f"✗ Gemini API エラー: {e}")
                raise

    raise RuntimeError("ニュース取得に失敗しました")

def save_news_topics(news_list, output_dir="data"):
    """
    ニュース概要をJSONファイルに保存

    Args:
        news_list: ニュース概要のリスト
        output_dir: 出力ディレクトリ

    Returns:
        str: 保存したファイルのパス
    """
    # タイムスタンプディレクトリを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_dir = Path(output_dir) / timestamp
    timestamp_dir.mkdir(parents=True, exist_ok=True)

    output_file = timestamp_dir / "topics.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print(f"💾 ニュース概要を保存しました: {output_file}")

    return str(output_file)

if __name__ == "__main__":
    print("RSSpeaker - Geminiグラウンディングでニュース概要生成")
    print("=" * 60)
    print()

    try:
        # ニュース概要を生成
        news_list = generate_news_topics_with_grounding()

        # 保存
        output_file = save_news_topics(news_list)

        print()
        print("=" * 60)
        print("✓ ニュース概要生成完了")
        print(f"  出力ファイル: {output_file}")
        print(f"  ニュース数: {len(news_list)}")

    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
