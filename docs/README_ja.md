<div align="center">

# NTE Auto-Fishing

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

**リアルタイムなゲーム操作に向けた、可視化と調整ができる自動釣りアシスタントです。**

Python、OpenCV、MSS、PyDirectInput、DearPyGui で構築されています。

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)
[![GitHub Stars](https://img.shields.io/github/stars/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/stargazers)

</div>

## 特長

- **ライブ操作パネル**：状態、釣果数、セッション時間、FPS、PID 出力、ROI、視覚トラッキングの状態を GUI で確認できます。
- **安全な制御フロー**：GUI 起動時は一時停止状態で開始し、停止コマンドを優先処理し、一時停止・停止・再校正・終了時に押下中のキーを解放します。
- **実行中の調整**：PID、HSV しきい値、タイミング、入力キー、グローバルホットキー、校正、デバッグ設定を Settings タブから調整できます。
- **解像度への適応**：比率ベースの ROI 校正と解像度比例フォールバックにより、1080p、2K、4K およびカスタム解像度に自動対応します。
- **高速なキャプチャと入力**：`mss` で画面領域を取得し、`PyDirectInput` でゲーム向けの入力イベントを送信します。
- **ポータブルビルド**：GitHub Actions が GUI 用の単一ファイル EXE と、初回実行時に依存関係を自動インストールする CLI ソースパッケージを生成します。

## プロジェクト構成

| パス | 説明 |
| :--- | :--- |
| `start_gui.py` | 推奨される GUI 起動エントリーポイント。 |
| `main.py` | ヘッドレス実行とコア Bot ループ。 |
| `config.py` | PID、HSV、キー、タイミング、校正の実行時設定。 |
| `gui/` | DearPyGui の操作画面、パネル、スレッド安全なブリッジ。 |
| `modules/` | キャプチャ、入力、画像認識、釣りロジックのモジュール。 |
| `templates/` | 自動 ROI 校正用の比率データ。 |
| `tools/ratio_annotator.py` | スクリーンショットから比率ベースの ROI JSON を作成する補助ツール。 |

## はじめ方

### 方法 1：ビルド済み実行ファイル（GUI）

1. [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) から最新の `NTE-Auto-Fish.exe` をダウンロードします。
2. ゲームへ入力を届けるため、管理者権限で実行します。

### 方法 2：CLI パッケージ

1. [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) から `NTE-Auto-Fish-CLI.zip` をダウンロードして展開します。
2. `run.bat` をダブルクリックすると、Python の確認と初回実行時の依存パッケージ自動インストールが行われます。
3. 詳細はターミナルで `python main.py --help` を実行してください。利用可能なコマンド：`start`、`calibrate`、`config show/set`、`reset`。

### 方法 3：ソースから実行

```bash
git clone https://github.com/Chizukuo/NTE-auto-fish.git
cd NTE-auto-fish
pip install -r requirements.txt
```

GUI を起動：

```bash
python start_gui.py
```

ヘッドレスモードを起動：

```bash
python main.py
```

## 注意

- Windows では管理者権限のターミナルから実行することを推奨します。
- ボーダーレスウィンドウまたはウィンドウ化フルスクリーンのほうが、キャプチャが安定しやすくなります。
- グローバルホットキーは GUI で変更でき、編集後に再登録されます。
- デバッグログは追加のトラッキングデータを `fishing_data.csv` に書き込みます。

## 既知の問題

- **夕暮れ・日の出時の照明干渉**：ゲーム内の日の出・日没時の暖色系の環境光が HSV ベースのカーソル検出に深刻な干渉を与え、追跡失敗や釣り成功率の大幅な低下を引き起こします。これは現在の色ベース検出方式の inherent な限界です。这种情况に遭遇した場合、設定でカーソルの HSV 閾値を調整して照明条件の変化に対応してください。
