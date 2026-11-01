"""Build OP + explanatory cards + predeclared logged episode + ED, without rerunning physics."""
import json,subprocess
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from rescue_delivery.replay import replay
from rescue_delivery.risk_model import load
from rescue_delivery.visualization import render
from compose_video import compose

if __name__=='__main__':
    out=Path('outputs/final');out.mkdir(parents=True,exist_ok=True)
    logdir=out/'benchmark/logs';model=load('models/risk.joblib')
    # Never select by performance: closure and smallest held-out seed were fixed in advance.
    ai=replay(logdir/'closure-10000-risk.jsonl.gz');base=replay(logdir/'closure-10000-distance.jsonl.gz')
    render(ai,model,str(out/'body.mp4'),75,8,comparison=base)
    Path('docs/figures').mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','70','-i',str(out/'body.mp4'),'-frames:v','1','docs/figures/trajectory.png'],check=True)
    summary=json.loads((out/'benchmark/summary.json').read_text())
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    cards=[('intro','災害救援物資の自律配送 — 2Dシミュレーション',
            '観測から局所衝突リスクを予測し、A*の経路コストへ反映\n独立安全停止・道路封鎖の再計画を共通条件で比較'),
           ('summary','未知90組・3方式の実測比較',
            '\n'.join(f"{label}：配送 {summary[m]['success']}/90、安全配送 {summary[m]['safe_success']}/90" for m,label in [('distance','距離優先'),('heuristic','ルール危険度'),('risk','AI危険度')])+'\n安全配送＝成功かつ衝突・ニアミス0。失敗も全件集計。')]
    for name,title,text in cards:
        fig=plt.figure(figsize=(12.8,7.2),dpi=100,facecolor='#eef5f7')
        fig.text(.07,.72,title,fontproperties=font,fontsize=26,color='#14364a')
        fig.text(.07,.40,text,fontproperties=font,fontsize=20,linespacing=1.8,color='#14364a')
        fig.savefig(out/f'{name}.png');plt.close(fig)
        subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(out/f'{name}.png'),'-t','4','-r','30','-c:v','libx264','-pix_fmt','yuv420p',str(out/f'{name}.mp4')],check=True)
    compose(out/'intro.mp4',out/'body.mp4',out/'summary.mp4',out/'content.mp4')
    report=compose('assets/opening.mp4',out/'content.mp4','assets/ending.mp4','submission/final_demo.mp4')
    report['demo_selection']='closure, seed 10000: smallest fixed final seed; no outcome selection'
    report['original_names']={'opening':'PAI応用1_最終課題_OP.mp4','ending':'PAI応用1_最終課題_ED.mp4'}
    report['intro_s']=4;report['simulation_video_s']=75;report['summary_s']=4
    import hashlib
    report['source_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['assets/opening.mp4','assets/ending.mp4']}
    Path('docs/video_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
