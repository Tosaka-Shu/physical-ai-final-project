import json
import pickle
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from .world import World
from .sensors import features


def dataset(seeds, samples=180):
    X, y, groups = [], [], []
    for seed in seeds:
        rng = np.random.default_rng(seed+10000)
        world = World(seed)
        free = np.argwhere(~world.grid)[:, ::-1]
        for i in range(samples):
            p = free[rng.integers(len(free))].astype(float)+rng.uniform(-.25,.25,2)
            heading = float(rng.uniform(-np.pi,np.pi))
            speed, t = float(rng.uniform(.2,1.2)), float(rng.uniform(0,30))
            # Open-loop local rollout, with moving obstacles advanced in time.
            distances = [world.clearance(p+speed*dt*np.array([np.cos(heading),np.sin(heading)]), t+dt)
                         for dt in np.linspace(0,1.5,16)]
            X.append(features(world,p,heading,speed,t))
            y.append(int(min(distances) < .38))  # radius .20 + near-miss margin .18
            groups.append(seed)
    return np.array(X), np.array(y), np.array(groups)


def train(output='models/risk.pkl'):
    train_seeds, test_seeds = list(range(30)), list(range(100,110))
    X,y,_ = dataset(train_seeds)
    Xt,yt,_ = dataset(test_seeds)
    model = RandomForestClassifier(n_estimators=100, max_depth=12, min_samples_leaf=4,
                                   random_state=42, n_jobs=2, class_weight='balanced')
    model.fit(X,y)
    metrics = {'train_scenarios':train_seeds,'test_scenarios':test_seeds,
               'train_samples':len(y),'test_samples':len(yt),
               'train_positive_rate':float(y.mean()),'test_positive_rate':float(yt.mean()),
               'accuracy':accuracy_score(yt,model.predict(Xt)),
               'roc_auc':roc_auc_score(yt,model.predict_proba(Xt)[:,1]),
               'label':'minimum clearance < 0.38 m during 1.5 s straight rollout'}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    with open(output,'wb') as f: pickle.dump(model,f)
    Path(output).with_suffix('.json').write_text(json.dumps(metrics,indent=2))
    return model, metrics


def load(path):
    # Only load locally generated trusted models: pickle can execute code.
    with open(path,'rb') as f: return pickle.load(f)
