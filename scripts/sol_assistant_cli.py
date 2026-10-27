#!/usr/bin/env python3
"""Real bundle consumer. No bundle/weights => unavailable, never a canned chat."""
import argparse,json
from sol_assistant_bundle import pack,verify_bundle,Unavailable

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('pack');q.add_argument('--request',required=True);q.add_argument('--out',required=True)
    for name in ('check','chat'):
        q=sub.add_parser(name);q.add_argument('--bundle',required=True)
        if name=='chat':q.add_argument('--state',required=True);q.add_argument('--device',default='cpu')
    a=p.parse_args()
    try:
        if a.command=='pack':print(json.dumps({'bundle':str(pack(a.request,a.out))}));return 0
        if a.command=='check':
            b=verify_bundle(a.bundle);print(json.dumps({'bytes_verified':True,'version':b['version'],
                'updates':b['checkpoint']['updates'],'factory_loaded':False,'sleep_ready':False,'semantic_English':'NOT SHOWN'}));return 0
        from sol_assistant_runtime import Assistant
        assistant=Assistant(a.bundle,a.state,a.device)
        print('Actual fitted diagnostic: fixed4; English quality and learned-stop readiness unqualified. /quit ends.')
        while True:
            try:text=input('you> ')
            except EOFError:break
            if text=='/quit':break
            kind='correction' if text.startswith('/correct ') else 'statement'
            if kind=='correction':text=text[len('/correct '):]
            print(assistant.reply(text,kind=kind))
        return 0
    except (Unavailable,FileNotFoundError) as exc:
        print(json.dumps({'status':'UNAVAILABLE','reason':str(exc),'training_started':False}));return 5
if __name__=='__main__':raise SystemExit(main())
