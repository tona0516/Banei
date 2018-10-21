# Overview
ばんえい競馬データをスクレイピングする

# Enviroment
python 3.7.0

# Commands
- venvで環境を切り分ける場合
  1. 新しい環境を作成する
    - `python -m venv <venv名>`
  1. アクティベート
    - `source <venv名>/bin/activate`
  1. ディアクティベート
    - `deactivate`
- 要求ライブラリの保存
  - `pip freeze > package.txt`
- 要求ライブラリのインストール
  - `pip install -r package.txt`
- 型チェック
  - `mypy src/`
- 実行
  - `python src/Main.py`
