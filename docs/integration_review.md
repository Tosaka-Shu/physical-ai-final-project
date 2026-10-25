# PR #1 / PR #2 統合確認

## 比較基準

PR #1を取り込んだmain（5943ac7）と、PR #2の実装を比較した。PR #2を現行仕様として同じモジュール内で置換し、旧版と新版の制御処理を並行して使わない。

|対象|PR #1|PR #2を基準とした結論|
|---|---|---|
|world / sensors|真値の直接参照、動的物体の譲り合い|ObservedMapとLiDAR観測へ置換。物体軌跡はロボットと独立。旧譲り合い処理は残さない|
|robot|車輪入力・速度制約中心|v/omega入力、加速度制限付き運動へ置換。差動二輪積分と車輪変換は維持|
|planner|真値由来のリスク特徴|観測特徴を使うA*へ置換。通常A*、RFコスト、重み0復帰を維持|
|risk_model|pickle、学習／テストのみ|joblib、学習／検証／テスト分離へ置換。旧モデルは既定値から参照しない|
|simulation|インライン安全処理、部分的な描画ログ|safety/logger/replayへ責務分離。真値は採点専用に維持|
|visualization / scripts|単一走行描画、旧JSON|JSONL検査・再生・左右比較を現行とする。旧JSON形式の再生互換処理は追加しない|
|requirements / lock|主要4依存と固定推移依存|既存ピンを維持。新規に直接importするjoblibをrequirements.txtにも明示。cloudpickle等は依存元が必要とするので維持|
|設定|コード内の定数中心|configs/default.jsonを正とし、部分上書きを既定値へ統合して検証する|
|pytest / CI|初期の配送テスト|既存の正常機能を新版テストで維持し、安全・ログ・設定の回帰検証を追加|
|docs|初版実測|現行結果へ置換。旧実測・失敗記録はdiagnosisに版を明示して保持し、実行用設定から分離|

## 今回の整理

- 空ディレクトリ用のsrc/.gitkeep、scripts/.gitkeep、tests/.gitkeepを削除した。
- 未使用importを削除した。旧モデル・旧世界状態ベースの並行実装は見つからなかった。
- CLI既定の出力先をREADMEの現行保存先へ統一した。
- APIのsettings上書きにも設定検証を適用し、未知キー、不正値、非整数の刻み数を開始前に拒否する。
- README、固定依存、設定、スクリプト、モデル保存形式、ログ形式、CIの参照を照合した。
- 既存の動画・モデル・ログはGit管理外のユーザー生成物として保持し、無条件に消さない。

過去のdocs/environment.json等はその実験時点の記録であり、現時点のGit状態やmainのバージョンを上書き表示するものではない。最終のmain動作確認は別の出力先outputs/main-integration-checkに保存する。
