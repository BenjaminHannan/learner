#!/usr/bin/env python3
"""Actual NEW ordered factory consumer. Capture persists; sleeping is not implemented here."""
import argparse,json,sys,time
from pathlib import Path
from sol_assistant_ordered_bundle_v10 import load,verify,Unavailable
from sol_assistant_runtime import Experience
from sol_assistant_bundle import sha
from sol_assistant_candidate_pointer_v10 import BundlePointer

class OrderedAssistant:
    def __init__(self,bundle,state,device='cuda'):
        self.path=Path(bundle);self.bundle,self.components=load(bundle,device);self.experience=Experience(state)
        self.last_activity=time.monotonic()
        self.experience.append(event='ordered_bundle_loaded',bundle_version=self.bundle['version'],bundle_sha256=sha(bundle),policy='fixed',cap=4,learned_stop_qualified=False)
    def reply(self,text,*,kind='statement',origin='interactive-cli'):
        import torch
        from scripts.sol_stop_adapter import FinalLatent
        from scripts.sol_stop_ordered_api2 import prepare_ordered_notebook
        from sol_translator_decoder import validate_final
        verify(self.path);self.last_activity=time.monotonic()
        history=self.experience.eligible();event=self.experience.human(text,kind=kind,origin=origin)
        context='\n'.join(row['text'] for row in history)
        f=self.components
        with torch.no_grad():
            encoded=f.input_encoder.encode(json.dumps({'question':text,'context':context}))
            book=prepare_ordered_notebook(encoded['notebook']);memo=book['notebook_latents']
            run=f.frozen_reasoner.execute_embeddings(encoded['embeddings'],encoded['answer_mask'],encoded['token_shape'],query_mask=encoded['answer_mask'],**book,policy='fixed',cap=4,compact=True)
            if type(run.final) is not FinalLatent:raise TypeError('canonical final query required')
            validate_final(run.final)
            if run.final.latent.shape[1]!=encoded['embeddings'].shape[1]:raise ValueError('notebook must stay internal to reasoner')
            ids=f.final_state_decoder.generate(run.final,64)[0];answer=f.tokenizer.decode(ids,skip_special_tokens=True)
        self.experience.assistant(answer,self.bundle['version'])
        self.experience.append(event='ordered_execution',human_event=event['sha256'],source_events=[r['event_sha256'] for r in history],query_positions=run.final.latent.shape[1],notebook_positions=memo.shape[1],notebook_original_positions=book['notebook_positions'].cpu().tolist(),input_account=encoded['input_account'],policy='fixed',cap=4,decoder_input='canonical final query ONLY',model_output_training_eligible=False)
        self.last_activity=time.monotonic();return answer

def main():
    p=argparse.ArgumentParser();source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--bundle');source.add_argument('--active-pointer')
    p.add_argument('--state',required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    # Pipes/imported strings must never gain human-origin eligibility via a CLI.
    if not sys.stdin.isatty():raise SystemExit('Interactive human input required; use separately verified corpus diagnostic driver for file input.')
    bundle=a.bundle if a.bundle else BundlePointer(a.active_pointer).current(check_bundle=verify)['bundle']['path']
    agent=OrderedAssistant(bundle,a.state,a.device)
    print('Ordered model: FIXED4 fallback; learned stop unqualified. Sleep learning pending; not a completed overnight-learning release. /correct TEXT; /quit')
    while True:
        try:typed=input('you> ')
        except (EOFError,KeyboardInterrupt):break
        if typed=='/quit':break
        correction=typed.startswith('/correct ')
        print(agent.reply(typed[9:] if correction else typed,kind='correction' if correction else 'statement'))
if __name__=='__main__':
    try:main()
    except (Unavailable,FileNotFoundError) as exc:raise SystemExit('UNAVAILABLE: '+str(exc))
