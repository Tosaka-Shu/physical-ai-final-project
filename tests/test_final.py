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


def test_media_concat_preserves_source_audio(tmp_path):
    import shutil,subprocess,sys,json
    if not shutil.which('ffmpeg'):pytest.skip('ffmpeg required')
    sources=[]
    for i in range(3):
        src=tmp_path/f'{i}.mp4';sources.append(src)
        cmd=['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=30:d=0.2']
        if i!=1:cmd+=['-f','lavfi','-i','sine=frequency=440:duration=0.2','-c:a','aac']
        cmd+=['-c:v','libx264','-pix_fmt','yuv420p','-t','0.2',str(src)]
        subprocess.run(cmd,check=True)
    out=tmp_path/'complete.mp4'
    subprocess.run([sys.executable,'scripts/compose_video.py','--opening',str(sources[0]),'--body',str(sources[1]),'--ending',str(sources[2]),'--output',str(out)],check=True)
    report=json.loads(out.with_suffix('.json').read_text())
    assert [p['source_audio'] for p in report['parts']]==[True,False,True]
    assert report['decode']=='passed'


def test_pdf_generation(tmp_path):
    import importlib.util,subprocess,sys
    if importlib.util.find_spec('reportlab') is None:pytest.skip('optional reportlab')
    src=tmp_path/'report.md';src.write_text('# 自律配送\n\n## 結果\n\n実測値だけを示す。\n')
    out=tmp_path/'report.pdf'
    subprocess.run([sys.executable,'scripts/generate_report.py','--source',str(src),'--output',str(out)],check=True)
    assert out.read_bytes().startswith(b'%PDF')
