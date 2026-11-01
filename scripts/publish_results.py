"""Generate all publication figures/text directly from frozen benchmark results."""
import json,shutil
from pathlib import Path
import numpy as np
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/rescue-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

if __name__=='__main__':
    src=Path('outputs/final/benchmark');out=Path('docs');figs=out/'figures';figs.mkdir(exist_ok=True)
    summary=json.loads((src/'summary.json').read_text());model=json.loads(Path('models/risk.json').read_text())
    names=['distance','heuristic','risk'];labels=['距離優先A*','ルール危険度A*','AI危険度A*']
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    for source,dest in [('summary.json','benchmark_summary.json'),('results.csv','benchmark_results.csv'),('results.json','benchmark_results.json'),('environment.json','environment.json')]:shutil.copyfile(src/source,out/dest)
    shutil.copyfile('models/risk.json',out/'model_metrics.json')
    shutil.copyfile('outputs/final/ablations.json',out/'ablations.json')
    if Path('outputs/final/baseline/results.json').exists():shutil.copyfile('outputs/final/baseline/results.json',out/'baseline_results.json')
    charts=[('safe_success','安全配送成功数'),('elapsed','配送時間（終了まで・秒）'),('distance','走行距離（m）'),('stop_time_s','停止時間（秒）'),('near_misses','ニアミス合計'),('runtime_s','CPU実行時間（秒）')]
    fig,axs=plt.subplots(3,2,figsize=(10,10),layout='constrained')
    for ax,(key,title) in zip(axs.flat,charts):
        vals=[summary[k][key] if not isinstance(summary[k][key],dict) else summary[k][key]['mean'] for k in names]
        ax.bar(labels,vals,color=['#7c8b9b','#d6a13a','#138b93'])
        ax.set_title(title,fontproperties=font);ax.set_xticks(range(3),labels,fontproperties=font)
        for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom')
        ax.margins(y=.2)
    fig.savefig(figs/'comparison.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));
    for name,vals in model['calibration_validation'].items():
        bins=vals['calibration_bins'];ax.plot([b['predicted'] for b in bins],[b['observed'] for b in bins],'o-',label={'raw':'未校正','isotonic':'校正後'}[name])
    ax.plot([0,1],[0,1],'k--');ax.set_xlabel('予測危険度',fontproperties=font);ax.set_ylabel('観測された危険頻度',fontproperties=font);ax.legend(prop=font);fig.tight_layout();fig.savefig(figs/'calibration.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,2.4));ax.axis('off')
    boxes=['距離センサー\n過去の検出差分','観測地図\n特徴計算・キャッシュ','Random Forest\n確率校正','A*経路計画\n進捗監視','独立安全ゲート\n差動二輪運動']
    for i,text in enumerate(boxes):
        x=i*.205;ax.text(x+.08,.5,text,ha='center',va='center',fontproperties=font,fontsize=11,bbox={'boxstyle':'round,pad=.5','fc':'#e8f3f5','ec':'#217080'})
        if i<4:ax.annotate('',xy=(x+.195,.5),xytext=(x+.165,.5),arrowprops={'arrowstyle':'->'})
    ax.set_xlim(-.04,1.04);fig.savefig(figs/'system.png',dpi=150,bbox_inches='tight');plt.close(fig)
    lines=['# 未知環境の対比較結果','','crossing・clutter・closure各30組、seed 10000–10029、hard、180秒制限。3方式×90組=270走行。安全配送は成功かつ衝突・ニアミス0。失敗例を除外しない。','','|指標|距離優先|ルール危険度|AI危険度|','|---|---:|---:|---:|']
    for key,title in [('success','成功数 / 90'),('safe_success','安全配送数 / 90'),('collisions','衝突合計'),('near_misses','ニアミス合計'),('elapsed','終了までの平均時間s'),('distance','平均距離m'),('stop_time_s','平均停止時間s'),('replans','平均再計画'),('min_clearance','平均最小余裕m'),('inference_latency_ms','平均推論合計ms'),('planning_time_ms','平均計画合計ms'),('runtime_s','平均CPU実行時間s')]:
        vals=[summary[n][key] if not isinstance(summary[n][key],dict) else summary[n][key]['mean'] for n in names]
        lines.append('|'+title+'|'+'|'.join(f'{v:.3f}' for v in vals)+'|')
    paired=summary['paired'];lines+=['',f"AI−距離優先の制限時間付き配送時間差：{paired['risk_minus_distance_time_mean']:.3f}秒、対ブートストラップ95%区間 {[round(x,3) for x in paired['time_bootstrap_95ci']]}。失敗は180秒とする。安全配送率差：{paired['safe_success_difference']*100:.2f}ポイント、95%区間 {[round(x*100,2) for x in paired['safe_difference_95ci']]}ポイント。区間は固定ベンチマーク内の標本不確実性で、別分布への保証ではない。",'', '![図1：全270走行を含む比較。時間と距離は失敗時の終了までを含む。](figures/comparison.png)','','全試行はbenchmark_results.csv / benchmark_results.json。gzip走行ログはoutputs/final/benchmark/logs。分類テストの性能と配送性能は区別する。ルール方式がAI方式を上回る場合もそのまま記載する。']
    (out/'results.md').write_text('\n'.join(lines)+'\n')
    table='\n'.join(lines[2:18]);test=model['test'];p=model['policy']
    report=['# AI危険度予測による災害救援物資の自律配送ロボット','','## 1. 目的とシステム','','災害現場を模した2D環境で、救援基地から避難所へ物資を配送する。AIが推定する局所衝突リスクを経路選択へ反映し、距離優先・ルール危険度・AI危険度の3方式を公平に比較する。CPU上のPython 3.12で動作し、GPU、外部API、ROS 2は使用しない。','','![図1：観測から行動までの構成。真の未来軌跡は学習ラベルと評価だけに使用。](figures/system.png)','','## 2. ロボットと環境','','25×20セル、1セル1m、基地(2,10)、避難所(22,10)。半径0.20m、車輪間隔0.40mの差動二輪ロボットを0.1秒刻みで積分する。最大速度0.9m/s、加速度1m/s²。全周32方向・最大5mの距離センサーで観測し、移動物体の速度は過去の検出差分から求める。静的初期地図と自己位置は既知とする。','','既存のbasic・shortcut・dynamicを維持し、交差する移動物体、全域の瓦礫、未知の壁位置・通路位置と道路封鎖を含むcrossing・clutter・closureを追加する。障害物の軌跡は方式に依存せず固定する。','','## 3. 学習と確率校正','','学習24シナリオ0–23、モデル選択6シナリオ40–45、確率校正6シナリオ60–65を分離し、各150候補を用いる。候補位置から1.5秒直進する局所走行を模擬し、障害物表面まで0.38m未満となる場合を危険とする。入力は壁距離、通路幅、観測物体との距離・接近速度・前方位置・横距離、速度、方向cos/sin、前方地図距離の10成分。','','Random Forestは80木、乱数42、最小葉4、深さ8/12を検証F1で選択する。isotonic回帰は独立した校正データで学習し、検証Brier scoreで採否を決める。分類テスト100–105は過去にも評価済みの診断集合であり、新しい未知配送環境とは区別する。', '',f"診断テスト900件：ROC AUC {test['roc_auc']:.4f}、PR AUC（average precision）{test['pr_auc']:.4f}、F1 {test['f1']:.4f}、適合率 {test['precision']:.4f}、再現率 {test['recall']:.4f}、Brier score {test['brier_score']:.4f}。分類精度を配送成功確率として解釈しない。",'','![図2：検証集合の信頼度曲線。対角線は予測確率と観測頻度が一致する場合。](figures/calibration.png)','','## 4. 経路選択と自律復帰','',f"距離方式の辺コストは1。ルール方式は同じ特徴量から壁近接と動的接近を評価する。AI方式は 1 + {p['risk_weight']} × max(0, p−{p['risk_floor']}) / (1−{p['risk_floor']}) を使用する。危険確率の低い領域で過剰な迂回コストを加えない。重みと閾値は配送検証seed 700・701の6環境で固定し、最終評価後は調整しない。辺コストは1以上で、マンハッタン距離は許容的である。これは局所リスクの加算コストであり、経路全体の衝突確率ではない。",'', '観測速度による2.5秒等速予測領域を全方式で一時通行禁止とする。新しい壁や接近を検知したら再計画し、3秒間に0.15m進まなければ先頭経路を一時回避する。迂回不能なら元の条件へ戻す。静的特徴だけをキャッシュし、新しい壁を観測したら無効化する。動的特徴は再計算する。小さな推論はCPUの1スレッドで実行する。','','## 5. 独立した安全制御','','近接、次の移動区間の静的・動的障害物、古い観測・指令、非有限値、モデル異常を監視し、AIに依存せず停止する。従来の閾値は緩和しない。停止中のロボットへ物体が進入する場合は衝突を防げず、評価器は接触を検出して失敗終了する。安全停止は理想即時停止であり実機のブレーキを保証しない。','','## 6. 未知配送ベンチマーク','','crossing・clutter・closure各30組、seed 10000–10029、hard、180秒制限を事前固定した。90組のうち60組は動的環境。全3方式で同じ地図・物体・センサー・安全制御を使用する。安全配送は時間内成功かつ衝突・ニアミス0と定義する。失敗を除外した時間平均は使わず、失敗時の終了までの値と、失敗を180秒として扱う制限時間付き指標を記録する。']
    for name,label in zip(names,labels):
        r=summary[name];report+=['',f"{label}：配送成功 {r['success']}/90、安全配送 {r['safe_success']}/90、衝突 {r['collisions']}、ニアミス {r['near_misses']}。平均終了時間 {r['elapsed']['mean']:.2f}秒、距離 {r['distance']['mean']:.2f}m、停止時間 {r['stop_time_s']['mean']:.2f}秒、CPU実行時間 {r['runtime_s']['mean']:.3f}秒。"]
    report+=['','![図3：同一90組における3方式比較。失敗走行を含む。](figures/comparison.png)','','## 7. 結果の解釈','',f"AI−距離優先の制限時間付き配送時間差は{paired['risk_minus_distance_time_mean']:.3f}秒、95%区間は{[round(x,3) for x in paired['time_bootstrap_95ci']]}。安全配送率差は{paired['safe_success_difference']*100:.2f}ポイント、95%区間は{[round(x*100,2) for x in paired['safe_difference_95ci']]}ポイント。", '', 'AIが距離方式を上回る項目があっても、ルール方式との比較も必要である。成功率の低下や未達目標を隠さず、図と全試行の数値で判断する。移動物体の進入による失敗は、局所直進ラベルと等速予測の限界を示す。単にAIを使うだけでは配送性能は保証されない。','','## 8. 要素別評価と制約','','独立した開発seed 800・801で、危険度重み0、未校正、低リスク域抑制なし、選択済み方式を比較する。全試行はablations.jsonに記録する。速度制御・安全層・進捗監視は全方式で共通であり、その改善をAI単独の効果とは主張しない。速度調整・再計画最適化の個別アブレーションは実施していない。','','推論実時間は測定するがシミュレーション時刻へ遅延として加えていないため、実時間制御性能は主張しない。合成データ、理想的な分類・自己位置、有限の地図分布、未モデル化の滑りや通信遅延が制約である。95%区間は固定集合内の対ブートストラップで、他環境への安全保証ではない。','','## 9. 動画と再現方法','','デモは事前規則「closureの最小最終評価seed 10000」に従って選び、結果を見て選別しない。実測走行を左右同時刻で比較し、危険度、再計画、道路封鎖、配送結果を表示する。OP・EDは提供素材を保持する。素材には音声がないため完成MP4には無音AACを付ける。再生倍率は表示のみで、制御精度を変更しない。','','学習はscripts/train_improved.py、配送評価はscripts/benchmark.py、図表・原稿はscripts/publish_results.py、動画はscripts/build_submission.py、PDFはscripts/generate_report.pyで生成する。設定、データ・モデルハッシュ、Gitコミット、依存は環境記録に保存する。','','## 10. 結論','','局所走行に基づく危険度学習、独立安全層、進捗監視を備えた配送シミュレーションを実装した。AIによる効果は、固定した未知環境で距離方式とルール方式の両方と比較して評価する。未達の指標や失敗事例も含む実測値が結論の範囲である。']
    d,a=summary['distance'],summary['risk']
    conclusion=(f"安全配送は距離優先{d['safe_success']}/90、ルール{summary['heuristic']['safe_success']}/90、AI{a['safe_success']}/90。"
        f"AIの安全配送率差は{paired['safe_success_difference']*100:.2f}ポイントだが95%区間は0を含む。5ポイント改善目標は未達。"
        f"失敗を180秒とする平均は距離方式{d['restricted_time_180']:.2f}秒、AI{a['restricted_time_180']:.2f}秒で、5%短縮目標も未達。"
        f"ニアミスは{d['near_misses']}件から{a['near_misses']}件、停止時間は平均{d['stop_time_s']['mean']:.3f}秒から{a['stop_time_s']['mean']:.3f}秒へ減った。"
        "これらは観測値の改善であり、一般的な優位性や安全保証を示さない。ルール方式は配送成功数と衝突数でAIを上回る。")
    report+=['','## 11. 結論の範囲','',conclusion]
    rows=json.loads(Path('outputs/final/ablations.json').read_text())
    report+=['','## 12. 要素別の実測値（独立開発集合）']
    for variant in ['selected','weight_zero','uncalibrated','floor_zero']:
        rr=[r for r in rows if r['variant']==variant]
        report+=['',f"{variant}：{len(rr)}走行、成功{sum(r['success'] for r in rr)}、衝突{sum(r['collisions'] for r in rr)}、ニアミス{sum(r['near_misses'] for r in rr)}、平均終了時間{np.mean([r['elapsed'] for r in rr]):.2f}秒。"]
    report+=['','条件ごとの結果だけから単一要素の普遍的優位性を判断しない。最終配送評価はこの比較に使っていない。ルール方式の重みはAIと同じ2で、独立した最適化は実施していない。']
    baseline=json.loads(Path('docs/baseline_comparison.json').read_text()) if Path('docs/baseline_comparison.json').exists() else None
    if baseline:
        b,a=baseline['before']['risk'],baseline['after']['risk']
        report+=['','## 13. 既存環境の回帰比較','',f"変更前コミット{baseline['baseline_commit'][:7]}と同じ6走行のAI比較では、配送成功は両方6/6、ニアミスは{b['near_misses']}件から{a['near_misses']}件、平均配送時間は{b['mean_elapsed']:.2f}秒から{a['mean_elapsed']:.2f}秒、CPU実行時間は{b['mean_runtime']:.2f}秒から{a['mean_runtime']:.2f}秒となった。これは既存分布の少数回帰確認であり、未知90組の結果と混同しない。CPU時間は同時実行負荷に依存する。"]
    scores=model['calibration_validation']
    report+=['',f"確率校正の検証Brier score：未校正{scores['raw']['brier_score']:.4f}、校正後{scores['isotonic']['brier_score']:.4f}。校正を分類F1や配送成功率の向上と同一視しない。"]
    audit=json.loads(Path('docs/artifact_validation.json').read_text()) if Path('docs/artifact_validation.json').exists() else {}
    if 'initial_paths_changed_by_selected_ai' in audit:report+=['',f"選択済みAIモデルは最終90組のうち{audit['initial_paths_changed_by_selected_ai']}組で距離方式と異なる初期経路を選んだ。これはログで確認した経路への寄与であり、安全性向上を意味するものではない。"]
    if (figs/'trajectory.png').exists():report+=['','![図4：事前指定したclosure・seed 10000の実測走行。](figures/trajectory.png)']
    (out/'report_outline.md').write_text('\n'.join(report)+'\n')
    (out/'results.md').write_text((out/'results.md').read_text()+'\n'+conclusion+'\n')
