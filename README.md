# 📊 YouTubeデータ分析Webアプリ

## 概要
Youtube Data APIを活用して、指定したYouTubeチャンネルの動画データを自動取得・分析・可視化します。  
ショート動画を中心に、視聴傾向や成功動画の特徴を抽出し、ビジュアルなレポートとともに分析結果を出力します。

## 主な機能
- チャンネル別 投稿本数・平均再生数
- 曜日・時間帯ごとの視聴傾向（棒グラフ・ヒートマップ）
- 今週のTop10動画抽出
- 成功動画のタイトル分析（頻出単語）
- ワードクラウド生成
- 投稿頻度・成功率によるチャンネル評価
- 動画の長さ別 再生傾向分析
- すべての結果をExcelに自動まとめて出力

## フォルダ構成📁

- 📊 `analyze.py`  
  └─ データ分析・グラフ可視化の処理を行うスクリプト

- 🚀 `main.py`  
  └─ APIから動画情報を取得し、自動で分析処理を呼び出すメイン起動ファイル

- 🔑 `config.py`  
  └─ YouTube APIキー（`YOUTUBE_API_KEY`）を設定するファイル

- 📄 `channels.csv`  
  └─ チャンネル名とチャンネルIDを記載したCSVファイル（ユーザーが用意）  
     例:  
     ```
     name,channel_id
     ヒカ〇ン,xxxxxxxxxxxxxxxxxxxxx
     ```

- 📂 `data/`  
  └─ 各チャンネルごとに取得された動画データ（CSV）が格納されるフォルダ

- 📁 `output/`  
  └─ 分析結果（グラフ、Excel、CSVなど）の出力先フォルダ




## 必要ライブラリ
以下のパッケージをインストールしてください。
（Python 3.8以降推奨）
 ```
 pip install pandas matplotlib seaborn janome wordcloud requests isodate xlsxwriter
 ```

## 使用方法

### ① APIキーを設定
config.py に以下のように記載してください。
```
YOUTUBE_API_KEY = "あなたのYouTube APIキー"
```

### ② チャンネルリストを用意
ルートに channels.csv を以下の形式で配置してください。
```
 name,channel_id
 ヒ〇キン,hogehogehogehoge
 はじ〇しゃちょー,fugafugafuga
```

### ③ アプリを実行
```
python main.py
```

## 出力される主なファイル（output/）
- チャンネル別_投稿本数.png
- 曜日別_平均再生数_ショート動画.png
- 時間帯別_平均再生数_ショート動画.png
- 曜日別_時間別_平均再生数_ヒートマップ.png
- 成功動画タイトル頻出ワード_Top20.png
- 動画長さ別_平均再生数.png
- ワードクラウド.png
- 今週のTop10動画.csv
- 分析レポート.xlsx（全結果まとめ）

## 補足
- analyze.py は単体でも使用可能です（既に data/ にCSVがある場合）
- 分析対象はショート動画（60秒以下）を優先
- 成功動画とは、平均再生数より上の再生数を記録した動画を指します

## ライセンス
MIT

## 作成者
中畑 倫（Rin Nakahata）  
- 技術ブログ（note）：[note記事はこちら](https://note.com/rin_nakahata/n/n965ab50b29a6)