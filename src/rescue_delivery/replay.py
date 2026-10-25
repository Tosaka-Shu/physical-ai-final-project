"""Rebuild traces from validated logs; never rerun dynamics during replay."""
from .logger import read_log
from .simulation import Result


def replay(path):
    rows=read_log(path); first=rows[0]; last=rows[-1]
    result=Result(first['seed'],'risk' if first['ai_active'] else 'distance',first['scenario_id'],first['difficulty'])
    result.logs=rows; result.outcome=last['delivery_result']; result.success=result.outcome=='success'
    result.elapsed=last['simulation_time']+last['dt']
    import numpy as np
    result.distance=sum(float(np.linalg.norm(np.array(r['next_pose'][:2])-r['robot_pose'][:2])) for r in rows)
    result.collisions=sum(r['collision'] for r in rows)
    result.replans=sum(r['replanning_event']['occurred'] for r in rows)
    result.near_misses=sum(r['near_miss'] and (i==0 or not rows[i-1]['near_miss']) for i,r in enumerate(rows))
    result.stops=sum(r['safety_stop_event']['occurred'] and (i==0 or not rows[i-1]['safety_stop_event']['occurred']) for i,r in enumerate(rows))
    for r in rows:
        result.frames.append({'t':r['simulation_time']+r['dt'],'pose':r['next_pose'],
                              'movers':r['evaluation']['movers'],'path':r['planned_path'],
                              'replan':r['replanning_event']['occurred'],
                              'stop':r['safety_stop_event']['occurred'],'success':r['delivery_result']=='success',
                              'outcome':r['delivery_result'],'risk':r['predicted_risk'],
                              'closure':r['evaluation']['closure_applied'],'scenario':r['scenario_id']})
    return result
