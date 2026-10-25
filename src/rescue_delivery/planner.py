import heapq
import math
import numpy as np
from .sensors import features


def astar(world, start, goal, model=None, t=0., blocked=frozenset(), risk_weight=8.):
    start, goal = tuple(map(int, start)), tuple(map(int, goal))
    queue = [(0., start)]
    cost, parent = {start: 0.}, {}
    # Batch inference once per heading for predictable CPU cost.
    risk = {}
    if model is not None:
        cells = [(x, y) for y in range(world.height) for x in range(world.width) if world.free((x,y))]
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            values = model.predict_proba([features(world, p, math.atan2(dy,dx), .9, t) for p in cells])[:,1]
            risk.update({(p,dx,dy): float(v) for p,v in zip(cells,values)})
    while queue:
        _, current = heapq.heappop(queue)
        if current == goal:
            path = [current]
            while current in parent:
                current = parent[current]
                path.append(current)
            return path[::-1]
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nxt = current[0]+dx, current[1]+dy
            if not world.free(nxt) or nxt in blocked:
                continue
            candidate = cost[current]+1+risk_weight*risk.get((nxt,dx,dy), 0.)
            if candidate < cost.get(nxt, float('inf')):
                cost[nxt], parent[nxt] = candidate, current
                heuristic = abs(nxt[0]-goal[0])+abs(nxt[1]-goal[1])
                heapq.heappush(queue, (candidate+heuristic, nxt))
    return []
