# AI危険度予測による災害救援物資の自律配送ロボット

災害現場を模した25×20セルの2D環境で、差動二輪ロボットが基地から避難所へ物資を配送するPython 3.12シミュレーションです。CPUだけで動作し、GPU・GUI・外部API・APIキーは不要です。

[説明資料PDF](submission/report.pdf) / [OP・ED付き完成動画](submission/final_demo.mp4) / [全試行の結果](docs/results.md) / [統計検証の事前設計](docs/statistical_plan.md)

## AIと共通の安全制御

Random Forestは壁距離、通路幅、観測物体の相対位置・接近速度、候補速度・方向など10特徴から、1.5秒の局所直進における衝突・ニアミスを予測します。独立した集合でisotonic確率校正を学習します。AIの辺コストは `1 + weight * max(0, p - floor) / (1 - floor)`。重み0では距離A*へ戻ります。

距離優先、同じ観測特徴から壁近接・動的接近を評価するルール方式、AI方式を比較します。ルール方式も独立に重みを調整し、意図的に弱い比較対象を使いません。30開発環境と6回帰環境で選んだ設定は [configs/method_policies.json](configs/method_policies.json) に固定しています。AIは重み2・floor 0.4、ルール方式は重み0.5です。

全方式で速度・加速度制約、観測速度による2.5秒予測領域、再計画、進捗監視、独立安全停止を共有します。3秒で0.15m進まない場合は先頭経路を一時回避し、迂回不能なら元の条件へ戻します。静的特徴のキャッシュは地図変更時に無効化し、動的特徴は毎回計算します。安全閾値を性能改善のために緩和しません。

## セットアップ

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

## 学習・調整・固定標本の評価

```bash
python scripts/generate_dataset.py
python scripts/train_model.py
python scripts/statistical_study.py tune --workers 4
python scripts/statistical_study.py test --workers 4
python scripts/audit_results.py
```

学習はシナリオ0–23、モデル選択40–45、校正60–65、各150例。RFは80木、乱数42、深さ8/12を検証F1で選択します。分類テスト100–105は過去にも使った診断集合で、新しい配送テストとは区別します。

配送の追加調整は各環境seed 1000–1009の30組。AI7候補・ルール5候補を、既存3環境のseed 310/311の回帰6組も含め計432走行で比較します。既存の安全配送を維持し、開発集合の安全配送数・成功数・衝突数・失敗時180秒の配送時間の順に選択します。CPU時間は調整基準に使いません。固定済み設定だけを適用する場合は `python scripts/statistical_study.py apply` で適用できます。

最終評価はcrossing 20000–20199、clutter 30000–30199、closure 40000–40199の600組、3方式で1,800走行です。シナリオ間でもシードを共有せず、動的環境400組を含みます。方式の実行順はシードで無作為化し、4プロセスで実行します。並列実行の壁時計時間と各プロセス自身のCPU時間を区別します。全圧縮ログを検査し、失敗も記録します。安全配送は180秒以内の成功かつ衝突・ニアミス0です。

主評価は安全配送率差。正確McNemar両側検定の2比較にHolm補正を適用し、補正p<0.05かつ対応95%区間下限>0の場合だけ当該比較の優位性を支持します。時間・距離などを後から主指標へ置き換えません。有意になるまで試行を追加せず、600組を最後まで実行します。5ポイントの効果・不一致率0.15という仮定での近似検出力は約83%ですが、有意差を保証する値ではありません。

モデルや制御を変更して再評価する際は、未使用シードの新しい計画と新しい `--root` を指定してください。最終評価の同じ結果を再開する場合は入力と設定の一致を確認し、成功・失敗とも保持します。調整実験は再実行時に全件を計算し、古いモデルの調整結果を流用しません。CPUの測定値はOS負荷などで変動します。評価だけを再集計する場合は `python scripts/statistical_study.py analyze` を使います。

## 提出動画・図表・PDF

```bash
python scripts/build_submission.py
python scripts/publish_results.py
python scripts/generate_report.py
# IDは手元で置き換え、公開コードへ記録しない
python scripts/generate_report.py --output outputs/submission/説明資料_PAI最終課題_ID.pdf
```

完成動画は、提供OP約3秒→説明4秒→実測比較71秒→全600組の結果8秒→提供ED約3秒、総尺約89秒、1280×720、H.264/AACです。デモは結果に依存しない規則「closureの最小最終シード40000」で固定します。シミュレーション表示と再生倍率を含み、再生速度は制御精度を変えません。全走行を表示し、最大4倍を超える尺は拒否します。

OPは `assets/opening.mp4`（提供名：PAI応用1_最終課題_OP.mp4）、EDは `assets/ending.mp4`（同ED.mp4）です。両素材に音声ストリームはないため、完成版には無音AACを付けます。音声付き素材には元の音声を保持する結合処理です。映像のアスペクト比と講座提供元のロゴを保持し、素材を切り詰めません。

## 保存先

- `models/risk.joblib`：校正済みモデル。信頼できるローカル生成joblibだけを読み込んでください。
- `configs/statistical_study.json`：標本数、評価項目、検定、多重比較補正、未使用シード
- `outputs/statistics/tuning_results.json`：432開発走行の記録
- `outputs/statistics/test/logs/frozen/*.jsonl.gz`：全1,800走行の検査済みログ
- `docs/benchmark_results.csv` / `.json`：全試行の指標
- `docs/benchmark_summary.json`：記述統計、対応比較、信頼区間、補正p値
- `docs/policy_validation.json`：開発用の調整結果
- `docs/pilot90_summary.json`：従来の90組の探索的参考値。現在の600組と混同しないでください。
- `docs/figures/`：実測グラフ、`docs/environment.json`：環境・モデルハッシュ・開始コミット
- `submission/report.pdf` / `submission/final_demo.mp4`：最新提出物
- `outputs/submission/`：手元の提出者ID入りPDF（Git管理外）

モデル・データ・大きな全走行ログ・中間動画はGit管理外です。小さい完成動画・PDF、デモの再生ログ、OP・ED素材と再生成コードを管理します。

## 制約

局所直進の危険度は、旋回や通過時刻を含む経路全体の安全確率ではありません。初期地図・自己位置・物体分類は理想的で、滑り、通信遅延、実機ブレーキは未モデル化です。停止中のロボットへ移動物体が進入すれば衝突する場合があり、失敗として記録します。CPU時間を仮想時刻へ加えていないため実時間制御性能を主張しません。

有意差がないことは同等性の証明ではありません。有意差があっても、5ポイント以上の実用的改善や実機の安全性を保証しません。推定差と区間、衝突・失敗件数を併記し、全方式で優れるか、特定の比較だけで支持されたかを区別します。

[設計](docs/design.md) / [統計計画](docs/statistical_plan.md) / [ログ仕様](docs/log_schema.md) / [提出条件](docs/requirements.md) / [ライセンス](docs/third_party_licenses.md)
