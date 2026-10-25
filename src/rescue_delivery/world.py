"""Ground truth and shared geometric operations; never passed to the planner."""
from dataclasses import dataclass
import numpy as np


@dataclass
class Mover:
    x: float
    y: float
    amplitude: float
    phase: float
    radius: float = .32
    frequency: float = .65

    def position(self, t):
        return np.array([self.x, self.y + self.amplitude*np.sin(self.frequency*t+self.phase)])


class GridMap:
    width, height = 25, 20
    start, goal = (2, 10), (22, 10)

    def refresh(self):
        self.obstacles = np.argwhere(self.grid)[:, ::-1].astype(float)

    def static_clearance(self, p):
        if not len(self.obstacles):
            return 100.
        delta = np.maximum(np.abs(self.obstacles-np.asarray(p))-.5, 0)
        return float(np.linalg.norm(delta, axis=1).min())

    def free(self, cell):
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height and not self.grid[y, x]


class World(GridMap):
    def __init__(self, seed=0, scenario='shortcut', difficulty='normal', varied=False):
        if scenario not in ('basic', 'shortcut', 'dynamic', 'unreachable'):
            raise ValueError('unknown scenario')
        if difficulty not in ('easy', 'normal', 'hard'):
            raise ValueError('unknown difficulty')
        self.seed, self.scenario, self.difficulty = seed, scenario, difficulty
        rng = np.random.default_rng(seed)
        self.grid = np.zeros((self.height, self.width), dtype=bool)
        self.grid[[0,-1],:] = True
        self.grid[:,[0,-1]] = True
        wall_x = int(rng.integers(10,15)) if varied else 12
        gap_y = int(rng.integers(8,12)) if varied else 10
        self.grid[1:16,wall_x] = True
        self.grid[gap_y,wall_x] = False
        if scenario == 'basic':
            self.grid[gap_y-1:gap_y+2,wall_x] = False
        else:
            self.grid[gap_y-2:gap_y,wall_x-3:wall_x+4] = True
            self.grid[gap_y+1:gap_y+3,wall_x-3:wall_x+4] = True
        for _ in range({'easy':5,'normal':14,'hard':25}[difficulty]):
            x,y = int(rng.integers(3,22)),int(rng.integers(2,7))
            self.grid[y,x] = True
        self.grid[self.start[1],self.start[0]] = False
        self.grid[self.goal[1],self.goal[0]] = False
        self.movers = []
        if scenario in ('shortcut','dynamic'):
            self.movers = [Mover(float(wall_x),float(gap_y),.65,float(rng.uniform(0,6.28)),
                                 frequency=float(rng.uniform(.4,.9))),
                           Mover(19.,14.,2.,float(rng.uniform(0,6.28)))]
        if scenario == 'dynamic':
            self.movers = self.movers[1:]  # closure, rather than central mover, blocks the shortcut
        if scenario == 'unreachable':
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                self.grid[self.goal[1]+dy,self.goal[0]+dx] = True
        self.closure_cell = (wall_x,gap_y)
        self.closure_time = 6. if scenario == 'dynamic' else None
        self.closure_applied = False
        self.initial_grid = self.grid.copy()
        self.refresh()

    def apply_events(self, t):
        if self.closure_time is not None and t >= self.closure_time and not self.closure_applied:
            self.grid[self.closure_cell[1],self.closure_cell[0]] = True
            self.refresh()
            self.closure_applied = True
            return [{'kind':'road_closure','cell':list(self.closure_cell),'time':float(t)}]
        return []

    def clearance(self, p, t):
        return min([self.static_clearance(p)] +
                   [float(np.linalg.norm(np.asarray(p)-m.position(t))-m.radius) for m in self.movers])
