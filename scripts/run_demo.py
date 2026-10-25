import argparse
import json
from pathlib import Path
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run
from rescue_delivery.planner import astar
from rescue_delivery.world import World
from rescue_delivery.visualization import render

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--model',default='models/risk.pkl')
    p.add_argument('--seed',type=int,default=200); p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--fps',type=int,default=12); p.add_argument('--output',default='outputs/preview.mp4')
    p.add_argument('--method',choices=['risk','distance'],default='risk'); a=p.parse_args()
    if a.seconds<=0 or a.fps<=0: p.error('seconds and fps must be positive')
    model=load(a.model); r=run(a.seed,model if a.method=='risk' else None,record=True)
    print(json.dumps(r.metrics()),flush=True)
    w=World(a.seed); baseline=astar(w,w.start,w.goal)
    print(json.dumps({'initial_path_changed_by_ai': r.initial_path != baseline, 'baseline_cells':len(baseline), 'selected_cells':len(r.initial_path)}),flush=True)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.with_suffix('.json').write_text(json.dumps({'metrics':r.metrics(),'initial_path':r.initial_path,'frames':r.frames}))
    render(r,model,str(out),a.seconds,a.fps)
    if not r.success: raise SystemExit('Delivery failed; video saved for diagnosis')
