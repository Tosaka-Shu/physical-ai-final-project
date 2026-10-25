# AI危険度予測による災害救援物資の自律配送ロボット

CPU・ヘッドレスで実行できるPython製2Dロボットシミュレーション。救援基地から避難所へ、壁・瓦礫・狭路・移動障害物を避けて配送する。通常A*とRandom Forest危険度をコストに加えたA*を比較する。実機やROS/Gazeboのシミュレーションではなく、独自の簡易運動モデルである。

## セットアップ

Python 3.12、FFmpeg（libx264対応）、日本語フォントNoto Sans CJKを使用。GPU・有料API・キーは不要。Debian/Ubuntuでシステム依存がない場合は `sudo apt-get install ffmpeg fonts-noto-cjk`。

```bash
cd /workspace/physical-ai-final-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
export PYTHONPATH="$PWD/src"
export MPLCONFIGDIR=/tmp/rescue-matplotlib
pytest -q
python scripts/train_model.py
python scripts/evaluate.py --seeds 200 201 202
python scripts/run_demo.py --seconds 12 --output outputs/preview.mp4
```

標準シェルでは実行前に毎回仮想環境とPYTHONPATHを設定する。`requirements.txt`は主要依存の固定、`requirements-lock.txt`は今回使用した推移依存を含む固定版。モデルは再学習で生成し、外部の未信頼pickleをロードしない。

## 実行と成果物

- `models/risk.pkl`：学習済みモデル（Git除外）
- `models/risk.json`：シナリオ分割・精度・ROC AUC
- `outputs/evaluation/results.{csv,json,md}`：複数シードでの実測
- `outputs/preview.mp4`：日本語テロップ付き720pプレビュー
- `outputs/preview.json`：動画の根拠となる時刻・姿勢・移動物体・経路・結果
- `docs/results.md`、`docs/evaluation.json`、`docs/model_metrics.json`：今回の小さな実測記録

通常方式の動画は `python scripts/run_demo.py --method distance --output outputs/distance.mp4`。
90秒版は `python scripts/run_demo.py --seconds 90 --fps 12 --output outputs/demo90.mp4`。指定した尺へ実走行ログを再サンプリングするため、タイトルに実際の再生倍率を表示する。位置はログから取り出し、架空の走行は追加しない。90秒版の生成状況は作業報告を参照。動画に音声はない。

## AI使用部分と再現条件

RandomForestClassifierの`predict_proba()`をA*の各移動コストに加算する。障害物からの距離・通路幅・移動障害物の相対位置と接近速度・進行方向と速度を入力する。ラベルは1.5秒の局所走行を実際に模擬した衝突またはニアミス。学習0–29、評価100–109、配送比較200–202のシナリオを分離し、モデル乱数42で固定する。

独自の工夫は、狭路と広路の選択、方向別危険度のバッチ推論、AIと独立した安全制御、実走行ログに基づく動画。テストでは学習したモデルが通常方式とは異なる経路を選ぶこと、両方式の配送、衝突回避、再計画を検証する。

## 結果と既知の制約

[実測結果](docs/results.md)では今回の3シードで両方式とも配送に成功した。AI方式の距離と再計画回数は増加しており、一般的な優位性は確認できていない。

地図の主要壁構造は固定、瓦礫配置と移動位相を乱数化する。経路と安全制御は完全な世界状態を使用し、仮想距離センサーは観測・記録用。移動障害物も接触を避ける譲り合い規則に従う。AIは到着時刻を予測せず、局所危険度は実環境で校正された確率ではない。実機安全性・SLAM・滑り・センサー雑音は対象外。

[設計](docs/design.md) / [レポート構成案](docs/report_outline.md) / [課題要件](docs/requirements.md)。1–3分の最終動画のYouTube公開、PDF作成・提出、mainへのマージは別途必要。
