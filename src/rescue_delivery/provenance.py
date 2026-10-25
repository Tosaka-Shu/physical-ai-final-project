import hashlib
import importlib.metadata
import platform
import subprocess
from pathlib import Path


def environment_info(settings,model_path=None):
    commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    dirty=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout.strip()
    return {'python':platform.python_version(),'platform':platform.platform(),'git_commit':commit,
            'working_tree_dirty':bool(dirty),'config':settings,
            'packages':{p:importlib.metadata.version(p) for p in ['numpy','scikit-learn','matplotlib','pytest','joblib']},
            'model_sha256':hashlib.sha256(Path(model_path).read_bytes()).hexdigest() if model_path else None,
            'ffmpeg':subprocess.run(['ffmpeg','-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]}
