# AI危険度予測による災害救援物資の自律配送ロボット

Risk-Aware Autonomous Rescue Delivery Robot。CPU・ヘッドレスで動く独自のPython製2D差動二輪シミュレーション。通常A*とRandom Forest危険度を加えたA*で、基地から避難所への配送を比較する。ROS 2/Gazebo・実機・外部API・GPUは使っていない。

添付課題資料（10/19改訂版）を提出要件の正本として確認し、今回のv2開発指示との差を[要件対応](docs/requirements.md)へ整理した。PDFや講義の非公開資料はリポジトリへ転載していない。

## セットアップ

Python 3.12を使用。FFmpeg（libx264対応）とNoto Sans CJKが必要。Debian/Ubuntuでシステム依存がない場合は `sudo apt-get install ffmpeg fonts-noto-cjk`。動画機能以外のテストではこれらは不要。

```bash
cd /workspace/physical-ai-final-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
export PYTHONPATH="$PWD/src"
export MPLCONFIGDIR=/tmp/rescue-matplotlib
pytest -q
python scripts/generate_dataset.py
python scripts/train_model.py
python scripts/evaluate.py --seeds 200 201 202 --output outputs/evaluation-v2-final
python scripts/run_demo.py --compare --output outputs/v2-final/preview.mp4
```

毎回、作業ディレクトリと仮想環境・PYTHONPATHを設定する。requirements.txtは主要依存、requirements-lock.txtは今回の全推移依存を固定。設定は[configs/default.json](configs/default.json)にまとめ、`--config`で部分上書き用JSONを指定できる。未指定キーは既定値を維持し、不正値・未知キーは実行前に拒否する。新しい依存を増やさないためYAMLではなくJSONを使用した。

## 実装とAI

- 25×20の壁・瓦礫・狭路、外生的に移動する円障害物、6秒で道路が閉じるイベント。
- 加速度制限付き差動二輪(x,y,theta,v,omega)、レイキャストLiDAR、過去観測差分の接近速度。
- 既知の初期静的地図＋実際に観測した障害物だけを計画へ渡す。真値と未来位置は教師ラベル／評価器に隔離する。
- RFの`predict_proba()`を実際のA*辺コストへ加算する。モデルの有無と重み0による経路変化をテスト。
- AIと独立した近接・掃引安全ゲート、指令／観測のタイムアウト、モデル異常時の停止。通常方式へ黙って切り替えない。
- 時刻付きJSONL、品質検査、保存ログからのリプレイ、比較CSV/JSON/Markdown。

データは局所直進1.5秒の衝突／ニアミスから生成する。学習24シナリオ0–23、検証6シナリオ40–45、テスト6シナリオ100–105を分離する。各150例。モデル乱数42。検証F1だけでRFの深さを選び、テストをモデル選択へ使わない。精度・適合率・再現率・F1・ROC AUC・混同行列・重要度・推論時間を保存する。joblibはローカル生成の信頼できるファイルだけを読み込む。

独自の工夫は、局所走行結果からの教師ラベル、方向ごとのリスクコスト、狭路と広路の選択、観測した接近速度による再計画、独立安全層、ログ整合性検査と実走行再生を一貫させた点。

## 比較と動画の再現

basic（静的基本）、shortcut（危険な近道）、dynamic（移動障害物＋道路封鎖）の3種類を、同じシード・初期地図・センサー・物体軌跡・安全設定で比較する。難易度は `--difficulty easy|normal|hard`。全18試行は[実測結果](docs/results.md)と[個別JSON](docs/evaluation.json)。AI方式が常に改善するとは仮定しない。

```bash
# 保存した観測・姿勢・イベントから90秒の比較動画を再生
python scripts/make_video.py outputs/v2-final/preview.jsonl \
  --baseline-log outputs/v2-final/preview-baseline.jsonl \
  --seconds 90 --fps 10 --output outputs/v2-final/demo90.mp4

# 通常方式だけの診断
python scripts/run_demo.py --method distance --scenario basic \
  --output outputs/v2-final/distance.mp4
```

12秒プレビューは冒頭抜粋（最大2倍速）で、提出動画ではない。60〜180秒の本番動画は全走行を再生し、最大2倍速を超える尺を拒否する。今回の90秒版は8fps・720フレームで実際に生成し全フレームのデコードと配送成功表示を確認した。90秒版は1280×720・H.264・日本語説明付きで、実際の姿勢・経路ログだけを表示する。「2Dロボットシミュレーション」と再生倍率を明記し、短い配送終了後の保持表示を設ける。ヒートマップは初期観測の東向き・0.9m/s参考値、現在の数値はログの局所推論値。音声はない。

## 生成物と文書

|保存先|内容|
|---|---|
|datasets/train.npz|自作学習データのサンプル生成（同じ生成関数を学習でも使用）|
|models/risk-v2.joblib / risk-v2.json|学習済みモデル／評価とデータハッシュ|
|outputs/evaluation-v2-final/|全試行CSV・JSON・Markdown、環境記録、各走行JSONL|
|outputs/v2-final/preview.mp4 / preview.jsonl|新版プレビュー／完全なAI走行ログ|
|outputs/v2-final/preview-baseline.jsonl|通常方式の比較走行ログ|
|outputs/v2-final/demo90.mp4|保存ログから生成する90秒比較動画|
|docs/model_metrics.json|今回のモデル評価の小さな記録|
|docs/diagnosis/|開発中に見つけた衝突と改善の記録（最終結果とは区別）|

動画・データ・モデル・一時ログはGit除外。旧版のoutputs/preview.mp4、outputs/demo90.mp4、models/risk.pkl等が残っていても、新版の成果物とは区別する。

[設計・構成図](docs/design.md) / [ログ仕様](docs/log_schema.md) / [OSSライセンス](docs/third_party_licenses.md) / [日本語レポート原稿](docs/report_outline.md)。GitHub ActionsのCPUテスト定義を追加したが、リモート実行結果はローカルpytestとは別に確認する。

## 既知の制約と提出状況

初期地図と自己位置は既知、検出は理想的な物体分類・中心推定を仮定する。学習地図は変化させるが、配送評価の主要壁構造は限定的。RF危険度は未校正で、実機安全性を保証しない。停止中のロボットへ物体が侵入するケースもあり、観測速度による早期迂回で軽減する。実機ブレーキ、SLAM、ノイズ・遅延、車輪の滑り、荷物の物理、ROS 2連携は未実装。

コードは作業ブランチとPRで提供し、mainへのマージ、YouTube公開、PDF化・提出、OmniCampusへのURL提出は自動実行しない。提出用識別子や個人情報は公開コードに含めず、提出時に手元で設定する。締切2026-11-02 10:00 JST。提出前に[要件チェック](docs/requirements.md)を確認する。

PR #1とPR #2の置換・維持・整理の対応は[統合確認](docs/integration_review.md)を参照。
