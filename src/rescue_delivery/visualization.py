from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/rescue-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle
import numpy as np
from .sensors import features, ObservedMap
from .planner import probability
from .world import World


def render(result, model, output, seconds=12, fps=10, comparison=None):
    results=[result] if comparison is None else [comparison,result]
    if any(not r.frames for r in results): raise ValueError('No recorded simulation frames')
    if seconds<=0 or fps<1: raise ValueError('positive duration/fps required')
    font_path=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if not font_path.exists(): raise RuntimeError('Japanese font required: fonts-noto-cjk')
    font=FontProperties(fname=str(font_path))
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    worlds=[World(r.seed,r.scenario,r.difficulty) for r in results]
    heatmaps=[]
    for r,w in zip(results,worlds):
        observed=ObservedMap(w.initial_grid); observed.update(r.logs[0]['sensor_observations'])
        heat=np.full(w.grid.shape,np.nan)
        cells=[(x,y) for y in range(w.height) for x in range(w.width) if w.free((x,y))]
        if model is not None:
            values=probability(model,[features(observed,p,0.,.9) for p in cells])
            for (x,y),v in zip(cells,values): heat[y,x]=v
        heatmaps.append(heat)
    fig,axes=plt.subplots(1,len(results),figsize=(12.8,7.2),dpi=100,squeeze=False)
    fig.subplots_adjust(left=.055,right=.98,bottom=.23,top=.85,wspace=.10)
    writer=FFMpegWriter(fps=fps,codec='libx264',extra_args=['-pix_fmt','yuv420p','-crf','23'])
    total=max(2,round(seconds*fps)); max_time=max(r.elapsed for r in results)
    preview=seconds<60
    hold=min(2.,seconds/5)
    playback_time=min(max_time,2*(seconds-hold)) if preview else max_time
    speed=playback_time/(seconds-hold)
    # Submission videos: retain the entire run and never exceed PDF's 2x allowance.
    if not preview and speed>2.+1e-9:
        raise ValueError('full video would exceed 2x; increase duration (max 180s for submission)')
    if not preview and seconds>180: raise ValueError('submission video must be <=180 seconds')
    with writer.saving(fig,output,100):
        for index in range(total):
            sim_t=min(playback_time,index/fps*speed)
            fig.suptitle('AI危険度予測による救援配送 — 2Dロボットシミュレーション\n'+
                         f'{"動作プレビュー（冒頭抜粋・提出用ではありません）" if preview else "通常A*とAI方式の実測比較"} | 再生倍率 {speed:.2f}倍',
                         fontproperties=font,fontsize=13)
            footer=[]
            for ax,r,w,heat in zip(axes[0],results,worlds,heatmaps):
                idx=min(len(r.frames)-1,int(np.searchsorted([f['t'] for f in r.frames],sim_t,side='right')))
                frame=r.frames[idx]; ax.clear()
                grid=w.initial_grid.copy()
                if frame['closure']: grid[w.closure_cell[1],w.closure_cell[0]]=True
                ax.imshow(heat,origin='lower',vmin=0,vmax=1,cmap='YlOrRd',alpha=.6)
                ax.imshow(np.ma.masked_where(~grid,grid),origin='lower',cmap='gray_r',vmin=0,vmax=1)
                ax.scatter(*w.start,marker='s',c='green',s=45)
                ax.scatter(*w.goal,marker='*',c='blue',s=90)
                for p in frame['movers']: ax.add_patch(Circle(p,.32,color='purple'))
                trail=np.array([f['pose'][:2] for f in r.frames[:idx+1]])
                ax.plot(trail[:,0],trail[:,1],color='navy',linewidth=1)
                if frame['path']:
                    path=np.array(frame['path']); ax.plot(path[:,0],path[:,1],'c--',linewidth=1)
                x,y,theta=frame['pose']
                ax.add_patch(Circle((x,y),.20,color='deepskyblue',ec='black'))
                ax.arrow(x,y,.6*np.cos(theta),.6*np.sin(theta),width=.06,color='blue')
                # Event display persists briefly using actual log timestamps.
                recent=r.frames[max(0,idx-10):idx+1]
                event='道路封鎖あり ' if frame['closure'] else ''
                if any(f['replan'] for f in recent): event+='再計画 '
                if frame['stop']: event+='安全停止 '
                status={'success':'配送成功','collision':'衝突で終了','timeout':'時間切れ',
                        'unreachable':'到達不能','model_unavailable':'AI異常・停止'}.get(frame['outcome'],'配送中')
                title='通常A*' if r.method=='distance' else 'AI危険度考慮A*'
                ax.set_title(f'{title} | {frame["t"]:.1f}秒 | {status}\n{event or "走行中"}',fontproperties=font,fontsize=11)
                ax.set_xlim(-.5,24.5); ax.set_ylim(-.5,19.5); ax.set_aspect('equal')
                ax.tick_params(labelsize=8)
                ax.set_xlabel(f'現在の推定危険度: {frame["risk"]:.2f}' if r.method=='risk' else 'AI不使用（共通センサー・安全層）',fontproperties=font,fontsize=10)
                footer.append(f'{title}: 全走行距離 {r.distance:.1f}m / 衝突 {r.collisions} / 再計画 {r.replans} / 停止 {r.stops}')
            # Use figure text replacement instead of accumulating artists.
            for text in list(fig.texts):
                if text is not fig._suptitle: text.remove()
            fig.text(.5,.12,'\n'.join(footer),ha='center',fontproperties=font,fontsize=10)
            fig.text(.5,.045,'緑四角:基地 / 青星:避難所 / 紫:移動障害物 / 水色破線:計画経路\n'
                     '赤色:初期観測・東向き・0.9m/sのAI推定値（未校正）。数値は保存ログの実測。',
                     ha='center',fontproperties=font,fontsize=9)
            writer.grab_frame()
    plt.close(fig)
