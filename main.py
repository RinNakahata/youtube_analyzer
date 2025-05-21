import os
import csv
import time
import requests
import pandas as pd
import isodate

from analyze import main as analyze_main
from config import YOUTUBE_API_KEY

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
os.makedirs("data", exist_ok=True)


def get_upload_playlist_id(channel_id):
    url = f"{YOUTUBE_API_URL}/channels"
    params = {
        "part": "contentDetails",
        "id": channel_id,
        "key": YOUTUBE_API_KEY
    }
    res = requests.get(url, params=params).json()
    try:
        return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except:
        print(f"[⚠️] チャンネルID無効または取得失敗: {channel_id}")
        return None


def get_videos_from_playlist(playlist_id):
    videos = []
    next_page_token = None

    while True:
        url = f"{YOUTUBE_API_URL}/playlistItems"
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "pageToken": next_page_token,
            "key": YOUTUBE_API_KEY
        }
        res = requests.get(url, params=params).json()

        for item in res.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            published_at = item["contentDetails"]["videoPublishedAt"]
            videos.append({"video_id": video_id, "title": title,
                          "published_at": published_at})

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break
        time.sleep(1)

    return videos


def get_video_statistics(video_ids):
    stats = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        url = f"{YOUTUBE_API_URL}/videos"
        params = {
            "part": "statistics,contentDetails",
            "id": ",".join(chunk),
            "key": YOUTUBE_API_KEY
        }
        res = requests.get(url, params=params).json()

        for item in res.get("items", []):
            duration_iso = item["contentDetails"].get("duration", "")
            duration_seconds = isodate.parse_duration(
                duration_iso).total_seconds() if duration_iso else 0
            is_short = duration_seconds <= 60

            stats.append({
                "video_id": item["id"],
                "viewCount": int(item["statistics"].get("viewCount", 0)),
                "likeCount": int(item["statistics"].get("likeCount", 0)),
                "duration": duration_seconds,
                "is_short": is_short
            })
        time.sleep(1)

    return stats


def fetch_and_save_channel_videos(channel_name, channel_id):
    print(f"📡 {channel_name} からデータ取得中...")
    playlist_id = get_upload_playlist_id(channel_id)
    if not playlist_id:
        return

    videos = get_videos_from_playlist(playlist_id)
    video_ids = [v["video_id"] for v in videos]
    stats = get_video_statistics(video_ids)

    df_videos = pd.DataFrame(videos)
    df_stats = pd.DataFrame(stats)
    df = pd.merge(df_videos, df_stats, on="video_id", how="left")
    save_path = f"data/{channel_name}.csv"
    df.to_csv(save_path, index=False)
    print(f"✅ {channel_name} のデータ保存完了: {save_path}")


# --- ユーザー操作をシンプルに ---
def run_app():
    print("📥 チャンネルリストを読み込んでいます...")
    try:
        with open("channels.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fetch_and_save_channel_videos(row["name"], row["channel_id"])
    except FileNotFoundError:
        print("❌ 'channels.csv' ファイルが見つかりません。チャンネル名とIDを含むCSVを作成してください。")
        return

    print("📊 分析を開始します...")
    analyze_main()
    print("🎉 分析が完了しました！outputフォルダをご確認ください。")


if __name__ == "__main__":
    run_app()
