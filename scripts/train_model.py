import argparse
import json
from rescue_delivery.risk_model import train

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',default='models/risk-v2.joblib')
    p.add_argument('--samples',type=int,default=150); a=p.parse_args()
    _,metrics=train(a.output,a.samples); print(json.dumps(metrics,indent=2))
