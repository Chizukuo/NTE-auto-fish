<div align="center">

# 🎣 NTE Auto-Fishing

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

**現代のゲーム向けに設計された、高性能でインテリジェントな自動釣りボット。**

Python、OpenCV、MSS、DearPyGui を使用して構築されています。

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)

</div>

## 🌟 特徴

- **ビジュアルコントロールパネル (GUI)**：洗練された DearPyGui インターフェースを通じて、リアルタイムの状態監視、PID 調整、および HSV 閾値設定が可能です。
- **設定の保存と読み込み**：GUI から設定を簡単に保存・読み込みでき、起動時に自動的に適用されます。
- **インテリジェントな解像度対応**：マルチスケールテンプレートマッチングをサポートし、失敗した場合は解像度ベースの座標推定に自動的にフォールバックします。1080p、2K、4K などに対応しています。
- **パフォーマンス最適化**：`mss` を使用した超高速スクリーンキャプチャと、`PyDirectInput` による正確な入力シミュレーション。
- **ポータブル**：単一ファイルのエグゼキュータとして利用可能で、Python 環境の構築や解凍は不要です。

## 📁 プロジェクト構成

| ファイル/フォルダ | 説明 |
| :--- | :--- |
| `start_gui.py` | GUI バージョンの推奨エントリーポイント。 |
| `main.py` | ヘッドレスモードのエントリーポイントおよびコアロジック。 |
| `config.py` | グローバル設定管理（PID、HSV など）。 |
| `gui/` | インタラクティブなダッシュボードと設定パネル。 |
| `modules/` | コア機能モジュール：IO、ビジョン、およびロジック。 |

## 🚀 はじめに

### 方法 1：ビルド済み EXE を使う（推奨）
1. [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) ページから最新の `NTE-Auto-Fish.exe` をダウンロードします。
2. **管理者権限で実行**してください（入力シミュレーションに必要です）。
3. （任意）精度を高めるために、EXE と同じディレクトリに `templates/` フォルダを作成し、`button_f.png` と `bar_icon_left.png` を配置します。

### 方法 2：ソースから実行する
1. **クローンとインストール**：
   ```bash
   git clone https://github.com/Chizukuo/NTE-auto-fish.git
   cd NTE-auto-fish
   pip install -r requirements.txt
   ```
2. **テンプレート**：`templates/` ディレクトリにマッチング用テンプレートを配置します。
3. **実行**：
   ```bash
   # GUI を起動
   python start_gui.py
   
   # ヘッドレスモードを起動
   python main.py
   ```
   *注意：常に管理者権限のターミナルを使用してください。*

## ⚙️ 主な機能

- **ダッシュボード**：成功回数、実行時間、処理周波数などのリアルタイムテレメトリを表示します。
- **PID 調整**：`Kp` と `Ki` を動的に調整して、完璧なリール反応を実現します。
- **HSV キャリブレーション**：シアン（安全エリア）、黄色（カーソル）、青色（アタリ判定）のカラー検出を、照明条件に合わせて調整できます。
- **ライブログ**：リアルタイム診断のための統合ログコンソール。

## ⚠️ 注意事項

- **権限**：ゲームウィンドウと対話するために、必ず管理者権限で実行してください。
- **ディスプレイ設定**：キャプチャの安定性のために、**ボーダーレスウィンドウ**または**ウィンドウモードのフルスクリーン**を推奨します。
- **自動化**：GitHub Actions により、プッシュごとに自動ビルドが行われます。

---

<div align="center">
高性能で信頼性の高い自動釣りツール。
</div>
