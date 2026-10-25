"""Past/current observations are features; future ground truth is label-only."""
from pathlib import Path
import hashlib
import numpy as np
from .world import World
from .sensors import Lidar, ObservedMap, features, FEATURES


HORIZON=1.5
DANGER_DISTANCE=.38


def rollout_label(world, p, heading, speed, t):
    direction=np.array([np.cos(heading),np.sin(heading)])
    distances=[world.clearance(np.asarray(p)+speed*dt*direction,t+dt) for dt in np.linspace(0,HORIZON,16)]
    return int(min(distances)<DANGER_DISTANCE)


def dataset(seeds, samples=150):
    X,y,groups=[],[],[]
    for seed in seeds:
        rng=np.random.default_rng(seed+10000)
        scenario=('basic','shortcut','dynamic')[seed%3]
        world=World(seed,scenario,('easy','normal','hard')[seed%3],varied=True)
        free=np.argwhere(~world.grid)[:,::-1]
        for _ in range(samples):
            p=free[rng.integers(len(free))].astype(float)+rng.uniform(-.25,.25,2)
            heading=float(rng.uniform(-np.pi,np.pi)); speed=float(rng.uniform(.1,1.1))
            t=float(rng.uniform(.2,25.))
            sensor=Lidar()
            # A previous observation is available to estimate approach velocity.
            sensor.observe(world,p,heading,t-.1)
            observation=sensor.observe(world,p,heading,t)
            known=ObservedMap(world.initial_grid); known.update(observation)
            X.append(features(known,p,heading,speed,t))
            y.append(rollout_label(world,p,heading,speed,t))
            groups.append(seed)
    return np.array(X),np.array(y,dtype=int),np.array(groups,dtype=int)


def validate_dataset(X,y,groups):
    if X.ndim!=2 or X.shape[1]!=len(FEATURES) or len(X)==0: raise ValueError('feature shape')
    if y.shape!=(len(X),) or groups.shape!=(len(X),): raise ValueError('row count')
    if not np.isfinite(X).all() or not np.isfinite(y).all(): raise ValueError('nonfinite data')
    if not set(np.unique(y))<= {0,1}: raise ValueError('invalid label')
    return {'samples':len(y),'positive_rate':float(y.mean()),'scenarios':sorted(map(int,set(groups)))}


def save_dataset(path,X,y,groups):
    validate_dataset(X,y,groups)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,X=X,y=y,groups=groups)


def data_hash(X,y,groups):
    h=hashlib.sha256()
    for array in (X,y,groups): h.update(array.tobytes())
    return h.hexdigest()
