# 阪神タイガース 新人王有資格者ドラフト ダッシュボード

阪神タイガースの新人王有資格者10名を対象とした独自ドラフトゲームの結果および、全新人王有資格者の中での「質と量」を可視化するダッシュボードです。

## 🌐 公開ページ (GitHub Pages)
GitHub Pages を有効化すると以下のURLで閲覧できます：
- https://kotowaru6949-debug.github.io/sinzinou/

## 📏 評価ルール（独自ポイント）
※対象は**1軍公式戦の成績のみ**（2軍成績は対象外）。
- **投手**：`1対戦打者 = 1ポイント`
- **野手**：`1打席 = 1ポイント`

## 📊 セイバーメトリクス指標（質と量）
`baseball-data.com` の1軍全選手データ（`tpa-1.html`, `ip3-1.html`）から算出した1軍リーグ全体平均を `100` として各選手の質を評価しています。
- **投手**
  - **対戦打者数（量）** / **K-BB実数（奪三振 − 与四球）**
  - **K-BB%（質）**：$\frac{\text{奪三振} - \text{与四球}}{\text{対戦打者}} \times 100$
  - **K-BB+（質・リーグ平均比）**：$100 \times \frac{\text{選手 K-BB\%}}{\text{1軍平均 K-BB\%}}$
- **野手**
  - **打席数（量）** / **塁打＋四球（生産量）**
  - **OPS（質）**：出塁率 ＋ 長打率
  - **OPS+（質・リーグ平均比）**：$100 \times \left(\frac{\text{選手 OBP}}{\text{1軍平均 OBP}} + \frac{\text{選手 SLG}}{\text{1軍平均 SLG}} - 1\right)$

## 📁 ファイル構成
- `index.html`: インタラクティブ・ダッシュボード（Chart.js による順位グラフ・4象限散布図・比較表）
- `game_result.json`: 集計済みスタッツおよびランキングデータ
- `build_full_analysis.py`: データ取得・指標算出・HTML生成スクリプト
- `.github/workflows/update.yml`: GitHub Actions による毎日定時・手動データ更新ワークフロー

## 🔄 データ更新方法
```bash
python build_full_analysis.py
```
また、GitHub リポジトリの **Actions** タブから「Update Draft Stats」ワークフローを手動実行（`workflow_dispatch`）することで、最新成績の取得とダッシュボード更新を自動で行えます（毎日定時スケジュールでも自動実行されます）。
