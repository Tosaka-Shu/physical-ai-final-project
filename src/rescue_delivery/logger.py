"""JSONL records capture pre-state, observation, command and post-state per step."""
import json
from pathlib import Path
import math


REQUIRED={'episode_id','scenario_id','seed','simulation_time','dt','robot_pose','robot_velocity',
          'sensor_observations','requested_action','selected_action','predicted_risk','planned_path',
          'replanning_event','safety_stop_event','collision','near_miss','delivery_result',
          'inference_latency_ms','next_pose','next_velocity','evaluation','ai_active'}


def write_log(path,records):
    validate_log(records)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w') as f:
        for row in records: f.write(json.dumps(row,allow_nan=False)+'\n')


def read_log(path):
    with Path(path).open() as f: records=[json.loads(line) for line in f if line.strip()]
    validate_log(records)
    return records


def _finite(value):
    if isinstance(value,float) and not math.isfinite(value): raise ValueError('NaN/Inf in log')
    if isinstance(value,dict):
        for v in value.values(): _finite(v)
    elif isinstance(value,(tuple,list)):
        for v in value: _finite(v)


def validate_log(records):
    if not records: raise ValueError('empty log')
    previous=None
    identity=None
    for row in records:
        if not REQUIRED <= row.keys(): raise ValueError('missing log fields')
        _finite(row)
        current_identity=(row['episode_id'],row['scenario_id'],row['seed'])
        if identity is not None and current_identity!=identity: raise ValueError('mixed episodes')
        identity=current_identity
        t,dt=row['simulation_time'],row['dt']
        if dt<=0: raise ValueError('invalid dt')
        obs=row['sensor_observations']
        if abs(obs['timestamp']-t)>1e-8: raise ValueError('sensor/control timestamp mismatch')
        if not obs['ranges'] or any(v<0 or v>obs['max_range']+1e-8 for v in obs['ranges']):
            raise ValueError('sensor range invalid')
        if len(obs['ranges'])!=len(obs['angles']): raise ValueError('sensor shape')
        if any(v is None for key in REQUIRED for v in [row[key]]): raise ValueError('missing value')
        if len(row['robot_pose'])!=3 or len(row['next_pose'])!=3: raise ValueError('pose shape')
        if len(row['selected_action'])!=2 or len(row['robot_velocity'])!=2: raise ValueError('action shape')
        from .robot import Robot
        robot=Robot(*row['robot_pose'])
        expected,theta=robot.propose(*row['selected_action'],dt)
        expected_pose=[float(expected[0]),float(expected[1]),theta]
        if any(abs(a-b)>1e-7 for a,b in zip(expected_pose,row['next_pose'])):
            raise ValueError('action/state integration mismatch')
        if any(abs(a-b)>1e-8 for a,b in zip(row['selected_action'],row['next_velocity'])):
            raise ValueError('velocity/action mismatch')
        if not 0<=row['predicted_risk']<=1: raise ValueError('risk range')
        if previous is not None:
            if t<=previous['simulation_time']: raise ValueError('timestamps not increasing')
            if abs(t-previous['simulation_time']-previous['dt'])>1e-8:
                raise ValueError('abnormal observation period')
            if any(abs(a-b)>1e-8 for a,b in zip(previous['next_pose'],row['robot_pose'])):
                raise ValueError('discontinuous state')
            if row['robot_velocity']!=previous['next_velocity']: raise ValueError('discontinuous velocity')
        previous=row
    return {'records':len(records),'duration_s':records[-1]['simulation_time']+records[-1]['dt']}
