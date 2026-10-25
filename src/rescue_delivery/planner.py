import heapq
import math
from time import perf_counter
import numpy as np
from .sensors import features, ObservedMap


def probability(model, X):
    values=np.asarray(model.predict_proba(X),dtype=float)
    if values.shape!=(len(X),2) or not np.isfinite(values).all() or (values<0).any() or (values>1).any():
        raise ValueError('invalid model probabilities')
    if not np.allclose(values.sum(axis=1),1.): raise ValueError('unnormalized model probabilities')
    if list(model.classes_) != [0,1]: raise ValueError('model must contain classes 0 and 1')
    return values[:,1]


def astar(observed, start, goal, model=None, t=0., blocked=frozenset(), risk_weight=8., telemetry=None):
    if not isinstance(observed,ObservedMap): raise TypeError('planner needs observed map')
    if not np.isfinite(risk_weight) or risk_weight<0: raise ValueError('risk weight must be nonnegative')
    start,goal=tuple(map(int,start)),tuple(map(int,goal))
    if not observed.free(start) or not observed.free(goal) or goal in blocked: return []
    risk={}
    if model is not None and risk_weight>0:
        cells=[(x,y) for y in range(observed.height) for x in range(observed.width) if observed.free((x,y))]
        rows=[]; keys=[]
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            rows.extend(features(observed,p,math.atan2(dy,dx),.9,t) for p in cells)
            keys.extend((p,dx,dy) for p in cells)
        begin=perf_counter(); values=probability(model,rows); latency=(perf_counter()-begin)*1000
        risk=dict(zip(keys,map(float,values)))
        if telemetry is not None:
            telemetry['inference_latency_ms']=telemetry.get('inference_latency_ms',0.)+latency
            telemetry['inference_samples']=telemetry.get('inference_samples',0)+len(rows)
    queue=[(0.,0.,start)]; cost={start:0.}; parent={}
    while queue:
        _,g,current=heapq.heappop(queue)
        if g>cost[current]: continue
        if current==goal:
            path=[current]
            while current in parent:
                current=parent[current]; path.append(current)
            if telemetry is not None: telemetry['path_cost']=g
            return path[::-1]
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nxt=current[0]+dx,current[1]+dy
            if not observed.free(nxt) or nxt in blocked: continue
            candidate=g+1+risk_weight*risk.get((nxt,dx,dy),0.)
            if candidate<cost.get(nxt,float('inf')):
                cost[nxt],parent[nxt]=candidate,current
                h=abs(nxt[0]-goal[0])+abs(nxt[1]-goal[1])
                heapq.heappush(queue,(candidate+h,candidate,nxt))
    return []
