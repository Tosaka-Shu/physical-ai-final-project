from dataclasses import dataclass
import numpy as np


@dataclass
class Mover:
    x: float
    y: float
    amplitude: float
    phase: float
    radius: float = .32

    def position(self, t):
        return np.array([self.x, self.y + self.amplitude * np.sin(.65*t+self.phase)])

    def velocity(self, t):
        return np.array([0., .65*self.amplitude*np.cos(.65*t+self.phase)])


class World:
    width, height = 25, 20
    start, goal = (2, 10), (22, 10)

    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.grid = np.zeros((self.height, self.width), dtype=bool)
        self.grid[[0, -1], :] = True
        self.grid[:, [0, -1]] = True
        # A short narrow central passage and a longer wide northern passage.
        self.grid[1:16, 12] = True
        self.grid[10, 12] = False
        self.grid[8:10, 9:16] = True
        self.grid[11:13, 9:16] = True
        for _ in range(14):
            x, y = rng.integers(3, 22), rng.integers(2, 8)
            self.grid[y, x] = True
        self.movers = [Mover(12., 10., .65, float(rng.uniform(0, 6.28))),
                       Mover(19., 14., 2., float(rng.uniform(0, 6.28)))]
        self.obstacles = np.argwhere(self.grid)[:, ::-1].astype(float)

    def static_clearance(self, p):
        # Exact distance from point to occupied axis-aligned unit squares.
        delta = np.maximum(np.abs(self.obstacles - np.asarray(p)) - .5, 0)
        return float(np.linalg.norm(delta, axis=1).min())

    def clearance(self, p, t):
        return min([self.static_clearance(p)] +
                   [float(np.linalg.norm(np.asarray(p)-m.position(t))-m.radius) for m in self.movers])

    def free(self, cell):
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height and not self.grid[y, x]
