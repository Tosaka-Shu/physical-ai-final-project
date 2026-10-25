"""Independent command gate. Uses observations, not RF probabilities or future truth."""
import numpy as np


def filter_action(robot, action, observation, observed, now, command_time, dt,
                  model_available=True, timeout=.25):
    def stop(reason): return (0.,0.),reason
    if not model_available: return stop('model_unavailable')
    if command_time is None or now-command_time>timeout: return stop('command_stale')
    if observation is None or now-observation['timestamp']>timeout: return stop('sensor_stale')
    if not np.isfinite(action).all(): return stop('invalid_command')
    if not np.isfinite(observation['ranges']).all(): return stop('invalid_sensor')
    limited=robot.limit(*action,dt)
    if min(observation['ranges']) < robot.radius+.06:
        return stop('proximity')
    proposed,_=robot.propose(*limited,dt)
    for fraction in np.linspace(0,1,7):
        p=robot.position+(proposed-robot.position)*fraction
        if observed.static_clearance(p)<robot.radius+.035:
            return stop('static_sweep')
        for track in observed.tracks:
            # Constant-velocity estimate from past detections + uncertainty margin.
            center=track.center+track.velocity*fraction*dt
            if np.linalg.norm(p-center)<robot.radius+track.radius+.12:
                return stop('moving_sweep')
    return limited,None
