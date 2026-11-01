# 検証結果

## 自動テスト

Python 3.12環境で `pytest -q` を実行し、45件すべて成功した。依存関係の検査には `python -m pip check` を使用する。

## 学習・評価

- 学習データ3,600件、検証データ900件、テストデータ900件を使用。分割はシナリオ単位。
- 評価はbasic、shortcut、dynamicの3シナリオ、seed 200・201・202、2方式の計18試行。
- 通常A*、AI A*とも配送成功は9/9。衝突・ニアミスは0件。
- CSV、JSON、Markdownの集計と各試行ログは `outputs/evaluation-v2-final/` に保存する。

## 動画

比較動画は75秒、1280×720、H.264、8fps、600フレーム。全フレームのデコードを確認した。動画は `submission/delivery_comparison_75s.mp4`、走行ログは `outputs/improvement/` に保存する。

配送結果の詳細は[比較実験の結果](results.md)、学習指標は `model_metrics.json` を参照する。
