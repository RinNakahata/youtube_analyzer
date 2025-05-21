import re
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from janome.tokenizer import Tokenizer
from wordcloud import WordCloud
from collections import Counter
from matplotlib.ticker import FuncFormatter

# --- 定数 ---
DATA_FOLDER = "data"
OUTPUT_BASE_FOLDER = "output"
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
OUTPUT_FOLDER = os.path.join(OUTPUT_BASE_FOLDER, TODAY_STR)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

EXCLUDED_POS = {"助詞", "助動詞", "記号", "接続詞", "連体詞", "感動詞", "フィラー", "その他"}
EXCLUDED_WORDS = {"する", "れる", "られる", "なる",
                  "ある", "こと", "もの", "てる", "くる", "いる", "できる"}
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday",
               "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS_JP = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"]

# --- フォント設定 ---
plt.rcParams['font.family'] = 'Meiryo' if os.name == 'nt' else 'IPAexGothic'


# --- ユーティリティ関数 ---
def comma_formatter(x, pos):
    return f'{int(x):,}'


def save_figure(filename):
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, filename))
    plt.close()


def get_channel_name(file):
    return os.path.splitext(file)[0]


def load_channel_files(folder=DATA_FOLDER):
    return [f for f in os.listdir(folder) if f.endswith(".csv")]


def read_data(filepath):
    df = pd.read_csv(filepath)
    df["published_at"] = pd.to_datetime(
        df["published_at"]).dt.tz_convert("Asia/Tokyo")
    return df


def extract_meaningful_words(text, tokenizer):
    text = re.sub(r'【[^】]*】', '', text)
    text = re.sub(r'#short', '', text, flags=re.IGNORECASE)
    for word in ["スカッと迷言集", "迷言集", "ch", "感動", "スレ", "ww", "スカッ", "10", "#"]:
        text = text.replace(word, "")
    text = text.strip()

    words = []
    for token in tokenizer.tokenize(text):
        pos = token.part_of_speech.split(',')[0]
        base = token.base_form
        if pos not in EXCLUDED_POS and base not in EXCLUDED_WORDS and len(base) > 1:
            words.append(base)
    return words


# --- チャンネル別統計 ---
def summarize_channels(files):
    summary = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        summary.append({
            "channel": get_channel_name(file),
            "video_count": len(df),
            "average_views": round(df["viewCount"].mean())
        })
    return pd.DataFrame(summary)


def plot_channel_summary(df):
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x="channel", y="video_count", palette="Greens_d")
    plt.title("チャンネル別・投稿本数")
    plt.xlabel("チャンネル名")
    plt.ylabel("投稿本数")
    plt.xticks(rotation=30, ha='right')
    save_figure("チャンネル別_投稿本数.png")


# --- 曜日・時間帯別 ---
def analyze_short_videos_by_weekday_hour(files):
    weekday_dfs, hour_dfs = [], []
    for file in files:
        df = pd.read_csv(os.path.join(DATA_FOLDER, file))
        if "is_short" not in df.columns:
            continue
        df = df[df["is_short"]]
        if df.empty:
            continue
        df["published_at"] = pd.to_datetime(df["published_at"])
        df["weekday"] = df["published_at"].dt.day_name()
        df["hour"] = df["published_at"].dt.hour
        df["channel"] = get_channel_name(file)
        weekday_dfs.append(df[["channel", "weekday", "viewCount"]])
        hour_dfs.append(df[["channel", "hour", "viewCount"]])
    return weekday_dfs, hour_dfs


def plot_weekday_views(weekday_dfs):
    if not weekday_dfs:
        return
    df = pd.concat(weekday_dfs)
    avg_views = df.groupby("weekday")["viewCount"].mean().reindex(WEEKDAYS_EN)
    avg_views.index = WEEKDAYS_JP
    plt.figure(figsize=(10, 6))
    sns.barplot(x=avg_views.index, y=avg_views.values, palette="coolwarm")
    plt.title("曜日別・平均再生数（ショート動画）")
    plt.xlabel("曜日")
    plt.ylabel("平均再生数")
    plt.gca().yaxis.set_major_formatter(FuncFormatter(comma_formatter))
    save_figure("曜日別_平均再生数_ショート動画.png")


def plot_hourly_views(hour_dfs):
    if not hour_dfs:
        return
    df = pd.concat(hour_dfs)
    avg_views = df.groupby("hour")["viewCount"].mean()
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=avg_views.index, y=avg_views.values, marker="o")
    plt.title("時間帯別・平均再生数（ショート動画）")
    plt.xlabel("時間（時）")
    plt.ylabel("平均再生数")
    plt.xticks(range(24))
    plt.gca().yaxis.set_major_formatter(FuncFormatter(comma_formatter))
    save_figure("時間帯別_平均再生数_ショート動画.png")


# --- Top10動画 ---
def get_top10_videos_this_week(files):
    now = pd.Timestamp.now(tz="Asia/Tokyo")
    one_week_ago = now - timedelta(days=7)
    top_videos = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        df = df[df["published_at"] >= one_week_ago]
        for _, row in df.iterrows():
            top_videos.append({
                "channel": get_channel_name(file),
                "title": row["title"],
                "viewCount": row["viewCount"],
                "published_at": row["published_at"]
            })
    top_df = pd.DataFrame(top_videos)
    return top_df.sort_values("viewCount", ascending=False).head(10)


def save_top10(top10_df):
    top10_df.to_csv(os.path.join(OUTPUT_FOLDER, "今週のTop10動画.csv"), index=False)


# --- ヒートマップ ---
def plot_heatmap_weekday_hour(files):
    all_dfs = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        df["weekday"] = df["published_at"].dt.dayofweek
        df["hour"] = df["published_at"].dt.hour
        all_dfs.append(df)

    combined = pd.concat(all_dfs)

    # ピボットテーブル作成
    heatmap_data = combined.pivot_table(
        index="hour",
        columns="weekday",
        values="viewCount",
        aggfunc="mean"
    )

    # 日本語の曜日に変換（月〜日）
    WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]
    heatmap_data.columns = [WEEKDAYS_JP[day] for day in heatmap_data.columns]

    # --- ヒートマップ描画 ---
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        heatmap_data,
        cmap="coolwarm",
        linewidths=0.5,
        linecolor='gray',
        annot=True,
        fmt=',.0f'
    )

    plt.title("曜日 × 時間帯別の平均再生数\n（視聴傾向を可視化）", fontsize=16)
    plt.xlabel("曜日", fontsize=12)
    plt.ylabel("時間帯（時）", fontsize=12)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)

    plt.tight_layout()

    # 保存ファイル名もわかりやすく
    save_figure("曜日別_時間別_平均再生数_ヒートマップ.png")


# --- チャンネルパフォーマンス ---
def analyze_channel_performance(files):
    performances = []
    all_videos = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        df["week"] = df["published_at"].dt.strftime("%Y-%U")
        df["channel"] = get_channel_name(file)
        all_videos.append(df)
        performances.append({
            "channel": df["channel"].iloc[0],
            "avg_views": round(df["viewCount"].mean()),
            "freq_per_week": round(len(df) / df["week"].nunique(), 2)
        })
    combined = pd.concat(all_videos)
    overall_avg = combined["viewCount"].mean()
    for perf in performances:
        ch_df = combined[combined["channel"] == perf["channel"]]
        success_rate = (ch_df["viewCount"] > overall_avg).sum() / len(ch_df)
        perf["success_rate"] = round(success_rate * 100, 1)
    return pd.DataFrame(performances)


def plot_channel_performance(df):
    for col, title, color, ylabel in [
        ("avg_views", "チャンネル別・平均再生数", "Blues_d", "平均再生数"),
        ("freq_per_week", "チャンネル別・投稿頻度（週あたり）", "Greens_d", "投稿頻度"),
        ("success_rate", "チャンネル別・成功率（%）", "Purples_d", "成功率（%）")
    ]:
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x="channel", y=col, palette=color)
        plt.title(title)
        plt.xlabel("チャンネル名")
        plt.ylabel(ylabel)
        if col == "avg_views":
            plt.gca().yaxis.set_major_formatter(FuncFormatter(comma_formatter))
        plt.xticks(rotation=30)
        save_figure(f"{title}.png")


# --- 動画の長さ別 ---
def analyze_views_by_duration(files):
    all_data = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        if "duration" not in df.columns:
            continue
        df = df.dropna(subset=["duration"])
        df["duration"] = df["duration"].astype(float)
        df["duration_cat"] = df["duration"].apply(lambda d: (
            "～15秒" if d <= 15 else
            "16～30秒" if d <= 30 else
            "31～45秒" if d <= 45 else
            "46～60秒" if d <= 60 else
            "60秒超"
        ))
        all_data.append(df)
    if not all_data:
        print("動画の長さデータがありません。")
        return
    combined = pd.concat(all_data)
    avg_views = combined.groupby("duration_cat")["viewCount"].mean().reindex(
        ["～15秒", "16～30秒", "31～45秒", "46～60秒", "60秒超"]
    )
    plt.figure(figsize=(10, 6))
    sns.barplot(x=avg_views.index, y=avg_views.values, palette="magma")
    plt.title("動画の長さ別・平均再生数")
    plt.xlabel("動画の長さ")
    plt.ylabel("平均再生数")
    plt.gca().yaxis.set_major_formatter(FuncFormatter(comma_formatter))
    save_figure("動画長さ別_平均再生数.png")


# --- ワードクラウド ---
def generate_wordcloud(files):
    tokenizer = Tokenizer()
    words = []
    for file in files:
        df = pd.read_csv(os.path.join(DATA_FOLDER, file))
        if "is_short" not in df.columns:
            continue
        df = df[df["is_short"]]
        for title in df["title"].dropna().astype(str):
            words.extend(extract_meaningful_words(title, tokenizer))
    if words:
        wc = WordCloud(font_path="C:/Windows/Fonts/meiryo.ttc",
                       background_color="white", width=800, height=600).generate(" ".join(words))
        plt.figure(figsize=(10, 8))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        save_figure("ワードクラウド.png")


# --- 成功動画ワード ---
def analyze_success_title_words(files):
    tokenizer = Tokenizer()
    all_dfs = []
    for file in files:
        df = read_data(os.path.join(DATA_FOLDER, file))
        df["channel"] = get_channel_name(file)
        all_dfs.append(df)
    combined = pd.concat(all_dfs)
    overall_avg_views = combined["viewCount"].mean()
    success_videos = combined[combined["viewCount"] >= overall_avg_views]
    if success_videos.empty:
        print("成功動画がありません。")
        return
    words = []
    for title in success_videos["title"].dropna().astype(str):
        words.extend(extract_meaningful_words(title, tokenizer))
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
    save_figure("成功動画タイトル頻出ワード_Top20.png")


def export_all_to_excel(summary_df, top10_df, weekday_dfs, hour_dfs, perf_df):
    output_path = os.path.join(OUTPUT_FOLDER, "分析レポート.xlsx")

    # タイムゾーンを除去（Excel対応）
    if "published_at" in top10_df.columns:
        top10_df["published_at"] = top10_df["published_at"].dt.tz_localize(
            None)

    # カラム名を日本語に変換（top10）
    top10_df = top10_df.rename(columns={
        "channel": "チャンネル名",
        "title": "タイトル",
        "viewCount": "再生数",
        "published_at": "投稿日"
    })

    # 曜日別
    if weekday_dfs:
        weekday_df = pd.concat(weekday_dfs)
        weekday_avg = weekday_df.groupby(
            "weekday")["viewCount"].mean().reindex(WEEKDAYS_EN)
        weekday_avg.index = WEEKDAYS_JP
        weekday_avg_df = weekday_avg.reset_index()
        weekday_avg_df.columns = ["曜日", "平均再生数"]
    else:
        weekday_avg_df = pd.DataFrame(columns=["曜日", "平均再生数"])

    # 時間帯別
    if hour_dfs:
        hour_df = pd.concat(hour_dfs)
        hour_avg = hour_df.groupby("hour")["viewCount"].mean().reset_index()
        hour_avg.columns = ["時間", "平均再生数"]
    else:
        hour_avg = pd.DataFrame(columns=["時間", "平均再生数"])

    # チャンネル別サマリ（投稿本数・平均再生数）
    summary_df = summary_df.rename(columns={
        "channel": "チャンネル名",
        "video_count": "投稿本数",
        "average_views": "平均再生数"
    })

    # チャンネルパフォーマンス（平均再生数・投稿頻度・成功率）
    perf_df = perf_df.rename(columns={
        "channel": "チャンネル名",
        "avg_views": "平均再生数",
        "freq_per_week": "投稿頻度（週あたり）",
        "success_rate": "成功率（%）"
    })

    # 書き出し
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, index=False, sheet_name="チャンネル別サマリ")
        top10_df.to_excel(writer, index=False, sheet_name="今週のTop10動画")
        weekday_avg_df.to_excel(writer, index=False,
                                sheet_name="曜日別平均再生数（ショート）")
        hour_avg.to_excel(writer, index=False, sheet_name="時間帯別平均再生数（ショート）")
        perf_df.to_excel(writer, index=False, sheet_name="チャンネルパフォーマンス分析")


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
    export_all_to_excel(summary_df, top10_df, weekday_dfs, hour_dfs, perf_df)


if __name__ == "__main__":
    print("📊 YouTubeデータ分析を開始します...")
    main()
