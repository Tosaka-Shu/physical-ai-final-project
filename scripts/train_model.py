import argparse
import json
from rescue_delivery.risk_model import train

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',default='models/risk.pkl'); a=p.parse_args()
    _,metrics=train(a.output); print(json.dumps(metrics,indent=2))
