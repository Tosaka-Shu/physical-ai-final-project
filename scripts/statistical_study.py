"""Predeclared tuning and independent fixed-size paired confirmatory study."""
import argparse,copy,csv,json,multiprocessing,time,hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.stats import binomtest,norm
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run
from rescue_delivery.logger import write_log
from rescue_delivery.provenance import environment_info

MODEL=None

def initialize():
    global MODEL
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    MODEL=load('models/risk.joblib')


def execute(task):
    phase,variant,scenario,seed,method,weight,floor,root=task
    out=Path(root)/phase/'logs'/variant/f'{scenario}-{seed}-{method}'
    metric=out.with_suffix('.json')
    if phase=='test' and metric.exists():
        cached=json.loads(metric.read_text())
        assert cached['weight']==weight and cached['floor']==floor and cached['method']==method
        return cached
    model=copy.copy(MODEL);model.risk_floor=floor
    started=time.process_time()
    r=run(seed,model,scenario=scenario,difficulty='hard' if phase=='test' or seed>=1000 else 'normal',
          method=method,settings={'risk_weight':weight})
    cpu=time.process_time()-started
    write_log(out.with_suffix('.jsonl.gz'),r.logs)
    row={**r.metrics(),'variant':variant,'weight':weight,'floor':floor,'process_cpu_s':cpu,
         'safe_success':r.success and r.collisions==0 and r.near_misses==0}
    metric.write_text(json.dumps(row,indent=2))
    return row


def controller_hash():
    h=hashlib.sha256()
    for p in sorted(Path('src/rescue_delivery').glob('*.py')):
        h.update(str(p).encode());h.update(p.read_bytes())
    h.update(Path('configs/default.json').read_bytes())
    return h.hexdigest()


def run_tasks(tasks,workers,path):
    rows=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialize) as pool:
        for row in pool.map(execute,tasks,chunksize=1):
            rows.append(row)
            if len(rows)%30==0:print(len(rows),'/',len(tasks),flush=True)
    rows.sort(key=lambda r:(r['scenario'],r['seed'],r['method'],r['variant']))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(rows,indent=2)+'\n')
    with path.with_suffix('.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    return rows


def statistics(rows):
    methods=['distance','heuristic','risk'];summary={}
    if not rows:raise ValueError('empty paired data')
    if {r['method'] for r in rows}!=set(methods):raise ValueError('incomplete method set')
    if any(r['safe_success']!=(r['success'] and r['collisions']==0 and r['near_misses']==0) for r in rows):raise ValueError('inconsistent safe delivery flag')
    for m in methods:
        rr=[r for r in rows if r['method']==m]
        summary[m]={'n':len(rr),'success':sum(r['success'] for r in rr),'safe_success':sum(r['safe_success'] for r in rr),
                    'collisions':sum(r['collisions'] for r in rr),'near_misses':sum(r['near_misses'] for r in rr)}
        for k in ['elapsed','distance','stop_time_s','process_cpu_s','runtime_s','planning_time_ms','inference_latency_ms','replans','min_clearance']:
            x=[r[k] for r in rr];summary[m][k]={'mean':float(np.mean(x)),'median':float(np.median(x)),'std':float(np.std(x))}
        summary[m]['restricted_time_180']=float(np.mean([r['elapsed'] if r['success'] else 180 for r in rr]))
    comparisons=[]
    index={(r['scenario'],r['seed'],r['method']):r for r in rows}
    if len(index)!=len(rows):raise ValueError('duplicate paired episode')
    pair_sets=[{(r['scenario'],r['seed']) for r in rows if r['method']==m} for m in methods]
    if any(keys!=pair_sets[0] for keys in pair_sets[1:]):raise ValueError('incomplete paired episodes')
    risk=[r for r in rows if r['method']=='risk']
    for m in ['distance','heuristic']:
        diffs=[];time_diffs=[];win=loss=0
        for r in risk:
            b=index[r['scenario'],r['seed'],m]
            delta=int(r['safe_success'])-int(b['safe_success']);diffs.append(delta)
            win+=delta==1;loss+=delta==-1
            time_diffs.append((r['elapsed'] if r['success'] else 180)-(b['elapsed'] if b['success'] else 180))
        rng=np.random.default_rng(426)
        # Resample independent paired episodes within each predeclared scenario stratum.
        bootstrap=np.zeros(5000);bootstrap_time=np.zeros(5000)
        for scenario in sorted({r['scenario'] for r in risk}):
            ii=[i for i,r in enumerate(risk) if r['scenario']==scenario]
            draw=rng.choice(ii,size=(5000,len(ii)),replace=True)
            bootstrap+=np.asarray(diffs)[draw].sum(axis=1)/len(risk)
            bootstrap_time+=np.asarray(time_diffs)[draw].sum(axis=1)/len(risk)
        comparisons.append({'baseline':m,'ai_wins':int(win),'ai_losses':int(loss),'difference':float(np.mean(diffs)),
            'stratified_paired_95ci':np.quantile(bootstrap,[.025,.975]).tolist(),
            'exact_mcnemar_two_sided_p':float(binomtest(win,win+loss,.5).pvalue) if win+loss else 1.,
            'restricted_time_difference_s':float(np.mean(time_diffs)),
            'restricted_time_95ci':np.quantile(bootstrap_time,[.025,.975]).tolist()})
    order=sorted(range(len(comparisons)),key=lambda i:comparisons[i]['exact_mcnemar_two_sided_p'])
    adjusted=0.
    for rank,i in enumerate(order):
        adjusted=max(adjusted,min(1.,(len(order)-rank)*comparisons[i]['exact_mcnemar_two_sided_p']))
        comparisons[i]['holm_adjusted_p']=adjusted
        comparisons[i]['superiority_supported']=bool(adjusted<.05 and comparisons[i]['stratified_paired_95ci'][0]>0)
    summary['by_scenario']={}
    for scenario in sorted({r['scenario'] for r in rows}):
        summary['by_scenario'][scenario]={}
        for method in methods:
            rr=[r for r in rows if r['scenario']==scenario and r['method']==method]
            summary['by_scenario'][scenario][method]={'n':len(rr),'success':sum(r['success'] for r in rr),'safe_success':sum(r['safe_success'] for r in rr),'collisions':sum(r['collisions'] for r in rr),'near_misses':sum(r['near_misses'] for r in rr)}
    summary['comparisons']=comparisons
    summary['all_baselines_superiority_supported']=all(c['superiority_supported'] for c in comparisons)
    return summary


def planning_power(plan):
    n=plan['fixed_sample_size'];effect=plan['minimum_practical_difference']
    discordance=plan['planning_assumptions']['paired_discordance'];family=len(plan['comparisons'])
    critical=norm.ppf(1-plan['alpha_family_wise']/(2*family));mu=effect*np.sqrt(n/(discordance-effect**2))
    return {'episodes':n,'target_difference':effect,'assumed_discordance':discordance,'family_comparisons':family,
            'conservative_bonferroni_critical_value':float(critical),
            'approximate_power':float(norm.cdf(mu-critical)+norm.cdf(-mu-critical)),
            'note':'planning normal approximation; not a guarantee for true unknown effect or discordance'}


def apply_selection(root):
    import joblib,shutil
    root=Path(root);root.mkdir(parents=True,exist_ok=True);selected=json.loads(((root/'selected.json') if (root/'selected.json').exists() else Path('configs/method_policies.json')).read_text())
    (root/'selected.json').write_text(json.dumps(selected,indent=2)+'\n')
    if not (root/'pilot_model.joblib').exists():shutil.copyfile('models/risk.joblib',root/'pilot_model.joblib')
    model=load('models/risk.joblib');model.risk_floor=selected['risk']['floor'];joblib.dump(model,'models/risk.joblib')
    Path('configs/selected.json').write_text(json.dumps({'risk_weight':selected['risk']['weight']},indent=2)+'\n')
    Path('configs/method_policies.json').write_text(json.dumps(selected,indent=2)+'\n')
    report=json.loads(Path('models/risk.json').read_text())
    report['initial_policy']=report.get('initial_policy',report['policy'])
    report['policy']={'risk_weight':selected['risk']['weight'],'risk_floor':selected['risk']['floor']}
    report.pop('delivery_test_seeds',None)
    report['confirmatory_delivery_test_plan']=json.loads(Path('configs/statistical_study.json').read_text())
    report['expanded_delivery_validation']={'seeds':list(range(1000,1010)),'regression_guard':[310,311],'selected':selected}
    Path('models/risk.json').write_text(json.dumps(report,indent=2)+'\n')
    print('frozen method policies:',selected,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['tune','test','analyze','apply']);p.add_argument('--workers',type=int,default=4);p.add_argument('--root',default='outputs/statistics');a=p.parse_args()
    root=Path(a.root);root.mkdir(exist_ok=True,parents=True)
    (root/'planning_power.json').write_text(json.dumps(planning_power(json.loads(Path('configs/statistical_study.json').read_text())),indent=2)+'\n')
    if a.phase=='tune':
        candidates=[('risk',w,f) for w,f in [(2,.4),(.5,.2),(1,.2),(2,0),(4,.2),(4,0),(8,0)]]+ [('heuristic',w,0) for w in [.5,1,2,4,8]]
        cases=[(s,seed) for s in ['crossing','clutter','closure'] for seed in range(1000,1010)]
        guards=[(s,seed) for s in ['basic','shortcut','dynamic'] for seed in [310,311]]
        tasks=[('tune',f'{m}-w{w}-f{f}',s,seed,m,w,f,str(root)) for m,w,f in candidates for s,seed in cases+guards]
        rows=run_tasks(tasks,a.workers,root/'tuning_results.json');selection={}
        for method in ['risk','heuristic']:
            ranks=[]
            for _,w,f in [c for c in candidates if c[0]==method]:
                rr=[r for r in rows if r['method']==method and r['weight']==w and r['floor']==f]
                guard=[r for r in rr if r['seed']<1000];dev=[r for r in rr if r['seed']>=1000]
                eligible=all(r['safe_success'] for r in guard)
                key=(eligible,sum(r['safe_success'] for r in dev),sum(r['success'] for r in dev),-sum(r['collisions'] for r in dev),-sum(r['elapsed'] if r['success'] else 180 for r in dev),-w)
                ranks.append((key,{'weight':w,'floor':f,'eligible':eligible,'development_safe':sum(r['safe_success'] for r in dev),'development_n':len(dev)}))
            selection[method]=max(ranks,key=lambda r:r[0])[1]
        (root/'selected.json').write_text(json.dumps(selection,indent=2)+'\n');print(selection,flush=True);apply_selection(root)
    elif a.phase=='test':
        plan=json.loads(Path('configs/statistical_study.json').read_text());selected=json.loads((root/'selected.json').read_text())
        tasks=[]
        for scenario,start in plan['test_seed_starts'].items():
            for seed in range(start,start+plan['episodes_per_scenario']):
                methods=list(['distance','heuristic','risk']);np.random.default_rng(seed).shuffle(methods)
                for m in methods:
                    policy=selected.get(m,{'weight':0,'floor':0})
                    tasks.append(('test','frozen',scenario,seed,m,policy['weight'],policy['floor'],str(root)))
        info=environment_info({'study_plan':plan,'selected':selected,'workers':a.workers},'models/risk.joblib')
        info['controller_sha256']=controller_hash()
        if (root/'environment.json').exists():
            previous=json.loads((root/'environment.json').read_text())
            assert previous['model_sha256']==info['model_sha256'] and previous['config']==info['config'] and previous.get('controller_sha256')==info['controller_sha256'],'cannot resume with changed study inputs'
            info=previous
        (root/'environment.json').write_text(json.dumps(info,indent=2)+'\n')
        rows=run_tasks(tasks,a.workers,root/'test_results.json')
        assert len(rows)==3*3*plan['episodes_per_scenario']
        (root/'summary.json').write_text(json.dumps(statistics(rows),indent=2)+'\n')
    elif a.phase=='apply':
        apply_selection(root)
    else:
        rows=json.loads((root/'test_results.json').read_text());(root/'summary.json').write_text(json.dumps(statistics(rows),indent=2)+'\n')
