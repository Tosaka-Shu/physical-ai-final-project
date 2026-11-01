"""Recompute delivery metrics from every validated trace, independent of physics runs."""
import json,hashlib
from pathlib import Path
import numpy as np
from rescue_delivery.logger import read_log

if __name__=='__main__':
    root=Path('outputs/final/benchmark');results=json.loads((root/'results.json').read_text())
    initial={}
    for r in results:
        rows=read_log(root/'logs'/f"{r['scenario']}-{r['seed']}-{r['method']}.jsonl.gz")
        initial[r['scenario'],r['seed'],r['method']]=rows[0]['planned_path']
        stops=[x['safety_stop_event']['occurred'] for x in rows]
        measured={'success':rows[-1]['delivery_result']=='success','elapsed':rows[-1]['simulation_time']+rows[-1]['dt'],
                  'distance':sum(float(np.linalg.norm(np.array(x['next_pose'][:2])-x['robot_pose'][:2])) for x in rows),
                  'collisions':sum(x['collision'] for x in rows),
                  'near_misses':sum(x['near_miss'] and (i==0 or not rows[i-1]['near_miss']) for i,x in enumerate(rows)),
                  'stops':sum(x and (i==0 or not stops[i-1]) for i,x in enumerate(stops)),
                  'stop_time_s':sum(x['dt'] for x in rows if x['safety_stop_event']['occurred']),
                  'replans':sum(x['replanning_event']['occurred'] for x in rows),
                  'min_clearance':min(x['evaluation']['clearance_m'] for x in rows)}
        for key,value in measured.items():
            assert abs(float(value)-float(r[key]))<1e-8,(r['scenario'],r['seed'],r['method'],key)
    report={'episodes_audited':len(results),'metrics_from_validated_logs':'passed','source_hashes_at_publication':{
        str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('src/rescue_delivery').glob('*.py'))}}
    changed=[[r['scenario'],r['seed']] for r in results if r['method']=='risk' and initial[r['scenario'],r['seed'],'risk']!=initial[r['scenario'],r['seed'],'distance']]
    report['initial_paths_changed_by_selected_ai']=len(changed)
    report['path_change_examples']=changed
    report['baseline_commit']=(Path('outputs/final/baseline_commit.txt').read_text().strip() if Path('outputs/final/baseline_commit.txt').exists() else json.loads(Path('docs/baseline_comparison.json').read_text())['baseline_commit'])
    Path('docs/artifact_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['episodes_audited'],'trace audits passed')
