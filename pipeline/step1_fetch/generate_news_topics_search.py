#!/usr/bin/env python3
"""
Gemini + Google Custom Search APIでニュース概要を生成
シンプルな2段階アプローチ：
1. Geminiに検索クエリを生成させる
2. Custom Search APIで実際に検索
3. 検索結果をGeminiに渡してJSON整形
"""
import os
import json
import sys
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import zoneinfo

# Google GenAI SDK
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
            "news_count": 20,
            "target_audience": "エンジニア",
            "content_depth": "詳細"
        }

    with open(prefs_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def google_custom_search(query, api_key, cx, num=10):
    """Google Custom Search APIで検索"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": num,
        "dateRestrict": "d1",  # 過去1日以内
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  検索エラー: {e}")
        return {"items": []}

def generate_news_topics(api_key=None):
    """ニュース概要を生成"""
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini APIキーが設定されていません。")

    search_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_cx = os.getenv("GOOGLE_SEARCH_CX")

    if not search_api_key or not search_cx:
        raise ValueError("Google Custom Search API の設定が不足しています。")

    # ユーザー設定を読み込む
    prefs = load_user_preferences()

    print(f"📋 ユーザー設定:")
    print(f"  興味のある分野: {', '.join(prefs['interests'])}")
    print(f"  対象読者: {prefs['target_audience']}")
    print(f"  ニュース数: {prefs['news_count']}")
    print()

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name='gemini-2.5-flash')

    # 検索クエリを生成
    interests_str = "、".join(prefs['interests'])
    query_count = prefs.get('search_query_count', 10)  # デフォルトは10

    query_prompt = f"""以下の分野に関する過去24時間以内の最新技術ニュースを検索するための、効果的な日本語検索クエリを{query_count}個生成してください。

興味のある分野: {interests_str}

各クエリは1行で、簡潔に（3-10ワード）してください。
多様な観点からニュースを探せるよう、異なる切り口のクエリを生成してください。
クエリのみを出力し、説明は不要です。"""

    print("🔍 検索クエリを生成中...")
    response = model.generate_content(query_prompt)
    search_queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]

    print(f"✓ 生成されたクエリ:")
    for i, q in enumerate(search_queries, 1):
        print(f"  {i}. {q}")
    print()

    # 各クエリで検索実行
    all_results = []
    for query in search_queries:
        print(f"🔍 検索中: {query}")
        results = google_custom_search(query, search_api_key, search_cx, num=10)

        if 'items' in results:
            for item in results['items']:
                all_results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source_query": query
                })
        time.sleep(1)  # レート制限対策

    print(f"✓ 合計 {len(all_results)} 件の検索結果を取得\n")

    if not all_results:
        print("⚠️  検索結果が見つかりませんでした。")
        return []

    # Geminiに詳細要約を生成させる
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.now(jst)
    cutoff_time = now - timedelta(hours=24)

    formatting_prompt = f"""以下の検索結果から、過去24時間以内（{cutoff_time.strftime('%Y-%m-%d %H:%M')} JST以降）に公開された技術ニュースを{prefs['news_count']}個選定し、JSON形式で出力してください。

検索結果:
{json.dumps(all_results[:20], ensure_ascii=False, indent=2)}

要件:
- 実在する確認可能なニュースのみ
- 架空のニュース、製品名は含めない
- タイトル: 30-50字
- 要約（summary）: 検索結果のsnippetを基に、事実のみを記載した要約を200-300字で作成
  * snippetの情報のみを使用すること
  * 推測や補足は一切含めないこと
  * 具体的な技術名、数値、事実を重視すること
- 日付: YYYY-MM-DD形式（検索結果から推定）
- ソース: 完全なURL

出力形式:
{{
  "news": [
    {{
      "title": "...",
      "summary": "検索結果のsnippetに基づく500-800字の詳細要約",
      "source": "https://...",
      "published_date": "YYYY-MM-DD"
    }}
  ]
}}

JSON以外の文字は一切含めないでください。"""

    print("📝 検索結果をGeminiで整形中...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                formatting_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=16000,
                )
            )

            response_text = response.text.strip()

            # JSON部分を抽出
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # JSONをパース
            result = json.loads(response_text)

            if "news" not in result:
                raise ValueError("レスポンスに'news'キーが含まれていません")

            news_list = result["news"]
            print(f"✓ {len(news_list)} 件のニュースを取得しました")

            # 24時間フィルタリング
            cutoff_date = (now - timedelta(hours=24)).date()
            filtered_news = []

            for news in news_list:
                if 'published_date' not in news:
                    print(f"⚠️  日付情報なし（スキップ）: {news.get('title', 'No Title')}")
                    continue

                try:
                    pub_date = datetime.strptime(news['published_date'], '%Y-%m-%d').date()
                    if pub_date >= cutoff_date:
                        filtered_news.append(news)
                    else:
                        print(f"⚠️  24時間以内でない（スキップ）: {news['title']} ({news['published_date']})")
                except ValueError:
                    print(f"⚠️  日付形式が不正（スキップ）: {news['title']} ({news['published_date']})")
                    continue

            print(f"✓ 24時間フィルタ後: {len(filtered_news)} 件\n")

            # ソート
            filtered_news.sort(key=lambda x: x['published_date'], reverse=True)

            # 最新N件を選択
            if len(filtered_news) > prefs['news_count']:
                filtered_news = filtered_news[:prefs['news_count']]
                print(f"✓ 最新{prefs['news_count']}件を選択しました\n")

            # 取得したニュースを表示
            for i, news in enumerate(filtered_news, 1):
                print(f"[{i}] {news['title']}")
                print(f"    {news['summary']}")
                if 'source' in news and news['source']:
                    print(f"    出典: {news['source']}")
                if 'published_date' in news:
                    print(f"    公開日: {news['published_date']}")
                print()

            return filtered_news

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
    """ニュース概要をJSONファイルに保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_dir = Path(output_dir) / timestamp
    timestamp_dir.mkdir(parents=True, exist_ok=True)

    output_file = timestamp_dir / "topics.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print(f"💾 ニュース概要を保存しました: {output_file}")

    return str(output_file)

if __name__ == "__main__":
    print("RSSpeaker - Gemini + Google Custom Searchでニュース概要生成")
    print("=" * 60)
    print()

    try:
        # ニュース概要を生成
        news_list = generate_news_topics()

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
