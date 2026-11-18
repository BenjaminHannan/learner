"""Exact saved TRAIN prefix restoration; never rewrites original evidence."""
from collections import Counter
import hashlib
import json


def restore_prefix(source,destination,cursor,schedule,frames,expected_hash,expected_config,guard):
    if cursor!=5120:raise ValueError('only fixed midpoint cursor permitted')
    h=hashlib.sha256();data=[];visits=Counter({i:40 for i in frames if frames[i]['cohort']=='original'})
    with source.open('rb') as stream:
        for n in range(1,cursor+1):
            line=stream.readline()
            if not line.endswith(b'\n'):raise ValueError('incomplete saved TRAIN prefix')
            r=json.loads(line);identity=schedule[n-1];visits[identity]+=1
            if not(r['additional_update']==n and r['update']==10240+n and r['id']==identity and r['visit_for_row']==visits[identity] and r['config_sha256']==expected_config):raise ValueError('saved prefix cursor/provenance differs')
            f=frames[identity]
            if r['labels']!=f['labels'] or r['label_mask']!=f['label_mask'] or r['input_frame_sha256']!=f['frame_sha256']:raise ValueError('saved prefix frame differs')
            h.update(line);data.append(line)
    if h.hexdigest()!=expected_hash:raise ValueError('saved prefix hash differs')
    payload=b''.join(data);guard(len(payload)+65536)
    import os
    with destination.open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
    return visits
