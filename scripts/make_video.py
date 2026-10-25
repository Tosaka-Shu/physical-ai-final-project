import argparse
from rescue_delivery.replay import replay
from rescue_delivery.visualization import render
from rescue_delivery.risk_model import load

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('log'); p.add_argument('--baseline-log')
    p.add_argument('--model',default='models/risk-v2.joblib'); p.add_argument('--seconds',type=float,default=90)
    p.add_argument('--fps',type=int,default=10); p.add_argument('--output',default='outputs/v2-final/replay.mp4')
    a=p.parse_args(); result=replay(a.log)
    baseline=replay(a.baseline_log) if a.baseline_log else None
    render(result,load(a.model),a.output,a.seconds,a.fps,comparison=baseline)
