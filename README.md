# AIChatbot for VRC/cluster

![AIChatbot Architecture Overview](overview.png) 

## リポジトリについて

GUIやPowerShellスクリプトなど、より使いやすくする機能が[bmaltais氏のリポジトリ](https://github.com/bmaltais/kohya_ss)で提供されています（英語です）のであわせてご覧ください。bmaltais氏に感謝します。

以下のスクリプトがあります。

* DreamBooth、U-NetおよびText Encoderの学習をサポート
* fine-tuning、同上
* LoRAの学習をサポート
* 画像生成
* モデル変換（Stable Diffision ckpt/safetensorsとDiffusersの相互変換）



## Macでの動作に必要なプログラム

- Homebrew: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
コマンド実行後にパスを通すための指示が出るので、それに従ってください。
- Python 3.10.x：brew install python@3.10
- git: brew install git
- pip: curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py

## Mac環境でのインストール

```terminal
git clone https://github.com/nayu-frontline/AIChatbot.git
cd AIChatbot

brew install portaudio
pip3 install --upgrade -r requirements.txt
```

ユーザディレクトリの直下の.zshrcファイルに以下を追記してください。
```
export PATH=$PATH:/opt/homebrew/bin/
```
なお、.zshrcファイルは隠しファイルとして設定されるので、ユーザディレクトでcommand、shift、.キーを同時に押すことで表示できます。
もし.zshrcファイルがなければ、以下のコマンドを実行してファイルを作成し、作成したファイルを開いて上記を追記してください。

```terminal
cd ~
touch .zshrc
```

参考：https://god48.com/zsh-path


GoogleのSpeech-to-text APIを使用するので、以下のサイトを参考に、サービスアカウントを作成して、秘密鍵をPCに保存してください。
https://qiita.com/vongole12gk/items/2e3a9359c39b5556e8c8

保存した秘密鍵を.zshrcファイルに追記して保存します。
```
export GOOGLE_APPLICATION_CREDENTIALS="秘密鍵のパス.json"
```
