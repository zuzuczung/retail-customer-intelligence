import argparse
from . import bootstrap,download,pipeline,dashboard,verify


def main():
    parser=argparse.ArgumentParser(description='Retail Customer Intelligence project CLI')
    parser.add_argument('action',choices=['download','extract','bootstrap','load','validate','dashboard','verify','all'])
    args=parser.parse_args()
    if args.action in ['extract','all']:
        from . import extract
    tasks={'download':download.main,'extract':lambda:extract.main(),'bootstrap':bootstrap.main,'load':pipeline.main,
           'validate':pipeline.validate,'dashboard':dashboard.main,'verify':verify.main}
    if args.action=='all':
        for step in ['download','extract','bootstrap','load','dashboard','verify']:tasks[step]()
    else:tasks[args.action]()


if __name__=='__main__':main()
