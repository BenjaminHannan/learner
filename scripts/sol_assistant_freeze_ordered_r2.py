#!/usr/bin/env python3
"""Freeze actual CLOSED V10r2 seed0; preserves original and additive source seals."""
import json
from pathlib import Path
from sol_assistant_bundle import ROOT,sha,pin,save_new,Unavailable
from sol_assistant_ordered_bundle_v10 import freeze,verify
EXPECTED={'parent-s0.pt':'e7aef267c0ba32aec41f01054d019317b6025e3d29b47de88c31e136a598d925','input-s0.pt':'825775fbc92eadfb624ba2a0a379413d503ca29170446b7e3d4a8a5ce37a177b','bootstrap-English-s0.pt':'4f6b41e257cb9ca5ff0f07d246741241ab30b7d9a0ed887ce6732686fa7a669f','resume-s0.pt':'a44095f3b29e296f7ec1755c7a8f1ca17eee1857314e6b0bbee16342975333b2','grounding-s0.json':'2b13d584e8a575c06deb5a41e672dacacdc9a996ef3f1e97ac5b060387ff7d4a'}
def main():
    if ROOT.as_posix()!='C:/Users/benja/sol-translator-ordered-v10r2':raise Unavailable('exact corrected PC deployment required')
    own=ROOT/'artifacts/sol-assistant-20260930';source=ROOT/'artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop'
    additive=ROOT/'artifacts/sol-compose-20260929/sol_compose_ORDERED-V10R2-SEAL.json'
    if sha(additive)!='917a562ff2647a0171de0ecdfdabd2a20dfd06fd177c6dcdc645518bf3f0a4c2':raise Unavailable('additive deployment seal mismatch')
    release=json.loads(additive.read_text(encoding='utf-8'))
    for path,h in release['files'].items():
        if sha(ROOT/path)!=h:raise Unavailable('r2 deployment source changed: '+path)
    for name,h in EXPECTED.items():
        if sha(source/name)!=h:raise Unavailable('closed receipt byte mismatch: '+name)
    req={'config_path':str(source/'runtime-config.json'),'release_path':str(ROOT/'artifacts/sol-translator-20260929/ORDERED-GROUND-V10-SEAL.json'),'release_sha256':'5946f8e94da4edb3182f04684a5420ab823e46328f3718393a11627d2082ca65','ledger_path':str(source/'grounding-s0.json'),'resume_path':str(source/'resume-s0.pt'),'transport_path':str(source/'TRANSPORT-RESULT.json'),'stdout_path':str(own/'ordered-v10r2-s0-final-stdout.log')}
    request=own/'freeze-ordered-r2-s0-request.json';save_new(request,req)
    output=own/'frozen-ordered-v10r2-s0-u500';freeze(request,output)
    b=verify(output/'bundle.json')
    save_new(own/'freeze-ordered-r2-s0-receipt.json',{'bundle':pin(output/'bundle.json'),'additive_release':pin(additive),'closed_tuple':EXPECTED,'source_version':pin(__file__),'optimizer_steps':0,'generation_calls':0,'semantic_claim':False})
    save_new(own/'freeze-ordered-r2-s0-safety-tuple.json',{role:{k:b['assets'][asset][k] for k in ('path','sha256')} for role,asset in [('parent','parent'),('reader','reader'),('prefix','adapter'),('provenance','lm_provenance')]})
if __name__=='__main__':main()
