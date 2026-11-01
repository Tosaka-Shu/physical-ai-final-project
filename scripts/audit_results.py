"""Recompute every confirmatory episode's metrics from validated compressed logs."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from rescue_delivery.logger import read_log

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='outputs/statistics');a=p.parse_args();root=Path(a.root)
    results=json.loads((root/'test_results.json').read_text());plan=json.loads(Path('configs/statistical_study.json').read_text())
    n=plan['fixed_sample_size'];assert len(results)==3*n
    initial={};observations={};cases={}
    policies=json.loads(Path('configs/method_policies.json').read_text())
    expected={(scenario,seed) for scenario,start in plan['test_seed_starts'].items() for seed in range(start,start+plan['episodes_per_scenario'])}
    for i,r in enumerate(results):
        key=(r['scenario'],r['seed'])
        assert key in expected and r['difficulty']=='hard'
        policy=policies.get(r['method'],{'weight':0,'floor':0})
        assert r['weight']==policy['weight'] and r['floor']==policy['floor']
        rows=read_log(root/'test/logs/frozen'/f"{r['scenario']}-{r['seed']}-{r['method']}.jsonl.gz")
        assert (key,r['method']) not in initial
        initial[key,r['method']]=rows[0]['planned_path'];cases.setdefault(key,set()).add(r['method'])
        digest=hashlib.sha256(json.dumps(rows[0]['sensor_observations'],sort_keys=True).encode()).hexdigest()
        assert key not in observations or observations[key]==digest,'unfair initial observation'
        observations[key]=digest
        stops=[x['safety_stop_event']['occurred'] for x in rows]
        measured={'success':rows[-1]['delivery_result']=='success','elapsed':rows[-1]['simulation_time']+rows[-1]['dt'],
                  'distance':sum(float(np.linalg.norm(np.array(x['next_pose'][:2])-x['robot_pose'][:2])) for x in rows),
                  'collisions':sum(x['collision'] for x in rows),
                  'near_misses':sum(x['near_miss'] and (j==0 or not rows[j-1]['near_miss']) for j,x in enumerate(rows)),
                  'stops':sum(x and (j==0 or not stops[j-1]) for j,x in enumerate(stops)),
                  'stop_time_s':sum(x['dt'] for x in rows if x['safety_stop_event']['occurred']),
                  'replans':sum(x['replanning_event']['occurred'] for x in rows),
                  'min_clearance':min(x['evaluation']['clearance_m'] for x in rows)}
        measured['inference_latency_ms']=sum(x['inference_latency_ms'] for x in rows)
        measured['safe_success']=measured['success'] and measured['collisions']==0 and measured['near_misses']==0
        for name,value in measured.items():assert abs(float(value)-float(r[name]))<1e-8,(key,r['method'],name)
        if i%100==0:print(i,'/',len(results),flush=True)
    assert set(cases)==expected and len(cases)==n and all(v=={'distance','heuristic','risk'} for v in cases.values())
    changed=[[scenario,seed] for scenario,seed in cases if initial[(scenario,seed),'risk']!=initial[(scenario,seed),'distance']]
    report={'episodes_audited':len(results),'unique_paired_environments':len(cases),'metrics_from_validated_logs':'passed',
            'shared_initial_observation':'passed','initial_paths_changed_by_selected_ai':len(changed),'path_change_examples':changed,
            'source_hashes_at_publication':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src/rescue_delivery').glob('*.py'))}}
    Path('docs/artifact_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(len(results),'trace audits passed')
