# ベースイメージ（Python3.12スリム版）
FROM python:3.12-slim

# apt-get更新 & ffmpegをインストール
RUN apt-get update && apt-get install -y ffmpeg

# 作業ディレクトリ設定
WORKDIR /app

# 依存パッケージ（requirements.txt）をコピーしインストール
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

RUN apt-get update && apt-get install -y libportaudio2

# Bot起動コマンド（例：bot.pyが起動スクリプト）
CMD ["python", "bot.py"]
