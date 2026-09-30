"""Bounded forward/backward API contracts only. NO optimizer or fitting."""
from __future__ import annotations
import argparse
import copy
import inspect
import json
import tempfile
from pathlib import Path
import torch
from sol_compose_data import build_pools, cycle_structure, oracle
from sol_compose_model import ARMS, D, build_model, parameter_counts, State
from sol_compose_notebook import NotebookStore, ByteFactEncoder, FinalStateTranslator


def contracts():
    torch.set_num_threads(2)
    checks, evidence = {}, {}
    # Two predetermined mechanical seeds, not performance evidence.
    for seed in (0,1):
        torch.manual_seed(93000+seed)
        pools = build_pools(seed,20,10)
        for key,dataset in pools.items():
            assert set(dataset.structures).issubset({(10,),(5,5)} if key.startswith('TRAIN') else {(7,3),(6,4)})
            for token, label, structure in zip(dataset.inputs.tokens, dataset.targets, dataset.structures):
                table={int(row[2])-2:int(row[3])-2 for row in token if row[0]==120}
                permutation=[table[i] for i in range(10)]
                assert cycle_structure(permutation)==structure
                query=token[token[:,3]==1][0]
                assert oracle(permutation,int(query[2])-2,tuple(query[:2].tolist()))==int(label.max())-2
                if key!='TRAIN_primitives':
                    assert oracle(permutation,int(query[2])-2,(119,118)) != oracle(permutation,int(query[2])-2,(118,119))
        assert pools['TRAIN'].audit == build_pools(seed,20,10)['TRAIN'].audit
        checks[f's{seed}_symbolic_labels_disjoint_structures_and_order'] = True
        inputs=pools['TRAIN'].inputs.select(torch.arange(2))
        m=build_model('compose')
        snapshot=copy.deepcopy(m.state_dict())
        result=m.rollout(inputs,rounds=3)
        assert result['logits'].shape==(2,3,11,125)
        result['states'][0].board.retain_grad()
        # Random tensor functional probes, NEVER task targets or optimizer steps.
        probe=torch.randn_like(result['logits'][:,-1])
        ((result['logits'][:,-1]*probe).mean()+result['halt'].square().mean()+result['aux']).backward()
        names=('record.record_gru.weight_ih','numeric.recurrent.weight_ih','blocks.0.attention.q.weight','blocks.0.router.weight')
        grads={name:float(dict(m.named_parameters())[name].grad.abs().sum()) for name in names}
        assert all(v>0 for v in grads.values())
        assert float(result['states'][0].board.grad.abs().sum())>0
        assert all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in m.parameters())
        assert all(torch.equal(snapshot[k],v) for k,v in m.state_dict().items())
        checks[f's{seed}_full_bptt_program_attention_router_gradients_no_updates']=True
        evidence[f's{seed}_gradient_l1']=grads
        with torch.no_grad():
            baseline=m.rollout(inputs,rounds=3)['state'].board
            reversed=m.rollout(inputs.select(torch.tensor([1,0])),rounds=3)['state'].board.flip(0)
            isolated=m.rollout(inputs.select(torch.tensor([0])),rounds=3)['state'].board
            error=max(float((baseline-reversed).abs().max()),float((baseline[:1]-isolated).abs().max()))
            assert error<2e-5
            ctx=m.encode(inputs); state=m.initial_state(ctx)
            assert not bool(ctx.anchor[~inputs.slots.any(-1)].any())
            changed=State(state.board+.25,state.records,state.atoms,state.numeric,state.public,state.rounds,state.aux)
            a=m.step(ctx,state); b=m.step(ctx,changed)
            assert float((a.numeric-b.numeric).abs().max())>1e-6
            assert float((a.records-b.records).abs().max())>1e-6
            cut=build_model('no_communication');cut.load_state_dict(m.state_dict())
            a=cut.step(ctx,state); b=cut.step(ctx,changed)
            assert torch.equal(a.numeric,b.numeric) and torch.equal(a.records,b.records)
            # Arbitrary private states cannot affect cut board or final outputs.
            altered=State(state.board,state.records+100,state.atoms-100,state.numeric+100,state.public+100,state.rounds,state.aux)
            c=cut.step(ctx,altered)
            assert torch.equal(a.board,c.board)
            assert torch.equal(cut.read(a)[0],cut.read(c)[0])
            evidence[f's{seed}_batch_isolation_error']=error
            checks[f's{seed}_communication_causal_and_cut_isolated']=True
            checks[f's{seed}_no_table_prompt_passthrough_and_no_cached_batch']=True
            # Read must ignore every private channel and round metadata.
            assert torch.equal(m.read(state)[0],m.read(altered)[0])
            m.halt.weight.zero_();m.halt.bias.fill_(20)
            inferred=m.infer(inputs,cap=3,min_rounds=2)
            assert inferred['rounds'].tolist()==[2,2]
            m.halt.bias.fill_(-20)
            assert m.infer(inputs,cap=3,min_rounds=2)['rounds'].tolist()==[3,3]
            checks[f's{seed}_learned_stop_removes_rows_and_cap']=True
        counts={}
        for arm in ARMS:
            control=build_model(arm)
            counts[arm]=parameter_counts(control)
            lg=control.rollout(inputs,rounds=2)['logits']
            assert torch.isfinite(lg).all()
        assert abs(counts['plain']['stored']/counts['compose']['stored']-1)<.005
        assert abs(counts['joint']['stored']/counts['compose']['stored']-1)<.005
        evidence['parameter_counts']=counts
        # No output translator can accept raw text, notebook store, or input tokens.
        decoder=FinalStateTranslator()
        assert list(inspect.signature(decoder.forward).parameters)==['final_state']
        with tempfile.TemporaryDirectory(prefix='sol-compose-contract-') as tmp:
            notebook=NotebookStore(Path(tmp)/'sol_compose_notebook.jsonl')
            # Exact user-origin phrase; STORE/INTERFACE CHECK ONLY, never training.
            raw=b'Need notebook accepts human English as data and reasoner retrieves/uses it, final translator sees state only.'
            ref=notebook.append(raw,origin='verified_human',source_ref='user-message-20260929',
                                origin_evidence='verbatim phrase from current human user; storage contract only')
            reloaded=NotebookStore(notebook.path)
            assert reloaded.raw([ref])==[raw]
            try:
                notebook.append(raw,origin='model',source_ref='test',origin_evidence='not human')
                raise AssertionError('model origin accepted')
            except ValueError:
                pass
            encoder=ByteFactEncoder()
            memory=encoder(reloaded.raw([ref]),reloaded.references([ref]))
            ext=type(memory)(memory.values.expand(2,-1,-1),memory.valid.expand(2,-1))
            outputs=build_model('joint').rollout(inputs,rounds=2,memory=ext)
            assert outputs['state'].board.shape==(2,11,D)
            assert decoder(outputs['state'].board).shape==(2,11,125)
        checks[f's{seed}_human_raw_notebook_digest_latent_only_boundary']=True
    # Source API compatibility using copied source class definitions; no source
    # checkpoint, environment import, task benchmark or optimizer operation.
    from sol_compose_source_interface import Net
    from sol_compose_context import BaseContextAdapter, export_composer
    from sol_compose_notebook import NotebookState
    from sol_compose_run import save_checkpoint, load_checkpoint, ensure_budget
    import time
    base=BaseContextAdapter(Net('loop'))
    t=torch.randint(2,12,(2,2,4));slots=torch.zeros_like(t)
    notebook=NotebookState(torch.randn(2,3,64),torch.tensor([[True,True,False],[True,False,False]]))
    first=base.step(base.encode(t,slots,notebook))
    assert base.joined_output(first).shape==(2,8,64)
    assert base.read(first)[1].shape==(2,)
    empty=NotebookState(torch.zeros(2,0,64),torch.zeros(2,0,dtype=torch.bool))
    assert torch.isfinite(base.step(base.encode(t,slots,empty)).hidden).all()
    checks['source_tensor_api_notebook_attention_export_empty_memory']=True
    with tempfile.TemporaryDirectory(prefix='sol-compose-checkpoint-') as tmp:
        tmp=Path(tmp);model=build_model('compose')
        before=copy.deepcopy(model.state_dict())
        save_checkpoint(tmp/'sol_compose_roundtrip.pt',model,0,'contract',{},'0'*64)
        loaded,metadata=load_checkpoint(tmp/'sol_compose_roundtrip.pt','cpu')
        assert metadata['schema']=='sol_compose.joined.v1'
        assert all(torch.equal(before[k],v) for k,v in loaded.state_dict().items())
        try:
            ensure_budget(time.monotonic(),{'wall_seconds':100,'free_disk_floor_bytes':0,
                         'idle_file':str(tmp/'sol_compose_missing_idle')},tmp)
            raise AssertionError('sleep ignored missing idle marker')
        except InterruptedError:pass
        (tmp/'STOP').touch()
        try:
            ensure_budget(time.monotonic(),{'wall_seconds':100,'free_disk_floor_bytes':0},tmp)
            raise AssertionError('STOP ignored')
        except InterruptedError:pass
        checks['serialization_roundtrip_and_idle_STOP_guards_no_updates']=True
    checks['no_training_no_optimizer_steps']=True
    return dict(scope='contract only; random initialized; no empirical task performance',
                seeds=[0,1],torch=torch.__version__,checks=checks,passed=sum(checks.values()),
                total=len(checks),evidence=evidence,optimizer_steps=0,trained=False,holdout_opened=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path)
    result=contracts()
    args=parser.parse_args()
    if args.out:
        with args.out.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
