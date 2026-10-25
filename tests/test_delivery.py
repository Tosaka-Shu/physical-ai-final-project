import json
import math
import numpy as np
import pytest
from rescue_delivery.world import World
from rescue_delivery.robot import Robot
from rescue_delivery.sensors import scan
from rescue_delivery.planner import astar
from rescue_delivery.risk_model import dataset, train
from rescue_delivery.simulation import run


@pytest.fixture(scope='session')
def model(tmp_path_factory):
    return train(str(tmp_path_factory.mktemp('model')/'risk.pkl'))[0]


def test_differential_drive():
    r=Robot(2.,2.)
    p,theta=r.propose(1,1,1)
    np.testing.assert_allclose(p,[3,2]); assert theta==0
    p,theta=r.propose(-.2,.2,1)
    np.testing.assert_allclose(p,[2,2]); assert theta==pytest.approx(1)


def test_world_and_sensor():
    w=World(200)
    assert not w.free((12,9)) and w.free(w.start)
    assert w.static_clearance((12,9))==0
    a=scan(w,np.array(w.start),0,0)
    assert len(a)==16 and np.all((a>=0)&(a<=4))
    assert not np.allclose(w.movers[0].position(0),w.movers[0].position(1))


def test_astar_and_unreachable():
    w=World(200)
    path=astar(w,w.start,w.goal)
    assert path[0]==w.start and path[-1]==w.goal
    assert all(w.free(p) for p in path)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
    assert astar(w,w.start,w.goal,blocked={w.goal})==[]


def test_data_reproducibility_and_scenario_split():
    X,y,g=dataset([2,3],samples=30)
    X2,y2,g2=dataset([2,3],samples=30)
    np.testing.assert_array_equal(X,X2); np.testing.assert_array_equal(y,y2)
    assert set(g)=={2,3} and set(y)=={0,1}
    assert set(g).isdisjoint(set(dataset([100],samples=2)[2]))


def test_learned_probability_changes_actual_path(model):
    w=World(200)
    ordinary=astar(w,w.start,w.goal)
    learned=astar(w,w.start,w.goal,model)
    assert ordinary != learned
    assert len(learned)>len(ordinary)
    assert any(y==10 and x==12 for x,y in ordinary)
    assert all(not (x==12 and y==10) for x,y in learned)


@pytest.mark.parametrize('ai',[False,True])
def test_delivery_and_independent_safety(ai,model):
    r=run(200,model if ai else None,record=True)
    assert r.success and r.collisions==0 and r.min_clearance>=0
    assert r.distance>20 and r.frames[-1]['success']
    json.dumps({'frames':r.frames,'metrics':r.metrics()})
    if ai: assert r.stops > 0
    if not ai: assert r.replans>0


def test_timeout_is_not_success():
    r=run(200,max_steps=1)
    assert not r.success
