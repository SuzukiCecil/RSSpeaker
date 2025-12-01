#!/usr/bin/env python3
"""
JSONファイルから音声を生成
"""
import json
import os
import requests
import sys
import time
import re
import wave
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

VOICEVOX_URL = "http://localhost:50021"
SPEAKER_ID = 3  # ずんだもん
CHUNK_SIZE = 300  # 1つのチャンクの最大文字数
MAX_WORKERS = 2  # 並列処理数（デフォルト2、環境変数で変更可能）

def sanitize_filename(title):
    """ファイル名として使用できる文字列に変換"""
    # 使用できない文字を削除または置換
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    # スペースをアンダースコアに
    title = title.replace(' ', '_')
    # 長すぎる場合は切り詰め（最大100文字）
    if len(title) > 100:
        title = title[:100]
    return title

def split_text_into_chunks(text, max_length=CHUNK_SIZE):
    """テキストを指定文字数以下のチャンクに分割"""
    chunks = []
    current_chunk = ""

    sentences = text.replace('\n', '').split('。')

    for sentence in sentences:
        if not sentence.strip():
            continue

        sentence = sentence.strip() + '。'

        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def concatenate_wav_files(wav_files, output_file):
    """複数のWAVファイルを正しく結合"""
    if not wav_files:
        return False

    # 最初のファイルのパラメータを読み取る
    with wave.open(wav_files[0], 'rb') as first_wav:
        params = first_wav.getparams()

    # 出力ファイルを開く
    with wave.open(output_file, 'wb') as output_wav:
        output_wav.setparams(params)

        # 各WAVファイルのデータを追加
        for wav_file in wav_files:
            with wave.open(wav_file, 'rb') as input_wav:
                output_wav.writeframes(input_wav.readframes(input_wav.getnframes()))

    return True

def generate_audio_with_chunking(text, output_path, speaker_id=SPEAKER_ID):
    """テキストをチャンクに分割して音声生成"""
    chunks = split_text_into_chunks(text)

    print(f"  テキストを {len(chunks)} チャンクに分割")

    temp_wav_files = []

    for i, chunk in enumerate(chunks, 1):
        print(f"  チャンク {i}/{len(chunks)} を生成中... ({len(chunk)} 文字)")

        # 音声合成用のクエリを作成
        query_response = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": chunk, "speaker": speaker_id},
            timeout=60
        )
        query_response.raise_for_status()

        # 音声合成
        synthesis_response = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker_id},
            json=query_response.json(),
            timeout=60
        )
        synthesis_response.raise_for_status()

        # 一時ファイルに保存（スレッドIDを含めて一意にする）
        thread_id = threading.get_ident()
        temp_file = f"/tmp/chunk_{i}_{os.getpid()}_{thread_id}.wav"
        with open(temp_file, 'wb') as f:
            f.write(synthesis_response.content)
        temp_wav_files.append(temp_file)

        time.sleep(0.5)

    # WAVファイルを正しく結合
    print(f"  音声ファイルを結合中...")
    concatenate_wav_files(temp_wav_files, output_path)

    # 一時ファイルを削除
    for temp_file in temp_wav_files:
        try:
            os.remove(temp_file)
        except:
            pass

    print(f"✓ 音声生成完了: {output_path}")

def process_single_article(article, index, total, output_dir):
    """1つの記事を処理（並列処理用）"""
    title = article.get('title', f'article_{index}')
    narration = article.get('narration_script', '')

    if not narration:
        return {
            'success': False,
            'index': index,
            'title': title,
            'error': 'ナレーション原稿がありません'
        }

    print(f"{'='*60}")
    print(f"[{index}/{total}] {title}")
    print(f"{'='*60}")
    print(f"文字数: {len(narration)} 文字\n")

    # ファイル名をサニタイズ
    safe_title = sanitize_filename(title)
    output_path = os.path.join(output_dir, f"{safe_title}.wav")

    try:
        generate_audio_with_chunking(narration, output_path)
        print()
        return {
            'success': True,
            'index': index,
            'title': title,
            'output_path': output_path
        }
    except Exception as e:
        print(f"✗ 音声生成エラー: {e}\n")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'index': index,
            'title': title,
            'error': str(e)
        }

def generate_audio_from_json(input_json_path, output_dir):
    """JSONファイルから音声ファイルを生成（並列処理版）"""
    print(f"📖 記事を読み込み中: {input_json_path}")

    with open(input_json_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    # 環境変数から並列数を取得（デフォルトはMAX_WORKERS）
    max_workers = int(os.environ.get('VOICEVOX_MAX_WORKERS', MAX_WORKERS))

    print(f"✓ {len(articles)} 件の記事を読み込みました")
    print(f"🔧 並列処理数: {max_workers}\n")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    # 並列処理で音声生成
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各記事の処理をスレッドプールに投入
        futures = {
            executor.submit(process_single_article, article, i, len(articles), output_dir): i
            for i, article in enumerate(articles, 1)
        }

        # 完了した順に結果を取得
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if not result['success']:
                if 'error' in result:
                    print(f"⚠️  [{result['index']}/{len(articles)}] {result['title']} - {result['error']}\n")

    # 成功した件数を集計
    success_count = sum(1 for r in results if r['success'])

    print(f"✓ 完了: {success_count}/{len(articles)} 件の音声ファイルを生成しました")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用法: python3 generate_audio_from_json.py <input_json> <output_dir>")
        sys.exit(1)

    input_json = sys.argv[1]
    output_dir = sys.argv[2]

    generate_audio_from_json(input_json, output_dir)
