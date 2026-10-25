from dataclasses import dataclass, field
import math
import numpy as np
from .world import World
from .robot import Robot
from .planner import astar
from .sensors import scan


@dataclass
class Result:
    seed: int
    method: str
    success: bool = False
    collisions: int = 0
    near_misses: int = 0
    distance: float = 0.
    replans: int = 0
    stops: int = 0
    elapsed: float = 0.
    min_clearance: float = 100.
    frames: list = field(default_factory=list, repr=False)
    initial_path: list = field(default_factory=list)

    def metrics(self):
        return {k:v for k,v in vars(self).items() if k not in ('frames','initial_path')}


def run(seed=200, model=None, max_steps=1800, record=False):
    world = World(seed)
    robot = Robot(*world.start)
    result = Result(seed, 'risk' if model is not None else 'distance')
    path = astar(world,world.start,world.goal,model)
    result.initial_path = path.copy()
    dt, last_plan, near_before = .1, -100., False
    for step in range(max_steps):
        t = step*dt
        # Do not permit an externally moving obstacle to enter the robot body.
        # Dynamic actors obey a deterministic yield rule, shared by both methods.
        # The safety check also predicts the full next interval for the robot.
        while path and np.linalg.norm(robot.position-np.array(path[0])) < .12:
            path.pop(0)
        if np.linalg.norm(robot.position-np.array(world.goal)) < .2:
            result.success = True
        replan = False
        ranges = scan(world,robot.position,robot.theta,t, rays=8, max_range=2.) if step%5==0 else None
        danger = any(np.linalg.norm(np.array(p)-m.position(t)) < 1.05
                     for p in path[:4] for m in world.movers)
        if (danger or not path) and t-last_plan > 3. and not result.success:
            blocked = {(x,y) for y in range(world.height) for x in range(world.width)
                       if any(np.linalg.norm(np.array([x,y])-m.position(t)) < .95 for m in world.movers)}
            start = tuple(np.rint(robot.position).astype(int))
            blocked.discard(start)
            new = astar(world,start,world.goal,model,t,blocked)
            if new:
                path = new
                while path and np.linalg.norm(robot.position-np.array(path[0])) < .12: path.pop(0)
            result.replans += 1
            last_plan, replan = t, True
        old = robot.position.copy()
        if path and not result.success:
            left,right = robot.command(path[0])
            proposed,theta = robot.propose(left,right,dt)
            # Conservative swept collision guard: current actor swept segment plus
            # its maximum possible motion for this interval, independent of AI.
            safe = all(world.static_clearance(old+(proposed-old)*a) > robot.radius+.03
                       and all(np.linalg.norm(old+(proposed-old)*a-m.position(t)) >
                               robot.radius+m.radius+.65*m.amplitude*dt+.03 for m in world.movers)
                       for a in np.linspace(0,1,5))
            if safe:
                robot.x,robot.y,robot.theta = *proposed,theta
            else:
                result.stops += 1
                # Turning in place remains safe and helps recovery.
                robot.theta = theta
        # Actors yield if their next step would overlap the robot. Freeze phase
        # evolution for that interval (no teleporting through the robot).
        for m in world.movers:
            if min(np.linalg.norm(m.position(t+a*dt)-robot.position) for a in np.linspace(0,1,5)) < m.radius+robot.radius+.03:
                m.phase -= .65*dt
        clearance = world.clearance(robot.position,t+dt)-robot.radius
        result.min_clearance = min(result.min_clearance,clearance)
        if clearance < -1e-8: result.collisions += 1
        near = clearance < .18
        if near and not near_before: result.near_misses += 1
        near_before = near
        result.distance += float(np.linalg.norm(robot.position-old))
        result.elapsed = t+dt
        if record and (step%5==0 or result.success):
            result.frames.append({'t':t+dt,'pose':[robot.x,robot.y,robot.theta],
                                  'movers':[m.position(t+dt).tolist() for m in world.movers],
                                  'path':list(path),'replan':replan or t-last_plan<.6,
                                  'success':result.success,
                                  'sensor':None if ranges is None else ranges.tolist()})
        if result.success: break
    return result
