"""Persistent human experience and real final-query-only V6 generation."""
from __future__ import annotations
import datetime
import json
import os
from pathlib import Path
import threading
import time
import uuid
from sol_assistant_bundle import (ROOT,owned,sha,identity,save_new,verify_bundle,load,
                                  require_sleep_readiness,Unavailable)

class Experience:
    """Source-byte capture is automatic; eligibility is not factual/label truth."""
    def __init__(self,directory):
        self.directory=owned(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.journal=self.directory/'events.jsonl';self.events=[];self.head='0'*64
        if self.journal.exists():
            for line in self.journal.read_text().splitlines():
                row=json.loads(line);body={k:v for k,v in row.items() if k!='sha256'}
                if row['seq']!=len(self.events) or row['previous']!=self.head or identity(body)!=row['sha256']:
                    raise ValueError('corrupt experience journal')
                self.events.append(row);self.head=row['sha256']

    def append(self,**fields):
        body=dict(seq=len(self.events),previous=self.head,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields)
        row=dict(body,sha256=identity(body))
        with self.journal.open('a') as f:
            f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        self.events.append(row);self.head=row['sha256'];return row

    def human(self,text,*,kind='statement',origin='interactive-cli'):
        if kind not in ('statement','correction'):raise ValueError('unknown human event kind')
        # Origin is provided by trusted UI event handlers, not parsed user text.
        eligible=origin in ('interactive-cli','trusted-ui-typed')
        path=self.directory/('human-'+uuid.uuid4().hex+'.txt')
        with path.open('xb') as f:f.write(text.encode('utf8'));f.flush();os.fsync(f.fileno())
        return self.append(event='turn',role='user',source=dict(path=str(path),sha256=sha(path),
                    byte_range=[0,len(text.encode('utf8'))]),origin=origin,kind=kind,
                    eligible_experience=eligible,verified_label=False,factual_ground_truth=False)

    def assistant(self,text,bundle_version):
        return self.append(event='turn',role='assistant',text=text,bundle_version=bundle_version,
                           eligible_experience=False,verified_label=False,factual_ground_truth=False)

    def eligible(self):
        result=[]
        for row in self.events:
            if row.get('role')!='user' or row.get('eligible_experience') is not True:continue
            if row.get('origin') not in ('interactive-cli','trusted-ui-typed'):raise ValueError('origin forged')
            source=row['source'];p=Path(source['path'])
            if not p.resolve().is_relative_to(self.directory) or sha(p)!=source['sha256']:
                raise ValueError('human source changed or moved')
            data=p.read_bytes();a,b=source['byte_range']
            if (a,b)!=(0,len(data)):raise ValueError('human source range differs')
            result.append(dict(event_sha256=row['sha256'],text=data.decode('utf8'),source=source,
                               kind=row['kind'],verified_label=False,factual_ground_truth=False))
        return result

class Assistant:
    def __init__(self,bundle_path,state_dir,device='cpu'):
        self.bundle_path=Path(bundle_path);self.bundle,self.components=load(bundle_path,device)
        self.experience=Experience(state_dir);self.lock=threading.RLock();self.last_activity=time.monotonic()
        self.experience.append(event='bundle_loaded',bundle_version=self.bundle['version'],
                               bundle_sha256=sha(bundle_path),semantic_status='NOT SHOWN')

    def reply(self,text,*,kind='statement',origin='interactive-cli',use_notebook=True):
        import torch
        from scripts.sol_stop_adapter import FinalLatent
        from sol_translator_decoder import validate_final
        with self.lock,torch.no_grad():
            # Pin verification immediately before inference also catches source drift.
            verify_bundle(self.bundle_path);self.last_activity=time.monotonic()
            memory=self.experience.eligible() if use_notebook else []
            event=self.experience.human(text,kind=kind,origin=origin)
            self._interrupt_sleep()
            # Sources are literal human observations, not assistant-authored frames.
            context='\n'.join(row['text'] for row in memory)
            encoded=self.components.input_encoder.encode(json.dumps(dict(question=text,context=context)))
            notebook=self.components.notebook_encoder(encoded['notebook'])
            mask=torch.ones(notebook.shape[:2],dtype=torch.bool,device=notebook.device)
            run=self.components.frozen_reasoner.execute_embeddings(encoded['embeddings'],encoded['answer_mask'],
                    encoded['token_shape'],notebook_latents=notebook,notebook_mask=mask,
                    policy='fixed',cap=4,compact=True)
            if type(run.final) is not FinalLatent:raise TypeError('canonical FinalLatent required')
            validate_final(run.final)
            if run.final.latent.shape[1]!=encoded['embeddings'].shape[1]:raise ValueError('notebook positions leaked to decoder')
            tokens=self.components.final_state_decoder.generate(run.final,64)[0]
            response=self.components.tokenizer.decode(tokens,skip_special_tokens=True)
            self.experience.assistant(response,self.bundle['version'])
            self.experience.append(event='execution',human_event=event['sha256'],policy='fixed',cap=4,
                query_positions=encoded['embeddings'].shape[1],notebook_positions=notebook.shape[1],
                final_query_positions=run.final.latent.shape[1],rounds=run.audit.rounds.cpu().tolist(),
                physical_row_rounds=run.audit.executed_row_rounds,decoder_payload='FinalLatent only',
                semantic_status='NOT SHOWN',sleep_ready=False)
            self.last_activity=time.monotonic();return response

    def _interrupt_sleep(self):
        running=self.experience.directory/'active-sleep.json'
        if running.exists():
            r=json.loads(running.read_text());target=owned(r['interrupt_path'])
            if not target.exists():save_new(target,dict(reason='human_activity',bundle_version=self.bundle['version']))

    def enqueue_sleep_if_idle(self,queue_writer,idle_seconds=1800):
        with self.lock:
            if time.monotonic()-self.last_activity<idle_seconds:return dict(queued=False,reason='active')
            current=verify_bundle(self.bundle_path)
            require_sleep_readiness(current)  # Always rejects current fixed4 diagnostics.
            # This path cannot execute until owner supplies accepted verifier binding.
            return queue_writer(current,self.experience.eligible())
