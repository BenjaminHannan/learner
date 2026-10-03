"""Predicted mechanical calculator calls inside exactly four native advances.

Gold answers/actions are never runtime arguments. Original query geometry is
fixed at begin; four value/status pairs are preallocated as notebook tokens.
Policy features are h+e for the original query and eligible reference states.
"""
import math

try:
    import torch
    from torch import nn
except ModuleNotFoundError:
    torch=None
    nn=None

ACTIONS=('NONE','ADD','SUB')
STATUSES=('PENDING','NONE','OK','ERROR')
STATUS_IDS={name:index for index,name in enumerate(STATUSES)}


class CalculatorPath(nn.Module if nn is not None else object):
    def __init__(self,dim=256):
        if torch is None:raise ImportError('CalculatorPath requires PyTorch; mechanical tools are stdlib-only')
        super().__init__()
        if dim!=256:raise ValueError('fixed calculator width256')
        self.dim=dim
        self.action=nn.Linear(dim,3)  # Explicit contract: ordinary Linear bias.
        self.left=nn.Parameter(torch.empty(dim,dim))
        self.right=nn.Parameter(torch.empty(dim,dim))
        nn.init.xavier_uniform_(self.left);nn.init.xavier_uniform_(self.right)
        self.status=nn.Embedding(4,dim);nn.init.zeros_(self.status.weight)
        self.role=nn.Parameter(torch.zeros(dim))

    def constructor(self):
        return {'family':'calculator-depth-compare-per-loop-D256-v1','dim':256,'loops':4,
            'action_names':list(ACTIONS),'action_bias':True,'pointer_heads':2,
            'pointer_rule':'query_mean_T_W_reference_mean/sqrt256','pointer_bias':False,
            'policy_features':'h+e','max_original_literal_spans':8,'reserved_tool_pairs':4,
            'status_codes':dict(STATUS_IDS),'status_initialization':'zero','role_initialization':'zero',
            'result_encoding':'one canonical numeric token; frozen LM embedding through same reader',
            'transport':'write own pair e; clear own pair h; retain ordered position/role codes',
            'eligible_references':'original literals plus earlier OK result value slots',
            'auxiliary_rule':'mean4-times-physical-block-count-observed-weight0'}

    def tool_named_parameters(self):return self.named_parameters()

    def _scores(self,features,query_n,candidates):
        query_mean=features[:,:query_n].mean(1)
        action_logits=self.action(query_mean)
        means=[]
        for candidate in candidates:
            indices=candidate['token_indices'] if candidate['source']=='literal' else [candidate['slot_index']]
            if not indices or any(type(i) is not int or not 0<=i<features.shape[1] for i in indices):
                raise ValueError('reference token indices outside fixed state')
            means.append(features[:,indices].mean(1))
        if means:
            reference_means=torch.stack(means,dim=1)
            left_logits=torch.einsum('bd,df,bcf->bc',query_mean,self.left,reference_means)/math.sqrt(self.dim)
            right_logits=torch.einsum('bd,df,bcf->bc',query_mean,self.right,reference_means)/math.sqrt(self.dim)
        else:
            left_logits=features.new_empty((1,0));right_logits=features.new_empty((1,0))
        return action_logits,left_logits,right_logits

    def _numeric_value(self,result,reader,lm,tokenizer,query):
        text=str(result)
        ids=tokenizer.encode(text,add_special_tokens=False)
        if (type(result) is not int or type(ids) is not list or len(ids)!=1
                or type(ids[0]) is not int or ids[0]<0
                or ids[0] in {getattr(tokenizer,name,None) for name in ('bos_token_id','eos_token_id','pad_token_id')}
                or tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)!=text):
            return None,None
        embedding=lm.get_input_embeddings()
        if embedding.weight.requires_grad:raise ValueError('calculator result lexical embedding must be frozen')
        token_ids=torch.tensor([ids],device=query.device,dtype=torch.long)
        encoded=reader(embedding(token_ids),torch.ones((1,1),device=query.device,dtype=torch.bool))
        if encoded.shape!=(1,1,1,256):raise ValueError('same reader must return one D256 tool state')
        return encoded[:,0,0].to(query.dtype),ids[0]

    def forward(self,core,reader,lm,tokenizer,inputquery,registry,querymask):
        from .calculator_tools import execute_integer_call
        if (inputquery.ndim!=4 or inputquery.shape[0]!=1 or inputquery.shape[1]!=1
                or inputquery.shape[-1]!=256 or querymask.dtype!=torch.bool
                or querymask.shape!=(1,inputquery.shape[2]) or querymask.device!=inputquery.device):
            raise ValueError('one physical [1,1,N,256] query with prefix bool mask required')
        contract=core.constructor()
        expected_blocks={'shallow':2,'deep':16}.get(contract.get('arm'))
        if (contract.get('family')!='fresh-core-calculator-compare-D256-v1'
                or expected_blocks is None or len(core.blocks)!=expected_blocks
                or contract.get('distinct_blocks_per_loop')!=expected_blocks
                or contract.get('expert_hidden')!={'shallow':1024,'deep':64}[contract['arm']]
                or contract.get('fixed_latent_loops')!=4 or contract.get('extra_stabilizer') is not False
                or contract.get('experts')!=8 or contract.get('active')!=2):
            raise ValueError('exact fresh shallow2H1024/deep16H64 ordered LOOP contract required')
        if type(registry) is not list or len(registry)>8:raise ValueError('at most8mechanical literal records')
        query_n=int(querymask.sum())
        if query_n<1 or not bool((querymask==torch.arange(inputquery.shape[2],device=inputquery.device)[None].lt(query_n)).all()):
            raise ValueError('nonempty prefix query mask required')
        if any(r['source']!='literal' or r['status']!='OK' or not r['token_indices']
                or any(type(i) is not int or not 0<=i<query_n for i in r['token_indices']) for r in registry):
            raise ValueError('literal reference must belong to original query tokens')
        if len({r['id'] for r in registry})!=len(registry):raise ValueError('duplicate original reference ID')
        memo=inputquery.new_zeros((1,8,256))
        pending=self.status.weight[STATUS_IDS['PENDING']].to(inputquery.dtype)
        for pair in range(4):
            memo[:,2*pair]=self.role.to(inputquery.dtype)
            memo[:,2*pair+1]=pending+self.role.to(inputquery.dtype)
        state=core.begin_latent(inputquery,memo,query_mask=querymask,
            notebook_mask=torch.ones((1,8),device=inputquery.device,dtype=torch.bool))
        if state['query_n']!=query_n or state['h'].shape!=(1,query_n+8,256):
            raise ValueError('native begin must retain query geometry plus8reserved positions')
        # This subtraction isolates the existing fixed ordered position codes.
        # It introduces no encoder and retains the core's neutral memo offsets.
        tool_position_codes=state['e'][:,query_n:]-memo
        candidates=[dict(r) for r in registry];loops=[];trace=[];aux=[];routing=[]
        original_e=state['e'][:,:query_n].clone()
        fixed_shapes=(state['h'].shape,state['e'].shape,state['dr'].shape,state['dc'].shape)
        for loop_index in range(4):
            action_logits,left_logits,right_logits=self._scores(state['h']+state['e'],query_n,candidates)
            action=ACTIONS[int(action_logits.argmax(-1).item())]
            left_index=right_index=None;refs=[]
            if action!='NONE' and candidates:
                left_index=int(left_logits.argmax(-1).item());right_index=int(right_logits.argmax(-1).item())
                refs=[candidates[left_index]['id'],candidates[right_index]['id']]
            observed=execute_integer_call(action,refs,candidates,call_index=loop_index+1)
            observed={**observed,'loop_index':loop_index,'left_index':left_index,'right_index':right_index,
                'candidate_ids':[r['id'] for r in candidates],'refs':list(refs),'policy_features':'h+e'}
            content=inputquery.new_zeros((1,256));numeric_token_id=None
            if observed['status']=='OK':
                content,numeric_token_id=self._numeric_value(observed['result']['value'],reader,lm,tokenizer,inputquery)
                if content is None:
                    observed={**observed,'status':'ERROR','error_code':'UNSUPPORTED_NUMERIC_TOKEN','result':None}
                    content=inputquery.new_zeros((1,256))
            status=observed['status']
            if status not in ('NONE','OK','ERROR'):raise ValueError('calculator returned unsupported status')
            value_slot=query_n+2*loop_index;status_slot=value_slot+1
            next_e=state['e'].clone();next_h=state['h'].clone()
            next_e[:,value_slot]=tool_position_codes[:,2*loop_index]+content+self.role.to(inputquery.dtype)
            next_e[:,status_slot]=tool_position_codes[:,2*loop_index+1]+self.status.weight[STATUS_IDS[status]].to(inputquery.dtype)+self.role.to(inputquery.dtype)
            next_h[:,value_slot:status_slot+1]=0
            if not torch.equal(next_h[:,:query_n],state['h'][:,:query_n]) or not torch.equal(next_e[:,:query_n],original_e):
                raise RuntimeError('tool insertion changed original query state')
            observed.update(value_slot=value_slot,status_slot=status_slot,numeric_token_id=numeric_token_id,
                value_content_zero=status!='OK',original_query_unchanged_on_insert=True)
            loops.append({'action_logits':action_logits,'left_logits':left_logits,'right_logits':right_logits,
                'candidates':[dict(r) for r in candidates],'trace':observed})
            trace.append(observed)
            if status=='OK':
                result={**observed['result'],'slot_index':value_slot,'token_indices':[value_slot]}
                candidates.append(result)
            state=core.advance_latent({**state,'h':next_h,'e':next_e})
            aux.extend(block.mlp.aux for block in core.blocks)
            for block_index,block in enumerate(core.blocks):
                counts=list(block.mlp.last_counts);assignments=sum(counts)
                tokens=state['h'].shape[0]*state['h'].shape[1]
                if len(counts)!=8 or assignments!=tokens*2:
                    raise RuntimeError('observed router assignment conservation failed')
                shares=[count/assignments for count in counts]
                routing.append({'loop_index':loop_index,'block_index':block_index,'tokens':tokens,
                    'assignments':assignments,'expert_assignment_counts':counts,
                    'unused_experts':[i for i,count in enumerate(counts) if count==0],
                    'max_assignment_share':max(shares),
                    'assignment_entropy':-sum(p*math.log(p) for p in shares if p)})
            if (state['query_n']!=query_n or state['round']!=loop_index+1
                    or fixed_shapes!=(state['h'].shape,state['e'].shape,state['dr'].shape,state['dc'].shape)):
                raise RuntimeError('calculator changed native shape, query length or advance count')
        if len(aux)!=4*expected_blocks or len(routing)!=4*expected_blocks:
            raise RuntimeError('exactly4-times-physical-block-count auxiliary/routing observations required')
        final_h,halt=core.read_latent(state)
        return {'h':final_h,'halt':halt,'loops':loops,'trace':trace,'total_advances':4,
            'auxiliary':torch.stack(aux).mean(),'routing':routing,'auxiliary_terms':len(aux),
            'constructor':self.constructor()}
