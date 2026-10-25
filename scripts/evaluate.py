import argparse
import csv
import json
from pathlib import Path
from statistics import mean, pstdev
from rescue_delivery.risk_model import load
from rescue_delivery.simulation import run, config
from rescue_delivery.logger import write_log
from rescue_delivery.provenance import environment_info


def summary_markdown(rows):
    lines=['# 比較実験の実測結果（v2）','','3シナリオの同一初期状態・同じ観測／制御設定で対比較。全試行を掲載。',
           '移動障害物はロボットと無関係な固定時刻軌跡を走る。AI方式にも真値・未来位置は与えない。',
           '距離・到達時間は全試行の実測（失敗時は終了まで）。停止回数は連続停止区間への進入回数。',
           '平均±母標準偏差。推論時間と実時間はCPU負荷で変動する。','',
           '|シナリオ|方式|n|成功率|衝突合計|ニアミス合計|距離m|時間s|再計画|停止|推論合計ms|実時間s|',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scenario in dict.fromkeys(r['scenario'] for r in rows):
        for method in ['distance','risk']:
            rr=[r for r in rows if r['method']==method and r['scenario']==scenario]
            def stat(key):
                values=[r[key] for r in rr]
                return f'{mean(values):.2f}±{pstdev(values):.2f}'
            lines.append(f"|{scenario}|{method}|{len(rr)}|{sum(r['success'] for r in rr)}/{len(rr)}|{sum(r['collisions'] for r in rr)}|{sum(r['near_misses'] for r in rr)}|"+
                         '|'.join(stat(k) for k in ['distance','elapsed','replans','stops','inference_latency_ms','runtime_s'])+'|')
    failures=[r for r in rows if not r['success']]
    lines+=['','## 失敗例と解釈','']
    if failures:
        lines += [f"- {r['scenario']}/{r['seed']}/{r['method']}: {r['outcome']}、距離{r['distance']:.2f}m、停止{r['stops']}回" for r in failures]
    else:
        lines += ['今回の配送評価で失敗はなかった。別途、到達不能・タイムアウト・モデル異常をテストし、安全側終了を検証した。']
    lines+=['','AIの危険度は局所直進の合成ラベルに対する未校正の推定値である。',
            '危険な近道を避けても、共通安全層と動的な再計画が通常方式を救済するため、成功率の改善につながるとは限らない。',
            '長い迂回やモデル推論の計算負荷もコストになる。少数の固定壁構造による結果から一般的優位性は主張しない。',
            '全試行の個別値・終了理由はevaluation.jsonに掲載する。']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--model',default='models/risk-v2.joblib')
    p.add_argument('--seeds',type=int,nargs='+',default=[200,201,202])
    p.add_argument('--scenarios',nargs='+',choices=['basic','shortcut','dynamic'],default=['basic','shortcut','dynamic'])
    p.add_argument('--difficulty',choices=['easy','normal','hard'],default='normal')
    p.add_argument('--config',default=None); p.add_argument('--output',default='outputs/evaluation-v2')
    a=p.parse_args(); model=load(a.model); rows=[]
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    settings=config(a.config)
    for scenario in a.scenarios:
        for seed in a.seeds:
            for method in ['distance','risk']:
                result=run(seed,model,scenario=scenario,difficulty=a.difficulty,method=method,settings=settings)
                write_log(out/'logs'/f'{scenario}-{seed}-{method}.jsonl',result.logs)
                rows.append(result.metrics()); print(json.dumps(rows[-1]),flush=True)
                (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    (out/'results.md').write_text(summary_markdown(rows))
    (out/'environment.json').write_text(json.dumps(environment_info(settings,a.model),indent=2)+'\n')
