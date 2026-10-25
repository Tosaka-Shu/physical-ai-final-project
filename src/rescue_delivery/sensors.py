"""Ideal segmented LiDAR + prior static map. No future-state access in inference."""
from dataclasses import dataclass
import numpy as np
from .world import GridMap


@dataclass
class Track:
    center: np.ndarray
    velocity: np.ndarray
    radius: float


class ObservedMap(GridMap):
    def __init__(self, initial_grid):
        self.grid = initial_grid.copy()
        self.tracks = []
        self.refresh()

    def update(self, observation):
        changed = False
        for x,y in observation['static_hits']:
            if not self.grid[y,x]:
                self.grid[y,x] = True
                changed = True
        if changed: self.refresh()
        self.tracks = [Track(np.array(d['position']),np.array(d['velocity']),d['radius'])
                       for d in observation['detections']]
        return changed


def raycast(grid, position, angles, max_range, circles=()):
    """Analytic ray intersections with unit AABBs and circles; first return only."""
    p = np.asarray(position,dtype=float)
    directions = np.column_stack([np.cos(angles),np.sin(angles)])
    ranges = np.full(len(angles),max_range,dtype=float)
    kinds = [None]*len(angles)
    cells = np.argwhere(grid)[:,::-1]
    for i,d in enumerate(directions):
        # Slab method handles parallel rays without dividing by zero.
        near = np.full((len(cells),2),-np.inf)
        far = np.full((len(cells),2),np.inf)
        for axis in (0,1):
            if abs(d[axis]) < 1e-10:
                outside = np.abs(cells[:,axis]-p[axis]) > .5
                near[outside,axis],far[outside,axis] = np.inf,-np.inf
            else:
                a=(cells[:,axis]-.5-p[axis])/d[axis]
                b=(cells[:,axis]+.5-p[axis])/d[axis]
                near[:,axis],far[:,axis]=np.minimum(a,b),np.maximum(a,b)
        enter,leave = np.maximum(near.max(axis=1),0),far.min(axis=1)
        valid = (leave >= enter)&(enter <= max_range)
        if valid.any():
            candidate = np.where(valid,enter,np.inf)
            j=int(candidate.argmin())
            ranges[i]=candidate[j]; kinds[i]=('static',tuple(map(int,cells[j])))
        for identity,center,radius in circles:
            delta=np.asarray(center)-p
            projection=float(np.dot(delta,d))
            disc=radius**2-float(np.dot(delta,delta))+projection**2
            if disc < 0: continue
            distance=max(0.,projection-np.sqrt(max(0.,disc)))
            if projection+np.sqrt(max(0.,disc))>=0 and distance<ranges[i]:
                ranges[i]=distance; kinds[i]=('moving',identity)
    return ranges,kinds


class Lidar:
    def __init__(self, rays=32, max_range=5.):
        self.rays,self.max_range=rays,max_range
        self.previous={}

    def observe(self, world, position, theta, t):
        angles=theta+np.linspace(-np.pi,np.pi,self.rays,endpoint=False)
        circles=[(i,m.position(t),m.radius) for i,m in enumerate(world.movers)]
        ranges,hits=raycast(world.grid,position,angles,self.max_range,circles)
        visible={hit[1] for hit in hits if hit and hit[0]=='moving'}
        detections=[]
        for i in sorted(visible):
            center=circles[i][1]
            previous=self.previous.get(i)
            velocity=np.zeros(2) if previous is None or t<=previous[0] else (center-previous[1])/(t-previous[0])
            self.previous[i]=(t,center.copy())
            detections.append({'id':i,'position':center.tolist(),'velocity':velocity.tolist(),
                               'radius':world.movers[i].radius})
        return {'timestamp':float(t),'ranges':ranges.tolist(),'max_range':self.max_range,
                'angles':angles.tolist(),'detections':detections,
                'static_hits':[list(hit[1]) for hit in hits if hit and hit[0]=='static']}


def scan(world, position, theta, t, rays=16, max_range=4.):
    return np.array(Lidar(rays,max_range).observe(world,position,theta,t)['ranges'])


def features(observed, p, heading, speed, t=0.):
    if not isinstance(observed,ObservedMap):
        raise TypeError('features requires an ObservedMap, never ground truth')
    p=np.asarray(p,dtype=float)
    direction=np.array([np.cos(heading),np.sin(heading)])
    lateral=np.array([-direction[1],direction[0]])
    ranges,_=raycast(observed.grid,p,np.array([heading-np.pi/2,heading,heading+np.pi/2]),5.)
    moving=[(np.linalg.norm(track.center-p),track) for track in observed.tracks]
    if moving:
        distance,track=min(moving,key=lambda pair:pair[0])
        relative=track.center-p
        closing=-np.dot(relative,track.velocity-speed*direction)/max(distance,.01)
        ahead,side=np.dot(relative,direction),abs(np.dot(relative,lateral))
    else:
        distance,closing,ahead,side=10.,0.,10.,10.
    return [observed.static_clearance(p),float(ranges[0]+ranges[2]),distance,closing,
            ahead,side,speed,np.cos(heading),np.sin(heading),float(ranges[1])]


FEATURES = ['static_clearance_m','passage_width_m','observed_mover_distance_m',
            'estimated_closing_mps','relative_forward_m','relative_lateral_m',
            'speed_mps','heading_cos','heading_sin','map_front_range_m']
