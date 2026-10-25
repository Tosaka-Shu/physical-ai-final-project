import numpy as np


def scan(world, position, theta, t, rays=16, max_range=4.):
    """Ray-marched virtual range finder (5 cm resolution)."""
    result = []
    for angle in theta+np.linspace(-np.pi, np.pi, rays, endpoint=False):
        direction = np.array([np.cos(angle), np.sin(angle)])
        distance = max_range
        for d in np.arange(0., max_range, .05):
            if world.clearance(position+d*direction, t) <= .025:
                distance = float(d)
                break
        result.append(distance)
    return np.array(result)


def features(world, p, heading, speed, t):
    p = np.asarray(p, dtype=float)
    direction = np.array([np.cos(heading), np.sin(heading)])
    lateral = np.array([-direction[1], direction[0]])
    # Passage width measured by two lateral static rays.
    widths = []
    for sign in [-1, 1]:
        width = 3.
        for d in np.arange(.1, 3., .15):
            if world.static_clearance(p+sign*d*lateral) < .05:
                width = d
                break
        widths.append(width)
    moving = [(np.linalg.norm(m.position(t)-p), m) for m in world.movers]
    if moving:
        distance, m = min(moving, key=lambda pair: pair[0])
        relative = m.position(t)-p
        closing = -np.dot(relative, m.velocity(t)-speed*direction)/max(distance, .01)
        ahead, side = np.dot(relative, direction), abs(np.dot(relative, lateral))
    else:
        distance, closing, ahead, side = 10., 0., 10., 10.
    return [world.static_clearance(p), sum(widths), distance, closing, ahead, side, speed,
            np.cos(heading), np.sin(heading)]
