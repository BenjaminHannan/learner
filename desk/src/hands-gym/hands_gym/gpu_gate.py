"""Conservative GPU admission. Never kill or pause another process."""
import json
import ntpath
import os
from pathlib import Path
import subprocess


def inspect():
    def run(args):
        p=subprocess.run(args,capture_output=True,text=True,check=True)
        return p.stdout.strip()
    apps=run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'])
    gpu=run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,power.draw','--format=csv,noheader,nounits'])
    return {'compute_apps':apps,'gpu':gpu}


def foreign_clients(status, own_pid=None):
    """Unknown CUDA clients block admission; the running owner can monitor itself."""
    # WDDM reports graphics-only clients in query-compute-apps too.
    graphics={'dwm.exe','crossdeviceresume.exe','wpcuapapp.exe','explorer.exe',
            'searchhost.exe','startmenuexperiencehost.exe','msedgewebview2.exe',
            'textinputhost.exe','tabtip.exe','shellexperiencehost.exe',
            'powertoys.advancedpaste.exe','powertoys.peek.ui.exe','powertoys.powerlauncher.exe',
            'ivcam.exe','chrome.exe','discord.exe','chatgpt.exe','codex-computer-use-swift.exe',
            'lively.exe','sharex.exe','msedge.exe','taskmgr.exe','notepad.exe',
            'phoneexperiencehost.exe','applicationframehost.exe','systemsettings.exe',
            'oktaverify.exe','powertoys.fancyzones.exe','lunar client.exe',
            'edgegameassist.exe','shellhost.exe','powertoys.colorpickerui.exe'}
    rows=[]
    for row in status['compute_apps'].splitlines():
        if not row.strip():continue
        pid,name=row.split(',',1)
        if own_pid is not None and int(pid.strip())==own_pid:continue
        if ntpath.basename(name.strip()).lower() not in graphics:rows.append(row)
    return rows


class Lease:
    def __init__(self,root):
        self.path=Path(root)/'GPU-OWNER.json'
        self.owned=False

    def __enter__(self):
        status=inspect()
        rows=foreign_clients(status)
        if rows:
            raise RuntimeError('GPU busy; wait for owner: '+json.dumps(status))
        util,mem,_=[float(x.strip()) for x in status['gpu'].split(',')]
        if util>10 or mem>4000:
            raise RuntimeError('GPU not idle: '+json.dumps(status))
        with self.path.open('x') as f:
            json.dump({'pid':os.getpid(),'owner':'HANDS-GYM','status':status},f)
        self.owned=True
        print(json.dumps({'gpu_admission':status,'pid':os.getpid()}),flush=True)
        return self

    def __exit__(self,*args):
        if self.owned:
            self.path.unlink()
