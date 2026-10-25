# 使用OSSとライセンス

今回のインストール済み配布メタデータと固定依存一覧を照合した記録。ライセンスの正式本文・同梱コンポーネントの権利は各配布物のLICENSE/COPYINGを参照する。ここでは依存を利用し、そのソースやバイナリを本リポジトリへ再配布していない。

|ライブラリ|バージョン|ライセンス|配布元|
|---|---|---|---|
|cloudpickle|3.1.2|BSD-3-Clause|https://pypi.org/project/cloudpickle/3.1.2/|
|contourpy|1.4.0|BSD-3-Clause|https://pypi.org/project/contourpy/1.4.0/|
|cycler|0.12.1|BSD-3-Clause|https://pypi.org/project/cycler/0.12.1/|
|fonttools|4.67.0|MIT|https://pypi.org/project/fonttools/4.67.0/|
|iniconfig|2.3.1|MIT|https://pypi.org/project/iniconfig/2.3.1/|
|joblib|1.6.0|BSD-3-Clause|https://pypi.org/project/joblib/1.6.0/|
|kiwisolver|1.5.1|BSD-3-Clause|https://pypi.org/project/kiwisolver/1.5.1/|
|matplotlib|3.10.7|Matplotlib license (PSF-based)|https://pypi.org/project/matplotlib/3.10.7/|
|numpy|2.2.6|BSD-3-Clause|https://pypi.org/project/numpy/2.2.6/|
|packaging|26.3|Apache-2.0 OR BSD-2-Clause|https://pypi.org/project/packaging/26.3/|
|pillow|13.0.0|MIT-CMU|https://pypi.org/project/pillow/13.0.0/|
|pluggy|1.7.0|MIT|https://pypi.org/project/pluggy/1.7.0/|
|Pygments|2.21.0|BSD-2-Clause|https://pypi.org/project/Pygments/2.21.0/|
|pyparsing|3.3.3|MIT|https://pypi.org/project/pyparsing/3.3.3/|
|pytest|8.4.2|MIT|https://pypi.org/project/pytest/8.4.2/|
|python-dateutil|3.0.0|Apache-2.0 OR BSD-3-Clause|https://pypi.org/project/python-dateutil/3.0.0/|
|scikit-learn|1.7.2|BSD-3-Clause|https://pypi.org/project/scikit-learn/1.7.2/|
|scipy|1.18.1|BSD-3-Clause|https://pypi.org/project/scipy/1.18.1/|
|six|1.17.0|MIT|https://pypi.org/project/six/1.17.0/|
|threadpoolctl|3.7.0|BSD-3-Clause|https://pypi.org/project/threadpoolctl/3.7.0/|
|tzdata|2026.5|Apache-2.0 (code); data public domain|https://pypi.org/project/tzdata/2026.5/|

その他の実行依存：Python 3.12.14（PSF-2.0）、FFmpeg 7.1.5（今回のビルドは--enable-gpl、GPL有効）、libx264（GPL-2.0-or-later）、Noto Sans CJK（SIL OFL-1.1）。
FFmpegの適用ライセンスはビルド構成に依存するため、再配布する場合は `ffmpeg -L` と依存コーデックの条件を確認する。NumPy/SciPy等のwheelにはBLAS等の追加ライセンスが同梱される場合がある。
フォント・ライブラリ本体・講義の非公開資料・添付PDFはGitへコピーしない。原著作物のライセンス通知は各インストール済み配布物に保持される。
地図・描画・学習データ生成・ロボット制御・レポート本文は本プロジェクトの独自実装。サンプルや講義図表の転載はない。
