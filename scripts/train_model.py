"""Scenario-separated calibration and delivery-policy validation, no final delivery seeds."""
import json
from pathlib import Path
import joblib
from sklearn.isotonic import IsotonicRegression
from rescue_delivery.risk_model import train, CalibratedRisk, metrics_for
from rescue_delivery.data_pipeline import dataset, data_hash
from rescue_delivery.simulation import run

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='RF学習・独立シナリオ校正・初期配送ポリシー検証')
    parser.add_argument('--output',default='models/risk.joblib')
    parser.add_argument('--samples',type=int,default=150)
    args=parser.parse_args()
    if args.samples<1:parser.error('samples must be positive')
    output=Path(args.output)
    base,report=train(str(output.parent/'base.joblib'),samples=args.samples)
    base.n_jobs=1
    Xc,yc,gc=dataset(range(60,66),args.samples)
    iso=IsotonicRegression(out_of_bounds='clip').fit(base.predict_proba(Xc)[:,1],yc)
    Xv,yv,_=dataset(range(40,46),args.samples)
    raw=CalibratedRisk(base)
    calibrated=CalibratedRisk(base,iso)
    scores={k:metrics_for(m,Xv,yv) for k,m in [('raw',raw),('isotonic',calibrated)]}
    selected=min(scores,key=lambda k:scores[k]['brier_score'])
    model={'raw':raw,'isotonic':calibrated}[selected]
    trials=[]
    for weight,floor in [(1.,.2),(2.,.4),(8.,0.)]:
        model.risk_floor=floor
        rows=[run(seed,model,scenario=scenario,difficulty='hard',settings={'risk_weight':weight}).metrics()
              for scenario in ['crossing','clutter','closure'] for seed in [700,701]]
        score=sum((not r['success'])*1000+r['collisions']*1000+r['near_misses']*100+r['elapsed'] for r in rows)
        trials.append({'weight':weight,'floor':floor,'score':score,'rows':rows})
        print(weight,floor,score,flush=True)
    best=min(trials,key=lambda r:r['score']); model.risk_floor=best['floor']
    joblib.dump(model,output)
    Xt,yt,_=dataset(range(100,106),args.samples)
    report.update({'calibration_scenarios':list(range(60,66)), 'calibration_sha256':data_hash(Xc,yc,gc),
                   'calibration_selection':selected,'calibration_validation':scores,
                   'test':metrics_for(model,Xt,yt),'delivery_validation':trials,
                   'policy':{'risk_weight':best['weight'],'risk_floor':best['floor']},
                   'delivery_protocol':'configs/statistical_study.json',
                   'test_note':'classification test reused for diagnostics; delivery test seeds are held out'})
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    policy_path=Path('configs/selected.json') if output.resolve()==Path('models/risk.joblib').resolve() else output.with_suffix('.policy.json')
    policy_path.write_text(json.dumps({'risk_weight':best['weight']},indent=2)+'\n')
