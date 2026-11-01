import numpy as np
import pytest
from rescue_delivery.risk_model import HeuristicRisk,CalibratedRisk
from rescue_delivery.planner import astar,probability
from rescue_delivery.world import World
from rescue_delivery.sensors import ObservedMap,features,Lidar
from rescue_delivery.simulation import run
from rescue_delivery.logger import write_log,read_log


def test_cache_invalidation_and_no_dynamic_cache():
    w=World(3,'basic');m=ObservedMap(w.initial_grid)
    a=features(m,[4,10],0,.9);assert m.feature_cache
    obs=Lidar().observe(w,[4,10],0,0);obs['static_hits'].append([5,10]);m.update(obs)
    assert not m.feature_cache
    assert features(m,[4,10],0,.9)[0]<a[0]

@pytest.mark.parametrize('scenario',['crossing','clutter','closure'])
def test_new_world_shared_observation(scenario):
    a=run(777,scenario=scenario,max_steps=1,method='distance')
    b=run(777,scenario=scenario,max_steps=1,method='heuristic')
    assert a.logs[0]['sensor_observations']==b.logs[0]['sensor_observations']
    assert a.collisions==b.collisions==0


def test_floor_and_zero_weight_and_gzip(tmp_path):
    m=HeuristicRisk();w=World(777,'clutter');known=ObservedMap(w.initial_grid)
    assert astar(known,w.start,w.goal,m,risk_weight=0)==astar(known,w.start,w.goal)
    m.risk_floor=1
    with pytest.raises(ValueError):astar(known,w.start,w.goal,m)
    r=run(777,max_steps=2);p=tmp_path/'log.jsonl.gz';write_log(p,r.logs);assert read_log(p)==r.logs


def test_heuristic_probability_bounds():
    m=HeuristicRisk();w=World(777);known=ObservedMap(w.initial_grid)
    p=probability(m,[features(known,[3,10],0,.9)])
    assert 0<=p[0]<=1
