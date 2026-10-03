"""One fresh input-only panel against eight fixed terminal5120 checkpoints.

Preparation/import/--check are stdlib-only. No oracle path exists in generation
configuration. Original tokenization, pre-reader caches, calculator/four-loop
forward and native greedy decoder are reused without changes. All128 durable
native observations precede the independent, separately invoked gold scorer.
V2 changes only scoped eligibility metadata admission; historical incompleteness
is retained and specifically parent reviewed before release. V1 is preserved.
"""
import argparse
from collections import Counter
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

SCHEMA = 'cap256.fresh-terminal-generation-config.v2'
SCOPE_CLAIM = 'Novelty is checked only against the named authorized question metadata and the supplied 40 operand-pair exclusions. Historical question metadata is incomplete; global question and operand-pair novelty are not established.'
PARENT_SCOPED_REVIEW_PATH = 'artifacts/cap256-launch/contextual-input-compare-v1/FRESH-TERMINAL-EVAL-PREPARATION-v1/PARENT-SCOPED-REVIEW-v1.json'
SUPPORT_SHA = 'd36efeb821c7c30b0d01ab89d2e158602c3c9d198abbcce488ccf143fcfe8c09'
NATIVE_SUPPORT_SHA = 'c826c12983607a8d4897bbae9f961a1a109d507eeae65413da6f9eef3dbbed78'
INSPECTION_SHA = '39a1d6f0eec5c309f07dd0f019297b81d8e7f6348ee27d917b55ee5530322233'
TERMINAL_CLOSED_SHA = 'b704f654874dd23ed01a17aa8eea9dbf55d1a341c147a511d38930281cb2c369'
LR_CONFIG_SHA = 'ce272d57462dc5da45dc1d82d661c322397023fac7729cd5e2f7b4aa464a9b3f'
ORDER = [(seed,arm,condition,lr) for seed,arm in
    ((1,'contextual'),(0,'static'),(0,'contextual'),(1,'static'))
    for condition,lr in (('control',0.001),('low_lr',0.0001))]
CP_SHAS = ['4c3c410f99ae37a8f46d5de58af7b71d550d841d6ecd306d2a1c2c8199c1330d',
    '75d1592f4ef24771e5083d915a50deeeb35894f683c5678739d798bb0df8d9d5',
    '9b026f7246e5ffe1a3841da5b1f70437e212d724bb0ae111add42cbc99a85294',
    '4387ca2a72471ac000aef289458d5bd5dec1fc4d3c690ef87f344a377d8892d7',
    '49a350235164a7c2f4ccc2731358dc615cf8a25086abd32afe71e4c3bd44c001',
    '4a7d9c661bf6a2e14595cfc95b1750786c919a8eb8f3b4bbc6561b8a973675a0',
    'e97082e348b5f25007f2c6ba020c62116b75388cdac5bfd4e48f2c0b596e263c',
    'f994cd10a52052840e6d8b3bd2f68547ce8cb666bd401f31af954313ff930531']
COMPONENTS = ('core','reader','prefix','tool')
REGISTRY_FIELDS = {'id','index','value','char_span','token_indices','source','status'}
EXPECTED_COUNTS = {'native_generate_calls':128,'four_loop_core_calls':128,
    'fixed_latent_advances':512,'contextual_input_backbone_calls':16,
    'static_input_embedding_calls':16,'teacherforced_calls':0,'optimizer_updates':0,'backward_calls':0}
MIB = 1024**2
CONFIG_KEYS = {'schema','source_root','checkpoint_root','source_train_config','runner',
    'native_support','diagnostic_support','terminal_inspection','terminal_closure','endpoints',
    'inputs','exposure_receipt','scoped_policy','resource_gate','protocol','output_namespace','budget','dispatch_allowed'}


def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(MIB),b''):result.update(block)
    return result.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def read(path):return json.loads(Path(path).read_bytes())


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result);return result


def load_support(root,cfg):
    p=cfg['diagnostic_support']
    if p.get('sha256')!=SUPPORT_SHA:raise ValueError('exact qualified stdlib support required')
    root=Path(root).resolve();path=(root/p.get('path','')).resolve()
    if not path.is_relative_to(root)or not path.is_file()or sha(path)!=SUPPORT_SHA:
        raise ValueError('qualified support physical pin differs')
    return load_module('_fresh_terminal_readonly_support',path)


def load_native_support(root,cfg,support):
    if cfg['native_support'].get('sha256')!=NATIVE_SUPPORT_SHA:
        raise ValueError('unchanged original native evaluator helper required')
    return support.load_module('_fresh_terminal_original_native',support.pinned(root,cfg['native_support']))


def validate_budget(budget):
    keys={'evaluation_seconds','cache_seconds','cache_cap_bytes','new_output_bytes',
        'raw_cap_bytes','cuda_peak_reserved_cap_bytes','retained_global_CUDA_free_bytes','project_cap_bytes','retained_free_bytes',
        'aggregate_spend_usd_cap'}
    if (set(budget)!=keys or any(type(budget[k])is not int or budget[k]<=0 for k in keys-{'aggregate_spend_usd_cap'})
            or budget['evaluation_seconds']>1500 or budget['cache_seconds']>120 or budget['cache_seconds']>=budget['evaluation_seconds']
            or budget['cache_cap_bytes']>12845056 or budget['new_output_bytes']>48*MIB
            or budget['raw_cap_bytes']>4*MIB or budget['raw_cap_bytes']>budget['new_output_bytes']
            or budget['cuda_peak_reserved_cap_bytes']>8*1024**3
            or budget['retained_global_CUDA_free_bytes']!=2*1024**3
            or budget['project_cap_bytes']!=100000000000 or budget['retained_free_bytes']!=2*1024**3
            or budget['aggregate_spend_usd_cap']!='0.00'):
        raise ValueError('bounded proposed fresh evaluation budget required; separate resource gate authorizes it')


def validate_cuda_resources(peak,global_free,budget):
    if peak>budget['cuda_peak_reserved_cap_bytes']:raise RuntimeError('fresh CUDA reservation cap exceeded')
    if global_free<budget['retained_global_CUDA_free_bytes']:raise RuntimeError('fresh global CUDA free reserve exceeded')


def validate_input_packet(packet,native):
    if type(packet)is not dict or set(packet)!={'schema','rows'}or packet['schema']!='cap256.contextual-input.EVAL-inputs.v1':
        raise ValueError('strict question-only packet; target/operation/gold metadata forbidden')
    frames=packet['rows'];native.validate_inputs(frames)
    for frame in frames:
        if (any(set(entry)!=REGISTRY_FIELDS for entry in frame['numeric_registry'])
                or any(type(entry['index'])is not int or entry['index']!=i or entry['id']!='literal:%d'%i
                    for i,entry in enumerate(frame['numeric_registry']))):
            raise ValueError('only unchanged literal source registry fields allowed')
    return frames


def prepare_input_frame(row,tokenizer,tools,native):
    """CPU question-tokenization wiring, never accepts semantic oracle fields."""
    if type(row)is not dict or set(row)!={'id','question','pair_id'}:
        raise ValueError('opaque id/pair and original question only; oracle fields refused')
    if any(type(row[k])is not str or not row[k] for k in row):raise ValueError('nonempty input strings required')
    ids=tokenizer.encode(row['question'],add_special_tokens=False)
    if len(ids)>48 or tokenizer.eos_token_id!=7 or 7 in ids:
        raise ValueError('complete original question within48 tokens; no truncation or new EOS')
    frame={**row,'question_sha256':hashlib.sha256(row['question'].encode()).hexdigest(),
        'input_ids':[ids+[7]],'input_mask':[[True]*(len(ids)+1)],'notebook_ids':[[]],
        'notebook_mask':[[]],'numeric_registry':tools.build_registry(row['question'],tokenizer),
        'split_role':'EVAL','source_group':row['pair_id']}
    frame['frame_sha256']=canonical(frame)
    return frame


def validate_endpoint_packet(packet,inspection,closed):
    required={'schema','terminal_inspection','terminal_closure','endpoints'}
    if (type(packet)is not dict or set(packet)!=required or packet['schema']!='cap256.fresh-terminal-endpoints.v1'
            or packet['terminal_inspection']['sha256']!=INSPECTION_SHA
            or packet['terminal_closure']['sha256']!=TERMINAL_CLOSED_SHA
            or inspection.get('checkpoint_inspection_complete')is not True
            or inspection.get('status')!='PASSED' or inspection.get('config_sha256')!=LR_CONFIG_SHA
            or closed.get('closed')is not True or closed.get('status')!='CLOSED'
            or closed.get('config_sha256')!=LR_CONFIG_SHA):
        raise ValueError('exact all-eight terminal physical inspection and closure required')
    endpoints=packet['endpoints'];physical=inspection['final_checkpoints'];closures=closed['endpoints']
    if len(endpoints)!=8 or len(physical)!=8 or len(closures)!=8:
        raise ValueError('exact all-eight fixed terminal checkpoints required')
    for index,(e,(seed,arm,condition,lr),cp,record)in enumerate(zip(endpoints,ORDER,physical,closures)):
        expected_path='artifacts/train-contextual-lr-stability-v1/%s/seed%d/%s/final-resume.pt'%(condition,seed,arm)
        if (set(e)!={'seed','arm','condition','learning_rate','checkpoint'}
                or (e['seed'],e['arm'],e['condition'],e['learning_rate'])!=(seed,arm,condition,lr)
                or e['checkpoint']!={'path':expected_path,'sha256':CP_SHAS[index]}
                or (cp['seed'],cp['arm'],cp['condition'],cp['sha256'])!=(seed,arm,condition,CP_SHAS[index])
                or cp['inspection']['final_update']!=5120 or cp['inspection']['learning_rate']!=lr
                or (record['seed'],record['arm'],record['condition'],record['learning_rate'])!=(seed,arm,condition,lr)
                or record.get('completed_steps')!=5120 or record.get('checkpoint')!=e['checkpoint']
                or record.get('checkpoint_reload_verified')is not True
                or record.get('final_fingerprints')!=cp['inspection']['final_module_fingerprints']):
            raise ValueError('fixed terminal5120 order/hash/weights required; no intermediate selection')
    return endpoints


def validate_resource_gate(gate,cfg):
    if (type(gate)is not dict or set(gate)!={'schema','approved','budget','zero_spend','no_historical_budget_reuse'}
            or gate['schema']!='cap256.fresh-terminal-resource-gate.v1' or gate['approved']is not True
            or gate['budget']!=cfg['budget'] or gate['zero_spend']is not True
            or gate['no_historical_budget_reuse']is not True):
        raise ValueError('separate prospective current-run resource approval required')


def validate_metadata_pin(record):
    if (type(record)is not dict or set(record)!={'path','sha256'}or type(record['path'])is not str
            or not record['path']or Path(record['path']).is_absolute()or '..'in Path(record['path']).parts
            or type(record['sha256'])is not str or re.fullmatch('[0-9a-f]{64}',record['sha256'])is None):
        raise ValueError('strict metadata pin required')


def validate_scoped_policy(policy,input_pin,endpoint_pin):
    keys={'schema','inputs','endpoints','input_producer_qualification','input_producer_qualification_sha256',
        'question_metadata_catalogues','supplied_pair_exclusions_metadata','supplied_pair_exclusions_count',
        'missing_historical_scopes','parent_scoped_review','claim_scope'}
    if (type(policy)is not dict or set(policy)!=keys
            or policy['schema']!='cap256.fresh-terminal-scoped-eligibility-policy.v2'
            or policy['inputs']!=input_pin or policy['endpoints']!=endpoint_pin
            or policy['supplied_pair_exclusions_count']!=40 or type(policy['supplied_pair_exclusions_count'])is not int
            or policy['claim_scope']!=SCOPE_CLAIM):
        raise ValueError('exact scoped metadata policy required; no global novelty or ancestry claim')
    for field in ('inputs','endpoints','input_producer_qualification','supplied_pair_exclusions_metadata','parent_scoped_review'):
        validate_metadata_pin(policy[field])
    if (policy['input_producer_qualification_sha256']!=policy['input_producer_qualification']['sha256']
            or policy['parent_scoped_review']['path']!=PARENT_SCOPED_REVIEW_PATH):
        raise ValueError('specific physical qualification and allowed parent-review metadata binding required')
    catalogues=policy['question_metadata_catalogues'];missing=policy['missing_historical_scopes']
    if (type(catalogues)is not list or not catalogues or type(missing)is not list or not missing
            or any(type(v)is not str or not v for v in missing)or len(set(missing))!=len(missing)):
        raise ValueError('checked catalogue scope and incomplete historical metadata must be explicit')
    scopes=set()
    for entry in catalogues:
        if (type(entry)is not dict or set(entry)!={'scope_id','role','rows','metadata'}
                or type(entry['scope_id'])is not str or not entry['scope_id']or entry['scope_id']in scopes
                or entry['role']not in ('TRAIN','CONSUMED_EVAL','CONSUMED_DEV')
                or type(entry['rows'])is not int or entry['rows']<=0):
            raise ValueError('strict authorized question-metadata catalogue summary required')
        scopes.add(entry['scope_id']);validate_metadata_pin(entry['metadata'])


def validate_exposure_receipt(receipt,input_pin,frames,policy,parent_review):
    expected={'schema':'cap256.fresh-terminal-scoped-exposure-receipt.v2','status':'SCOPED_ELIGIBLE_PARENT_REVIEWED',
        'rows':16,'pairs':8,'inputs':input_pin,'questions_sha256s':[f['question_sha256']for f in frames],
        'independent_Luna_panel_checked':True,'source_identity_frozen':True,'input_producer_qualified':True,
        'semantic_and_gold_checks_independent':True,'new_panel_only':True,'model_outputs_seen_before_panel_freeze':False,
        'available_authorized_question_metadata_checked':True,
        'question_metadata_catalogues':policy['question_metadata_catalogues'],'question_collisions':0,
        'supplied_pair_exclusions_checked':40,'supplied_pair_collisions':0,
        'historical_question_metadata_incomplete':True,'global_operand_pair_novelty_verified':False,
        'reserved_or_blind_payloads_opened':False,'missing_historical_scopes':policy['missing_historical_scopes'],
        'parent_scoped_review':policy['parent_scoped_review']}
    if (type(receipt)is not dict or set(receipt)!=set(expected)
            or any(type(receipt.get(k))is not type(v)or receipt[k]!=v for k,v in expected.items())):
        raise ValueError('scoped fresh input gate incomplete or not specifically parent reviewed')
    core={k:v for k,v in receipt.items()if k not in ('status','parent_scoped_review')}
    review={'schema':'cap256.fresh-terminal-parent-scoped-review.v1','status':'APPROVED',
        'inputs':input_pin,'endpoints':policy['endpoints'],
        'input_producer_qualification':policy['input_producer_qualification'],
        'input_producer_qualification_sha256':policy['input_producer_qualification_sha256'],
        'receipt_core_sha256':canonical(core),
        'policy_core_sha256':canonical({k:v for k,v in policy.items()if k!='parent_scoped_review'}),
        'one_panel_once':True,
        'historical_question_metadata_incomplete':True,'global_operand_pair_novelty_verified':False,
        'reserved_or_blind_payloads_opened':False}
    if (type(parent_review)is not dict or set(parent_review)!=set(review)
            or any(type(parent_review.get(k))is not type(v)or parent_review[k]!=v for k,v in review.items())):
        raise ValueError('specific parent-scoped review must bind checked scope, inputs, eight checkpoints and actual CPU qualification')


def cpu_preflight(root,cfg,workerpath):
    root=Path(root).resolve()
    if set(cfg)!=CONFIG_KEYS or cfg['schema']!=SCHEMA:raise ValueError('positive generation-only config allowlist required')
    support=load_support(root,cfg);native=load_native_support(root,cfg,support)
    if support.pinned(root,cfg['runner'])!=Path(workerpath).resolve():raise ValueError('fresh generation worker self pin differs')
    validate_budget(cfg['budget'])
    source=Path(cfg['source_root']).resolve();checkpoints=Path(cfg['checkpoint_root']).resolve()
    if any(a==b or a.is_relative_to(b)or b.is_relative_to(a)for a,b in
            ((root,source),(root,checkpoints),(source,checkpoints))):
        raise ValueError('new generation, original source and terminal checkpoint roots must be separate siblings')
    if cfg['source_train_config']['sha256']!=support.TRAIN_CONFIG_SHA:raise ValueError('original frozen source recipe required')
    train=support.read(support.pinned(source,cfg['source_train_config']))
    if train['runner']['sha256']!=support.WORKER_SHA:raise ValueError('exact original question interface required')
    admission=support.read(support.pinned(source,train['source_admission']))
    if len(admission['files'])!=52 or admission.get('no_dataset_payload_admitted')is not True:
        raise ValueError('exact all52 original source code admission required')
    for relative,digest in admission['files'].items():
        if not relative.endswith('.py'):raise ValueError('source admission must contain code only')
        support.pinned(source,{'path':relative,'sha256':digest})
    # Only code/model path metadata is admitted. No old TRAIN/EVAL payloads,
    # teacher-forced labels or old comparison protocols are opened here.
    source_fields=('runner','resume_helpers','runtime_module','constructor_module','calculator_tools',
        'source_runner','storage_snapshot','linux_adapter','source_plan','path_map','source_admission')
    for key in source_fields:support.pinned(source,train[key])
    if cfg['terminal_inspection']['sha256']!=INSPECTION_SHA or cfg['terminal_closure']['sha256']!=TERMINAL_CLOSED_SHA:
        raise ValueError('fixed terminal evidence pins differ')
    inspection=support.read(support.pinned(root,cfg['terminal_inspection']))
    closed=support.read(support.pinned(checkpoints,cfg['terminal_closure']))
    packet=support.read(support.pinned(root,cfg['endpoints']))
    if packet['terminal_inspection']!=cfg['terminal_inspection']or packet['terminal_closure']!=cfg['terminal_closure']:
        raise ValueError('terminal packet evidence paths differ')
    endpoints=validate_endpoint_packet(packet,inspection,closed)
    for endpoint in endpoints:support.pinned(checkpoints,endpoint['checkpoint'])
    frames=validate_input_packet(support.read(support.pinned(root,cfg['inputs'])),native)
    exposure=support.read(support.pinned(root,cfg['exposure_receipt']))
    policy=support.read(support.pinned(root,cfg['scoped_policy']))
    validate_scoped_policy(policy,cfg['inputs'],cfg['endpoints'])
    parent_review=support.read(support.pinned(root,policy['parent_scoped_review']))
    validate_exposure_receipt(exposure,cfg['inputs'],frames,policy,parent_review)
    validate_resource_gate(support.read(support.pinned(root,cfg['resource_gate'])),cfg)
    protocol=support.read(support.pinned(root,cfg['protocol']))
    expected={'schema':'cap256.fresh-terminal-generation-protocol.v2','rows':16,'pairs':8,
        'terminal_update':5120,'native_calls':128,'max_new_tokens':32,'fixed_latent_loops':4,
        'teacherforced_calls':0,'optimizer_updates':0,'all128_frozen_before_any_gold_access':True,
        'inputs':cfg['inputs'],'endpoints':cfg['endpoints'],'exposure_receipt':cfg['exposure_receipt'],
        'scoped_policy':cfg['scoped_policy'],'exposure_scope_claim':SCOPE_CLAIM,
        'feature_identity_sha256':canonical(train['feature_identity']),
        'execution_order':[[s,a,c,lr]for s,a,c,lr in ORDER]}
    if type(protocol)is not dict or set(protocol)!=set(expected)or any(type(protocol[k])is not type(v)or protocol[k]!=v for k,v in expected.items()):
        raise ValueError('exact oracle-free generation protocol required')
    support.safe(root,cfg['output_namespace'])
    return {'schema':SCHEMA,'checked':True,'Torch_imported':False,'model_calls':0,'optimizer_updates':0,
        'backward_calls':0,'native_generation_calls':0,'gold_accessed':False,'panel_rows':16,
        'fixed_terminal_checkpoints':8,'terminal_update':5120,'protected_payloads_opened':0,
        'source_files':52,'expected_call_account':EXPECTED_COUNTS}


def validate_frozen_records(rows,frames,endpoints,frozen,raw_sha,config_sha,runner_sha):
    expected={'native_calls':128,'optimizer_updates':0,'teacherforced_examples':0,
        'gold_accessed':False,'all128_raw_frozen':True,'sha256':raw_sha,
        'generation_config_sha256':config_sha,'generation_runner_sha256':runner_sha,
        'checkpoint_bindings':endpoints}
    if len(rows)!=128 or any(type(frozen.get(k))is not type(v)or frozen[k]!=v for k,v in expected.items()):
        raise ValueError('complete raw128 freeze required before separate scoring')
    for i,row in enumerate(rows):
        endpoint=endpoints[i//16];frame=frames[i%16]
        identity={'call_index':i+1,'sequence_index':i,'physical_row_index':i%16,'phase':'EVAL',
            'id':frame['id'],'input_frame_sha256':frame['frame_sha256'],
            'checkpoint_sha256':endpoint['checkpoint']['sha256'],'config_sha256':config_sha,
            'runner_sha256':runner_sha,'native_generate_call_count':1,'total_advances':4,
            **{key:endpoint[key]for key in ('seed','arm','condition','learning_rate')}}
        if any(type(row.get(k))is not type(v)or row[k]!=v for k,v in identity.items()):
            raise ValueError('raw terminal/frame/native sequence binding differs')
    return True


def run(args):
    started=time.monotonic();root=Path(args.root).resolve();cfgpath=Path(args.config).resolve()
    if not cfgpath.is_relative_to(root)or sha(cfgpath)!=args.config_sha256:raise ValueError('owned generation config pin differs')
    cfg=read(cfgpath)
    if args.require_owned_stdin:
        print(json.dumps({'event':'actual-worker-ready','pid':os.getpid(),'ppid':os.getppid(),
            'sys_executable':sys.executable,'config_sha256':args.config_sha256}),flush=True)
        if sys.stdin.readline()!='BEGIN PINNED TRAIN DIAGNOSTIC\n':raise ValueError('qualified sole-driver owned release required')
    admission=cpu_preflight(root,cfg,Path(__file__))
    if args.check:print(json.dumps(admission,sort_keys=True),flush=True);return 0
    if cfg['dispatch_allowed']is not True or not args.require_owned_stdin:
        raise ValueError('no GPU dispatch until checked panel/resources/native driver readiness fixed')
    support=load_support(root,cfg);native=load_native_support(root,cfg,support)
    source=Path(cfg['source_root']).resolve();cp_root=Path(cfg['checkpoint_root']).resolve()
    train=support.read(support.pinned(source,cfg['source_train_config']))
    worker=support.load_module('_fresh_original_question_worker',support.pinned(source,train['runner']))
    helper=worker.load_helpers(source,train)
    paths={key:support.pinned(source,train[key])for key in ('source_admission','source_runner',
        'storage_snapshot','linux_adapter','source_plan','runtime_module','constructor_module','calculator_tools')}
    storage=helper.load_module(paths['storage_snapshot'],'_fresh_terminal_storage')
    adapter=support.load_module('_fresh_terminal_path_adapter',paths['linux_adapter'])
    mapper=adapter.PinnedPathMap(source,train['path_map'],train['path_map_identity_pins'])
    old=support.read(paths['source_plan']);binding=old['warmstart']['tuples']['0']
    model,provenance,bootstrap=native.resolve_lm_inputs(mapper,binding,train)
    frames=validate_input_packet(support.read(support.pinned(root,cfg['inputs'])),native)
    packet=support.read(support.pinned(root,cfg['endpoints']));endpoints=packet['endpoints']
    inspection=support.read(support.pinned(root,cfg['terminal_inspection']))
    closed=support.read(support.pinned(cp_root,cfg['terminal_closure']))
    out=support.safe(root,cfg['output_namespace']);budget=cfg['budget']
    if out.exists():raise ValueError('unique fresh output required; preserve partial panel exposure')
    project=Path(train['operational_preparation']['pc_project_root']).resolve()
    if not all(p.is_relative_to(project)for p in (root,source,cp_root)):
        raise ValueError('authorized project root differs')
    unit=storage.filesystem_allocation_unit(root);reserve=4*MIB
    def account():return{'package_bytes':storage.allocated_bytes(root,unit),
        'output_bytes':storage.allocated_bytes(out,unit)if out.exists()else 0,
        'project_bytes':storage.allocated_bytes(project,unit),'free_bytes':shutil.disk_usage(project).free}
    def guard(extra=0,check_wall=True):
        value=account()
        if (value['package_bytes']+extra+reserve>budget['new_output_bytes']
                or value['output_bytes']+extra>budget['raw_cap_bytes']
                or value['project_bytes']+extra+reserve>=budget['project_cap_bytes']
                or value['free_bytes']-extra-reserve<budget['retained_free_bytes']):
            raise RuntimeError('fresh output/project/free cap exceeded')
        if check_wall and time.monotonic()-started>budget['evaluation_seconds']:
            raise RuntimeError('fresh evaluation wall cap exceeded')
        return value
    def write(name,value,append=False,check_wall=True):
        if Path(name).name!=name:raise ValueError('direct owned receipt only')
        data=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        guard(len(data)+unit,check_wall)
        with (out/name).open('ab'if append else'xb')as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
    guard();out.mkdir(parents=True)
    identity={'schema':'cap256.fresh-terminal-native-generation.v1','config_sha256':args.config_sha256,
        'runner_sha256':cfg['runner']['sha256'],'generation_config_sha256':args.config_sha256,
        'generation_runner_sha256':cfg['runner']['sha256'],'input_manifest_sha256':cfg['inputs']['sha256'],
        'protocol_sha256':cfg['protocol']['sha256'],'terminal_inspection_sha256':INSPECTION_SHA,
        'checkpoint_closed':cfg['terminal_closure'],'gold_accessed':False,'optimizer_updates':0,
        'teacherforced_examples':0,'backward_calls':0,'terminal_update':5120}
    counts=Counter({key:0 for key in EXPECTED_COUNTS});phase='setup';observations=[];endpoint_runtime=[]
    inflight={'cache':False,'core':False,'native':False,'raw_write':False};attempts=Counter();durable_rows=0;active_query=None
    write('CLAIM.json',{**identity,'native_call_limit':128,'all8_terminal5120_fixed':True,
        'selection_or_fit_gate_used':False,'input_only_cache':True,'checkpoint_copies':0})
    try:
        sys.path[:0]=[str(source),str(source/'scripts')]
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection
        from sol_translator_english_ordered_v10 import load_ordered_english
        import sol_spatial_poc_ordered_v2
        import sol_spatial_poc_ordered_train_api_v2
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_decoder import FinalLatent
        from sol_translator_runtime import component_fingerprint
        runtime=importlib.import_module('scripts.cap256_launch.calculator_runtime_depth_compare')
        constructors=importlib.import_module('scripts.cap256_launch.fresh_core_calculator_constructor')
        tools=importlib.import_module('scripts.cap256_launch.calculator_tools')
        helper.verify_runtime_imports(source,support.read(paths['source_admission']),
            [train[k]for k in support.RUNTIME_PINS])
        sealed=helper.load_module(paths['source_runner'],'_fresh_terminal_sealed')
        torch.set_num_threads(2)
        allocation=worker.install_cuda_memory_budget(torch,budget['cuda_peak_reserved_cap_bytes'])
        torch.cuda.reset_peak_memory_stats()
        def gpu_guard():
            peak=torch.cuda.max_memory_reserved()
            global_free,global_total=torch.cuda.mem_get_info()
            validate_cuda_resources(peak,global_free,budget)
            return{'peak_reserved_bytes':peak,'reserved_bytes':torch.cuda.memory_reserved(),
                'allocated_bytes':torch.cuda.memory_allocated(),'global_free_bytes':global_free,'global_total_bytes':global_total}
        dec,tokenizer,loaded_provenance=load_ordered_english(str(model),str(provenance),str(bootstrap),'cuda')
        dec.eval().requires_grad_(False);lm=dec.lm;lm.eval().requires_grad_(False)
        worker.verify_feature_provenance(loaded_provenance,train['feature_identity'])
        worker.verify_lm_runtime(lm,tokenizer,train['feature_identity'],torch)
        gpu_guard()
        lm_before=component_fingerprint(lm)
        for frame in frames:
            rebuilt=prepare_input_frame({key:frame[key]for key in ('id','question','pair_id')},tokenizer,tools,native)
            if rebuilt!=frame:raise ValueError('exact original question tokens/EOS/masks/numeral spans differ')
        phase='input-only-feature-cache'
        inflight['cache']=True;attempts['feature_cache_builds']+=1
        caches,cache_receipt=native.final_feature_cache(lm,frames,worker,train['feature_identity'],
            torch,guard,gpu_guard,budget)
        inflight['cache']=False
        if cache_receipt['cache_bytes']>12845056:raise RuntimeError('complete49-token shared cache structural bound exceeded')
        counts['contextual_input_backbone_calls']=16;counts['static_input_embedding_calls']=16
        write('EVAL-QUESTION-FEATURE-CACHE.json',{**identity,**cache_receipt,
            'all_eight_terminal_closures_verified_before_extract':True,
            'shared_across_seeds_and_LR':True,'durable_tensor_copies':0})
        cache_hash=sha(out/'EVAL-QUESTION-FEATURE-CACHE.json')
        with torch.no_grad():
            for endpoint,cp_metadata,closed_endpoint in zip(endpoints,inspection['final_checkpoints'],closed['endpoints']):
                endpoint_started=time.monotonic();seed=endpoint['seed'];arm=endpoint['arm'];phase='endpoint-load'
                saved=torch.load(support.pinned(cp_root,endpoint['checkpoint']),map_location='cpu',weights_only=True)
                core=constructors.build_fresh_core('shallow',seed,'cuda')
                reader=HumanInputProjection(2048,state_width=256,hidden=32).to('cuda')
                tool=runtime.CalculatorPath(dim=256).to('cuda')
                modules=(('core',core),('reader',reader),('prefix',dec.adapter),('tool',tool))
                expected={'seed':seed,'arm':arm,'condition':endpoint['condition'],
                    'learning_rate':endpoint['learning_rate'],'update':5120,'schedule_cursor':5120,
                    'config_sha256':LR_CONFIG_SHA,'recipe':train['recipe'],
                    'constructor':core.constructor(),'tool_constructor':tool.constructor(),
                    'model_state_fingerprints':cp_metadata['inspection']['final_module_fingerprints']}
                if any(type(saved.get(k))is not type(v)or saved[k]!=v for k,v in expected.items()):
                    raise ValueError('exact terminal5120 checkpoint metadata/constructors differ')
                for name,module in modules:
                    module.load_state_dict(saved[name],strict=True);module.eval().requires_grad_(False)
                    if component_fingerprint(module)!=expected['model_state_fingerprints'][name]:
                        raise ValueError('terminal module physical fingerprint differs: '+name)
                if any(p.dtype!=torch.float32 for module in [lm]+[m for _,m in modules]for p in module.parameters()):
                    raise ValueError('unchanged full FP32 native evaluation required')
                support.restore_rng({k:saved[k]for k in ('torch_rng','cuda_rng','python_rng')},torch)
                del saved;phase='EVAL'
                endpoint_rng_before=support.rng_snapshot(torch)
                modes_before=[module.training for _,root_module in [('decoder',dec),('core',core),('reader',reader),('tool',tool)]for module in root_module.modules()]
                for index,frame in enumerate(frames):
                    query_wall_started=time.monotonic()
                    active_query={'sequence_index':len(observations),'physical_row_index':index,'id':frame['id'],
                        **{key:endpoint[key]for key in ('seed','arm','condition','learning_rate')}}
                    guard();gpu_guard()
                    if counts['four_loop_core_calls']>=128 or counts['native_generate_calls']>=128:
                        raise RuntimeError('fixed128 native/core call ceiling')
                    mask=torch.tensor(frame['input_mask'],device='cuda',dtype=torch.bool)
                    query,reader_seconds=worker.timed_call(lambda:worker.project_cached_question(reader,caches[arm][index],mask),torch)
                    def advance():
                        with ordered_attention_math():
                            return tool.forward(core,reader,lm,tokenizer,query,frame['numeric_registry'],mask)
                    gpu_guard();inflight['core']=True;attempts['four_loop_core_calls']+=1
                    output,core_seconds=worker.timed_call(advance,torch);counts['four_loop_core_calls']+=1;inflight['core']=False
                    if output['total_advances']!=4 or len(output['trace'])!=4 or output['auxiliary_terms']!=4*len(core.blocks):
                        raise ValueError('unchanged four fixed latent loops required')
                    counts['fixed_latent_advances']+=4;h=output['h']
                    gpu_guard();inflight['native']=True;attempts['native_generate_calls']+=1
                    observed,decode_seconds=worker.timed_call(lambda:sealed.observe_generation(dec,
                        FinalLatent(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),32),torch)
                    count=observed.get('native_generate_call_count')
                    if type(count)is not int or count<0:raise ValueError('native call count not observable')
                    counts['native_generate_calls']+=count;inflight['native']=False
                    gpu_guard()
                    feature=cache_receipt['features'][arm]['records'][index]
                    row={**identity,**{key:endpoint[key]for key in ('seed','arm','condition','learning_rate')},
                        'phase':'EVAL','id':frame['id'],'call_index':len(observations)+1,
                        'sequence_index':len(observations),'physical_row_index':index,
                        'checkpoint_sha256':endpoint['checkpoint']['sha256'],
                        'input_frame_sha256':frame['frame_sha256'],'frame_sha256':frame['frame_sha256'],
                        'feature_cache_receipt_sha256':cache_hash,'question_feature_key_sha256':feature['key_sha256'],
                        'question_features_sha256':feature['features_sha256'],'predicted_trace':output['trace'],
                        'routing':output['routing'],'total_advances':4,**observed,
                        'performance':{'reader_seconds':reader_seconds,'core_four_loop_seconds':core_seconds,
                            'total_answer_seconds':time.monotonic()-query_wall_started,
                            'query_wall_scope':'Whole query from pre-guard/preparation through completed native output; excludes raw serialization/write/fsync.',
                            'output_decoding_seconds':decode_seconds,'original_question_cache_hit':True,
                            'original_question_backbone_forward_calls':0,'memory':worker.performance_snapshot(torch)}}
                    inflight['raw_write']=True
                    write('EVAL-OBSERVATIONS.jsonl',row,True,False)
                    durable_rows+=1;observations.append(row);inflight['raw_write']=False
                    active_query=None
                    if count!=1 or observed.get('native_call_contract_valid')is not True or observed.get('generation_error')is not None:
                        raise ValueError('normal single greedy generation failed; preserve recorded output')
                if any(component_fingerprint(module)!=expected['model_state_fingerprints'][name]for name,module in modules):
                    raise ValueError('terminal module changed during fresh inference')
                endpoint_rng_after=support.rng_snapshot(torch)
                modes_after=[module.training for _,root_module in [('decoder',dec),('core',core),('reader',reader),('tool',tool)]for module in root_module.modules()]
                if not helper.state_equal(endpoint_rng_before,endpoint_rng_after,torch)or modes_before!=modes_after:
                    support.restore_rng(endpoint_rng_before,torch)
                    raise ValueError('native fresh inference changed RNG or module modes')
                support.pinned(cp_root,endpoint['checkpoint'])
                endpoint_runtime.append({**{key:endpoint[key]for key in ('seed','arm','condition','learning_rate')},
                    'rows':16,'checkpoint':endpoint['checkpoint'],'weights_unchanged':True,
                    'inference_RNG_unchanged':True,'module_modes_unchanged':True,
                    'RNG_before_sha256':support.tree_digest(endpoint_rng_before,torch),
                    'RNG_after_sha256':support.tree_digest(endpoint_rng_after,torch),
                    'wall_seconds':time.monotonic()-endpoint_started})
                del modules,core,reader,tool,query,output,h
        if dict(counts)!=EXPECTED_COUNTS:raise ValueError('exact named input/core/native/no-training counts differ')
        if component_fingerprint(lm)!=lm_before or any(p.grad is not None for p in lm.parameters()):
            raise ValueError('frozen original LM state/gradients changed')
        guard();gpu_guard();phase='raw128-freeze';raw_hash=sha(out/'EVAL-OBSERVATIONS.jsonl')
        frozen={**identity,'schema':'cap256.fresh-terminal-raw128-frozen.v1','sha256':raw_hash,
            'native_calls':128,'all128_raw_frozen':True,'all128_raw_frozen_before_any_gold_access':True,
            'gold_scoring_started':False,'fit_gate_used':False,'checkpoint_bindings':endpoints,
            'model_call_account':dict(counts),'LM_unchanged':True,'all_endpoint_weights_unchanged':True}
        validate_frozen_records(observations,frames,endpoints,frozen,raw_hash,args.config_sha256,cfg['runner']['sha256'])
        write('EVAL-OBSERVATIONS-FROZEN.json',frozen)
        cpu_preflight(root,cfg,Path(__file__))
        result={**identity,'schema':'cap256.fresh-terminal-generated-closed.v1','closed':True,
            'status':'FROZEN-ALL128-NATIVE-OUTPUTS','native_calls':128,'all128_raw_frozen':True,
            'gold_scoring_started':False,'fit_gate_used':False,'raw_sha256':raw_hash,
            'frozen_sha256':sha(out/'EVAL-OBSERVATIONS-FROZEN.json'),'checkpoint_bindings':endpoints,
            'input_pin':cfg['inputs'],'endpoint_runtime':endpoint_runtime,'model_call_account':dict(counts),
            'counted_core_plus_contextual_backbone_forwards':144,
            'count_convention':'128 four-loop core calls plus16 contextual input backbone calls; static16 embedding lookups and128 native generation calls separately reported; native internal LM forwards excluded.',
            'LM_unchanged':True,'all_endpoint_weights_unchanged':True,'checkpoint_bytes_unchanged':True,
            'allocation_budget':allocation,'wall_seconds':time.monotonic()-started,'output_account':account()}
        write('GENERATED-CLOSED.json',result)
        print(json.dumps({'event':'fresh-terminal128-raw-frozen','native_calls':128,
            'raw_sha256':raw_hash,'frozen_sha256':result['frozen_sha256'],
            'closed_sha256':sha(out/'GENERATED-CLOSED.json')}),flush=True)
        return 0
    except Exception as error:
        try:write('FAILED.json',{**identity,'phase':phase,'error':type(error).__name__+': '+str(error),
            'model_call_account':dict(counts),'counter_scope':'Completed helper returns and observed native calls only; failure accounting is incomplete.',
            'accounting_complete':False,'actual_counters_known':not any(inflight[k]for k in ('cache','core','native')),
            'attempted_helper_calls':dict(attempts),'inflight':inflight,'durable_raw_rows_confirmed':durable_rows,
            'active_query':active_query,'active_query_wall_seconds':None if active_query is None else time.monotonic()-query_wall_started,
            'raw_partial_write_or_durability_unknown':inflight['raw_write'],'gold_accessed':False,
            'fresh_status':'ACCESS_ATTEMPTED_PRESERVE_ALL','evidence_preserved':True},check_wall=False)
        except Exception as receipt_error:
            print(json.dumps({'event':'fresh-failure-receipt-blocked','primary_error':str(error),
                'receipt_error':str(receipt_error)}),flush=True)
        raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--config',required=True)
    p.add_argument('--config-sha256',required=True);p.add_argument('--require-owned-stdin',action='store_true')
    p.add_argument('--check',action='store_true');return run(p.parse_args())


if __name__=='__main__':sys.exit(main())
