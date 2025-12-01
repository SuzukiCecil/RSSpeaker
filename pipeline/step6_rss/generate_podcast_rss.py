#!/usr/bin/env python3
"""
S3上の音声ファイルからPodcast RSSフィードを生成
"""
import json
import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import boto3
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートの.envファイルを読み込む
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

# 環境変数から設定を読み込む（デフォルト値を設定）
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "rsspeaker-audio-files")
S3_REGION = os.getenv("S3_REGION", "ap-southeast-2")
PODCAST_TITLE = os.getenv("PODCAST_TITLE", "RSSpeaker Tech News")
PODCAST_DESCRIPTION = os.getenv("PODCAST_DESCRIPTION", "AI技術ニュースを音声でお届けします")
PODCAST_AUTHOR = os.getenv("PODCAST_AUTHOR", "RSSpeaker")
PODCAST_EMAIL = os.getenv("PODCAST_EMAIL", "podcast@example.com")
PODCAST_IMAGE_URL = os.getenv("PODCAST_IMAGE_URL", "https://www.kcsf.co.jp/wp-content/uploads/2020/03/ai.jpg")

def get_audio_files_from_s3():
    """S3から音声ファイルのリストを取得"""
    s3 = boto3.client('s3', region_name=S3_REGION)

    episodes = []

    # S3バケット内のフォルダをリスト
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Delimiter='/')

    if 'CommonPrefixes' not in response:
        return episodes

    for prefix in response['CommonPrefixes']:
        folder_name = prefix['Prefix'].rstrip('/')

        # フォルダ内の音声ファイルをリスト
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix['Prefix'])

        if 'Contents' not in objects:
            continue

        for obj in objects['Contents']:
            if obj['Key'].endswith('.wav'):
                file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{obj['Key']}"

                # ファイル名から記事タイトルを抽出
                filename = os.path.basename(obj['Key'])
                title = filename.replace('.wav', '').replace('_', ' ')

                episodes.append({
                    'title': title,
                    'url': file_url,
                    'pub_date': obj['LastModified'],
                    'size': obj['Size'],
                    'folder': folder_name
                })

    # 日付順にソート（新しい順）
    episodes.sort(key=lambda x: x['pub_date'], reverse=True)

    return episodes

def generate_rss_feed(episodes):
    """Podcast RSSフィードを生成"""
    rss = Element('rss', version='2.0')
    rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
    rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')

    channel = SubElement(rss, 'channel')

    # Podcastメタデータ
    SubElement(channel, 'title').text = PODCAST_TITLE
    SubElement(channel, 'description').text = PODCAST_DESCRIPTION
    SubElement(channel, 'link').text = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/"
    SubElement(channel, 'language').text = 'ja'
    SubElement(channel, 'copyright').text = f"© {datetime.now().year} {PODCAST_AUTHOR}"
    SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    # iTunes固有のタグ
    SubElement(channel, 'itunes:author').text = PODCAST_AUTHOR
    SubElement(channel, 'itunes:summary').text = PODCAST_DESCRIPTION
    owner = SubElement(channel, 'itunes:owner')
    SubElement(owner, 'itunes:name').text = PODCAST_AUTHOR
    SubElement(owner, 'itunes:email').text = PODCAST_EMAIL

    SubElement(channel, 'itunes:image', href=PODCAST_IMAGE_URL)
    SubElement(channel, 'itunes:explicit').text = 'false'
    SubElement(channel, 'itunes:category', text='Technology')

    # エピソードを追加
    for episode in episodes:
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = episode['title']
        SubElement(item, 'description').text = f"{episode['folder']}のニュース"
        SubElement(item, 'pubDate').text = episode['pub_date'].strftime('%a, %d %b %Y %H:%M:%S GMT')
        SubElement(item, 'guid').text = episode['url']

        SubElement(item, 'enclosure',
                   url=episode['url'],
                   length=str(episode['size']),
                   type='audio/wav')

        SubElement(item, 'itunes:duration').text = '600'
        SubElement(item, 'itunes:explicit').text = 'false'

    # XMLを整形（XML宣言を含める）
    rough_string = tostring(rss, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)

    # XML宣言付きで出力
    xml_str = reparsed.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')

    return xml_str

def main():
    print("🎙️  Podcast RSSフィード生成中...")

    # S3から音声ファイルを取得
    episodes = get_audio_files_from_s3()
    print(f"✓ {len(episodes)} エピソードを検出")

    # RSSフィードを生成
    rss_feed = generate_rss_feed(episodes)

    # S3にアップロード
    s3 = boto3.client('s3', region_name=S3_REGION)
    s3.put_object(
        Bucket=S3_BUCKET,
        Key='podcast.rss',
        Body=rss_feed.encode('utf-8'),
        ContentType='application/rss+xml; charset=utf-8'  # charset指定を追加
    )

    rss_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/podcast.rss"
    print(f"✓ RSSフィードを生成しました")
    print(f"📡 RSS URL: {rss_url}")
    print("\nApple Podcastsに追加:")
    print(f"1. Apple Podcastsアプリを開く")
    print(f"2. 「ライブラリ」→「番組をURLで追加」")
    print(f"3. 以下のURLを入力:")
    print(f"   {rss_url}")

if __name__ == "__main__":
    main()

