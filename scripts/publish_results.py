"""Publish the fixed confirmatory study, with explicit multiplicity and failures."""
import argparse,json,os,shutil
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/rescue-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='outputs/statistics');a=p.parse_args();root=Path(a.root)
    s=json.loads((root/'summary.json').read_text());rows=json.loads((root/'test_results.json').read_text());model=json.loads(Path('models/risk.json').read_text())
    plan=json.loads(Path('configs/statistical_study.json').read_text());policies=json.loads(Path('configs/method_policies.json').read_text())
    out=Path('docs');figs=out/'figures';figs.mkdir(exist_ok=True);n=s['risk']['n'];assert len(rows)==3*n==1800
    for src,dst in [('summary.json','benchmark_summary.json'),('test_results.json','benchmark_results.json'),('test_results.csv','benchmark_results.csv'),('environment.json','environment.json'),('tuning_results.json','policy_validation.json')]:shutil.copyfile(root/src,out/dst)
    if (root/'planning_power.json').exists():shutil.copyfile(root/'planning_power.json',out/'planning_power.json')
    shutil.copyfile('models/risk.json',out/'model_metrics.json')
    if (root/'ablations.json').exists():shutil.copyfile(root/'ablations.json',out/'ablations.json')
    names=['distance','heuristic','risk'];labels=['距離優先','ルール危険度','AI危険度'];colors=['#7c8b9b','#d6a13a','#138b93']
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    charts=[('safe_success','安全配送率（%）'),('restricted_time_180','失敗を180秒とする配送時間（秒）'),('distance','終了までの距離（m）'),('stop_time_s','停止時間（秒）'),('near_misses','ニアミス件数'),('process_cpu_s','プロセスCPU時間（秒）')]
    fig,axs=plt.subplots(3,2,figsize=(10,10),layout='constrained')
    for ax,(key,title) in zip(axs.flat,charts):
        vals=[s[m][key]['mean'] if isinstance(s[m][key],dict) else s[m][key] for m in names]
        if key=='safe_success':vals=[v/n*100 for v in vals]
        ax.bar(range(3),vals,color=colors);ax.set_xticks(range(3),labels,fontproperties=font);ax.set_title(title,fontproperties=font)
        for i,v in enumerate(vals):ax.text(i,v,f'{v:.2f}',ha='center',va='bottom')
        ax.margins(y=.2)
    fig.savefig(figs/'comparison.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5));cs=s['comparisons']
    for i,c in enumerate(cs):
        delta=c['difference']*100;lo,hi=np.array(c['stratified_paired_95ci'])*100
        ax.errorbar(delta,i,xerr=[[max(0,delta-lo)],[max(0,hi-delta)]],fmt='o',capsize=5,color='#138b93')
        ax.text(hi+.3,i,f"補正p={c['holm_adjusted_p']:.4g}",fontproperties=font,va='center')
    ax.set_yticks([0,1],['AI − 距離優先','AI − ルール危険度'],fontproperties=font);ax.axvline(0,color='gray',ls='--');ax.set_xlabel('安全配送率差（ポイント）と対応95%区間',fontproperties=font);ax.margins(x=.4,y=.5);fig.tight_layout();fig.savefig(figs/'paired_effect.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4))
    for name,values in model['calibration_validation'].items():
        bins=values['calibration_bins'];ax.plot([b['predicted'] for b in bins],[b['observed'] for b in bins],'o-',label={'raw':'未校正','isotonic':'校正後'}[name])
    ax.plot([0,1],[0,1],'k--');ax.set_xlabel('予測危険度',fontproperties=font);ax.set_ylabel('観測された危険頻度',fontproperties=font);ax.legend(prop=font);fig.tight_layout();fig.savefig(figs/'calibration.png',dpi=150);plt.close(fig)
    lines=['# 固定600組の対比較結果','',f'全{n}組・3方式・{3*n}走行。各シナリオ200組、180秒制限。失敗を含む。安全配送＝時間内成功かつ衝突・ニアミス0。','','|指標|距離優先|ルール危険度|AI危険度|','|---|---:|---:|---:|']
    for key,title in [('success','配送成功'),('safe_success','安全配送'),('collisions','衝突合計'),('near_misses','ニアミス合計'),('elapsed','終了までの平均時間s'),('restricted_time_180','失敗180秒の平均配送時間s'),('distance','平均距離m'),('stop_time_s','平均停止時間s'),('process_cpu_s','平均プロセスCPU時間s'),('runtime_s','並列実行中の平均壁時計時間s'),('replans','平均再計画')]:
        vals=[s[m][key]['mean'] if isinstance(s[m][key],dict) else s[m][key] for m in names]
        lines.append('|'+title+'|'+'|'.join(f'{v:.3f}' for v in vals)+'|')
    interpretation=[]
    for c in cs:
        label={'distance':'距離方式','heuristic':'ルール方式'}[c['baseline']];ci=[round(v*100,2) for v in c['stratified_paired_95ci']]
        statement=(f"AI対{label}：安全配送率差 {c['difference']*100:.2f}ポイント、95%区間 {ci}。AIだけ安全配送 {c['ai_wins']}組、相手だけ安全配送 {c['ai_losses']}組。正確McNemar両側p={c['exact_mcnemar_two_sided_p']:.6g}、Holm補正p={c['holm_adjusted_p']:.6g}。"
                   +('事前基準で当該比較の優位性が統計的に支持された。' if c['superiority_supported'] else ('当該比較ではAI方式の安全配送率低下が統計的に示された。' if c['holm_adjusted_p']<.05 and c['stratified_paired_95ci'][1]<0 else '事前基準では当該比較の優位性を支持できなかった。同等性の証明ではない。')))
        interpretation.append(statement)
    lines+=['',*interpretation,'','表示した95%区間は各比較の周辺区間で同時区間ではない。区間が0を含まなくても、Holm補正pが0.05以上なら事前の優位性基準を満たさない。','','95%区間は各シナリオ内の対応を維持する5,000回のブートストラップ（乱数426）。検定の2比較へHolm補正を適用。時間などの副指標は探索的な記述評価で、主指標の代わりに結論へ使わない。','','![図1：失敗を含む全走行の比較。](figures/comparison.png)','','![図2：対応差の95%区間。](figures/paired_effect.png)']
    (out/'results.md').write_text('\n'.join(lines)+'\n')
    test=model['test'];risk=policies['risk'];heur=policies['heuristic'];power=json.loads(Path('docs/planning_power.json').read_text())
    report=['# AI危険度予測による災害救援物資の自律配送ロボット','','## 1. 目的とシステム','','災害現場を模した2D環境で救援基地から避難所へ配送する。学習済み局所リスクが経路選択と配送性能へ寄与するかを、距離方式と独立調整したルール方式に対して評価する。CPU上のPython 3.12で動作し、GPU・GUI・外部APIは不要である。','','![図1：観測から行動までの構成。真の未来軌跡はラベル生成・評価専用。](figures/system.png)','','## 2. ロボット・観測・安全制御','','25×20セル、1セル1m。半径0.20m、車輪間隔0.40mの差動二輪ロボットを0.1秒刻みで積分する。最大速度0.9m/s、加速度1m/s²。32方向・最大5mの距離センサーで物体を検出し、速度は過去位置の差分から求める。初期静的地図と自己位置は既知とする。','','全方式で観測速度の2.5秒等速予測領域、同じ再計画・進捗監視と独立安全停止を共有する。3秒で0.15m進まない場合は先頭経路を一時回避し、迂回不能なら元の条件へ戻す。近接、古い指令・観測、非有限値、モデル異常では停止する。壁の余裕0.035m、移動円の余裕0.12mなどの安全閾値は緩和しない。停止中に物体が進入する衝突は防げるとは限らず、真値評価器が失敗として記録する。','','## 3. AIモデルと経路コスト','','1.5秒の局所直進で障害物表面まで0.38m未満となる場合を危険ラベルとする。入力は壁距離、通路幅、観測物体の距離・接近速度・前方位置・横距離、速度、方向cos/sin、前方地図距離の10成分。学習24シナリオ0–23、モデル選択40–45、校正60–65、各150例を分離する。RFは80木、乱数42、最小葉4、深さ8/12を検証F1で選ぶ。isotonic校正は独立した校正集合で学習し、検証Brier scoreで採否を選ぶ。','','分類テスト100–105は過去にも使用した診断集合で、未知配送テストとは区別する。',f"診断900件：ROC AUC {test['roc_auc']:.4f}、PR AUC（average precision）{test['pr_auc']:.4f}、F1 {test['f1']:.4f}、適合率 {test['precision']:.4f}、再現率 {test['recall']:.4f}、Brier score {test['brier_score']:.4f}。分類精度は配送成功確率ではない。",'','![図2：分類検証集合の信頼度曲線。](figures/calibration.png)','',f"距離方式は辺コスト1。AI方式は 1 + {risk['weight']} × max(0,p−{risk['floor']})/(1−{risk['floor']}) を使う。ルール方式は同じ観測特徴から壁近接と動的接近を計算し、独立に選んだ重み{heur['weight']}を使う。辺コストは1以上なのでマンハッタン距離は許容的である。局所リスクの加算は経路全体の衝突確率ではない。静的特徴だけをキャッシュし、新しい壁を観測したら無効化する。動的特徴は再計算する。",'', '## 4. 開発用調整と回帰確認','',f"配送検証はcrossing・clutter・closure各10シード1000–1009の30組へ拡張した。AIの重みと閾値7候補、ルール方式の重み5候補を独立に比較する。既存3環境・seed 310/311の6組で安全配送を維持することを優先し、開発集合の安全配送数、成功数、衝突数、失敗時180秒の時間で選ぶ。合計432走行を使用した。選択済みAIは開発30組中{risk['development_safe']}組、ルール方式は{heur['development_safe']}組で安全配送し、両方が回帰6組の安全配送を維持した。CPU時間は選択に使わない。",'', '従来の90組は探索的な参考結果として区別する。新しい最終テストを重みやモデルの調整に使わない。以前の少数調整に比べて合わせ込みを抑える設計だが、汎化性能の向上は最終結果で判断する。','','## 5. 統計検証の事前設計','',f"主評価項目は180秒以内の安全配送率。AI対距離方式・AI対ルール方式の2比較を事前指定し、正確McNemar両側検定へHolm補正を適用する。補正p<0.05かつ対応95%区間の下限>0の場合だけ、当該比較が統計的に支持されたとする。区間はシナリオ内の対ブートストラップ5,000回、乱数426。全方式への優位性を主張するには両比較が条件を満たす必要がある。",'', f"標本数は600組に固定した。5ポイントの効果と不一致率0.15を仮定した近似検出力は約{power['approximate_power']*100:.0f}%である。真の効果が小さければ検出力は下がり、600組でも有意差は保証されない。有意になるまで試行を追加する運用は行わない。",'', '## 6. 未使用600組の評価条件','','crossingは20000–20199、clutterは30000–30199、closureは40000–40199、各200組。シナリオ間でもシードを共有しない。動的環境400組を含む。地図・物体の位相・速度をシードで固定し、全方式へ同じ環境を適用する。方式の実行順をシードから無作為化し、4プロセスで実行した。各プロセス自身のCPU時間と、並列負荷を含む壁時計時間を区別する。失敗を除外せず、終了までの指標と失敗を180秒とする配送時間の両方を記録する。','','## 7. 結果']
    for m,label in zip(names,labels):
        r=s[m];report+=['',f"{label}：配送成功{r['success']}/{n}、安全配送{r['safe_success']}/{n}、衝突{r['collisions']}件、ニアミス{r['near_misses']}件。平均終了時間{r['elapsed']['mean']:.2f}秒、失敗180秒の平均配送時間{r['restricted_time_180']:.2f}秒、距離{r['distance']['mean']:.2f}m、停止時間{r['stop_time_s']['mean']:.3f}秒、プロセスCPU時間{r['process_cpu_s']['mean']:.3f}秒。"]
    report+=['','![図3：全1,800走行の記述指標。失敗を除外しない。](figures/comparison.png)','','## 8. 対応比較と考察','',*interpretation,'','![図4：安全配送率差と対応95%区間。検定の2比較にはHolm補正を適用する。](figures/paired_effect.png)']
    report+=['','シナリオ別の安全配送数は次のとおり。部分群は探索的な記述であり、主評価の代わりに有利な環境だけを結論へ使わない。']
    for scenario,methods in s.get('by_scenario',{}).items():
        report+=['',scenario+'：'+'、'.join(f"{label} {methods[m]['safe_success']}/{methods[m]['n']}" for m,label in zip(names,labels))+'。']
    claim=('両比較で事前基準を満たした。この固定ベンチマークではAIの安全配送率の優位性が統計的に支持された。' if s['all_baselines_superiority_supported'] else '少なくとも一方の比較が事前基準を満たさず、全方式に対するAIの統計的優位性は主張しない。')
    if all(c['difference']<0 for c in cs):claim+=' 今回はAIの安全配送率の点推定が両比較とも低く、以前90組で観察された小さな改善は新しい600組では再現されなかった。'
    report+=['',claim,'','95%区間は比較ごとの周辺区間で、2比較同時の区間ではない。Holm補正後pが0.05以上の場合は、区間が0を含まなくても事前の判定基準では統計的な優位性を主張しない。','','探索候補は有限で、ルール方式のあらゆる改良に対する優位性を意味しない。有意差があっても、5ポイント以上という実用上の改善幅や他環境への安全性を保証するものではない。推定差、区間、衝突・失敗件数を併記して判断する。時間・距離・停止時間は副次的な記述評価であり、主指標が不利な場合に別の指標へ結論を置き換えない。','','## 9. 制約と改善余地','','局所直進ラベルは旋回や到着時刻を含む経路全体をモデル化していない。等速予測の誤差、未観測物体、停止中の物体進入による失敗が残る。自己位置と物体分類は理想的で、滑り・通信遅延・実機のブレーキは未モデル化。CPU計算時間は仮想時刻へ加算しないため、実時間制御性能は主張しない。検定は固定した3環境分布を対象とし、実災害全般への汎化を保証しない。','','静的なclutterでは全方式が安全配送できる一方、動的なcrossingとclosureでAIの点推定が低かった。局所直進の分類器には経路の到着時刻・旋回・予測不確実性が直接含まれず、異なる経路や到着時間が移動物体との遭遇を増やした可能性がある。これは結果と整合する仮説で、因果関係を分離した検証は未実施である。既存の正常6環境を維持できても、動的な未知環境への安全性は保証されない。', '', '検証集合を増やし比較対象も調整することで、公平性と考察の根拠は強まる。ただしモデルを複雑にすれば必ず性能が上がるわけではない。今後は観測誤差と経路通過時刻を含むリスク予測を、別の開発集合と未使用の最終集合で検証する。安全閾値の緩和を性能向上の手段にはしない。','','## 10. デモと再現','','デモは結果に依存しない事前規則「closureの最小最終シード40000」を使う。通常方式とAI方式を同じ実測時刻で描画し、全600組の結果カードを併記する。提供OP約3秒→説明4秒→実測比較71秒→結果8秒→提供ED約3秒、総尺約89秒。両素材には音声がないため無音AACを追加する。再生倍率は表示だけで、制御周期・精度を変えない。','','学習はtrain_model.py、追加調整と最終実験はstatistical_study.py、全ログ照合はaudit_results.py、動画はbuild_submission.py、図表・原稿はpublish_results.py、PDFはgenerate_report.pyで生成する。モデルとデータのハッシュ、設定、依存、開始コミットを記録する。全試行CSV・JSONと対応比較の結果を保存し、失敗例も再現できる。']
    audit=json.loads(Path('docs/artifact_validation.json').read_text())
    report+=['',f"全ログの監査では、AIは600組中{audit['initial_paths_changed_by_selected_ai']}組で距離方式と異なる初期経路を選んだ。経路への寄与は確認できるが、性能向上とは区別する。"]
    if (figs/'trajectory.png').exists():report+=['','![図5：事前指定したclosure・seed 40000の実測走行。結果による選別を行わない。](figures/trajectory.png)']
    (out/'report_outline.md').write_text('\n'.join(report)+'\n')
