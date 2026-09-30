#!/usr/bin/env python3
"""Fail-closed admission of human text and separated final-state caches.
No dataset, official panel or model is downloaded by this module.
"""
import hashlib,json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def safe_source(path,root):
    p=(Path(root)/path).resolve()
    allowed=(Path(root)/'data/open').resolve()
    corpus=(Path(root)/'artifacts/sol-translator-20260929/corpus/human-documents').resolve()
    # Human source documents only, no artifacts/official benchmarks or handoff.
    if not (p.is_relative_to(allowed) or p.is_relative_to(corpus)) or not p.is_file():
        raise ValueError('source must be an admitted file under data/open')
    return p


def admit_rows(manifest_path,registry_path,root):
    """Registry must record an independently verified source, NOT generated rows.
A registry assertion is necessary but still needs external audit before claims.
"""
    registry=json.loads(Path(registry_path).read_text())
    if registry.get('verification_status')!='verified-human-origin' or not registry.get('verification_evidence'):
        raise ValueError('human-origin verification absent')
    entries=registry['sources']
    rows=json.loads(Path(manifest_path).read_text())
    required={'id','split','source_path','source_sha256','source_span','target_text','packet_path','packet_sha256','content_key','reasoner_seed'}
    ids=set(); documents={'train':set(),'dev':set()}; content={'train':set(),'dev':set()}
    hashes={}
    for row in rows:
        if set(row)!=required or row['split'] not in documents or row['reasoner_seed'] not in (0,1) or row['id'] in ids:
            raise ValueError('unexpected text manifest schema or duplicate ID')
        ids.add(row['id'])
        source=safe_source(row['source_path'],root)
        evidence=entries.get(row['source_path'],{})
        if evidence.get('sha256')!=row['source_sha256'] or evidence.get('origin')!='human-authored' or not evidence.get('evidence_url'):
            raise ValueError('row lacks verified human source evidence')
        actual=hashes.setdefault(str(source),sha(source))
        if actual!=row['source_sha256']:
            raise ValueError('human source hash mismatch')
        begin,end=row['source_span']
        if type(begin) is not int or type(end) is not int or not 0<=begin<end<=source.stat().st_size:
            raise ValueError('source span invalid')
        with source.open('rb') as f:
            f.seek(begin); original=f.read(end-begin).decode('utf-8')
        if original!=row['target_text']:
            raise ValueError('target is not verbatim human source text')
        packet=(Path(root)/row['packet_path']).resolve()
        if not packet.is_relative_to((Path(root)/'artifacts/sol-translator-20260929').resolve()) or sha(packet)!=row['packet_sha256']:
            raise ValueError('owned state cache missing or hash mismatch')
        documents[row['split']].add(str(source)); content[row['split']].add(row['content_key'])
    if documents['train']&documents['dev'] or content['train']&content['dev']:
        raise ValueError('document or content leaks between train/dev')
    return rows
