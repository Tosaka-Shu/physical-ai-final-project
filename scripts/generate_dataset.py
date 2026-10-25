import argparse
from rescue_delivery.data_pipeline import dataset, save_dataset, validate_dataset

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--seeds',nargs='+',type=int,default=list(range(24)))
    p.add_argument('--samples',type=int,default=150); p.add_argument('--output',default='datasets/train.npz')
    a=p.parse_args(); data=dataset(a.seeds,a.samples); save_dataset(a.output,*data); print(validate_dataset(*data))
