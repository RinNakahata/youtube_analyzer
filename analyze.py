import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from janome.tokenizer import Tokenizer
from wordcloud import WordCloud
from collections import Counter

# --- 初期設定 ---
plt.rcParams['font.family'] = 'Meiryo' if os.name == 'nt' else 'IPAexGothic'
DATA_FOLDER = "data"
OUTPUT_BASE_FOLDER = "output"
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
OUTPUT_FOLDER = os.path.join(OUTPUT_BASE_FOLDER, TODAY_STR)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# フォント設定（日本語対応）
plt.rcParams['font.family'] = 'Meiryo' if os.name == 'nt' else 'IPAexGothic'

# データフォルダと出力フォルダ定義
DATA_FOLDER = "data"
TODAY = datetime.now().strftime("%Y-%m-%d")  # 実行日
OUTPUT_DIR = os.path.join("output", TODAY)

# 出力フォルダがなければ作成
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# --- 動画の長さ別再生数分析 ---


def analyze_views_by_duration(files):
    """
    動画長さ（duration秒）をカテゴリ別に分けて平均再生数を算出し、棒グラフを表示する。
    """
    all_data = []

    for file in files:
        df = read_data(file)
        if "duration" not in df.columns:
            continue
        channel = file.replace(".csv", "")
        # durationは秒数として扱う
        df = df.dropna(subset=["duration"])
        df["duration"] = df["duration"].astype(float)

        # カテゴリ分け（例）
        def categorize_duration(d):
            if d <= 15:
                return "～15秒"
            elif d <= 30:
                return "16～30秒"
            elif d <= 45:
                return "31～45秒"
            elif d <= 60:
                return "46～60秒"
            else:
                return "60秒超"

        df["duration_cat"] = df["duration"].apply(categorize_duration)
        all_data.append(df)

    if not all_data:
        print("動画の長さデータがありません。")
        return

    combined = pd.concat(all_data)
    avg_views = combined.groupby("duration_cat")["viewCount"].mean().reindex(
        ["～15秒", "16～30秒", "31～45秒", "46～60秒", "60秒超"])

    plt.figure(figsize=(10, 6))
    sns.barplot(x=avg_views.index, y=avg_views.values, palette="magma")
    plt.title("動画の長さ別・平均再生数")
    plt.xlabel("動画の長さ")
    plt.ylabel("平均再生数")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/views_by_duration.png")
    plt.show()


# --- 成功動画タイトルワードランキング（Top20） ---


def analyze_success_title_words(files):
    """
    全動画の平均再生数以上の動画タイトルから形態素解析し、頻出単語Top20を抽出して表示する。
    """
    tokenizer = Tokenizer()
    all_dfs = []

    for file in files:
        df = read_data(file)
        df["channel"] = file.replace(".csv", "")
        all_dfs.append(df)

    combined = pd.concat(all_dfs)
    overall_avg_views = combined["viewCount"].mean()
    success_videos = combined[combined["viewCount"] >= overall_avg_views]

    if success_videos.empty:
        print("成功動画がありません。")
        return

    words = []
    for title in success_videos["title"].dropna().astype(str):
        tokens = tokenizer.tokenize(title)
        for token in tokens:
            pos = token.part_of_speech.split(',')[0]
            if pos in ["名詞", "動詞", "形容詞"]:
                base = token.base_form
                if len(base) > 1:
                    words.append(base)

    if not words:
        print("成功動画タイトルから抽出できる単語がありません。")
        return

    word_counts = Counter(words)
    common_words = word_counts.most_common(20)
    words_list, counts = zip(*common_words)

    plt.figure(figsize=(12, 6))
    sns.barplot(x=list(counts), y=list(words_list), palette="viridis")
    plt.title("成功動画タイトル頻出ワード Top20")
    plt.xlabel("出現回数")
    plt.ylabel("単語")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/success_title_words_top20.png")
    plt.show()

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
    analyze_views_by_duration(files)
    analyze_success_title_words(files)


if __name__ == "__main__":
    print("📊 YouTubeデータ分析を開始します...")
    main()
