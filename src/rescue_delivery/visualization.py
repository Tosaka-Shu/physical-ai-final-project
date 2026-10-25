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
from .sensors import features
from .world import World


def render(result, model, output, seconds=12, fps=12):
    if not result.frames: raise ValueError('No recorded simulation frames')
    world=World(result.seed)
    font_path=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if not font_path.exists():
        raise RuntimeError('Japanese font required: install fonts-noto-cjk')
    font=FontProperties(fname=str(font_path))
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    heat=np.full(world.grid.shape,np.nan)
    cells=[(x,y) for y in range(world.height) for x in range(world.width) if world.free((x,y))]
    values=model.predict_proba([features(world,p,0.,.9,0.) for p in cells])[:,1]
    for (x,y),v in zip(cells,values): heat[y,x]=v
    fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=100)
    writer=FFMpegWriter(fps=fps,codec='libx264',extra_args=['-pix_fmt','yuv420p','-crf','23'])
    total=max(2,round(seconds*fps))
    # Every rendered position comes from the recorded run; no invented motion.
    indices=np.rint(np.linspace(0,len(result.frames)-1,total)).astype(int)
    speed=result.elapsed/seconds
    with writer.saving(fig,output,100):
        for idx in indices:
            frame=result.frames[idx]; ax.clear()
            ax.imshow(heat,origin='lower',vmin=0,vmax=1,cmap='YlOrRd',alpha=.65)
            walls=np.ma.masked_where(~world.grid,world.grid)
            ax.imshow(walls,origin='lower',cmap='gray_r',vmin=0,vmax=1)
            ax.scatter(*world.start,marker='s',c='green',s=90,label='基地')
            ax.scatter(*world.goal,marker='*',c='blue',s=140,label='避難所')
            for p in frame['movers']: ax.add_patch(Circle(p,.32,color='purple'))
            trail=np.array([f['pose'][:2] for f in result.frames[:idx+1]])
            ax.plot(trail[:,0],trail[:,1],color='navy',linewidth=1.5)
            if frame['path']:
                p=np.array(frame['path']); ax.plot(p[:,0],p[:,1],'c--',label='計画経路')
            x,y,theta=frame['pose']
            ax.add_patch(Circle((x,y),.2,color='deepskyblue',ec='black'))
            ax.arrow(x,y,.6*np.cos(theta),.6*np.sin(theta),width=.07,color='blue')
            status='配送完了' if frame['success'] else ('経路再計画' if frame['replan'] else '救援物資を配送中')
            ax.set_title(f'AI自律配送ロボット — シミュレーション\n{status} | {frame["t"]:.1f}秒 | 再生倍率 {speed:.2f}倍',fontproperties=font)
            ax.set_xlim(-.5,24.5); ax.set_ylim(-.5,19.5); ax.set_aspect('equal')
            ax.legend(prop=font,loc='upper left')
            ax.set_xlabel('赤: AI危険度（初期時刻・東向き・速度0.9m/s） 紫: 移動障害物\n'
                          f'方式: {result.method} / 衝突 {result.collisions} / ニアミス {result.near_misses} / 距離 {result.distance:.1f}m',fontproperties=font)
            fig.tight_layout(); writer.grab_frame()
    plt.close(fig)
