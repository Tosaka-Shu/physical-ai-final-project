# 配送制御と計算性能の評価

basic / shortcut / dynamic、hard、seed 200・201、通常A* / AI A*の12試行を同条件で比較する。

|方式|成功|衝突|ニアミス|平均距離m|平均時間s|
|---|---:|---:|---:|---:|---:|
|基準実装|12/12|0|0|30.413|47.550|
|進捗監視・ベクトル化|12/12|0|0|30.413|47.550|

成功率・経路距離の改善はこの評価では認められない。進捗監視は3秒間で0.15m進まない場合に再計画する。停滞した先頭2セルを一時回避し、迂回不能なら元の条件で再計画する。障害物判定と安全停止は共通であり、AI異常時の停止も維持する。停滞は低速条件の専用テストで再現する。通常配送の結果から、未検証の障害状況での復帰成功率は主張しない。

移動物体の2.5秒等速包絡は500セルを配列計算する。参照実装とのセル一致を検査した。1物体・25×20セルの単体計測では参照14.080ms、配列計算0.110ms。約128倍は当該関数の計測であり、配送全体の速度比ではない。同時実行負荷のある実時間は参考値とする。

デモはdynamic / hard / seed 200の実走行。75秒・720pで通常A*とAI A*を比較し、道路封鎖、迂回、再計画、配送完了を表示する。再生倍率は表示用の時間換算であり、制御周期や成功率を変更しない。最大4倍を上限とする。

再現コマンド：

```bash
PYTHONPATH=src python scripts/evaluate.py --seeds 200 201 --difficulty hard --output outputs/improvement/final
PYTHONPATH=src python scripts/run_demo.py --compare --difficulty hard --scenario dynamic --seconds 75 --fps 8 --output outputs/improvement/demo75.mp4
pytest -q
```
