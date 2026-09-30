#!/usr/bin/env python3
"""Read-only exact capability256 preflight recovery; never stages or launches training."""
import ctypes,datetime,hashlib,importlib.util,json,os,pathlib,platform,shutil,subprocess,sys,traceback
spec={'arm': 'loop', 'files': [{'bytes': 80173, 'path': 'scripts/sol_cloud_capability256_v1.py', 'sha256': 'dfeef09f14fdcd0a1987c38d6a89a560f4ef02159b732cd1665cf51e9fa39b01'}, {'bytes': 17896, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json', 'sha256': 'ceb522253ae98f80ad65c4102563a3a604b5d4dc70b4ffb671d4e59f4c1e8470'}, {'bytes': 8632, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/SEAL-v7.json', 'sha256': '3fbc0e67deb805784599025067ab2e9b18f28784aa3d2387bee7c9831f4d263e'}, {'bytes': 408, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/RELEASE-v2.json', 'sha256': 'e82c801f2f858b712a570a18690682340a1d621706ef1ab5e8688ddcad172e69'}, {'bytes': 1927, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/COMPARATORS-v4.json', 'sha256': '0b1dad8b7cd4c913686721c26cfe63fb94dbe521e2bee0336a4938f3a76481be'}, {'bytes': 60252, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/MANIFEST-v3.json', 'sha256': '7107fe12971f0255458746cb05d0df073899564848e68d3b71dbdb974878e1d5'}, {'bytes': 10416, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PROTOCOL-v3.json', 'sha256': 'a5a803586db7b14c686bd6fab1a8c8d3521d1fd1a321716c537db338a2b27aaa'}, {'bytes': 118931, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/QUESTION-PACKET-v3.json', 'sha256': '2df3a4e79101dacd38bd399461306cebb723e1643722e80131b6200ad78449af'}, {'bytes': 10613, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/ROW-SEAL-v3.json', 'sha256': '39b9d3170118e4d794f2cd14c63b2973db51e6ec2177d2fd0d8c63fae74e7c34'}, {'bytes': 92163, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/SCHEDULE-s0-v4.json', 'sha256': '7f29f47c297f12eaa9c4e5578403d1be81524afa1c94e045c0831d892aaa661f'}, {'bytes': 92163, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/SCHEDULE-s1-v4.json', 'sha256': 'd07db744c886c2af2dd620735b3e75cf78f6be3be52fb06e8db2b030e3dacd30'}, {'bytes': 632971, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TOKEN-AUDIT-v4.json', 'sha256': '2ed29a909a56ddd4c6778a899aa386acddaba7cb1cc6e0111c81892f84e79842'}, {'bytes': 51678, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/TRAIN-NUMERIC-TARGETS-v3.json', 'sha256': '1f1e86bdaf59b824d0415c7f1045ae07d5798b0b516247391a6e2a68a03dc234'}, {'bytes': 26388, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v1/MAC-LAUNCH-v1.py', 'sha256': '81c5dcc6bd0c1ffccfde62f2b0c166b80d8452c9013fc7895d78a43143ecd697'}, {'bytes': 26782, 'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v2/MAC-LAUNCH-v2.py', 'sha256': 'cc9a7e95cb1d33ec84b1f654ee38ca043deed1d8d471ec3ec99112b705a1e32b'}, {'bytes': 64177, 'path': 'artifacts/sol-cloud-luna-train-20260930/consolidated1965-input-v1/luna_accepted_corpus/verified_targets.jsonl', 'sha256': '3196dcba0bb2ab3dc236354207477350e6c57826e2b313fd7479f696780dd225'}, {'bytes': 3786, 'path': 'artifacts/sol-cloud-verifier-20260930/CORPUS1965-CAPABILITY256-SOURCE-REVIEW-v1.json', 'sha256': '52e1ab2940be6b226e5eec2a69d940a499406f7cad062165e491c73cb935bfcc'}, {'bytes': 5125, 'path': 'artifacts/sol-cloud-verifier-20260930/CORPUS1965-SELECTED416-TOKEN-GATE-v1.json', 'sha256': 'ba90de72ead54448e37edb309f2f60a40d813780de840bacde634083f1d2eb21'}, {'bytes': 966, 'path': 'artifacts/sol-translator-20260929/CACHED-LFM-ORIGINAL-PROVENANCE.json', 'sha256': 'ec5d42dc87c2f2d8a25168de33b5c8324c8f777f75e7c1b69b8c6205fe97bee8'}, {'bytes': 8233, 'path': 'scripts/claude_blurt1.py', 'sha256': 'c00aa62f4bc9ed710019581ee61288256238539c5bcfb6759d17f89c01a958de'}, {'bytes': 7170, 'path': 'scripts/claude_fewex_net.py', 'sha256': '2f9415f5973686733c130b5edcfcfea6901de9ede546b3863fc1a4699f89c5d7'}, {'bytes': 12818, 'path': 'scripts/claude_rsn358a_envs.py', 'sha256': 'af350749936eaa084af696cf191c9111cc3aaf03594cd84e8827ba883c9b54d0'}, {'bytes': 19126, 'path': 'scripts/sol_cloud_queue_recovery_v1.py', 'sha256': '4708726dc856823f1bea1248fe08607e519dacee521723816d54dd5e89f50876'}, {'bytes': 7026, 'path': 'scripts/sol_spatial_attention_core.py', 'sha256': 'b14b3a0df49c04fc3905d910abd05fdc38759846928fd25026a3ff806eb9cf25'}, {'bytes': 582, 'path': 'scripts/sol_spatial_decoder_parity_adapter_v12.py', 'sha256': '59bbb0efc1edcd55a9de9704394e7bcd8598348659ab69aa52c56a25e0e7de6a'}, {'bytes': 7951, 'path': 'scripts/sol_spatial_decoder_parity_v12.py', 'sha256': 'f3fb27499600e3f5e32e3a686a114514da78ed2ec3b56669326dd6d8e32236d5'}, {'bytes': 6948, 'path': 'scripts/sol_spatial_poc_memory.py', 'sha256': 'e61b292892669f8175129dc0afa9ec6e9507db396072efc13d35dba21f7813ff'}, {'bytes': 1043, 'path': 'scripts/sol_spatial_poc_ordered_train_api_v2.py', 'sha256': 'c2bcbf5ec222053bd711d8834429e3f7197490706aebe457634eb4dbc9b0cf1a'}, {'bytes': 7417, 'path': 'scripts/sol_spatial_poc_ordered_v2.py', 'sha256': '5344e622855c875312f77a88095d287a5709e17dbaca23c90bdd8733b0a38291'}, {'bytes': 7291, 'path': 'scripts/sol_spatial_poc_plain.py', 'sha256': '878de58d016d30912323664a240952b7221870f2070e21feeecee82079c12fef'}, {'bytes': 30200, 'path': 'scripts/sol_stop_adapter.py', 'sha256': '3e4356e027c2e8c9746a9aef1cb20b04c3b1fe6160ffe5c35a4bf2c727a198d5'}, {'bytes': 1552, 'path': 'scripts/sol_stop_api4.py', 'sha256': '845f955e798af2f1850804e27fa74af80c5d96751cd77d36effaa72c3e67d680'}, {'bytes': 9840, 'path': 'scripts/sol_stop_grounded_adapter_v4.py', 'sha256': 'f81aa9b304d409ed00d47d0fefc7e322334f4746d63fe7dbef519989ee8df6bd'}, {'bytes': 7863, 'path': 'scripts/sol_stop_ordered_api2.py', 'sha256': '150290c3f2bc82d46cab91047c8e21879de2ddc231f44f06371148e1116e5238'}, {'bytes': 1504, 'path': 'scripts/sol_translator_answer_data_v11.py', 'sha256': '6f3a1f81784e232627200fcf066bc3f481117d3f5c71fe6910b1854b6d068583'}, {'bytes': 5564, 'path': 'scripts/sol_translator_answer_deploy_v11.py', 'sha256': '695a6bc9ccf0b908bc658ffeb2390a4589ae7116965511fc5589fa1f94341a30'}, {'bytes': 3215, 'path': 'scripts/sol_translator_answer_states_v11.py', 'sha256': '5fc673e6eab4e6cebc8ac866d4bbc2d2dd5470b6eb55fe47b00cf94b96ce2e5a'}, {'bytes': 2965, 'path': 'scripts/sol_translator_cache_policy_v6.py', 'sha256': '13579440c1283298569edcc2f2b5014b0d4aef7871a7a9eacea34c88cc6e7edc'}, {'bytes': 3044, 'path': 'scripts/sol_translator_decoder.py', 'sha256': '5253fb2c4e85e36a2d77cdf0f0e73337c7cbefea1374fecdb1b05315ae3e667c'}, {'bytes': 4237, 'path': 'scripts/sol_translator_deploy_v6.py', 'sha256': '7b8b21968b290f98fcf18eca375ede5f43d49fc637cb463e76dc2c5e696b55bf'}, {'bytes': 6575, 'path': 'scripts/sol_translator_diagnostic_answer_v11.py', 'sha256': '5375d4eb02c434aff88f3b0008f60c04eb04745f968cd28097a519c80bd6ee66'}, {'bytes': 6296, 'path': 'scripts/sol_translator_diagnostic_ordered_v10.py', 'sha256': '52d4f50b31a014a8045476a07467eeb6c0f5385a5ab335db6c5809d17056360b'}, {'bytes': 5785, 'path': 'scripts/sol_translator_diagnostic_v7.py', 'sha256': '7d27cabe276f912d26eb5b871d8ae17a0416a6631f1f314dc55304e1f6e4b9b0'}, {'bytes': 7835, 'path': 'scripts/sol_translator_english.py', 'sha256': '2b96d9581b27204232d177335e90b2918a46dbda23d28fc7f01174b0f0709f47'}, {'bytes': 1952, 'path': 'scripts/sol_translator_english_ordered_v10.py', 'sha256': '321f5f7339d129f922e6aa50e3a4470f3d7836c48eae5066f60753b88ee227ec'}, {'bytes': 9277, 'path': 'scripts/sol_translator_english_v6.py', 'sha256': 'b0aff6aa8bbbb8be62d2d194e5da13e2d3bb7302cc6bee3cb9db9026d23ac39f'}, {'bytes': 2627, 'path': 'scripts/sol_translator_factories.py', 'sha256': '3fdbba089a5c00ac91104aec0eb4724eb9d11a2e9bfa6149723f0c48d503ea13'}, {'bytes': 3675, 'path': 'scripts/sol_translator_followup_deploy_v7.py', 'sha256': '03baab57b2210b1805e5fbafb13f7adf028b33d5e2aecce5df890fb7b2e0f466'}, {'bytes': 26259, 'path': 'scripts/sol_translator_ground_answer_v11.py', 'sha256': 'a354a1702a1bf16f2387197261fc169193405fce175a2df2fc1adc720140f90f'}, {'bytes': 25236, 'path': 'scripts/sol_translator_ground_ordered_v10.py', 'sha256': '5bc42f01ab72f9ac3beae2b2f55e6ea22fb1156dc6ec907be1f0e5c8940524c8'}, {'bytes': 11602, 'path': 'scripts/sol_translator_grounding.py', 'sha256': '13720d071b4425e8f3813a3cc91618523525a21c2d4f17f80e39a9e0b2c62263'}, {'bytes': 19529, 'path': 'scripts/sol_translator_grounding_v6.py', 'sha256': '285529d88e08555dd7caa609a07d0ea58c9c915bef57411f6f979f7c2d2be1f4'}, {'bytes': 10472, 'path': 'scripts/sol_translator_language_proof.py', 'sha256': '2b2e9d407e343526b0577ca44f7f48ee6d6fa81bb019439656ca0eec6c87f0f3'}, {'bytes': 3346, 'path': 'scripts/sol_translator_ordered_contracts_v10.py', 'sha256': 'd1515adbcf3be9efa66b25a04ceeef3fccc0188755fee3862e65fefde373666e'}, {'bytes': 5339, 'path': 'scripts/sol_translator_ordered_deploy_v10.py', 'sha256': 'd9c2ee2a2b0d997611ce17f8deed00be3e3fe2bca9a084cfbafe0785698fb505'}, {'bytes': 3109, 'path': 'scripts/sol_translator_ordered_states_v10.py', 'sha256': '72d913b77b4b7093d2970857bed4c92738c5eb149996df852b030b476408645e'}, {'bytes': 3624, 'path': 'scripts/sol_translator_pc_preflight_v6.py', 'sha256': '2c69477aa8e5afda161c3b079233140d787d99fcccd211dc43fa7e9dc938b35e'}, {'bytes': 13665, 'path': 'scripts/sol_translator_prefix_train_v7.py', 'sha256': 'da861dce8a76232546d99ad1fa76dc5254973dfe983fbe6a11a4d96f13f40ebd'}, {'bytes': 3149, 'path': 'scripts/sol_translator_proof_contracts_v6.py', 'sha256': '0b60c5601821de08bacafa88288b91164a691a6708f3427a118dc35318489120'}, {'bytes': 14447, 'path': 'scripts/sol_translator_proof_v6.py', 'sha256': '54b235bc4ccc6067e0a7c70b67183bc78e34456bdc644ef995b4b9d63e7b3d23'}, {'bytes': 3306, 'path': 'scripts/sol_translator_provenance.py', 'sha256': '6e11dc3ea9d11a3c8ec3a84ebeada66ffaa4b19f6622205354f577b8f6f22934'}, {'bytes': 7704, 'path': 'scripts/sol_translator_runtime.py', 'sha256': 'aa46bbf22756ff366d4fcc23771f4e33403fe70977bc8822cde5817cc191efe8'}, {'bytes': 4524, 'path': 'scripts/sol_translator_runtime_fixed4_v6.py', 'sha256': '02c5dd5f81eeaf84378194f50101d6b87f5ef1bbf80e03935015f3182c3286b9'}, {'bytes': 5630, 'path': 'scripts/sol_translator_runtime_ordered_v10.py', 'sha256': 'b00c78f2bee11117ef0176d472e904158e9ce579e4004d23e18feb5d702c4e76'}, {'bytes': 4268, 'path': 'scripts/sol_translator_runtime_v6.py', 'sha256': 'bea978aa8f377f48b625b75e51352c93c821ad3577047fa752b4086f9193856b'}, {'bytes': 2937, 'path': 'scripts/sol_translator_v6_tests.py', 'sha256': '2ae5b518118ccb150f344d69a25c8c9f4c21537d0dcc76223afd8704b0aefd62'}, {'bytes': 1242, 'path': 'artifacts/sol-cloud-verifier-20260930/CORPUS1965-CAPABILITY256-R2-SEAL-REVIEW-v1.json', 'sha256': 'a2726e8252a45b3b70110f7fcb4481ed474a11ee3c37cf46d9ded6d55b6a230a'}], 'inventory_path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/run-capability256-v1/inventory/s0-loop-r2.json', 'job': 'sol-cloud-capability256-v1-s0-loop-train-r2', 'numeric16_loop_sha256': {'0': '6b63344aeeafaa2d51a6255c282b20822cca3872a47f0fe44f8fc35b74908584', '1': '4f0b2614cff2e6e10ea2e52b8765f6102d81099aad89538e99b5fd4c8b42b51e'}, 'pc_root': 'C:/Users/benja/sol-cloud-numeric-capability-v1', 'phase': 'train', 'plan': {'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/PLAN-v3.json', 'sha256': 'ceb522253ae98f80ad65c4102563a3a604b5d4dc70b4ffb671d4e59f4c1e8470'}, 'release': {'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/RELEASE-v2.json', 'sha256': 'e82c801f2f858b712a570a18690682340a1d621706ef1ab5e8688ddcad172e69'}, 'run_namespace': 'run-capability256-v1', 'runner': {'path': 'scripts/sol_cloud_capability256_v1.py', 'sha256': 'dfeef09f14fdcd0a1987c38d6a89a560f4ef02159b732cd1665cf51e9fa39b01'}, 'schema': 'sol.cloud.capability256.mac-launch-spec.v1', 'seal': {'path': 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/SEAL-v7.json', 'sha256': '3fbc0e67deb805784599025067ab2e9b18f28784aa3d2387bee7c9831f4d263e'}, 'seed': 0}
root=pathlib.Path('C:/Users/benja/sol-cloud-numeric-capability-v1')
records=spec['files'];record_map={};staged=[];proof={'other_watcher_running_claims':[]}
def digest(data):return hashlib.sha256(data).hexdigest()
def pin(pin):
 path=pathlib.Path(pin['path']);path=path if path.is_absolute() else root/path
 assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
 data=path.read_bytes();assert digest(data)==pin['sha256'];return path,json.loads(data)
stage='read-only-package'
try:
 assert platform.system()=='Windows' and sys.version_info[:3]==(3,10,9),'actual PC runtime differs'
 assert root.is_dir() and not root.is_symlink(),'owned root missing'
 for r in records:
  p=root.joinpath(*pathlib.PurePosixPath(r['path']).parts)
  assert p.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
  b=p.read_bytes();assert len(b)==r['bytes'] and digest(b)==r['sha256'],r['path']
  record_map[r['path']]=p;staged.append((p,r['sha256'],len(b)))
 plan_path,plan=pin(spec['plan']);seal_path,seal=pin(spec['seal']);release_path,release=pin(spec['release'])
 runner_path=record_map[spec['runner']['path']]
 stage='exact-native-and-resource-gates'
 helper_path=record_map['scripts/sol_cloud_queue_recovery_v1.py']
 helper_spec=importlib.util.spec_from_file_location('_capability_queue_recovery',helper_path)
 helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
 file_pins=[{key:r[key] for key in ('path','sha256','bytes')} for r in records]
 required=helper.packaged_runtime_pins(spec,plan,seal,release)
 package_smoke=helper.package_smoke(root,file_pins,required_pins=required)
 # Native import/help smoke is CPU-only and runs before resource snapshot or runner.
 import_code="import importlib.util,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); s=importlib.util.spec_from_file_location('_capability_runner_smoke',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(json.dumps({'imported':True,'root':str(m.ROOT)}))"
 imported=subprocess.run([sys.executable,'-X','utf8','-B','-c',import_code,str(runner_path)],
  cwd=str(root),capture_output=True,text=True,timeout=20)
 print(json.dumps({'stage':'native_import','returncode':imported.returncode,'stdout':imported.stdout[:65536],'stderr':imported.stderr[:65536]}),flush=True)
 if imported.returncode or len(imported.stdout)>65536 or len(imported.stderr)>65536:
  raise RuntimeError('native runner import smoke failed')
 help_run=subprocess.run([sys.executable,'-X','utf8','-B',str(runner_path),'--help'],
  cwd=str(root),capture_output=True,text=True,timeout=20)
 print(json.dumps({'stage':'native_help','returncode':help_run.returncode,'stdout':help_run.stdout[:65536],'stderr':help_run.stderr[:65536]}),flush=True)
 if (help_run.returncode or '--phase' not in help_run.stdout or '--final-freeze-sha256' not in help_run.stdout
     or len(help_run.stdout)>65536 or len(help_run.stderr)>65536):
  raise RuntimeError('native runner CLI help smoke failed')
 native_smoke={'python_version':platform.python_version(),'import_returncode':imported.returncode,
  'import_stdout_sha256':digest(imported.stdout.encode()),'import_stderr_sha256':digest(imported.stderr.encode()),
  'help_returncode':help_run.returncode,'help_stdout_sha256':digest(help_run.stdout.encode()),
  'help_stderr_sha256':digest(help_run.stderr.encode()),'model_calls':0,'optimizer_updates':0}
 # Snapshot only bounded Python metadata, GPU rows/app PIDs, free bytes and owned-path matches.
 def cmd(argv):
  p=subprocess.run(argv,capture_output=True,text=True,timeout=12)
  if p.returncode:raise RuntimeError('bounded resource probe returned nonzero')
  return p.stdout
 pytext=cmd(['powershell','-NoProfile','-Command',
  "Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('python.exe','pythonw.exe')} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress"])
 py=json.loads(pytext or '[]');py=[py] if isinstance(py,dict) else py
 by_pid={int(x['ProcessId']):x for x in py if isinstance(x,dict) and str(x.get('ProcessId','')).isdecimal()}
 lineage={os.getpid()};cursor=os.getpid()
 while cursor in by_pid:
  parent=int(by_pid[cursor].get('ParentProcessId') or 0)
  if parent<=0 or parent in lineage:break
  lineage.add(parent);cursor=parent
 py_summary=[];project_conflicts=[]
 for x in py:
  if not isinstance(x,dict):raise RuntimeError('malformed Python process inventory')
  pid=int(x['ProcessId']);cmdline=str(x.get('CommandLine') or '').lower();exe=str(x.get('ExecutablePath') or '').lower()
  owned=(str(root).lower() in cmdline or 'sol_cloud_capability256_v1.py' in cmdline)
  py_summary.append({'pid':pid,'parent_pid':x.get('ParentProcessId'),'name':x.get('Name'),
                     'owned_command_match':owned,'bootstrap_lineage':pid in lineage,
                     'base_executable_match':exe==str(pathlib.Path(sys.executable)).lower()})
  if pid not in lineage or owned:project_conflicts.append({'pid':pid,'name':x.get('Name')})
 if project_conflicts:raise RuntimeError('unreconciled Python process or project process already active')
 gpu=cmd(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'])
 gpu_rows=[[int(v.strip()) for v in row.split(',')] for row in gpu.strip().splitlines() if row.strip()]
 apps=cmd(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'])
 gpu_pids=[];gpu_app_memory={}
 for row in apps.strip().splitlines():
  if row.strip():
   parts=[part.strip() for part in row.split(',')]
   if len(parts)!=2 or not parts[0].isdecimal():raise RuntimeError('malformed essential GPU PID inventory')
   pid=int(parts[0]);gpu_pids.append(pid);gpu_app_memory[pid]=parts[1]
 pid_text=','.join(map(str,gpu_pids)) or '-1'
 name_text=cmd(['powershell','-NoProfile','-Command',
  "$ids=@("+pid_text+"); Get-CimInstance Win32_Process | Where-Object {$ids -contains $_.ProcessId} | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"])
 proc=json.loads(name_text or '[]');proc=[proc] if isinstance(proc,dict) else proc
 proc_by_pid={int(x['ProcessId']):x for x in proc if isinstance(x,dict) and str(x.get('ProcessId','')).isdecimal()}
 # This PC's audited WDDM baseline reports desktop/UI processes in nvidia-smi.
 # Unknown owners block; known graphics/browser applications do not claim the optimizer.
 graphics_names={'dwm.exe','oktaverify.exe','explorer.exe','crossdeviceresume.exe','widgetboard.exe',
  'searchhost.exe','startmenuexperiencehost.exe','msedgewebview2.exe','textinputhost.exe',
  'powertoys.advancedpaste.exe','powertoys.colorpickerui.exe','powertoys.fancyzones.exe',
  'powertoys.peek.ui.exe','powertoys.powerlauncher.exe','discord.exe','ivcam.exe','chrome.exe',
  'lively.exe','sharex.exe','applicationframehost.exe','systemsettings.exe','shellexperiencehost.exe',
  'shellhost.exe','edgegameassist.exe','lunar client.exe','msedge.exe','javaw.exe','claude.exe',
  'phoneexperiencehost.exe'}
 project_gpu=[];unknown_gpu=[];gpu_processes=[]
 for pid in gpu_pids:
  x=proc_by_pid.get(pid)
  if x is None:unknown_gpu.append({'pid':pid,'reason':'process name unavailable'});continue
  name=str(x.get('Name') or '').casefold();cmdline=str(x.get('CommandLine') or '').casefold()
  gpu_processes.append({'pid':pid,'name':x.get('Name'),'used_memory':gpu_app_memory.get(pid)})
  model_runtime=any(mark in (name+' '+cmdline) for mark in ('sol_cloud_capability256_v1.py',str(root).lower(),
   'lm studio','lmstudio','llama-server','ollama','vllm','text-generation','kobold','exllama','torchrun'))
  if name in ('python.exe','pythonw.exe') or model_runtime:
   project_gpu.append({'pid':pid,'name':x.get('Name')})
  elif name not in graphics_names:
   unknown_gpu.append({'pid':pid,'name':x.get('Name'),'reason':'not in audited desktop/UI baseline'})
  elif gpu_app_memory.get(pid)!='N/A':
   unknown_gpu.append({'pid':pid,'name':x.get('Name'),'used_memory':gpu_app_memory.get(pid),
                       'reason':'desktop/UI exception requires per-process N/A memory'})
 if project_gpu:raise RuntimeError('competing Python/model-runtime GPU owner already active')
 if unknown_gpu:raise RuntimeError('uncertain GPU process owner blocks exclusive-resource gate')
 if len(gpu_rows)!=1 or len(gpu_rows[0])!=4 or not 0<=gpu_rows[0][2]<3000 or not 0<=gpu_rows[0][1]<=100:
  raise RuntimeError('GPU resource values outside audited desktop baseline')
 if gpu_rows[0][1]>0 and not gpu_pids:
  raise RuntimeError('GPU activity has no attributable process; owner is uncertain')
 # Device utilization is timing noise when reported PIDs are audited desktop/UI
 # processes with WDDM N/A memory; project and unknown owners already fail above.
 unit=65536
 if os.name=='nt':
  sectors,bytes_per_sector,free_clusters,total_clusters=(ctypes.c_ulong() for _ in range(4))
  if not ctypes.windll.kernel32.GetDiskFreeSpaceW('C:\\',ctypes.byref(sectors),ctypes.byref(bytes_per_sector),ctypes.byref(free_clusters),ctypes.byref(total_clusters)):
   raise RuntimeError('filesystem allocation-unit query failed')
  unit=sectors.value*bytes_per_sector.value
 if not 0<unit<=65536:raise RuntimeError('allocation unit exceeds sealed reserve')
 allocated=sum(((n+unit-1)//unit)*unit for _,_,n in staged)

 stage='read-only-complete'
except Exception as error:
 failure={'stage':stage,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(limit=5)}
else:
 failure=None
summary={'schema':'sol.cloud.capability256.readonly-preflight-probe.v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_job':spec['job'],'failure':failure,'C_free_bytes':shutil.disk_usage(root).free,'model_calls':0,'optimizer_calls':0,'PC_file_writes':0}
for key in ('py_summary','project_conflicts','gpu_rows','gpu_processes','project_gpu','unknown_gpu','native_smoke'):
 if key in globals():summary[key]=globals()[key]
failure_dir=root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/runner/failures'
summary['runner_failure_metadata']=[]
if failure_dir.is_dir():
 for p in sorted(failure_dir.glob('*.json'))[:16]:
  if p.is_file() and not p.is_symlink() and p.stat().st_size<=65536:
   b=p.read_bytes();r=json.loads(b)
   summary['runner_failure_metadata'].append({'name':p.name,'bytes':len(b),'sha256':digest(b),'record':{k:r[k] for k in ('stage','error_type','error','optimizer_updates','model_calls') if k in r}})
print(json.dumps(summary,sort_keys=True),flush=True)
