import argparse
import json
from pathlib import Path
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run, config
from rescue_delivery.logger import write_log
from rescue_delivery.planner import astar
from rescue_delivery.sensors import ObservedMap
from rescue_delivery.world import World
from rescue_delivery.visualization import render
from rescue_delivery.provenance import environment_info

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--model',default='models/risk-v2.joblib')
    p.add_argument('--seed',type=int,default=200); p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--fps',type=int,default=10); p.add_argument('--output',default='outputs/v2/preview.mp4')
    p.add_argument('--method',choices=['risk','distance'],default='risk')
    p.add_argument('--scenario',choices=['basic','shortcut','dynamic'],default='dynamic')
    p.add_argument('--difficulty',choices=['easy','normal','hard'],default='normal')
    p.add_argument('--config',default=None); p.add_argument('--compare',action='store_true'); a=p.parse_args()
    if a.seconds<=0 or a.fps<=0: p.error('seconds and fps must be positive')
    model=load(a.model) if a.method=='risk' else None
    cfg=config(a.config); r=run(a.seed,model,record=True,scenario=a.scenario,difficulty=a.difficulty,method=a.method,settings=cfg)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    write_log(out.with_suffix('.jsonl'),r.logs)
    w=World(a.seed,a.scenario,a.difficulty); observed=ObservedMap(w.initial_grid)
    observed.update(r.logs[0]['sensor_observations'])
    baseline=astar(observed,w.start,w.goal)
    evidence={'metrics':r.metrics(),'initial_path_changed_by_ai':r.initial_path!=baseline,
              'baseline_cells':len(baseline),'selected_cells':len(r.initial_path),
              'environment':environment_info(cfg,a.model if model is not None else None)}
    out.with_suffix('.json').write_text(json.dumps(evidence,indent=2)+'\n'); print(json.dumps(evidence),flush=True)
    baseline_result=None
    if a.compare:
        baseline_result=run(a.seed,record=True,scenario=a.scenario,difficulty=a.difficulty,settings=cfg)
        write_log(out.with_name(out.stem+'-baseline.jsonl'),baseline_result.logs)
    render(r,model,str(out),a.seconds,a.fps,comparison=baseline_result)
    if not r.success: raise SystemExit('Delivery failed; video saved for diagnosis')
