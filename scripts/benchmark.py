"""Fixed held-out, three-method paired delivery benchmark; full validated logs."""
import argparse,csv,gzip,json,hashlib
from pathlib import Path
import numpy as np
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run,config
from rescue_delivery.logger import write_log
from rescue_delivery.provenance import environment_info

def summarize(rows):
    result={}
    for method in ['distance','heuristic','risk']:
        rr=[r for r in rows if r['method']==method]
        if not rr: continue
        item={'n':len(rr),'success':sum(r['success'] for r in rr),
              'safe_success':sum(r['success'] and r['collisions']==0 and r['near_misses']==0 for r in rr),
              'collisions':sum(r['collisions'] for r in rr),'near_misses':sum(r['near_misses'] for r in rr)}
        for k in ['elapsed','distance','stop_time_s','replans','min_clearance','inference_latency_ms','planning_time_ms','runtime_s']:
            x=[r[k] for r in rr];item[k]={'mean':float(np.mean(x)),'median':float(np.median(x)),'std':float(np.std(x))}
        item['restricted_time_180']=float(np.mean([r['elapsed'] if r['success'] else 180 for r in rr]))
        result[method]=item
    if 'risk' in result and 'distance' in result:
        index={(r['scenario'],r['seed'],r['method']):r for r in rows}
        diffs=[];safe=[]
        for r in rows:
            if r['method']!='risk':continue
            b=index[r['scenario'],r['seed'],'distance']
            diffs.append((r['elapsed'] if r['success'] else 180)-(b['elapsed'] if b['success'] else 180))
            safe.append(int(r['success'] and r['near_misses']==0)-int(b['success'] and b['near_misses']==0))
        rng=np.random.default_rng(42);idx=rng.integers(0,len(diffs),(2000,len(diffs)))
        result['paired']={'risk_minus_distance_time_mean':float(np.mean(diffs)),
                          'time_bootstrap_95ci':np.quantile(np.asarray(diffs)[idx].mean(axis=1),[.025,.975]).tolist(),
                          'safe_success_difference':float(np.mean(safe)),
                          'safe_difference_95ci':np.quantile(np.asarray(safe)[idx].mean(axis=1),[.025,.975]).tolist()}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=10000);p.add_argument('--count',type=int,default=30)
    p.add_argument('--output',default='outputs/final/benchmark');p.add_argument('--model',default='models/risk.joblib')
    a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    model=load(a.model);cfg=config('configs/selected.json');rows=[]
    info=environment_info(cfg,a.model);info.update({'start':a.start,'count_per_scenario':a.count,'scenarios':['crossing','clutter','closure'],
        'timeout_s':180,'safe_definition':'success and zero collisions and zero near-miss events','selection':'all fixed episodes; no post-test tuning'})
    (out/'environment.json').write_text(json.dumps(info,indent=2))
    for scenario in info['scenarios']:
        for seed in range(a.start,a.start+a.count):
            for method in ['distance','heuristic','risk']:
                r=run(seed,model,scenario=scenario,difficulty='hard',method=method,settings=cfg)
                write_log(out/'logs'/f'{scenario}-{seed}-{method}.jsonl.gz',r.logs)
                rows.append(r.metrics());print(json.dumps(rows[-1]),flush=True)
                (out/'results.json').write_text(json.dumps(rows,indent=2))
    with (out/'results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summarize(rows),indent=2))
