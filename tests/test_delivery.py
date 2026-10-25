import copy
import json
import math
import numpy as np
import pytest
from rescue_delivery.world import World, Mover
from rescue_delivery.robot import Robot
from rescue_delivery.sensors import Lidar, ObservedMap, features, scan
from rescue_delivery.planner import astar
from rescue_delivery.data_pipeline import dataset, rollout_label, validate_dataset, save_dataset
from rescue_delivery.risk_model import train, load, metrics_for
from rescue_delivery.simulation import run
from rescue_delivery.safety import filter_action
from rescue_delivery.logger import write_log, read_log, validate_log
from rescue_delivery.replay import replay


@pytest.fixture(scope='session')
def model(tmp_path_factory):
    path=tmp_path_factory.mktemp('model')/'risk.joblib'
    model,report=train(str(path),samples=90)
    assert set(report['split_scenarios']['train']).isdisjoint(report['split_scenarios']['validation'])
    assert set(report['split_scenarios']['test']).isdisjoint(report['split_scenarios']['validation'])
    assert set(report['split_scenarios']['test']).isdisjoint(report['split_scenarios']['train'])
    restored=load(path)
    X,_,_=dataset([333],samples=8)
    np.testing.assert_allclose(model.predict_proba(X),restored.predict_proba(X),rtol=1e-14,atol=1e-14)
    assert len(report['test']['confusion_matrix'])==2
    assert sum(report['feature_importance'].values())==pytest.approx(1.)
    return restored


def known(world): return ObservedMap(world.initial_grid)


def test_differential_drive_arc_and_limits():
    robot=Robot(2.,2.)
    p,theta=robot.propose(1,0,1); np.testing.assert_allclose(p,[3,2]); assert theta==0
    p,theta=robot.propose(0,1,1); np.testing.assert_allclose(p,[2,2]); assert theta==pytest.approx(1)
    p,theta=robot.propose(1,1,1)
    np.testing.assert_allclose(p,[2+math.sin(1),3-math.cos(1)])
    assert robot.limit(100,100,.1)==pytest.approx((.1,.4))
    assert robot.wheels(1,0)==(1,1)


@pytest.mark.parametrize('scenario',['basic','shortcut','dynamic'])
def test_world_map_and_difficulty(scenario):
    a,b=World(2,scenario),World(2,scenario)
    np.testing.assert_array_equal(a.grid,b.grid)
    assert a.free(a.start) and a.free(a.goal) and not a.free((0,0))
    assert a.static_clearance((0,0))==0
    assert not np.array_equal(World(2,difficulty='easy').grid,World(2,difficulty='hard').grid)


def test_sensor_range_timestamp_and_occlusion():
    w=World(2,'basic'); w.grid[10,10]=True; w.refresh()
    w.movers=[Mover(12,10,0,0)]
    sensor=Lidar(32,5); obs=sensor.observe(w,np.array([8.,10.]),0,1.2)
    assert obs['timestamp']==1.2 and not obs['detections']
    assert len(obs['ranges'])==32 and min(obs['ranges'])==pytest.approx(1.5)
    assert max(obs['ranges'])<=5
    assert len(scan(w,np.array(w.start),0,0))==16


def test_observed_velocity_uses_past_only():
    w=World(2,'basic'); w.movers=[Mover(5,10,1,0)]
    sensor=Lidar(); sensor.observe(w,np.array(w.start),0,1.)
    obs=sensor.observe(w,np.array(w.start),0,1.1)
    expected=(w.movers[0].position(1.1)-w.movers[0].position(1.))/.1
    np.testing.assert_allclose(obs['detections'][0]['velocity'],expected)
    observed=known(w); observed.update(obs)
    before=features(observed,w.start,0,.9)
    w.movers[0].phase=100
    np.testing.assert_array_equal(before,features(observed,w.start,0,.9))
    with pytest.raises(TypeError): features(w,w.start,0,.9)
    with pytest.raises(TypeError): astar(w,w.start,w.goal)


def test_astar_and_unreachable():
    w=World(200); path=astar(known(w),w.start,w.goal)
    assert path[0]==w.start and path[-1]==w.goal
    assert all(w.free(p) for p in path)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
    assert astar(known(w),w.start,w.goal,blocked={w.goal})==[]
    unreachable=run(200,scenario='unreachable')
    assert unreachable.outcome=='unreachable' and not unreachable.success


def test_rollout_labels_and_dataset_validation(tmp_path):
    w=World(1,'basic')
    assert rollout_label(w,[1.,10.],math.pi,1.,0)==1
    assert rollout_label(w,[3.,10.],0,.1,0)==0
    X,y,g=dataset([2,3],samples=30)
    X2,y2,g2=dataset([2,3],samples=30)
    np.testing.assert_array_equal(X,X2); np.testing.assert_array_equal(y,y2)
    assert set(y)=={0,1} and set(g)=={2,3}
    validate_dataset(X,y,g); save_dataset(tmp_path/'data.npz',X,y,g)
    np.testing.assert_array_equal(np.load(tmp_path/'data.npz')['X'],X)
    X[0,0]=np.nan
    with pytest.raises(ValueError): validate_dataset(X,y,g)


def test_model_reload_influence_and_zero_weight(model):
    w=World(200); observed=known(w)
    ordinary=astar(observed,w.start,w.goal)
    learned=astar(observed,w.start,w.goal,model)
    assert ordinary!=learned and len(learned)>len(ordinary)
    assert (12,10) in ordinary and (12,10) not in learned
    assert astar(observed,w.start,w.goal,model,risk_weight=0)==ordinary
    with pytest.raises(ValueError): astar(observed,w.start,w.goal,model,risk_weight=-1)


@pytest.mark.parametrize('reason',['proximity','command_stale','sensor_stale','model_unavailable','invalid_command','static_sweep','moving_sweep'])
def test_independent_safety_stops(reason):
    w=World(200,'basic'); robot=Robot(*w.start); observed=known(w)
    obs=Lidar().observe(w,robot.position,robot.theta,0)
    now=0.; command_time=0.; model_available=True; action=(.9,0)
    if reason=='proximity': obs['ranges'][0]=.1
    if reason=='command_stale': command_time=-1
    if reason=='sensor_stale': obs['timestamp']=-1
    if reason=='model_unavailable': model_available=False
    if reason=='invalid_command': action=(np.nan,0)
    if reason=='static_sweep':
        observed.grid[10,2]=True; observed.refresh()
    if reason=='moving_sweep':
        from rescue_delivery.sensors import Track
        observed.tracks=[Track(np.array([2.6,10.]),np.array([-1.,0.]),.32)]
    selected,why=filter_action(robot,action,obs,observed,now,command_time,.1,model_available)
    assert selected==(0.,0.) and why==reason


@pytest.mark.parametrize('ai',[False,True])
def test_delivery_and_log_roundtrip(ai,model,tmp_path):
    r=run(200,model if ai else None,record=True)
    assert r.success and r.collisions==0 and r.min_clearance>=0
    assert r.distance>20 and r.frames[-1]['success']
    path=tmp_path/'episode.jsonl'; write_log(path,r.logs)
    restored=read_log(path); assert restored==r.logs
    played=replay(path)
    assert played.success and played.distance==pytest.approx(r.distance)
    assert played.frames[-1]['pose']==r.frames[-1]['pose']
    assert played.replans==r.replans and played.stops==r.stops


def test_road_closure_replans_after_observation():
    r=run(200,scenario='dynamic')
    assert r.success and r.replans>0
    closures=[row for row in r.logs if row['evaluation']['world_events']]
    assert len(closures)==1 and closures[0]['simulation_time']==6.
    changes=[row for row in r.logs if row['replanning_event']['reason']=='observed_map_change']
    assert changes and all(row['simulation_time']>=6. for row in changes)
    assert all([12,10] not in row['planned_path'] for row in changes)


def test_no_yield_future_leak_and_shared_initial_observation(model):
    a=run(200,model,max_steps=2,method='distance')
    b=run(200,model,max_steps=2,method='risk')
    assert a.logs[0]['sensor_observations']==b.logs[0]['sensor_observations']
    # Truth mover phase is immutable: no robot-dependent yield or path alteration.
    w=World(200); phases=[m.phase for m in w.movers]
    run(200,world=w,max_steps=50)
    assert phases==[m.phase for m in w.movers]


def test_collision_terminal_and_timeout():
    w=World(1,'basic'); w.grid[10,2]=True; w.initial_grid=w.grid.copy(); w.refresh()
    r=run(1,world=w)
    assert r.outcome=='collision' and r.collisions==1 and not r.success
    r=run(200,max_steps=1)
    assert r.outcome=='timeout' and not r.success


def test_missing_and_failed_model_fail_closed(model):
    r=run(200,method='risk')
    assert r.outcome=='model_unavailable' and r.distance==0 and r.stops==1
    class Broken:
        classes_=[0,1]
        def predict_proba(self,X): return np.full((len(X),2),np.nan)
    r=run(200,Broken())
    assert r.outcome=='model_unavailable' and r.distance==0


@pytest.mark.parametrize('defect',['time','nan','range','missing','period','state','action','sensor_time'])
def test_log_quality_rejects_corruption(defect):
    rows=copy.deepcopy(run(200,max_steps=3).logs)
    if defect=='time': rows[1]['simulation_time']=rows[0]['simulation_time']
    if defect=='nan': rows[0]['predicted_risk']=float('nan')
    if defect=='range': rows[0]['sensor_observations']['ranges'][0]=100
    if defect=='missing': del rows[0]['selected_action']
    if defect=='period':
        rows[1]['simulation_time']+=.01; rows[1]['sensor_observations']['timestamp']+=.01
    if defect=='state': rows[1]['robot_pose'][0]+=1
    if defect=='action': rows[0]['selected_action'][0]=100
    if defect=='sensor_time': rows[0]['sensor_observations']['timestamp']=1
    with pytest.raises(ValueError): validate_log(rows)


def test_fixed_seed_rollout_reproducible():
    a,b=run(201,scenario='dynamic'),run(201,scenario='dynamic')
    for x,y in zip(a.logs,b.logs):
        assert x['robot_pose']==y['robot_pose'] and x['selected_action']==y['selected_action']
    assert len(a.logs)==len(b.logs) and a.distance==b.distance


def test_single_class_auc_reason(model):
    X,_,_=dataset([500],samples=5)
    report=metrics_for(model,X,np.zeros(5,dtype=int))
    assert report['roc_auc'] is None and report['roc_auc_unavailable_reason']


def test_dynamic_incoming_mover_regression(model):
    # Before the observed-velocity envelope, seed 200 hit the stopped robot.
    r=run(200,model,scenario='dynamic')
    assert r.success and r.collisions==0
    assert r.replans>0 and any(row['evaluation']['closure_applied'] for row in r.logs)


def test_ai_fixed_seed_reproducibility(model):
    a=run(201,model,max_steps=20)
    b=run(201,model,max_steps=20)
    assert a.initial_path==b.initial_path
    assert [r['next_pose'] for r in a.logs]==[r['next_pose'] for r in b.logs]
