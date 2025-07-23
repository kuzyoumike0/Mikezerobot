#!/bin/bash

# ffmpeg をインストール（初回のみ）
apt update && apt install -y ffmpeg

# Bot を起動
python3 main.py
