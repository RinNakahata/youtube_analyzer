import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from janome.tokenizer import Tokenizer
from wordcloud import WordCloud

# --- 初期設定 ---
plt.rcParams['font.family'] = 'Meiryo' if os.name == 'nt' else 'IPAexGothic'
DATA_FOLDER = "data"
OUTPUT_BASE_FOLDER = "output"
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
OUTPUT_FOLDER = os.path.join(OUTPUT_BASE_FOLDER, TODAY_STR)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- データ読み込み関連関数 ---


def load_channel_files(folder=DATA_FOLDER):
    return [f for f in os.listdir(folder) if f.endswith(".csv")]


def read_data(file):
    df = pd.read_csv(os.path.join(DATA_FOLDER, file))
    # タイムゾーン変換（指定により変更禁止）
    df["published_at"] = pd.to_datetime(
        df["published_at"]).dt.tz_convert("Asia/Tokyo")
    return df

# --- チャンネル別統計（動画数・平均再生数） ---


def summarize_channels(files):
    summary = []
    for file in files:
        df = read_data(file)
        channel = file.replace(".csv", "")
        summary.append({
            "channel": channel,
            "video_count": len(df),
            "average_views": round(df["viewCount"].mean())
        })
    return pd.DataFrame(summary)


def plot_channel_summary(df):
    # 平均再生数
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x="channel", y="average_views", palette="Blues_d")
    plt.title("チャンネル別・平均再生数")
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "avg_views.png"))
    plt.close()

    # 動画数
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x="channel", y="video_count", palette="Greens_d")
    plt.title("チャンネル別・投稿本数")
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "video_count.png"))
    plt.close()

# --- 曜日・時間別再生傾向 ---


def analyze_short_videos_by_weekday_hour(files):
    weekday_dfs, hour_dfs = [], []
    for file in files:
        df = pd.read_csv(os.path.join(DATA_FOLDER, file))
        if "is_short" not in df.columns:
            continue
        df = df[df["is_short"] == True].copy()
        if df.empty:
            continue
        df["published_at"] = pd.to_datetime(df["published_at"])
        df["weekday"] = df["published_at"].dt.day_name()
        df["hour"] = df["published_at"].dt.hour
        df["channel"] = file.replace(".csv", "")
        weekday_dfs.append(df[["channel", "weekday", "viewCount"]])
        hour_dfs.append(df[["channel", "hour", "viewCount"]])
    return weekday_dfs, hour_dfs


def plot_weekday_views(weekday_dfs):
    if not weekday_dfs:
        return
    df = pd.concat(weekday_dfs)
    order = ["Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday", "Sunday"]
    avg_views = df.groupby("weekday")["viewCount"].mean().reindex(order)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=avg_views.index, y=avg_views.values, palette="coolwarm")
    plt.title("曜日別・平均再生数（ショート動画）")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "weekday_views.png"))
    plt.close()


def plot_hourly_views(hour_dfs):
    if not hour_dfs:
        return
    df = pd.concat(hour_dfs)
    avg_views = df.groupby("hour")["viewCount"].mean()
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=avg_views.index, y=avg_views.values, marker="o")
    plt.title("時間帯別・平均再生数（ショート動画）")
    plt.xticks(range(24))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "hourly_views.png"))
    plt.close()

# --- ワードクラウド ---


def generate_wordcloud(files):
    tokenizer = Tokenizer()
    words = []
    for file in files:
        df = pd.read_csv(os.path.join(DATA_FOLDER, file))
        if "is_short" not in df.columns:
            continue
        df = df[df["is_short"] == True]
        if df.empty:
            continue
        for title in df["title"].dropna().astype(str):
            for token in tokenizer.tokenize(title):
                pos = token.part_of_speech.split(',')[0]
                if pos in ["名詞", "動詞", "形容詞"]:
                    base = token.base_form
                    if len(base) > 1:
                        words.append(base)
    if words:
        wc = WordCloud(font_path="C:/Windows/Fonts/meiryo.ttc",
                       background_color="white", width=800, height=600).generate(" ".join(words))
        plt.figure(figsize=(10, 8))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_FOLDER, "wordcloud.png"))
        plt.close()

# --- 今週のTop10動画 ---


def get_top10_videos_this_week(files):
    now = pd.Timestamp.now(tz="Asia/Tokyo")
    one_week_ago = now - timedelta(days=7)
    top_videos = []
    for file in files:
        df = read_data(file)
        recent_df = df[df["published_at"] >= one_week_ago]
        channel = file.replace(".csv", "")
        for _, row in recent_df.iterrows():
            top_videos.append({
                "channel": channel,
                "title": row["title"],
                "viewCount": row["viewCount"],
                "published_at": row["published_at"]
            })
    top_df = pd.DataFrame(top_videos)
    return top_df.sort_values("viewCount", ascending=False).head(10)


def save_top10(top10_df):
    top10_df.to_csv(os.path.join(
        OUTPUT_FOLDER, "top10_this_week.csv"), index=False)

# --- ヒートマップ（曜日×時間帯） ---


def plot_heatmap_weekday_hour(files):
    all_dfs = []
    for file in files:
        df = read_data(file)
        df["weekday"] = df["published_at"].dt.dayofweek
        df["hour"] = df["published_at"].dt.hour
        all_dfs.append(df)
    combined = pd.concat(all_dfs)
    heatmap_data = combined.pivot_table(
        index="hour", columns="weekday", values="viewCount", aggfunc="mean")
    plt.figure(figsize=(12, 6))
    sns.heatmap(heatmap_data, cmap="YlOrRd",
                linewidths=0.5, annot=True, fmt=".0f")
    plt.title("⏰ 曜日 × 時間帯別 平均再生数")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, "heatmap_weekday_hour.png"))
    plt.close()

# --- チャンネルパフォーマンス分析 ---


def analyze_channel_performance(files):
    performances = []
    all_videos = []
    for file in files:
        df = read_data(file)
        df["week"] = df["published_at"].dt.strftime("%Y-%U")
        channel = file.replace(".csv", "")
        avg_views = df["viewCount"].mean()
        freq_per_week = len(df) / df["week"].nunique()
        df["channel"] = channel
        all_videos.append(df)
        performances.append({
            "channel": channel,
            "avg_views": round(avg_views),
            "freq_per_week": round(freq_per_week, 2)
        })
    combined = pd.concat(all_videos)
    overall_avg = combined["viewCount"].mean()
    for perf in performances:
        ch_df = combined[combined["channel"] == perf["channel"]]
        success_rate = (ch_df["viewCount"] > overall_avg).sum() / len(ch_df)
        perf["success_rate"] = round(success_rate * 100, 1)
    return pd.DataFrame(performances)


def plot_channel_performance(df):
    for col, title, color in [("avg_views", "平均再生数", "Blues_d"),
                              ("freq_per_week", "投稿頻度（週）", "Greens_d"),
                              ("success_rate", "成功率（%）", "Purples_d")]:
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x="channel", y=col, palette=color)
        plt.title(title)
        plt.xticks(rotation=30)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_FOLDER, f"{col}.png"))
        plt.close()
    df.to_excel(os.path.join(OUTPUT_FOLDER,
                "channel_performance.xlsx"), index=False)

# --- メイン処理 ---


def main():
    files = load_channel_files()
    summary_df = summarize_channels(files)
    plot_channel_summary(summary_df)
    weekday_dfs, hour_dfs = analyze_short_videos_by_weekday_hour(files)
    plot_weekday_views(weekday_dfs)
    plot_hourly_views(hour_dfs)
    generate_wordcloud(files)
    top10_df = get_top10_videos_this_week(files)
    save_top10(top10_df)
    plot_heatmap_weekday_hour(files)
    perf_df = analyze_channel_performance(files)
    plot_channel_performance(perf_df)


if __name__ == "__main__":
    print("📊 YouTubeデータ分析を開始します...")
    main()
