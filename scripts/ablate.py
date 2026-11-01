"""Predeclared development-only policy ablations, separate from held-out benchmark."""
import json,copy
from pathlib import Path
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run,config
m=load('models/risk.joblib');cfg=config('configs/selected.json');rows=[]
for variant in ['selected','weight_zero','uncalibrated','floor_zero']:
    model=copy.deepcopy(m);settings=cfg.copy()
    if variant=='weight_zero':settings['risk_weight']=0
    if variant=='uncalibrated':model.calibrator=None
    if variant=='floor_zero':model.risk_floor=0
    for scenario in ['crossing','clutter','closure']:
        for seed in [800,801]:
            r=run(seed,model,scenario=scenario,difficulty='hard',settings=settings)
            rows.append({'variant':variant,**r.metrics()})
    print(variant,flush=True)
Path('outputs/statistics/ablations.json').write_text(json.dumps(rows,indent=2))
