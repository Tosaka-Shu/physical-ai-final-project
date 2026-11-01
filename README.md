# AI危険度予測による災害救援物資の自律配送ロボット

25×20セルの災害現場で、差動二輪ロボットが壁・瓦礫・移動物体を避けて避難所へ配送するPython 3.12シミュレーションです。CPUだけで動作し、GPU・外部API・APIキーは不要です。

[説明資料PDF](submission/report.pdf) / [OP・ED付き完成動画](submission/final_demo.mp4) / [全試行の比較](docs/results.md)

## AIと安全制御

Random Forestは、壁距離・通路幅・観測した物体の相対位置と接近速度・候補方向と速度から、1.5秒の局所直進における衝突・ニアミスを予測します。独立したシナリオでisotonic確率校正を学習します。A*の辺コストは `1 + weight * max(0, p - floor) / (1 - floor)`。検証で重み2、floor 0.4を選び、最終テスト前に固定しました。重み0では距離A*へ戻ります。

距離方式、同じ特徴から壁近接・動的接近を計算するルール方式、AI方式を比較します。初期地図と自己位置は既知で、移動物体は観測できた過去・現在の情報だけを使います。未来の真値はラベル生成と評価専用です。

全方式が同じ速度・加速度制限、観測速度の2.5秒予測領域、独立安全停止、再計画、進捗監視を共有します。3秒で0.15m進まない場合は先頭経路を一時回避し、迂回不能なら元の条件で再試行します。新しい壁を観測した際には静的特徴キャッシュを無効化し、動的特徴は毎回計算します。

## 環境とセットアップ

LinuxではFFmpegと日本語フォントを用意してください。GUIは不要です。

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg fonts-noto-cjk python3.12-venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt -r requirements-report.txt
export PYTHONPATH="$PWD/src"
export MPLCONFIGDIR=/tmp/rescue-matplotlib
pytest -q
```

## 学習と評価

```bash
python scripts/generate_dataset.py
python scripts/train_improved.py
python scripts/ablate.py
python scripts/benchmark.py
```

学習はseed 0–23、モデル選択40–45、校正60–65、各150例。RFは80木、乱数42、深さ8/12を検証F1で選択します。分類テスト100–105は過去に使った診断集合です。配送のパラメータ選択は700・701、アブレーションは800・801、最終配送は10000–10029で分離しています。

最終比較はcrossing・clutter・closure各30組、3方式の270走行で、動的環境60組を含みます。地図の壁位置・通路・瓦礫・移動位相をシードで固定し、全方式へ同じ環境を適用します。180秒制限、成功・衝突・ニアミス、終了までの時間・距離、停止時間、再計画、最小余裕、推論・計画・CPU実行時間を全件記録します。安全配送は時間内成功かつ衝突・ニアミス0。失敗を除外せず、失敗を180秒とする指標とシード単位の対クラスターブートストラップ区間も保存します。結果を見て最終環境やパラメータを調整しません。

[数値と解釈](docs/results.md)、[モデル指標](docs/model_metrics.json)、[実行環境・モデルハッシュ](docs/environment.json)、[要素別評価](docs/ablations.json)を参照してください。旧AIの測定は[基準測定](docs/baseline_results.json)に残します。AIが全指標で優れるとは仮定しません。

## 動画とPDF

```bash
python scripts/build_submission.py
python scripts/audit_results.py
python scripts/publish_results.py
python scripts/generate_report.py
# IDは手元で置き換え、公開コードに記録しない
python scripts/generate_report.py --output outputs/submission/説明資料_PAI最終課題_ID.pdf
```

完成動画は、提供OP（assets/opening.mp4）→説明カード→実測比較→全評価の結果カード→提供ED（assets/ending.mp4）です。OP約3.04秒、ED約2.97秒をカットせず、アスペクト比を維持します。両素材に音声ストリームはなく、互換性のため無音AACを追加します。別の素材に音声があれば保持する結合処理です。素材には講座提供元のロゴが含まれます。

デモは事前規則「closure・最小テストseed 10000」で固定し、有利な結果による選別を行いません。本編75秒、説明・結果カード各4秒、全体約89秒、1280×720、H.264/AACです。画面の再生倍率は時間表示の換算だけで、制御周期や成功率を変更しません。全走行を表示し最大4倍を超える場合は拒否します。

集計前に1走行だけ確認する場合：

```bash
python scripts/run_demo.py --compare --scenario closure --seed 10000 --difficulty hard --seconds 75 --fps 8 --output outputs/demo.mp4
```

## 保存先

- `models/risk.joblib`：校正済みモデル（ローカル生成の信頼できるjoblibのみ読み込み）
- `configs/selected.json`：配送検証で固定した重み
- `outputs/final/benchmark/logs/*.jsonl.gz`：全270走行の検査済み観測・制御ログ
- `docs/benchmark_results.csv` / `docs/benchmark_results.json`：全試行の指標
- `docs/benchmark_summary.json`：平均・中央値・標準偏差と対比較区間
- `docs/figures/`：実測値から生成するグラフ
- `submission/report.pdf` / `submission/final_demo.mp4`：最新提出物
- `outputs/submission/`：手元の提出者ID入りPDF（Git管理外）

データ・モデル・走行ログ・中間動画はGit管理外です。小さい完成動画・PDFと再生成に必要なOP・ED素材はGitで管理します。

## 制約

局所直進ラベルは、旋回や経路全体の安全確率を表しません。物体検出と自己位置は理想的で、車輪滑り・通信遅延・実機ブレーキは未モデル化です。停止しても移動物体が進入すれば衝突する場合があり、失敗として全件記録します。CPU推論時間を仮想時刻へ加えていないため実時間制御性能は保証しません。最終テストで目標未達でも結果を調整しません。

[設計](docs/design.md) / [ログ仕様](docs/log_schema.md) / [提出条件](docs/requirements.md) / [ライセンス](docs/third_party_licenses.md)
