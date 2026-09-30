#!/usr/bin/env python3
"""Real ordered chat plus genuine human correction capture for queued day learning."""
import argparse,sys
from sol_assistant_ordered_chat_v10 import OrderedAssistant
from sol_assistant_ordered_bundle_v10 import verify
from sol_assistant_candidate_pointer_v10 import BundlePointer
from sol_assistant_day_v3 import DayStore

def main():
    p=argparse.ArgumentParser();p.add_argument('--active-pointer',required=True);p.add_argument('--state',required=True);p.add_argument('--day-state',required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    if not sys.stdin.isatty():raise SystemExit('Human interactive input required; unknown imports cannot acquire provenance.')
    pointer=BundlePointer(a.active_pointer);bundle=pointer.current(check_bundle=verify)['bundle']['path']
    agent=OrderedAssistant(bundle,a.state,a.device);day=DayStore(a.day_state);last=None
    print('FIXED4 fallback; learned stopping unqualified. /teach captures your literal correction to the last question; /quit exits. Queued learning requires validated day data and a watcher job.')
    while True:
        try:typed=input('you> ')
        except (EOFError,KeyboardInterrupt):break
        day.activity()
        if typed=='/quit':break
        if typed=='/teach':
            if last is None:print('Ask a question first.');continue
            context=day.typed(input('Human source context (may be empty)> '),'context')
            target=day.typed(input('Your correction> '),'correction')
            day.correction(last,context,target)
            print('Human correction captured; factual truth not automatically certified. No optimizer update executed here.');continue
        if not typed.strip():continue
        last=day.typed(typed,'question')
        try:print(agent.reply(typed))
        finally:day.activity()
if __name__=='__main__':main()
