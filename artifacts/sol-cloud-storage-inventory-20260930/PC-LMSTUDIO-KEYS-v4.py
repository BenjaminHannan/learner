#!/usr/bin/env python3
"""One pinned LM Studio settings file: nonsecret key names/types, no values."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

PATH=Path('C:/Users/benja/.lmstudio/settings.json')
EXPECTED='1e37e73877413d62998d2be2ff56af5d07bedc49ebb8fcacc9472f73b35c44bf'
SIZE=3476


def hidden(key):
    name=re.sub('[^a-z]','',str(key).casefold())
    return any(word in name for word in ('secret','password','token','cookie','credential','apikey','authorization','authentication'))


def main():
    if platform.system()!='Windows' or sys.version_info[:3]!=(3,10,9):raise ValueError('verified nativePC3.10.9 required')
    if PATH.stat().st_size!=SIZE:raise ValueError('actual pinnedsettings size changed; no guessed schema')
    data=PATH.read_bytes()
    if hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError('actual pinnedsettings bytes changed; preserve prior receipt')
    value=json.loads(data)
    if not isinstance(value,dict):raise ValueError('actual settings object required')
    nodes=[]
    def visit(item,path=(),depth=0):
        if depth>6 or len(nodes)>=300:return
        if isinstance(item,dict):
            for key,child in item.items():
                if hidden(key):continue
                current=path+(str(key),)
                if re.search('model|download|storage|cache|directory|folder|path|config|root',str(key),re.I):
                    nodes.append({'key_path':list(current),'value_type':type(child).__name__,'value_withheld':True,
                                  'container_items':len(child) if isinstance(child,(dict,list)) else None})
                if isinstance(child,(dict,list)):visit(child,current,depth+1)
        elif isinstance(item,list):
            for index,child in enumerate(item[:30]):
                if isinstance(child,(dict,list)):visit(child,path+('[%d]'%index,),depth+1)
    visit(value)
    print(json.dumps({'schema':'sol.cloud.LMStudio.settings-key-schema.v4','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'settings_path':str(PATH),'settings_bytes':SIZE,'settings_sha256':EXPECTED,
                      'top_level_nonsecret_key_names':[str(key) for key in value if not hidden(key)],
                      'model_storage_related_key_nodes':nodes,'all_setting_values_withheld':True,'credential_subtrees_omitted':True,
                      'configured_directory_values_read_to_output':False,'settings_only_no_model_rescan':True,'CLI_invocations':0,
                      'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_writes':0,'deletions':0},sort_keys=True),flush=True)


if __name__=='__main__':main()
