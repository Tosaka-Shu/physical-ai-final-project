import argparse
import csv
import json
from pathlib import Path
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--model',default='models/risk.pkl')
    p.add_argument('--seeds',type=int,nargs='+',default=list(range(200,205)))
    p.add_argument('--output',default='outputs/evaluation'); a=p.parse_args()
    model=load(a.model); rows=[]
    for seed in a.seeds:
        for m in [None,model]:
            r=run(seed,m); rows.append(r.metrics()); print(json.dumps(rows[-1]),flush=True)
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(rows,indent=2))
    with (out/'results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    lines=['# 比較実験の実測結果','','同一シードの対比較。学習0–29、モデル評価100–109、配送評価200以降。',
           '衝突は重なりが観測されたステップ数、ニアミスは余裕0.18m未満への進入イベント数。',
           '移動障害物にも接触回避の譲り合い制御がある。実環境の安全性は保証しない。','',
           '|方式|配送成功率|衝突合計|ニアミス合計|平均走行距離(m)|平均再計画数|',
           '|---|---:|---:|---:|---:|---:|']
    for method in ['distance','risk']:
        rr=[r for r in rows if r['method']==method]; n=len(rr)
        lines.append(f"|{method}|{sum(r['success'] for r in rr)}/{n}|{sum(r['collisions'] for r in rr)}|{sum(r['near_misses'] for r in rr)}|{sum(r['distance'] for r in rr)/n:.2f}|{sum(r['replans'] for r in rr)/n:.2f}|")
    lines+=['','少数の合成シナリオによる結果であり、AI方式の一般的な優位性を示すものではない。',
            '安全制御は両方式で共通。危険度コストにより距離が増える可能性がある。']
    (out/'results.md').write_text('\n'.join(lines)+'\n')
