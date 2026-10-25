import json
from pathlib import Path
from time import perf_counter
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score,precision_score,recall_score,f1_score,
                             confusion_matrix,roc_auc_score)
from .data_pipeline import dataset, validate_dataset, data_hash
from .sensors import FEATURES


def metrics_for(model,X,y):
    start=perf_counter(); proba=model.predict_proba(X)[:,1]; latency=(perf_counter()-start)*1000
    pred=(proba>=.5).astype(int)
    auc=roc_auc_score(y,proba) if len(set(y))==2 else None
    return {'accuracy':accuracy_score(y,pred),'precision':precision_score(y,pred,zero_division=0),
            'recall':recall_score(y,pred,zero_division=0),'f1':f1_score(y,pred,zero_division=0),
            'confusion_matrix':confusion_matrix(y,pred,labels=[0,1]).tolist(),
            'roc_auc':auc,'roc_auc_unavailable_reason':None if auc is not None else 'only one ground-truth class',
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
