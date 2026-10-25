from dataclasses import dataclass
import math
import numpy as np


@dataclass
class Robot:
    x: float
    y: float
    theta: float = 0.
    radius: float = .20
    axle: float = .4

    @property
    def position(self):
        return np.array([self.x, self.y])

    def propose(self, left, right, dt):
        v, w = (left+right)/2, (right-left)/self.axle
        if abs(w) < 1e-10:
            return self.position + dt*v*np.array([math.cos(self.theta), math.sin(self.theta)]), self.theta
        angle = self.theta+w*dt
        p = self.position + v/w*np.array([math.sin(angle)-math.sin(self.theta),
                                         -math.cos(angle)+math.cos(self.theta)])
        return p, math.atan2(math.sin(angle), math.cos(angle))

    def command(self, target):
        delta = np.asarray(target)-self.position
        err = math.atan2(delta[1], delta[0])-self.theta
        err = math.atan2(math.sin(err), math.cos(err))
        v = min(.9, np.linalg.norm(delta)*2)*max(0., math.cos(err)) if abs(err) < .65 else 0.
        w = float(np.clip(3*err, -2., 2.))
        return v-w*self.axle/2, v+w*self.axle/2
