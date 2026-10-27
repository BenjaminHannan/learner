#!/usr/bin/env python3
"""CPU-only extracted bootstrap gate review; does not import or launch bootstrap."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'sol-cloud-coordinator-20260930/integration'
OLD = BASE / 'exposure16-r5-v1/PC-BOOTSTRAP.py'
NEW = BASE / 'exposure16-r5-r1/PC-BOOTSTRAP.py'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def extract(path):
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='exclusive_inventory')
    return compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec')

def trial(code, override):
    rows=[{'ProcessId':900,'ParentProcessId':901,'Name':'python.exe'},
          {'ProcessId':901,'ParentProcessId':990,'Name':'python.exe'}]
    ids=list(range(1000,1031))
    names=[{'ProcessId':p,'Name':['dwm.exe','explorer.exe','msedge.exe'][p%3]} for p in ids]
    values={'rows':json.dumps(rows),'pids':'\n'.join(map(str,ids)),
            'names':json.dumps(names),'gpu':'1837, 0'}
    values.update(override)
    calls=[]
    def run(command,**kw):
        assert kw.get('check') is True and kw.get('timeout') in (10,15)
        calls.append(command)
        if '--query-compute-apps=pid' in command: key='pids'
        elif '--query-gpu=memory.used,utilization.gpu' in command:key='gpu'
        elif 'ParentProcessId' in command[-1]:key='rows'
        else:key='names'
        return SimpleNamespace(stdout=values[key])
    ns={'json':json,'os':SimpleNamespace(getpid=lambda:900),'subprocess':SimpleNamespace(run=run)}
    exec(code,ns)
    try:
        value=ns['exclusive_inventory']()
        return {'accepted':True,'metadata':value,'mock_inventory_calls':len(calls)}
    except (AssertionError,ValueError,TypeError,KeyError,IndexError) as error:
        return {'accepted':False,'exception':type(error).__name__,'message':str(error),'mock_inventory_calls':len(calls)}

def main():
    code=extract(NEW)
    base_names=[{'ProcessId':p,'Name':'dwm.exe'} for p in range(1000,1031)]
    cases=[
      ('desktop_baseline',{},True),
      ('own_bootstrap_and_venv_launcher',{'pids':'','names':'[]'},True),
      ('unknown_python_project',{'rows':json.dumps([{'ProcessId':900,'ParentProcessId':901,'Name':'python.exe'},{'ProcessId':901,'ParentProcessId':990,'Name':'python.exe'},{'ProcessId':999,'ParentProcessId':1,'Name':'python.exe'}])},False),
      ('pythonw_gpu',{'names':json.dumps(base_names[:-1]+[{'ProcessId':1030,'Name':'pythonw.exe'}])},False),
      ('python_exe_gpu',{'names':json.dumps(base_names[:-1]+[{'ProcessId':1030,'Name':'PYTHON.EXE'}])},False),
      ('own_bootstrap_gpu_rejected',{'pids':'900','names':json.dumps([{'ProcessId':900,'Name':'python.exe'}])},False),
      ('memory_threshold',{'gpu':'3000, 0'},False),
      ('malformed_python_inventory',{'rows':'{"ProcessId":"bad","ParentProcessId":1,"Name":"python.exe"}'},False),
      ('malformed_gpu_pid',{'pids':'garbage'},False),
      ('missing_gpu_name_map_nonfatal',{'names':'[]'},True),
      ('partial_gpu_name_map_nonfatal',{'names':json.dumps(base_names[:-1])},True),
      ('negative_gpu_memory',{'gpu':'-1, 0'},False),
      ('invalid_gpu_utilization',{'gpu':'1837, 101'},False),
      ('malformed_gpu_fields',{'gpu':'1837'},False),
    ]
    results=[]
    for name,override,expected in cases:
        got=trial(code,override)
        results.append({'name':name,'expected_accepted':expected,'passed':got['accepted']==expected,**got})
    out={'schema':'sol.cloud.exposure16.transport-delta-review.cpu.v1','bootstrap':{'path':str(NEW),'sha256':digest(NEW)},
         'original_bootstrap_sha256':digest(OLD),'checks':results,'passed':sum(r['passed'] for r in results),'total':len(results),
         'model_calls':0,'optimizer_calls':0,'actual_process_launches':0,'queue_operations':0,'subprocess_calls_mocked':True}
    destination=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'RAW-v1.json'
    with destination.open('x') as stream:json.dump(out,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'passed':out['passed'],'total':len(results),'failures':[r['name'] for r in results if not r['passed']],'raw':str(destination)}))
    return 0 if out['passed']==out['total'] else 1

if __name__=='__main__':sys.exit(main())
