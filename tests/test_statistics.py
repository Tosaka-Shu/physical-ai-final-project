import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('study','scripts/statistical_study.py')
study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)


def sample_rows(advantage):
    rows=[]
    for i in range(20):
        for method in ['distance','heuristic','risk']:
            safe=(i<10 or (advantage and method=='risk'))
            r={k:0. for k in ['distance','stop_time_s','process_cpu_s','runtime_s','planning_time_ms','inference_latency_ms','replans','min_clearance']}
            r.update(method=method,scenario='crossing',seed=20000+i,elapsed=30. if safe else 1.,
                     success=safe,safe_success=safe,collisions=0 if safe else 1,near_misses=0)
            rows.append(r)
    return rows


def test_paired_exact_test_and_holm():
    s=study.statistics(sample_rows(True))
    for c in s['comparisons']:
        assert (c['ai_wins'],c['ai_losses'])==(10,0)
        assert c['exact_mcnemar_two_sided_p']==pytest.approx(2/1024)
        assert c['holm_adjusted_p']==pytest.approx(4/1024)
        assert c['superiority_supported']
    assert s['all_baselines_superiority_supported']
    assert s['distance']['restricted_time_180']==105.
    assert s['distance']['elapsed']['mean']==15.5  # failed episodes retained


def test_equal_methods_never_claim_superiority():
    s=study.statistics(sample_rows(False))
    assert not s['all_baselines_superiority_supported']
    assert all(c['holm_adjusted_p']==1 and c['stratified_paired_95ci']==[0.,0.] for c in s['comparisons'])


def test_confirmatory_plan_independent_seed_blocks():
    p=json.loads(Path('configs/statistical_study.json').read_text())
    blocks=[set(range(start,start+p['episodes_per_scenario'])) for start in p['test_seed_starts'].values()]
    assert len(set.union(*blocks))==p['fixed_sample_size']==600
    assert all(not a.intersection(b) for i,a in enumerate(blocks) for b in blocks[i+1:])
    assert not set.union(*blocks).intersection(p['tuning_seeds']+p['regression_guard_seeds']+list(range(10000,10030)))


def test_duplicate_or_missing_pair_rejected():
    rows=sample_rows(False)
    with pytest.raises(ValueError,match='empty'):study.statistics([])
    with pytest.raises(ValueError,match='duplicate'):study.statistics(rows+[rows[0]])
    with pytest.raises(ValueError,match='incomplete'):study.statistics(rows[1:])
