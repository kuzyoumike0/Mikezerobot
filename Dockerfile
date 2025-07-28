# ベースイメージ（Python3.12スリム版）
FROM python:3.12-slim

# 環境変数を設定（非対話モード）
ENV DEBIAN_FRONTEND=noninteractive

# 必要なシステムパッケージをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    libsndfile1 \
    libasound2 \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    

# 作業ディレクトリを作成
WORKDIR /app

# requirements.txt をコピーしてインストール
COPY requirements.txt .

# Pythonパッケージのインストール（キャッシュなし）
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install numpy sounddevice scipy


# アプリケーションのソースコードをコピー
COPY . .

# コンテナ起動時に bot を実行
CMD ["python", "bot.py"]
