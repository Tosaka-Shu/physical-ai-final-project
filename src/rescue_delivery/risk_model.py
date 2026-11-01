import json
from pathlib import Path
from time import perf_counter
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score,precision_score,recall_score,f1_score,
                             confusion_matrix,roc_auc_score,average_precision_score,brier_score_loss)
from .data_pipeline import dataset, validate_dataset, data_hash
from .sensors import FEATURES


def metrics_for(model,X,y):
    start=perf_counter(); proba=model.predict_proba(X)[:,1]; latency=(perf_counter()-start)*1000
    pred=(proba>=.5).astype(int)
    auc=roc_auc_score(y,proba) if len(set(y))==2 else None
    return {'accuracy':accuracy_score(y,pred),'precision':precision_score(y,pred,zero_division=0),
            'recall':recall_score(y,pred,zero_division=0),'f1':f1_score(y,pred,zero_division=0),
            'confusion_matrix':confusion_matrix(y,pred,labels=[0,1]).tolist(),
            'pr_auc':float(average_precision_score(y,proba)) if sum(y)>0 else None, 'brier_score':float(brier_score_loss(y,proba)),
            'calibration_bins':calibration_bins(y,proba), 'roc_auc':auc,'roc_auc_unavailable_reason':None if auc is not None else 'only one ground-truth class',
            'batch_inference_ms':latency,'mean_inference_ms_per_sample':latency/len(y)}


def train(output='models/risk-v2.joblib', samples=150):
    splits={'train':list(range(24)),'validation':list(range(40,46)),'test':list(range(100,106))}
    data={key:dataset(seeds,samples) for key,seeds in splits.items()}
    summaries={key:validate_dataset(*values) for key,values in data.items()}
    X,y,_=data['train']; Xv,yv,_=data['validation']
    candidates=[]
    # Only validation F1 selects depth. Test is evaluated once after selection.
    for depth in (8,12):
        model=RandomForestClassifier(n_estimators=80,max_depth=depth,min_samples_leaf=4,
                                     random_state=42,n_jobs=2,class_weight='balanced')
        model.fit(X,y)
        candidates.append((f1_score(yv,model.predict(Xv),zero_division=0),depth,model))
    _,depth,model=max(candidates,key=lambda row:(row[0],-row[1]))
    report={'schema_version':2,'split_scenarios':splits,'data_validation':summaries,
            'dataset_sha256':{key:data_hash(*values) for key,values in data.items()},
            'random_seed':42,'selected_max_depth':depth,
            'validation_candidates':[{'depth':d,'f1':float(f)} for f,d,_ in candidates],
            'validation':metrics_for(model,*data['validation'][:2]),
            'test':metrics_for(model,*data['test'][:2]),
            'feature_importance':dict(zip(FEATURES,map(float,model.feature_importances_))),
            'label':{'horizon_s':1.5,'surface_distance_threshold_m':.38,'rollout_samples':16},
            'features':FEATURES}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,output)
    Path(output).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    return model,report


def load(path):
    """Load only a locally generated trusted joblib model (pickle semantics)."""
    return joblib.load(path)


def calibration_bins(y,p):
    import numpy as np
    rows=[]
    for i in range(10):
        lo=i/10
        mask=np.minimum((p*10).astype(int),9)==i
        if mask.any(): rows.append({'lower':float(lo),'count':int(mask.sum()),'predicted':float(p[mask].mean()),'observed':float(y[mask].mean())})
    return rows


class HeuristicRisk:
    classes_=[0,1]
    risk_floor=0.
    def predict_proba(self,X):
        import numpy as np
        X=np.asarray(X,dtype=float)
        # Same features as RF, no label or future trajectory access.
        wall=np.clip((1.2-X[:,0])/1.2,0,1)
        approach=np.clip((2.-X[:,2])/2.,0,1)*np.clip(X[:,3],0,1)
        p=np.maximum(wall,approach)
        return np.column_stack([1-p,p])


class CalibratedRisk:
    classes_=[0,1]
    def __init__(self,base,calibrator=None,risk_floor=.2):
        self.base,self.calibrator,self.risk_floor=base,calibrator,risk_floor
    def predict_proba(self,X):
        import numpy as np
        p=self.base.predict_proba(X)[:,1]
        if self.calibrator is not None: p=self.calibrator.predict(p)
        return np.column_stack([1-p,p])
