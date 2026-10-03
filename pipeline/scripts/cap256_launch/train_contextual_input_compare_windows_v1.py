"""Windows port of the matched fresh-reader/core question-feature comparison.

TRAIN32 only. Static embeddings or the pinned LFM2 final post-norm token
states enter the same thin reader. Calculator returns retain static lexical
encoding through that shared reader. Output training retains prefix gradients.
This worker owns no supervisor, allocation, network access or fresh EVAL panel.
"""
import argparse
from collections import Counter
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import shutil
import sys
import time

UPDATES = 1024
ARMS = ('static', 'contextual')
READER_SEED_OFFSET = 200000
TOOL_SEED_OFFSET = 100000
MODEL_ID = 'LiquidAI/LFM2.5-1.2B-Instruct'
MODEL_REVISION = '0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
TRAIN32_FRAMES_SHA256 = '0447bfca6a5ba7ceed7c052903bba493a0d2fb2b09c44eeaa75dc16e2b283840'
RECIPE = {
    'batch':1, 'dim':256, 'rounds':4, 'experts':8, 'active':2,
    'physical_core':{'arm':'shallow','blocks':2,'hidden':1024},
    'fresh_core':True, 'fresh_reader':True, 'optimizer_reset':True,
    'reader':{'lm_width':2048,'hidden':32,'state_width':256,'parameters':78112},
    'reader_initialization':'isolated-CPU-seed-200000-plus-seed',
    'core_initialization':'existing-fresh-shallow-constructor-matched-seed',
    'prefix_source':'matched-original-loop40-update10240-parent-prefix-only',
    'tool_seed_offset':TOOL_SEED_OFFSET,
    'training_RNG':'restore-original-matched-parent-after-all-construction-and-cache',
    'reader_trainable':True, 'prefix_trainable':True, 'LM_frozen':True,
    'halt_frozen':True, 'full_FP32':True,
    'normalization':'existing-block-preLN-plain-residuals-existing-outer-ln_state',
    'extra_stabilizer':False, 'expert_initialization':'equal-clones-current-zero-router',
    'objective':'final-numeric-CE-plus-mean4-action-CE-plus-eligible-loop-mean2-pointer-CE',
    'loss_weights':{'final_CE':1,'action_CE':1,'pointer_CE':1,'sparse_auxiliary':0},
    'optimizer':{'name':'AdamW','lr':0.001,'weight_decay':0,'betas':[0.9,0.999],'eps':1e-8,'clip_norm':1},
    'question_feature_modes':list(ARMS),
    'contextual_layer':'model.last_hidden_state-final-post-embedding_norm',
    'input_sequence':'original-question-token-IDs-plus-observed-EOS-no-template-no-crop',
    'input_cache':'frozen-pre-reader-only-exact-model-input-mask-position-dtype-pins',
    'calculator_return_encoding':'unchanged-static-canonical-single-numeric-token-same-reader',
    'output_conditioning':'existing-thin-prefix-and-native-decoder-output-gradients-enabled',
    'predicted_calls_only':True, 'calls_per_loop_max':1, 'calls_total_max':4,
    'original_literal_max':8, 'reserved_tool_pairs':4,
    'additional_updates':UPDATES, 'TRAIN_rows':32, 'TRAIN_pairs':16,
    'item_exposure':32,
    'case_exposure':{'carry':256,'no_carry':256,'borrow':256,'no_borrow':256},
    'checkpoint_updates':[UPDATES], 'midpoint_checkpoint':False,
    'native_TRAIN':'one-normal-native-answer-per-frozen-TRAIN-row-after-final-checkpoint',
    'fresh_access':False, 'no_additional_probe':True,
}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def load_helpers(root,cfg):
    pin=cfg['resume_helpers']; path=(root/pin['path']).resolve()
    if (pin['path']!='scripts/cap256_launch/train_primitive_curriculum_v2.py'
            or not path.is_relative_to(root) or digest(path)!=pin['sha256']):
        raise ValueError('exact root/hash-pinned stdlib resume helpers required')
    spec=importlib.util.spec_from_file_location('_contextual_resume_helpers',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def validate_feature_identity(identity):
    required={'schema','model_id','revision','model_files','tokenizer_files','runtime',
        'model_code_sha256','configuration_code_sha256','worker_sha256',
        'dtype','feature_width','contextual_layer','attention_implementation',
        'special_token_ids','cache_protocol'}
    if (type(identity)is not dict or set(identity)!=required
            or identity['schema']!='cap256.question-feature-identity.v1'
            or identity['model_id']!=MODEL_ID or identity['revision']!=MODEL_REVISION
            or identity['dtype']!='float32' or identity['feature_width']!=2048
            or identity['contextual_layer']!=RECIPE['contextual_layer']
            or identity['special_token_ids']!={'bos':1,'eos':7,'pad':0}
            or identity['cache_protocol']!='ordered-full-question-causal-no-past-no-cache-pre-reader-v1'
            or identity['attention_implementation']not in ('eager','sdpa')):
        raise ValueError('exact fixed final-layer FP32 LFM2 input identity required')
    for name in ('model_code_sha256','configuration_code_sha256','worker_sha256'):
        if type(identity[name])is not str or not re.fullmatch('[0-9a-f]{64}',identity[name]):
            raise ValueError('exact installed-code/worker digest required')
    for name in ('model_files','tokenizer_files'):
        if (type(identity[name])is not dict or not identity[name]
                or any(type(k)is not str or not k or type(v)is not str
                    or not re.fullmatch('[0-9a-f]{64}',v) for k,v in identity[name].items())):
            raise ValueError('complete model/tokenizer file hashes required')
    if (not {'config.json','model.safetensors'}<=identity['model_files'].keys()
            or not {'tokenizer.json','tokenizer_config.json','special_tokens_map.json'}<=identity['tokenizer_files'].keys()
            or type(identity['runtime'])is not dict
            or set(identity['runtime'])!={'torch','transformers','safetensors'}
            or any(type(v)is not str or not v for v in identity['runtime'].values())):
        raise ValueError('exact runtime and tokenizer closure required')


def question_feature_key(frame,arm,feature_identity):
    """Only original inputs enter the cache key; labels/answer metadata do not."""
    validate_feature_identity(feature_identity)
    if arm not in ARMS: raise ValueError('fixed static/contextual feature mode required')
    ids=frame.get('input_ids');mask=frame.get('input_mask')
    if (type(ids)is not list or len(ids)!=1 or type(ids[0])is not list
            or not 1<=len(ids[0])<=49 or any(type(v)is not int or not 0<=v<65536 for v in ids[0])
            or type(mask)is not list or len(mask)!=1 or type(mask[0])is not list
            or len(mask[0])!=len(ids[0]) or any(type(v)is not bool for v in mask[0])
            or not all(mask[0]) or ids[0][-1]!=7 or 7 in ids[0][:-1]
            or type(frame.get('question'))is not str or not frame['question']
            or frame.get('question_sha256')!=hashlib.sha256(frame['question'].encode()).hexdigest()):
        raise ValueError('complete original ordered question IDs, observed EOS and mask required')
    return {'schema':'cap256.question-feature-key.v1','arm':arm,
        'feature_identity':feature_identity,'question_sha256':frame['question_sha256'],
        'input_ids':ids,'input_mask':mask,'position_ids':[list(range(len(ids[0])))],
        'past_key_values':None,'use_cache':False,'output_hidden_states':False,
        'output_attentions':False,'return_dict':True,
        'layer':'embedding' if arm=='static' else feature_identity['contextual_layer']}


def verify_lm_runtime(lm,tokenizer,identity,torch_api):
    validate_feature_identity(identity)
    import importlib.metadata
    if type(lm).__name__!='Lfm2ForCausalLM' or type(lm.model).__name__!='Lfm2Model':
        raise ValueError('same pinned LFM2 causal decoder/backbone object required')
    if (lm.config.hidden_size!=2048 or lm.config.num_hidden_layers!=16
            or getattr(lm.config,'_attn_implementation',None)!=identity['attention_implementation']
            or lm.model.embed_tokens is not lm.get_input_embeddings()
            or lm.training or lm.model.training or any(p.requires_grad for p in lm.parameters())
            or any(p.dtype!=torch_api.float32 for p in lm.parameters())):
        raise ValueError('frozen FP32 original LM architecture/runtime differs')
    if ({'bos':tokenizer.bos_token_id,'eos':tokenizer.eos_token_id,'pad':tokenizer.pad_token_id}
            !=identity['special_token_ids']): raise ValueError('observed tokenizer BOS/EOS/PAD differs')
    for package,expected in identity['runtime'].items():
        if importlib.metadata.version(package)!=expected: raise ValueError('exact package version differs: '+package)
    modeling=importlib.import_module(type(lm).__module__)
    configuration=importlib.import_module(type(lm.config).__module__)
    if (digest(modeling.__file__)!=identity['model_code_sha256']
            or digest(configuration.__file__)!=identity['configuration_code_sha256']):
        raise ValueError('installed LFM2 implementation differs from feature pin')


def verify_feature_provenance(provenance,identity):
    expected={**identity['model_files'],**identity['tokenizer_files']}
    if (provenance.get('model_id')!=identity['model_id']
            or provenance.get('revision')!=identity['revision']
            or provenance.get('files')!=expected):
        raise ValueError('feature model/tokenizer bytes differ from verified frozen loader provenance')


def build_fresh_reader(torch_api,reader_factory,seed,device):
    if type(seed)is not int or seed not in (0,1): raise ValueError('matched seeds0/1 required')
    # CPU construction makes the seed independent of the target CUDA count.
    with torch_api.random.fork_rng(devices=[]):
        torch_api.random.default_generator.manual_seed(READER_SEED_OFFSET+seed)
        reader=reader_factory(2048,state_width=256,hidden=32)
    if sum(p.numel() for p in reader.parameters())!=78112:
        raise ValueError('exact existing thin-reader layout required')
    return reader.to(device)


def tensor_digest(tensor):
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def timed_call(function,torch_api):
    """Device work is completed on both timing boundaries; no extra forward."""
    torch_api.cuda.synchronize();started=time.perf_counter()
    result=function();torch_api.cuda.synchronize()
    return result,time.perf_counter()-started


def performance_snapshot(torch_api):
    process={'peak_resident_bytes':None,'peak_source':'unavailable','resident_bytes':None}
    try:
        import resource
    except ModuleNotFoundError:
        # CPU contract verification also runs on Windows, where this optional
        # Unix module does not exist. Unavailable RAM is an explicit value.
        resource=None
    if resource is not None:
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        process.update(peak_resident_bytes=int(peak if sys.platform=='darwin' else peak*1024),
            peak_source='resource.getrusage.ru_maxrss')
    status=Path('/proc/self/status')
    if sys.platform.startswith('linux') and status.is_file():
        for line in status.read_text().splitlines():
            if line.startswith('VmRSS:'): process['resident_bytes']=int(line.split()[1])*1024
            elif line.startswith('VmHWM:'):
                process.update(peak_resident_bytes=int(line.split()[1])*1024,
                    peak_source='/proc/self/status.VmHWM')
    device_free,device_total=torch_api.cuda.mem_get_info()
    return {'cuda_process_allocated_bytes':torch_api.cuda.memory_allocated(),
        'cuda_process_reserved_bytes':torch_api.cuda.memory_reserved(),
        'cuda_process_peak_allocated_bytes':torch_api.cuda.max_memory_allocated(),
        'cuda_process_peak_reserved_bytes':torch_api.cuda.max_memory_reserved(),
        'cuda_device_total_memory_bytes':torch_api.cuda.get_device_properties(torch_api.cuda.current_device()).total_memory,
        'cuda_device_global_free_bytes':device_free,'cuda_device_global_total_bytes':device_total,
        'cuda_device_global_used_bytes':device_total-device_free,
        'process_cuda_scope':'current-process-PyTorch-allocator-excluding-driver-context-and-other-processes',
        'process_RAM':process}


def install_cuda_memory_budget(torch_api, cap_bytes):
    """Install the Windows allocator cap before any model/tensor allocation."""
    if type(cap_bytes) is not int or not 0 < cap_bytes <= 12 * 1024 ** 3:
        raise ValueError('explicit positive Windows CUDA cap at most12GiB required')
    if torch_api.cuda.memory_allocated(0) or torch_api.cuda.memory_reserved(0):
        raise RuntimeError('CUDA tensors/reservation predate the allocator cap')
    total = torch_api.cuda.get_device_properties(0).total_memory
    if type(total) is not int or total <= 0 or cap_bytes > total:
        raise ValueError('actual CUDA device cannot admit the requested allocator cap')
    if torch_api.cuda.memory_allocated(0) or torch_api.cuda.memory_reserved(0):
        raise RuntimeError('CUDA tensor allocation occurred during device qualification')
    fraction = cap_bytes / total
    torch_api.cuda.set_per_process_memory_fraction(fraction, device=0)
    return {'cuda_allocator_cap_bytes': cap_bytes, 'cuda_device_total_memory_bytes': total,
        'per_process_memory_fraction': fraction, 'installed_before_tensor_allocation': True}


def extract_question_features(lm,ids,mask,arm,torch_api):
    """Frozen extraction only; caller projects with the trainable reader later."""
    if arm not in ARMS: raise ValueError('static/contextual only')
    if lm.training or any(p.requires_grad for p in lm.parameters()):
        raise ValueError('frozen eval-mode LM required before feature extraction')
    with torch_api.no_grad():
        if arm=='static': features=lm.get_input_embeddings()(ids)
        else:
            positions=torch_api.arange(ids.shape[1],device=ids.device,dtype=torch_api.long)[None,:]
            features=lm.model(input_ids=ids,attention_mask=mask.long(),position_ids=positions,
                past_key_values=None,use_cache=False,output_hidden_states=False,
                output_attentions=False,return_dict=True).last_hidden_state
        if (tuple(features.shape)!=(1,ids.shape[1],2048) or features.dtype!=torch_api.float32
                or features.requires_grad or not bool(torch_api.isfinite(features).all())):
            raise ValueError('finite detached FP32 full token features required')
        return features.detach()


def project_cached_question(reader,features,mask):
    # Intentionally outside no_grad: reader parameters must receive gradients.
    return reader(features,mask)


def build_question_feature_cache(lm,frames,arm,identity,torch_api,*,device,
        guard,max_seconds,max_bytes,gpu_guard):
    if (type(frames)is not list or len(frames)!=32
            or any(frame.get('split_role')!='TRAIN' for frame in frames)):
        raise ValueError('only exact32 TRAIN question features admitted by training cache builder')
    started=time.monotonic();result=[];records=[];bytes_used=0
    for frame in frames:
        key=question_feature_key(frame,arm,identity);guard();gpu_guard()
        if time.monotonic()-started>max_seconds: raise RuntimeError('input cache wall cap exceeded')
        ids=torch_api.tensor(key['input_ids'],device=device,dtype=torch_api.long)
        mask=torch_api.tensor(key['input_mask'],device=device,dtype=torch_api.bool)
        feature,encoding_seconds=timed_call(lambda:extract_question_features(lm,ids,mask,arm,torch_api),torch_api)
        bytes_used+=feature.numel()*feature.element_size()
        if bytes_used>max_bytes or time.monotonic()-started>max_seconds:
            raise RuntimeError('input cache byte/wall cap exceeded')
        records.append({'id':frame['id'],'key_sha256':canonical(key),
            'features_sha256':tensor_digest(feature),'shape':list(feature.shape),'bytes':feature.numel()*feature.element_size(),
            'cold_original_question_encoding_seconds':encoding_seconds,'cache_hit':False,
            'backbone_forward_calls':1 if arm=='contextual' else 0,
            'memory':performance_snapshot(torch_api)})
        result.append(feature);gpu_guard()
    account={'TRAIN_input_contextual_backbone':len(frames)} if arm=='contextual' else {'TRAIN_input_static_embedding':len(frames)}
    return result,{'schema':'cap256.question-feature-cache.v1','arm':arm,
        'rows':len(frames),'records':records,'feature_identity':identity,
        'cache_bytes':bytes_used,'cache_seconds':time.monotonic()-started,
        'pre_reader_only':True,'input_only':True,'gold_accessed':False,
        'model_call_account':account,'backbone_forward_calls':len(frames) if arm=='contextual' else 0,
        'reused':False}


def prepare_question_feature_cache(lm,frames,arm,identity,torch_api,*,device,
        directory,guard,max_seconds,max_bytes,gpu_guard):
    """Reuse exact frozen features across seeds; no projected reader states saved."""
    if (type(frames)is not list or len(frames)!=32
            or any(frame.get('split_role')!='TRAIN' for frame in frames)):
        raise ValueError('shared training cache is TRAIN32-only')
    keys=[question_feature_key(frame,arm,identity) for frame in frames]
    key_digest=canonical(keys);directory=Path(directory)
    path=directory/(arm+'-'+key_digest+'.pt')
    manifest=directory/(arm+'-'+key_digest+'.json')
    started=time.monotonic()
    if path.exists() or manifest.exists():
        if not path.is_file() or not manifest.is_file():
            raise RuntimeError('partial feature cache preserved; explicit operational recovery required')
        receipt=json.loads(manifest.read_bytes())
        if (receipt.get('cache_key_sha256')!=key_digest or receipt.get('arm')!=arm
                or receipt.get('feature_identity')!=identity or receipt.get('rows')!=32
                or receipt.get('cache_file_sha256')!=digest(path)):
            raise ValueError('saved cache identity/file digest differs')
        if path.stat().st_size>max_bytes+1024**2: raise RuntimeError('saved cache storage cap exceeded')
        guard();gpu_guard()
        payload=torch_api.load(path,map_location=device,weights_only=True)
        if (type(payload)is not dict or set(payload)!={'cache_key_sha256','features'}
                or payload['cache_key_sha256']!=key_digest
                or type(payload['features'])is not list or len(payload['features'])!=32
                or len(receipt.get('records',[]))!=32):
            raise ValueError('saved cache typed payload differs')
        features=payload['features'];actual_bytes=0
        for frame,key,feature,record in zip(frames,keys,features,receipt['records']):
            if (tuple(feature.shape)!=(1,len(frame['input_ids'][0]),2048)
                    or feature.dtype!=torch_api.float32 or feature.requires_grad
                    or not bool(torch_api.isfinite(feature).all())
                    or record.get('id')!=frame['id'] or record.get('key_sha256')!=canonical(key)
                    or record.get('features_sha256')!=tensor_digest(feature)):
                raise ValueError('saved exact frozen feature values differ')
            actual_bytes+=feature.numel()*feature.element_size()
        if actual_bytes!=receipt['cache_bytes'] or actual_bytes>max_bytes:
            raise RuntimeError('saved cache byte accounting differs')
        if time.monotonic()-started>max_seconds: raise RuntimeError('cache reload wall cap exceeded')
        gpu_guard()
        return features,{**receipt,'reused':True,'cache_load_seconds':time.monotonic()-started,
            'model_call_account':{},'backbone_forward_calls':0}
    # The existing exclusive queue serializes writers. A partial first build is
    # never silently replaced and the saved manifest follows the frozen tensor.
    features,receipt=build_question_feature_cache(lm,frames,arm,identity,torch_api,
        device=device,guard=guard,max_seconds=max_seconds,max_bytes=max_bytes,gpu_guard=gpu_guard)
    guard(receipt['cache_bytes']+1024**2);directory.mkdir(parents=True,exist_ok=True)
    payload={'cache_key_sha256':key_digest,'features':[feature.detach().cpu() for feature in features]}
    with path.open('xb') as stream:
        torch_api.save(payload,stream);stream.flush();os.fsync(stream.fileno())
    if path.stat().st_size>max_bytes+1024**2: raise RuntimeError('cache storage cap exceeded')
    receipt={**receipt,'cache_key_sha256':key_digest,'cache_file':path.as_posix(),
        'cache_file_sha256':digest(path),'cache_file_bytes':path.stat().st_size,
        'cache_build_and_tensor_save_seconds':time.monotonic()-started}
    data=(json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    guard(len(data)+4096)
    with manifest.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    if time.monotonic()-started>max_seconds: raise RuntimeError('whole cache save wall cap exceeded')
    return features,receipt


def readiness_issues(cfg,probe=False):
    if probe: return ['no disposable training or additional scientific probe authorized']
    issues=[]
    if cfg.get('dispatch_allowed')is not True: issues.append('dispatch_allowed is not true')
    for name in ('architecture_contract_frozen','corpus_frozen','corpus_paired_qualified',
            'numeric_registry_tokenizer_qualified','source_state_verified','live_driver_verified',
            'comparison_protocol_frozen','comparison_provenance_verified','resource_budget_verified',
            'windows_portability_verified','zero_spend_verified','owned_child_shutdown_verified'):
        if cfg.get('readiness',{}).get(name)is not True: issues.append(name+' is not verified')
    return issues


def validate_config(cfg):
    if (cfg.get('schema')!='cap256.contextual-input-train.v1' or cfg.get('arms')!=list(ARMS)
            or cfg.get('seeds')!=[0,1] or cfg.get('recipe')!=RECIPE
            or type(cfg.get('additional_updates'))is not int or cfg['additional_updates']!=UPDATES
            or cfg.get('probe_allowed')is not False or cfg.get('resume_sources')
            or any(key in cfg for key in ('fresh_frames','fresh_rows','eval_frames','eval_rows','evaluation_protocol'))
            or cfg.get('control_reuse_allowed')is not False):
        raise ValueError('exact TRAIN32 fresh-reader/core two-seed static/contextual recipe required')
    validate_feature_identity(cfg.get('feature_identity'))
    if cfg['feature_identity']['worker_sha256']!=cfg['runner']['sha256']:
        raise ValueError('cache worker identity differs from running worker pin')
    if (cfg.get('frames',{}).get('sha256')!=TRAIN32_FRAMES_SHA256
            or type(cfg.get('original_ids'))is not list or len(cfg['original_ids'])!=256
            or len(set(cfg['original_ids']))!=256
            or [source.get('seed') for source in cfg.get('sources',[])]!=[0,1]):
        raise ValueError('exact checked TRAIN32 and original10240 seed parents required')
    if cfg.get('execution_order')!=[[0,'static'],[0,'contextual'],[1,'static'],[1,'contextual']]:
        raise ValueError('fixed four-fit execution order required')
    budget=cfg.get('budget',{})
    for name in ('optimizer_seconds','worker_seconds','cache_seconds','cache_cap_bytes',
            'matrix_cap_bytes','pair_cap_bytes','checkpoint_cap_bytes','project_cap_bytes',
            'retained_free_bytes','raw_cap_bytes_per_pair','cuda_peak_reserved_cap_bytes'):
        if type(budget.get(name))is not int or budget[name]<=0: raise ValueError('explicit cap required: '+name)
    if (budget['optimizer_seconds']>=budget['worker_seconds']
            or budget['cache_seconds']>=budget['worker_seconds']
            or budget['checkpoint_cap_bytes']>128*1024**2
            or budget['cache_cap_bytes']>64*1024**2
            or budget['matrix_cap_bytes']>2*1024**3
            or budget['cuda_peak_reserved_cap_bytes']>12*1024**3
            or budget['retained_free_bytes']<2*1024**3
            or budget.get('aggregate_spend_usd_cap')!='0.00'
            or budget.get('historical_recovery_budget_reused')is not False
            or type(cfg.get('output_accounting_extra_paths'))is not list):
        raise ValueError('current bounded zero-spend Windows comparison resources required')


def endpoint_identity(cfg,config_sha256,seed,arm):
    if type(seed)is not int or seed not in (0,1) or arm not in ARMS:
        raise ValueError('exact matched seed and feature arm required')
    source=next(source for source in cfg['sources'] if source['seed']==seed)
    fields={'runner_sha256':'runner','runtime_sha256':'runtime_module',
        'constructor_sha256':'constructor_module','architecture_contract_sha256':'architecture_contract',
        'training_contract_sha256':'training_contract','calculator_tools_sha256':'calculator_tools',
        'resume_helpers_sha256':'resume_helpers','source_plan_sha256':'source_plan',
        'source_seal_sha256':'source_seal','source_admission_sha256':'source_admission',
        'frames_sha256':'frames','schedule_sha256':'schedules'}
    return {'schema':'cap256.contextual-input.identity.v1','seed':seed,'arm':arm,
        'physical_core_arm':'shallow','config_sha256':config_sha256,
        **{field:cfg[name]['sha256'] for field,name in fields.items()},
        'source_parent_sha256':source['checkpoint']['sha256'],
        'fresh_reader':True,'fresh_core':True,'prefix_exact_parent_copy':True,'optimizer_reset':True,
        'selected_common_updates':UPDATES,'target_updates':UPDATES,
        'comparison_protocol':cfg['comparison_protocol'],
        'question_feature_identity_sha256':canonical(cfg['feature_identity']),
        'question_only_feature_change':True,'tool_return_encoding_unchanged':True,
        'disposable_probe':False,'TRAIN_only':True,'fresh_accessed':False,'total_latent_advances':4}


def preflight(root,cfg,args,helper):
    validate_config(cfg)
    issues=readiness_issues(cfg,args.probe)
    if issues: raise ValueError('; '.join(issues))
    names=('runner','runtime_module','calculator_tools','constructor_module','training_contract',
        'resume_helpers','source_plan','source_seal','source_admission','source_release','source_runner',
        'frames','schedules','storage_snapshot','checkpoint_io','architecture_contract',
        'corpus_audit','comparison_protocol','train32_reference','linux_adapter','path_map','resource_authorization',
        'coverage_contract')
    pins={name:helper.pinned(root,cfg[name]) for name in names}
    if pins['runner'].resolve()!=Path(__file__).resolve(): raise ValueError('running worker pin differs')
    original_seal=helper.read(pins['source_seal']);admission=helper.read(pins['source_admission'])
    code={path:expected for path,expected in original_seal['files'].items() if path.endswith('.py')}
    if (len(code)!=52 or admission.get('schema')!='cap256.contextual-input-source-admission.v1'
            or admission.get('source_seal')!=cfg['source_seal'] or admission.get('files')!=code
            or admission.get('no_dataset_payload_admitted')is not True):
        raise ValueError('exact all52 old source-code admission required; no dataset payload')
    for path,expected in code.items(): helper.pinned(root,{'path':path,'sha256':expected})
    adapter=helper.load_module(pins['linux_adapter'],'_contextual_linux_adapter')
    mapper=adapter.PinnedPathMap(root,cfg['path_map'],cfg['path_map_identity_pins'])
    old=helper.read(pins['source_plan']);entry=next(source for source in cfg['sources'] if source['seed']==args.seed)
    source={name:mapper.resolve_pin(entry[name],kind={'checkpoint':'checkpoint','closed':'receipt'}[name]).path
        for name in ('checkpoint','closed')}
    if old.get('selected_ids')!=cfg['original_ids']:
        raise ValueError('original parent TRAIN256 identity differs from frozen source PLAN')
    coverage=helper.load_module(pins['coverage_contract'],'_contextual_coverage_contract')
    selected=coverage.validate_coverage_corpus(cfg['selected_rows'],'TRAIN32')
    reference=helper.read(pins['train32_reference'])
    if reference['selected_rows']!=cfg['selected_rows'] or reference['frames']!=cfg['frames']:
        raise ValueError('exact existing checked TRAIN32 metadata/frame pin required')
    frames=helper.read(pins['frames'])['rows']
    if len(frames)!=32 or {frame['id'] for frame in frames}!=set(selected):
        raise ValueError('exact checked TRAIN32 input rows required')
    for frame in frames:
        row=selected[frame['id']]
        question_feature_key(frame,args.arm,cfg['feature_identity'])
        if (frame.get('frame_sha256')!=helper.canonical({k:v for k,v in frame.items() if k!='frame_sha256'})
                or frame.get('question')!=row['question'] or frame.get('question_sha256')!=row['question_sha256']
                or frame.get('canonical_numeric_target')!=row['canonical_numeric_target']
                or frame.get('notebook_ids')!=[[]] or frame.get('notebook_mask')!=[[]]
                or frame.get('label_mask')!=[[True]*len(frame['labels'][0])]
                or not 1<=len(frame['labels'][0])<=32
                or type(frame.get('numeric_registry'))is not list or not 1<=len(frame['numeric_registry'])<=8):
            raise ValueError('source-preserving TRAIN tensors/registry/labels required')
    coverage.validate_paired_registry(selected,frames)
    schedules=helper.read(pins['schedules'])['schedules']
    for seed in (0,1):
        schedule=schedules[str(seed)]['result_value_coverage']['TRAIN32']
        coverage.validate_schedule(schedule,cfg['selected_rows'],UPDATES)
        if schedule!=coverage.make_schedule(cfg['selected_rows'],seed,UPDATES):
            raise ValueError('same immutable matched-seed TRAIN32 schedule required')
    protocol=helper.read(pins['comparison_protocol'])
    required={'schema':'cap256.contextual-input-protocol.v1','seeds':[0,1],'arms':list(ARMS),
        'additional_updates':UPDATES,'TRAIN_rows':32,'TRAIN_pairs':16,'new_EVAL_rows':16,'new_EVAL_pairs':8,
        'fresh_reader_both_arms':True,'fresh_core_both_arms':True,'same_original_output_prefix_both_arms':True,
        'question_only_feature_change':True,'tool_return_encoding_unchanged':True,'four_fixed_latent_loops':True,
        'no_control_reuse':True,'no_consumed_panel_reuse':True,
        'selection_rule':'both-seed-EVAL-correct-pair-gain-and-TRAIN32-strict-item-nonloss'}
    if any(type(protocol.get(key))is not type(value) or protocol[key]!=value for key,value in required.items()):
        raise ValueError('approved contextual comparison protocol not frozen')
    authority=helper.read(pins['resource_authorization'])
    if (authority.get('authorized')is not True or authority.get('budget')!=cfg['budget']
            or authority.get('comparison_protocol')!=cfg['comparison_protocol']):
        raise ValueError('explicit whole comparison aggregate resource authority differs')
    return pins,old,entry,source,frames,schedules[str(args.seed)]['result_value_coverage']['TRAIN32'],selected,mapper


def pair_scores(scored,selected):
    byid={record['id']:record for record in scored};groups={}
    for identity,row in selected.items(): groups.setdefault(tuple(sorted(row['operands'])),[]).append(identity)
    return [{'quantities':list(pair),'member_ids':sorted(ids),
        'both_members_correct':len(ids)==2 and all(byid[identity]['strict_final_correct'] for identity in ids),
        'both_members_call_and_final_correct':len(ids)==2 and all(byid[identity]['combined_correct'] for identity in ids)}
        for pair,ids in sorted(groups.items())]


def validate_matched_initialization(static_initial,static_closed,identity,fingerprints):
    for record in (static_initial,static_closed):
        if (record.get('arm')!='static' or record.get('seed')!=identity['seed']
                or record.get('config_sha256')!=identity['config_sha256']
                or record.get('runner_sha256')!=identity['runner_sha256']
                or record.get('source_parent_sha256')!=identity['source_parent_sha256']
                or record.get('fresh_reader')is not True or record.get('fresh_core')is not True
                or record.get('optimizer_reset')is not True
                or record.get('initial_fingerprints')!=fingerprints):
            raise ValueError('matched static reader/core/prefix/tool initialization differs')
    if (static_closed.get('closed')is not True or static_closed.get('optimizer_updates')!=UPDATES
            or static_closed.get('native_TRAIN_calls')!=32 or static_closed.get('fresh_calls')!=0
            or static_closed.get('durable_model_and_Adam_reload_equal')is not True):
        raise ValueError('same-seed matched static endpoint must be durably CLOSED first')


def run(args):
    root = Path(args.root).resolve(); path = Path(args.config).resolve()
    if not path.is_relative_to(root) or digest(path) != args.config_sha256: raise ValueError('immutable root-bound config required')
    cfg = json.loads(path.read_bytes()); validate_config(cfg)
    if args.probe or args.arm not in ARMS: raise ValueError('contextual comparison authorizes static/contextual final fits only')
    issues = readiness_issues(cfg, args.probe)
    if args.check:
        if not issues: preflight(root, cfg, args, load_helpers(root, cfg))
        print(json.dumps({'status': 'PREPARED-BLOCKED' if issues else 'CPU-PREFLIGHT-PASSED', 'issues': issues,
            'model_calls': 0, 'optimizer_updates': 0, 'fresh_accessed': False, 'live_execution_validated': False}), flush=True)
        return
    helper = load_helpers(root, cfg)
    pins, old, entry, source, frames, schedule, selected, mapper = preflight(root, cfg, args, helper)
    if os.environ.get('TREE') != str(root) or not os.environ.get('JOB') or cfg.get('exclusive_lock_verified') is not True:
        raise ValueError('exclusive queue owner/root/job binding required')
    sealed = helper.load_module(pins['source_runner'], '_fresh_core_sealed_numeric')
    sealed.validate_plan(old)
    contract = helper.load_module(pins['training_contract'], '_fresh_core_tool_labels')
    storage = helper.load_module(pins['storage_snapshot'], '_fresh_core_storage')
    checkpoint_io = helper.load_module(pins['checkpoint_io'], '_fresh_core_checkpoint_io')
    matrix = helper.safe(root, cfg['output_namespace'])
    out = matrix / ('seed%d' % args.seed) / args.arm
    if out.exists(): raise RuntimeError('output exists; preserve it and prevent duplicate execution')
    extras = [helper.safe(root, relative) for relative in cfg['output_accounting_extra_paths']]
    budget = cfg['budget']; limit = budget
    unit = storage.filesystem_allocation_unit(root); started = time.monotonic(); phase = 'setup'
    updates = 0; calls = Counter(); requested_tools = Counter(); participation = Counter(); nonzero = Counter()
    def account():
        return {'matrix': storage.allocated_bytes(matrix, unit) + sum(storage.allocated_bytes(p, unit) for p in extras),
            'pair': storage.allocated_bytes(out.parent, unit), 'project': storage.allocated_bytes(root, unit),
            'raw': storage.raw_allocated_bytes(out.parent, unit)}
    def guard(extra=0, check_wall=True):
        now = account()
        if (now['matrix'] + extra > limit['matrix_cap_bytes'] or now['pair'] + extra > budget['pair_cap_bytes']
                or now['project'] + extra > budget['project_cap_bytes']
                or shutil.disk_usage(root).free - extra < budget['retained_free_bytes']):
            raise RuntimeError('fresh comparison matrix/pair/project/free cap exceeded')
        if check_wall and time.monotonic() - started > limit['worker_seconds']: raise RuntimeError('worker hard wall cap exceeded')
        return now
    reserved = 2 * 1024 ** 2 if args.probe else (4 * (budget['checkpoint_cap_bytes'] + budget['raw_cap_bytes_per_pair'])
        + 16 * 1024 ** 2 + 10 * 1024 ** 2)
    # Account total future storage against matrix/project/free; per-pair only its own peak.
    before = account()
    if (before['matrix'] + reserved > limit['matrix_cap_bytes']
            or before['project'] + reserved > budget['project_cap_bytes']
            or shutil.disk_usage(root).free - reserved < budget['retained_free_bytes']):
        raise RuntimeError('whole four-endpoint storage reservation unavailable before model load')
    guard(unit); out.mkdir(parents=True)
    identity = {**endpoint_identity(cfg, args.config_sha256, args.seed, args.arm), 'job':os.environ['JOB']}
    def write(name, value, append=False, check_wall=True):
        data = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        counts = guard(len(data) + unit, check_wall)
        if counts['raw'] + len(data) + unit > budget['raw_cap_bytes_per_pair']: raise RuntimeError('raw cap exceeded')
        with (out / name).open('ab' if append else 'xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    target_updates = UPDATES
    write('LAUNCH.json', {**identity, 'target_updates': target_updates, 'recipe': RECIPE,
        'whole_run_storage_reserved_bytes': reserved, 'native_call_limit': len(frames),
        'checkpoint_limit': 1})
    try:
        sys.path[:0] = [str(root), str(root / 'scripts')]
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        import torch
        from sol_translator_grounding_v6 import HumanInputProjection, human_loss
        from sol_translator_english_ordered_v10 import load_ordered_english
        import sol_spatial_poc_ordered_v2
        import sol_spatial_poc_ordered_train_api_v2
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        from sol_translator_runtime import component_fingerprint
        from sol_translator_decoder import FinalLatent
        runtime = importlib.import_module('scripts.cap256_launch.calculator_runtime_depth_compare')
        constructors = importlib.import_module('scripts.cap256_launch.fresh_core_calculator_constructor')
        tools = importlib.import_module('scripts.cap256_launch.calculator_tools')
        for name, module in (('runtime_module', runtime), ('constructor_module', constructors), ('calculator_tools', tools)):
            if Path(module.__file__).resolve() != pins[name].resolve(): raise ValueError('module import path differs: ' + name)
        helper.verify_runtime_imports(root, helper.read(pins['source_admission']), [cfg[name] for name in
            ('runner', 'runtime_module', 'constructor_module', 'calculator_tools', 'training_contract',
             'resume_helpers', 'source_runner', 'storage_snapshot', 'checkpoint_io', 'linux_adapter', 'coverage_contract')])
        torch.set_num_threads(2)
        if not torch.cuda.is_available(): raise RuntimeError('authorized CUDA unavailable')
        cuda_allocation_budget = install_cuda_memory_budget(torch, budget['cuda_peak_reserved_cap_bytes'])
        write('CUDA-ALLOCATION-BUDGET.json', {**identity, **cuda_allocation_budget})
        torch.cuda.reset_peak_memory_stats()
        def gpu_guard():
            peak = torch.cuda.max_memory_reserved()
            if peak > budget['cuda_peak_reserved_cap_bytes']: raise RuntimeError('GPU peak reserved cap exceeded')
            return {'peak_reserved_bytes': peak, 'reserved_bytes': torch.cuda.memory_reserved(),
                'allocated_bytes': torch.cuda.memory_allocated()}
        prior = torch.load(source['checkpoint'], map_location='cpu', weights_only=True)
        closed = helper.read(source['closed']); helper.validate_initial_metadata(prior, closed, entry, cfg['original_ids'])
        binding = old['warmstart']['tuples'][str(args.seed)]
        model_path = mapper.resolve_directory(binding['lm_path'], cfg['lm_closure_sha256'])
        provenance_path = mapper.resolve_pin({'path':binding['lm_provenance'],
            'sha256':cfg['lm_provenance_sha256']}, kind='provenance').path
        adapter_path = mapper.resolve_pin({'path':binding['adapter_path'],
            'sha256':binding['adapter_sha256']}, kind='checkpoint').path
        dec, tokenizer, provenance = load_ordered_english(str(model_path), str(provenance_path), str(adapter_path), 'cuda')
        lm = dec.lm; lm.eval().requires_grad_(False)
        verify_feature_provenance(provenance,cfg['feature_identity'])
        verify_lm_runtime(lm, tokenizer, cfg['feature_identity'], torch)
        reader = build_fresh_reader(torch, HumanInputProjection, args.seed, 'cuda')
        dec.adapter.load_state_dict(prior['prefix'], strict=True)
        if component_fingerprint(dec.adapter) != closed['final_fingerprints']['prefix']:
            raise ValueError('same original parent output prefix fingerprint differs')
        reader.train().requires_grad_(True); dec.adapter.train().requires_grad_(True)
        core = constructors.build_fresh_core('shallow', args.seed, 'cuda'); core.train(); core.halt.requires_grad_(False)
        with torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(TOOL_SEED_OFFSET + args.seed)
            tool = runtime.CalculatorPath(dim=256).to('cuda')
        tool.train().requires_grad_(True)
        modules = (('core', core), ('reader', reader), ('prefix', dec.adapter), ('tool', tool))
        if any(p.dtype != torch.float32 for module in [lm]+[module for _,module in modules] for p in module.parameters()): raise ValueError('FP32 required')
        named = [(group + '.' + name, p) for group, module in modules for name, p in module.named_parameters() if p.requires_grad]
        params = [p for _, p in named]
        if (not args.probe and 3 * sum(p.numel() * p.element_size() for p in params)
                + 3 * 1024 ** 2 > budget['checkpoint_cap_bytes']):
            raise RuntimeError('checkpoint reservation bound insufficient before any fit update')
        opt = torch.optim.AdamW(params, lr=0.001, weight_decay=0, betas=(0.9, 0.999), eps=1e-8)
        if opt.state or len(opt.param_groups) != 1: raise ValueError('fresh complete optimizer state required')
        tokens = []; byid = {}
        for index, frame in enumerate(frames):
            row = selected[frame['id']]; registry = tools.build_registry(row['question'], tokenizer)
            ids = tokenizer.encode(row['question'], add_special_tokens=False)
            if (registry != frame['numeric_registry'] or frame['input_ids'] != [ids + [dec.eos_id]]
                    or dec.eos_id in ids or frame['labels'] != [tokenizer.encode(row['canonical_numeric_target'], add_special_tokens=False) + [dec.eos_id]]):
                raise ValueError('actual tokenizer/EOS/registry qualification differs')
            contract.checked_target_refs(row, registry)
            tokens.append((torch.tensor(frame['input_ids'], device='cuda'),
                torch.tensor(frame['input_mask'], device='cuda', dtype=torch.bool), torch.tensor(frame['labels'], device='cuda')))
            byid[frame['id']] = index
        phase='input-feature-cache'
        feature_cache, cache_receipt = prepare_question_feature_cache(lm, frames, args.arm,
            cfg['feature_identity'], torch, device='cuda', guard=guard,
            directory=matrix/'question-feature-cache',max_seconds=budget['cache_seconds'],
            max_bytes=budget['cache_cap_bytes'],gpu_guard=gpu_guard)
        calls.update(cache_receipt['model_call_account'])
        write('QUESTION-FEATURE-CACHE.json', {**identity, **cache_receipt})
        rng = (prior['torch_rng'], prior['cuda_rng'], prior['python_rng']); del prior
        torch.set_rng_state(rng[0]); torch.cuda.set_rng_state_all(rng[1]); random.setstate(rng[2])
        if (not torch.equal(torch.get_rng_state(), rng[0]) or not helper.state_equal(torch.cuda.get_rng_state_all(), rng[1], torch)
                or random.getstate() != rng[2]): raise ValueError('matched source training RNG restoration differs')
        del rng
        initial = {name: component_fingerprint(module) for name, module in modules}
        matched_static_verified=False
        if args.arm=='contextual':
            static_out=matrix/('seed%d'%args.seed)/'static'
            static_initial=helper.read(static_out/'INITIALIZATION.json')
            static_closed=helper.read(static_out/'CLOSED.json')
            validate_matched_initialization(static_initial,static_closed,identity,initial)
            static_checkpoint=helper.safe(root,static_closed['checkpoint']['path'])
            if digest(static_checkpoint)!=static_closed['checkpoint']['sha256']:
                raise ValueError('matched static physical checkpoint differs from durable closure')
            matched_static_verified=True
        lm_before = component_fingerprint(lm); halt_before = component_fingerprint(core.halt)
        buffers_before = {name: value.detach().cpu().clone() for name, value in core.named_buffers()}
        write('INITIALIZATION.json', {**identity, 'initial_fingerprints': initial, 'constructor': core.constructor(),
            'tool_constructor': tool.constructor(), 'stored_core_parameters': sum(p.numel() for p in core.parameters()),
            'parameter_names': [name for name, _ in named], 'optimizer_state_empty': True,
            'old_core_and_Adam_not_reused': True, 'fresh_reader':True, 'original_reader_not_reused':True, 'prefix_exact_parent_copy':True,
            'matched_static_initialization_verified':matched_static_verified,
            'core_seed':args.seed, 'reader_seed':READER_SEED_OFFSET+args.seed, 'tool_seed':TOOL_SEED_OFFSET+args.seed, 'training_RNG_exact_parent_restored': True,
            'counts_by_component': {name: sum(p.numel() for p in module.parameters()) for name, module in modules},
            'physical_block_visits_per_example': 4 * len(core.blocks), 'initial_gpu': gpu_guard()})
        optimizer_budget = sealed.OptimizerBudget(limit['optimizer_seconds'])
        def check_parameters():
            if not bool(torch.stack([torch.isfinite(p.detach()).all() for p in params]).all()): raise RuntimeError('nonfinite parameter')
        def graph(index, training=True):
            _, mask, _ = tokens[index]
            lookup_started=time.perf_counter();features=feature_cache[index]
            lookup_seconds=time.perf_counter()-lookup_started
            query,reader_seconds=timed_call(lambda:project_cached_question(reader,features,mask),torch)
            def advance():
                with ordered_attention_math():
                    return tool.forward(core,reader,lm,tokenizer,query,frames[index]['numeric_registry'],mask)
            output,core_seconds=timed_call(advance,torch)
            if output['total_advances'] != 4 or output['auxiliary_terms'] != 4 * len(core.blocks): raise ValueError('physical4-loop count differs')
            h = output['h']
            if training:
                prefix,prefix_seconds=timed_call(lambda:dec.adapter.project_training(h,
                    torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),torch)
            else: prefix=None;prefix_seconds=0.0
            return output,prefix,{'original_question_cache_hit':True,'cache_lookup_seconds':lookup_seconds,
                'original_question_backbone_forward_calls':0,'reader_seconds':reader_seconds,
                'core_four_loop_seconds':core_seconds,'core_loops_per_second':4/core_seconds if core_seconds>0 else None,
                'output_prefix_project_seconds':prefix_seconds}
        visits = Counter(); check_parameters(); phase = 'training'
        training_started = time.monotonic(); setup_seconds = training_started - started; step_wall = []
        for additional, identity_id in enumerate(schedule[:target_updates], 1):
            step_started = time.monotonic()
            guard(); gpu_guard(); optimizer_budget.begin(); index = byid[identity_id]; opt.zero_grad(set_to_none=True)
            phase = 'model-forward'; output, prefix, timings = graph(index)
            (per,pred),output_seconds=timed_call(lambda:human_loss(lm,prefix,tokens[index][2],
                dec.bos_id,dec.eos_id,True,True),torch)
            calls['TRAIN_optimizer_teacherforcing'] += 1
            labels = contract.supervision(selected[identity_id], frames[index]['numeric_registry'], output['loops'])
            action_ce, pointer_ce = contract.weighted_call_loss(output['loops'], labels, torch, runtime.ACTIONS)
            loss = per.mean() + action_ce + pointer_ce; phase = 'optimizer-step'; gradient = {}
            def before_step():
                finite = [torch.isfinite(p.grad).all() for _, p in named if p.grad is not None]
                if finite and not bool(torch.stack(finite).all()): raise RuntimeError('nonfinite gradient')
                for component, module in modules:
                    gradients = [p.grad for p in module.parameters() if p.grad is not None]
                    gradient[component] = {'grad_norm': float(torch.stack([g.detach().float().square().sum() for g in gradients]).sum().sqrt()) if gradients else 0.0,
                        'parameters_with_gradient': len(gradients),
                        'nonzero_gradient_parameters': sum(bool(torch.count_nonzero(g)) for g in gradients)}
                for name, p in named:
                    if p.grad is not None:
                        participation[name] += 1
                        if bool(torch.count_nonzero(p.grad)): nonzero[name] += 1
            preclip = sealed.numeric_optimizer_step(loss, opt, params, torch, before_step)
            torch.cuda.synchronize(); optimizer_budget.end(); updates = additional; visits[identity_id] += 1
            check_parameters(); guard(); gpu_guard()
            if any(p.grad is not None for p in lm.parameters()) or any(p.grad is not None for p in core.halt.parameters()): raise ValueError('frozen gradient')
            requested_tools['TRAIN_requested_tools'] += sum(trace['action'] != 'NONE' for trace in output['trace'])
            phase = 'durable-raw'
            write('TRAIN-RAW.jsonl', {**identity,
                'schema':'cap256.contextual-input.TRAIN-raw.v1','job':os.environ['JOB'],'seed':args.seed,'arm':args.arm,
                'config_sha256':args.config_sha256,'additional_update':additional,'id':identity_id,
                'frame_sha256':frames[index]['frame_sha256'],'numeric_CE':float(per.mean().detach()),
                'action_CE':float(action_ce.detach()),'pointer_CE':float(pointer_ce.detach()),'total_loss':float(loss.detach()),
                'preclip_norm':float(preclip),'component_gradient':gradient,'loss_labels':labels,
                'predicted_trace':output['trace'],'routing':output['routing'],'auxiliary_terms':output['auxiliary_terms'],
                'sparse_auxiliary_observed_excluded':float(output['auxiliary'].detach()),'auxiliary_weight':0,
                'teacherforced_argmax':pred.cpu().tolist(),'optimizer_seconds':optimizer_budget.elapsed,
                'wall_seconds':time.monotonic()-started,'gpu':gpu_guard(),
                'performance':{**timings,'output_teacherforcing_seconds':output_seconds,
                    'memory':performance_snapshot(torch)}}, True)
            step_wall.append(time.monotonic() - step_started)
            phase = 'training'
        training_wall_seconds = time.monotonic() - training_started
        if updates != target_updates or calls['TRAIN_optimizer_teacherforcing'] != target_updates: raise ValueError('exact update/call count differs')
        if component_fingerprint(lm) != lm_before or component_fingerprint(core.halt) != halt_before: raise ValueError('frozen LM/halt changed')
        after = dict(core.named_buffers())
        if buffers_before.keys() != after.keys() or not all(torch.equal(v, after[n].detach().cpu()) for n,v in buffers_before.items()): raise ValueError('ordered buffers changed')
        if visits != Counter(schedule): raise ValueError('full endpoint exposures differ')
        phase = 'checkpoint'; final = {name:component_fingerprint(module) for name,module in modules}
        audit=[]
        for name,p in named:
            state=opt.state.get(p,{});step=int(state['step']) if state else 0
            if step != participation[name]: raise ValueError('Adam steps differ from observed participation')
            audit.append({'name':name,'participation':participation[name],'nonzero_gradient_updates':nonzero[name],'Adam_step':step})
        checkpoint={**identity,'recipe':RECIPE,'update':target_updates,'additional_updates':target_updates,
            'constructor':core.constructor(),'tool_constructor':tool.constructor(),
            **{name:module.state_dict() for name,module in modules},'optimizer':opt.state_dict(),
            'optimizer_parameter_names':[name for name,_ in named],'optimizer_audit':audit,
            'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'python_rng':random.getstate(),
            'model_state_fingerprints':final,'initial_fingerprints':initial,'participation':dict(participation),
            'visits':dict(visits),'schedule_cursor':target_updates,'model_call_account':dict(calls),
            'TRAIN_raw_sha256':helper.sha(out/'TRAIN-RAW.jsonl')}
        allowance=budget['checkpoint_cap_bytes']
        if 3*sum(p.numel()*p.element_size() for p in params)+3*1024**2>allowance: raise RuntimeError('checkpoint reservation bound insufficient')
        cp=out/'final-resume.pt'
        checkpoint_io.save_reserved(cp,allowance,lambda sink:torch.save(checkpoint,sink),sealed.save_new_atomic_file,
            guard,lambda:shutil.disk_usage(root).free,budget['retained_free_bytes'],unit)
        restored=torch.load(cp,map_location='cpu',weights_only=True)
        if (not helper.state_equal(checkpoint,restored,torch)
                or not torch.equal(restored['torch_rng'],torch.get_rng_state())
                or not helper.state_equal(restored['cuda_rng'],torch.cuda.get_rng_state_all(),torch)
                or restored['python_rng']!=random.getstate()): raise ValueError('durable model/Adam/RNG reload differs')
        del restored,checkpoint
        # Saved endpoint and immutable observations precede TRAIN gold scoring.
        for _,module in modules: module.eval().requires_grad_(False)
        phase='native-TRAIN';observations=[]
        with torch.no_grad():
            for index,frame in enumerate(frames):
                guard();gpu_guard();answer_started=time.perf_counter()
                output,_,timings=graph(index,training=False);h=output['h'];mask=tokens[index][1]
                observed,decode_seconds=timed_call(lambda:sealed.observe_generation(dec,
                    FinalLatent(h,torch.ones_like(h,dtype=torch.bool),mask,(1,h.shape[1])),32),torch)
                answer_seconds=time.perf_counter()-answer_started
                generated_ids=observed.get('MODEL_generated_ids_with_observed_EOS')
                generated_tokens=len(generated_ids) if type(generated_ids)is list else None
                calls['TRAIN_native_generation']+=observed['native_generate_call_count']
                record={**identity,'id':frame['id'],'checkpoint_sha256':helper.sha(cp),
                    'predicted_trace':output['trace'],'routing':output['routing'],'total_advances':4,**observed,
                    'performance':{**timings,'output_decoding_seconds':decode_seconds,
                        'generated_tokens_including_observed_EOS':generated_tokens,
                        'output_tokens_per_second':generated_tokens/decode_seconds if generated_tokens is not None and decode_seconds>0 else None,
                        'total_warm_cache_answer_seconds':answer_seconds,'memory':performance_snapshot(torch)}}
                observations.append(record);write('TRAIN-OBSERVATIONS.jsonl',record,True)
                if observed['native_generate_call_count']!=1:raise ValueError('one native answer per TRAIN row required')
        frozen_hash=helper.sha(out/'TRAIN-OBSERVATIONS.jsonl')
        write('TRAIN-OBSERVATIONS-FROZEN.json',{**identity,'sha256':frozen_hash,'native_calls':len(frames),'gold_scoring_started':False})
        scored=[]
        for observed,frame in zip(observations,frames):
            row=selected[frame['id']];refs=contract.checked_target_refs(row,frame['numeric_registry'])
            call_correct=any(contract.task_call_matches(trace,contract.action_for(row),refs)
                and type((trace.get('result') or {}).get('value')) is int
                and trace['result']['value']==int(row['canonical_numeric_target']) for trace in observed['predicted_trace'])
            exact=(observed.get('native_call_contract_valid') is True and observed.get('generation_error') is None
                and observed.get('raw_output_single_typed_sequence') is True
                and sealed.score_observed_generation(observed,frame['labels'][0],dec.eos_id))
            scored.append({'id':frame['id'],'equivalent_task_call_correct':call_correct,'strict_final_correct':exact,'combined_correct':call_correct and exact})
        if helper.sha(out/'TRAIN-OBSERVATIONS.jsonl')!=frozen_hash: raise ValueError('TRAIN observations changed after scoring')
        if any(component_fingerprint(module)!=final[name] for name,module in modules) or component_fingerprint(lm)!=lm_before: raise ValueError('endpoint changed during native TRAIN')
        phase='closure'
        write('CLOSED.json',{**identity,'closed':True,'optimizer_updates':target_updates,'additional_optimizer_updates':target_updates,
            'checkpoint':{'path':cp.relative_to(root).as_posix(),'sha256':helper.sha(cp)},'constructor':core.constructor(),
            'tool_constructor':tool.constructor(),'final_fingerprints':final,'initial_fingerprints':initial,
            'durable_model_and_Adam_reload_equal':True,'model_call_account':dict(calls),'model_calls_exact':True,
            'optimizer_updates_exact':True,'native_TRAIN_calls':len(frames),'TRAIN_native_results':scored,
            'TRAIN_pair_results':pair_scores(scored,selected),'TRAIN_item_correct':sum(record['strict_final_correct'] for record in scored),
            'TRAIN_combined_call_and_final_correct':sum(record['combined_correct'] for record in scored),
            'TRAIN_strict_final_correct':sum(record['strict_final_correct'] for record in scored),
            'TRAIN_correct_task_calls':sum(record['equivalent_task_call_correct'] for record in scored),
            'TRAIN_call_conditioned_final_correct':sum(record['combined_correct'] for record in scored),
            'question_feature_cache':cache_receipt,
            'raw_frozen_before_scoring':True,'TRAIN_observations_sha256':frozen_hash,
            'TRAIN_raw_sha256':helper.sha(out/'TRAIN-RAW.jsonl'),'fresh_calls':0,
            'native_weight_unchanged':True,'optimizer_seconds':optimizer_budget.elapsed,
            'wall_seconds':time.monotonic()-started,'training_wall_seconds':training_wall_seconds,
            'setup_seconds':setup_seconds,'max_step_wall':max(step_wall),'gpu':gpu_guard(),'output_account':account(),
            'LM_unchanged':True,'halt_unchanged':True,'ordered_buffers_unchanged':True})
        print(json.dumps({'status':'CLOSED-CONTEXTUAL-INPUT-COMPARISON','selected_common_updates':target_updates,'seed':args.seed,'arm':args.arm,
            'native_TRAIN_calls':len(frames),'fresh_calls':0,'checkpoint_sha256':helper.sha(cp)}),flush=True)
    except Exception as error:
        try:
            write('FAILED.json',{**identity,'phase':phase,'error_type':type(error).__name__,'error':str(error),
                'additional_optimizer_updates':updates,'last_completed_model_call_account':dict(calls),
                'model_calls_exact':phase=='setup','optimizer_updates_exact':phase!='optimizer-step',
                'fresh_calls':0,'source_parent_preserved':entry['checkpoint'],'evidence_preserved':True},check_wall=False)
        except Exception as receipt_error:
            print(json.dumps({'status':'FAILURE-RECEIPT-BLOCKED','primary_error':str(error),'receipt_error':str(receipt_error),
                'output_directory':out.as_posix(),'existing_evidence_preserved':True}),flush=True)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True);parser.add_argument('--config',required=True);parser.add_argument('--config-sha256',required=True)
    parser.add_argument('--seed',type=int,choices=(0,1),required=True);parser.add_argument('--arm',choices=ARMS,required=True)
    parser.set_defaults(probe=False);parser.add_argument('--check',action='store_true')
    run(parser.parse_args())
