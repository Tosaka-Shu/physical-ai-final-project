from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
import json
import math
import numpy as np
from .world import World
from .robot import Robot
from .sensors import Lidar, ObservedMap, features
from .planner import astar, probability
from .safety import filter_action


DEFAULT_CONFIG=Path(__file__).resolve().parents[2]/'configs/default.json'


def config(path=None, overrides=None):
    values=json.loads(DEFAULT_CONFIG.read_text())
    updates=json.loads(Path(path).read_text()) if path is not None else {}
    if not isinstance(updates,dict) or (overrides is not None and not isinstance(overrides,dict)):
        raise ValueError('configuration overrides must be an object')
    updates.update(overrides or {})
    unknown=set(updates)-set(values)
    if unknown: raise ValueError(f'unknown configuration keys: {sorted(unknown)}')
    values.update(updates)
    for key,value in values.items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
            raise ValueError(f'{key} must be a finite number')
        if value<0 or (key!='risk_weight' and value==0):
            raise ValueError(f'{key} must be positive (risk_weight may be zero)')
    for key in ('sensor_rays','max_steps'):
        if int(values[key])!=values[key]: raise ValueError(f'{key} must be an integer')
    if values['sensor_rays']<4: raise ValueError('sensor_rays must be at least 4')
    return values


@dataclass
class Result:
    seed: int
    method: str
    scenario: str = 'shortcut'
    difficulty: str = 'normal'
    success: bool = False
    outcome: str = 'running'
    collisions: int = 0
    near_misses: int = 0
    distance: float = 0.
    replans: int = 0
    stops: int = 0
    elapsed: float = 0.
    min_clearance: float = 100.
    inference_latency_ms: float = 0.
    inference_calls: int = 0
    runtime_s: float = 0.
    frames: list = field(default_factory=list,repr=False)
    initial_path: list = field(default_factory=list)
    logs: list = field(default_factory=list,repr=False)
    config: dict = field(default_factory=dict,repr=False)

    def metrics(self):
        return {k:v for k,v in vars(self).items() if k not in ('frames','initial_path','logs','config')}


def run(seed=200, model=None, max_steps=None, record=False, scenario='shortcut',
        difficulty='normal', method=None, settings=None, world=None):
    cfg=config(overrides=settings)
    if max_steps is None: max_steps=int(cfg['max_steps'])
    if isinstance(max_steps,bool) or not isinstance(max_steps,int) or max_steps<1:
        raise ValueError('max_steps must be a positive integer')
    if method is None: method='risk' if model is not None else 'distance'
    if method not in ('distance','risk'): raise ValueError('unknown method')
    wallclock=perf_counter(); world=world or World(seed,scenario,difficulty)
    result=Result(seed,method,world.scenario,world.difficulty,config=cfg.copy())
    robot=Robot(*world.start,**{k:cfg[k] for k in ['max_speed','max_omega','max_acceleration','max_angular_acceleration']})
    observed=ObservedMap(world.initial_grid)
    sensor=Lidar(int(cfg['sensor_rays']),cfg['sensor_range'])
    path=[]; last_plan=-100.; near_before=False; stop_before=False; no_path_since=None
    dt=cfg['dt']; model_ok=(model is not None) if method=='risk' else True
    for step in range(max_steps):
        t=step*dt
        truth_events=world.apply_events(t)
        pre_pose=[robot.x,robot.y,robot.theta]; pre_velocity=[robot.v,robot.omega]
        observation=sensor.observe(world,robot.position,robot.theta,t)
        map_changed=observed.update(observation)
        while path and np.linalg.norm(robot.position-np.array(path[0]))<.15: path.pop(0)
        blocked={(x,y) for y in range(observed.height) for x in range(observed.width)
                 if any(min(np.linalg.norm(np.array([x,y])-(track.center+track.velocity*tau))
                            for tau in np.linspace(0,2.5,6))<1.05 for track in observed.tracks)}
        start=tuple(map(int,np.rint(robot.position))); blocked.discard(start)
        danger=any(p in blocked or not observed.free(p) for p in path[:5])
        replan=False; plan_reason=''; latency=0.; predicted=0.
        if step==0 or (map_changed or danger or not path) and t-last_plan>=cfg['replan_interval']:
            plan_reason='initial' if step==0 else ('observed_map_change' if map_changed else 'observed_path_blocked')
            telemetry={}
            try:
                if method=='risk' and not model_ok: raise ValueError('model unavailable')
                new=astar(observed,start,world.goal,model if method=='risk' else None,t,blocked,
                          cfg['risk_weight'],telemetry)
                path=new
            except Exception:
                # Fail closed: never silently turn risk mode into baseline.
                model_ok=False; path=[]
            latency+=telemetry.get('inference_latency_ms',0.)
            if telemetry.get('inference_samples',0): result.inference_calls+=1
            if step==0: result.initial_path=path.copy()
            else: result.replans+=1; replan=True
            last_plan=t
            while path and np.linalg.norm(robot.position-np.array(path[0]))<.15: path.pop(0)
        if not path:
            if no_path_since is None: no_path_since=t
        else: no_path_since=None
        desired=robot.command(path[0]) if path else (0.,0.)
        if method=='risk' and model_ok:
            direction=math.atan2(path[0][1]-robot.y,path[0][0]-robot.x) if path else robot.theta
            try:
                begin=perf_counter()
                predicted=float(probability(model,[features(observed,robot.position,direction,desired[0],t)])[0])
                latency+=(perf_counter()-begin)*1000; result.inference_calls+=1
            except Exception: model_ok=False
        action,stop_reason=filter_action(robot,desired,observation,observed,t,t,dt,
                                         model_ok,cfg['command_timeout'])
        robot.advance(action,dt)
        # Evaluation-only ground truth; never passed into controller/inference.
        clearances=[world.clearance(np.array(pre_pose[:2])+(robot.position-np.array(pre_pose[:2]))*a,t+a*dt)-robot.radius
                    for a in np.linspace(0,1,7)]
        clearance=min(clearances); collision=clearance < -1e-8; near=clearance<.18
        if collision: result.collisions+=1
        if near and not near_before: result.near_misses+=1
        near_before=near
        if stop_reason and not stop_before: result.stops+=1
        stop_before=bool(stop_reason)
        result.distance+=float(np.linalg.norm(robot.position-np.array(pre_pose[:2])))
        result.elapsed=t+dt; result.min_clearance=min(result.min_clearance,clearance)
        result.inference_latency_ms+=latency
        if collision: result.outcome='collision'
        elif not model_ok: result.outcome='model_unavailable'
        elif np.linalg.norm(robot.position-np.array(world.goal))<.20:
            result.success=True; result.outcome='success'
        elif no_path_since is not None and (not observed.tracks or t-no_path_since>=5.):
            result.outcome='unreachable'
        elif step==max_steps-1: result.outcome='timeout'
        row={'episode_id':f'{world.scenario}-{world.difficulty}-{seed}-{method}',
             'scenario_id':world.scenario,'difficulty':world.difficulty,'seed':seed,
             'simulation_time':float(t),'dt':dt,'robot_pose':pre_pose,'robot_velocity':pre_velocity,
             'sensor_observations':observation,'requested_action':list(desired),'selected_action':list(action),
             'predicted_risk':predicted,'ai_active':method=='risk','planned_path':[list(p) for p in path],
             'replanning_event':{'occurred':replan,'reason':plan_reason},
             'safety_stop_event':{'occurred':bool(stop_reason),'reason':stop_reason or ''},
             'collision':bool(collision),'near_miss':bool(near),'delivery_result':result.outcome,
             'inference_latency_ms':latency,'next_pose':[robot.x,robot.y,robot.theta],
             'next_velocity':[robot.v,robot.omega],
             'evaluation':{'movers':[m.position(t+dt).tolist() for m in world.movers],
                           'clearance_m':float(clearance),'world_events':truth_events,
                           'closure_applied':world.closure_applied}}
        result.logs.append(row)
        if record:
            result.frames.append({'t':t+dt,'pose':row['next_pose'],'movers':row['evaluation']['movers'],
                                  'path':row['planned_path'],'replan':replan,'success':result.success,
                                  'outcome':result.outcome,'risk':predicted,'stop':bool(stop_reason),
                                  'closure':world.closure_applied,'scenario':world.scenario})
        if result.outcome!='running': break
    result.runtime_s=perf_counter()-wallclock
    return result
