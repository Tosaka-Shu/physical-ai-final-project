# 提出条件とシステム要件

## 提出条件

- AIを何らかの形で使い、自由に設定したタスクをロボットに実行させる。推論のみでもよい。
- ROS/Gazebo/Genesis以外のツールも利用できる。本作はPython製の簡易2Dロボットシミュレーションを使用し、ROS 2を使ったとは表現しない。
- 動画はMP4、1〜3分。2倍速を利用する場合は明記。本実装は本番動画を最大2倍速に制限し、短いプレビューは冒頭抜粋として提出用と区別する。
- コード一式のGitHubリポジトリはpublic。URLをOmniCampusに提出する。mainへのマージは本プロジェクトの運用上のチェックであり、PDFにブランチ名指定はない。
- 説明資料はPDF形式。概要・目的・工夫を説明する。提出ファイル名は `説明資料_PAI最終課題_<OmniCampus識別子>.pdf`。
- 動画は本人のYouTubeへアップロードし、指定フォームへURLを提出する。最低でも限定公開、全体公開は推奨。タイトルは `PAI最終課題_<OmniCampusアカウント名またはID>`。
- 氏名・所属・メールアドレス等を成果物へ載せない。アカウント名が個人名ならIDを用いる。識別子は公開コードへ書き込まず提出時に手元で設定する。
- YouTubeでは子ども向け・年齢制限を「いいえ」にし、インスタントプレミア公開は使わない。予約公開なら締切までに公開される設定とし、採点完了まで削除・非公開化しない。
- 剽窃、サンプルの丸写し、無関係な提出物を避け、独自の設計と工夫を説明する。
- 締切は2026年11月2日 10:00 JST。

## システム要件と実装箇所

|開発要求|実装／検証箇所|
|---|---|
|CPU、Python 3.12、固定依存、無料・API不要|requirements-lock.txt、README、CI|
|25×20、差動二輪、速度・加速度制限|world.py、robot.py、configs/default.json|
|距離観測、時刻、真値との分離|sensors.py、ObservedMap型、観測遮蔽・未来漏洩テスト|
|安全停止、指令ウォッチドッグ、モデル異常|safety.py、モデル異常テスト|
|局所走行ラベル、学習／検証／テスト分割|data_pipeline.py、risk_model.py、docs/model_metrics.json|
|AIをA*コストへ統合、重み0の基準復帰|planner.py、経路変更・重み0テスト|
|封鎖観測後の再計画、到達不能処理|simulation.py、道路封鎖・到達不能テスト|
|ログ保存・品質検査・リプレイ|logger.py、replay.py、docs/log_schema.md|
|3シナリオ・複数シード・失敗を含む評価|scripts/evaluate.py、docs/results.md|
|日本語720p動画、実測ログから再生|scripts/run_demo.py、scripts/make_video.py|
|構成図・データフロー・ライセンス|docs/design.md、docs/third_party_licenses.md|

ROS 2、rosbag2、dora-rs、実機連携は対象外とする。現状の制約はREADMEと設計書に記載する。

## 提出前チェック（外部操作は未実施）

- [ ] 実装ブランチを確認し、必要ならmainへマージ
- [ ] publicのGitHub URLとコード一式を確認
- [ ] 1〜3分のMP4と動画内の説明を確認
- [ ] YouTubeへ公開または限定公開し、URL・タイトル・設定を確認
- [ ] 日本語原稿をPDF化し、手元で提出用識別子を設定
- [ ] 動画・PDF・コードを個人情報と秘密情報について最終確認
- [ ] OmniCampusへPDF、GitHub URL、YouTube URLを提出
