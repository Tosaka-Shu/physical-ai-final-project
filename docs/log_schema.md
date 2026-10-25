# JSONLログの仕様（v2）

1行=0.1秒の制御ステップ。`simulation_time`は**更新前**のシミュレーション時刻。センサー観測と制御選択がこの時刻に対応し、`next_pose`は`dt`秒後の状態。各行にepisode_id/scenario_id/seedを記録する。欠損値・NaN・Infは許容しない。AI不使用時の危険度は0、`ai_active=false`で区別する。イベント不発時は`occurred=false, reason=""`。物体が見えない場合のdetectionsは空配列であり、欠損ではない。

|キー|意味／単位|
|---|---|
|episode_id / scenario_id / seed / difficulty|走行と条件の識別子|
|simulation_time / dt|観測・制御時刻／刻み（秒）|
|robot_pose / next_pose|更新前／後の[x(m), y(m), theta(rad)]|
|robot_velocity / next_velocity|更新前／後の[v(m/s), omega(rad/s)]|
|sensor_observations|timestamp(s)、ranges(m)、angles(rad)、max_range(m)、static_hits、detections|
|detections|レイが命中した移動物体のみ。id、現在の中心position(m)、過去観測差分velocity(m/s)、半径radius(m)|
|requested_action / selected_action|追従制御の要求／加速度制限と安全ゲート通過後の[v, omega]|
|predicted_risk / ai_active|現在位置・候補方向のRF危険度[0,1]／AI使用有無|
|planned_path|実際の追従用経路の残りセル列|
|replanning_event|再計画の有無と理由。initialは初期計画なのでoccurred=false|
|safety_stop_event|安全停止の有無と理由。stale、proximity、sweep、model異常など|
|collision / near_miss|刻み内に真値で評価した接触／余裕0.18m未満|
|delivery_result|running / success / collision / timeout / unreachable / model_unavailable|
|inference_latency_ms|そのステップのRF predict_proba実時間合計（候補経路＋局所リスク）。特徴量構築は含めない|
|evaluation|描画・採点専用の真値。物体位置、最小余裕、封鎖イベント、封鎖適用状態。AI・安全層へ入力しない|

安全ゲートは完全な世界状態ではなく、static prior map＋観測更新と、過去／現在の物体検出のみを使用する。移動物体はレイに当たった場合に理想的に分類・中心推定できるセンサーとしてモデル化する。実際の点群クラスタリングや物体認識AIは未実装。

`logger.validate_log`は必須キー、値の有限性、単調時刻、観測周期、センサー範囲、同一エピソード、観測／指令時刻、行間の姿勢・速度の連続性、指令の運動積分と次状態の整合性を検査する。`write_log/read_log`で自動実行する。

```bash
export PYTHONPATH="$PWD/src"
.venv/bin/python scripts/make_video.py outputs/v2/preview.jsonl \
  --baseline-log outputs/v2/preview-baseline.jsonl \
  --seconds 90 --fps 10 --output outputs/v2/replay90.mp4
```

リプレイは保存した観測・姿勢・真値表示情報を読み戻すだけで運動を再計算しない。通常のPython JSONLであり、ROS 2やrosbag2を使用したとは呼ばない。
