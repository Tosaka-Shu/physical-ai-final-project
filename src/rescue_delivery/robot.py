"""Unicycle form of a differential-drive robot; units m, rad, s."""
from dataclasses import dataclass
import math
import numpy as np


@dataclass
class Robot:
    x: float
    y: float
    theta: float = 0.
    v: float = 0.
    omega: float = 0.
    radius: float = .20
    axle: float = .40
    max_speed: float = .9
    max_omega: float = 2.
    max_acceleration: float = 1.
    max_angular_acceleration: float = 4.

    @property
    def position(self):
        return np.array([self.x,self.y])

    def limit(self, linear, angular, dt):
        v=float(np.clip(linear,-self.max_speed,self.max_speed))
        w=float(np.clip(angular,-self.max_omega,self.max_omega))
        return (float(np.clip(v,self.v-self.max_acceleration*dt,self.v+self.max_acceleration*dt)),
                float(np.clip(w,self.omega-self.max_angular_acceleration*dt,self.omega+self.max_angular_acceleration*dt)))

    def propose(self, linear, angular, dt):
        if abs(angular)<1e-10:
            return self.position+dt*linear*np.array([math.cos(self.theta),math.sin(self.theta)]),self.theta
        angle=self.theta+angular*dt
        p=self.position+linear/angular*np.array([math.sin(angle)-math.sin(self.theta),
                                                -math.cos(angle)+math.cos(self.theta)])
        return p,math.atan2(math.sin(angle),math.cos(angle))

    def command(self, target):
        delta=np.asarray(target)-self.position
        err=math.atan2(delta[1],delta[0])-self.theta
        err=math.atan2(math.sin(err),math.cos(err))
        v=min(self.max_speed,np.linalg.norm(delta)*2)*max(0.,math.cos(err)) if abs(err)<.60 else 0.
        return float(v),float(np.clip(3*err,-self.max_omega,self.max_omega))

    def advance(self, action, dt):
        p,theta=self.propose(*action,dt)
        self.x,self.y=map(float,p)
        self.theta,self.v,self.omega=float(theta),float(action[0]),float(action[1])

    def wheels(self, linear, angular):
        return linear-angular*self.axle/2,linear+angular*self.axle/2
