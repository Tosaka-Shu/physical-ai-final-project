# 制御ログ仕様

1行は0.1秒の制御ステップ。simulation_timeは更新前時刻、robot_poseは更新前姿勢、next_poseは更新後姿勢。観測、要求指令、実行指令、推定危険度、経路、安全停止、再計画、真値による配送評価を保持する。

methodはdistance・heuristic・risk。ai_activeはriskのみtrueで、ルール方式の推定値もpredicted_riskへ記録する。旧ログのmethodがない場合はai_activeから復元する。リプレイは物理を再実行せず、保存した姿勢と物体位置を使う。

logger.pyは単調時刻、有限値、センサー範囲、周期、状態積分、連続性を検査する。jsonl.gzでも同じ検査を行う。最終ログはoutputs/final/benchmark/logs。評価指標CSV・JSONはdocs/benchmark_results.*に保存する。
