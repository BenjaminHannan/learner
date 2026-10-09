"""CPU probe of the core's 8 front vectors inside the real frozen LFM2.5-1.2B (no GPU, no training).

Rebuilds reader + core + StatePrefix from the real checkpoints (pilot parent seed 0, skills main2) with the
pipeline's own core code, feeds hand-written curriculum-style questions, and measures:
  1. the norm of each of the 8 front vectors vs the question's own word vectors and BOS;
  2. how much the LM changes those positions layer by layer (cosine to the input vector);
  3. how much of the answer's attention lands on the 8 front positions;
  4. the gradient that reaches the front vectors vs the question's word vectors;
  5. how similar the front vectors are across questions (same family vs different family).
Layout = the copy path the skills runs train with: [8 front][question + EOS][BOS][answer].
"""
import json
import math
import sys
from pathlib import Path

import torch
from torch import nn

S = Path(__file__).resolve().parent
sys.path[:0] = [str(S / 'rpc/pipeline/scripts'), str(S / 'rpc/pipeline/scripts/cap256_launch'), str(S / 'rpc/pipeline')]
torch.set_num_threads(4)
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from fresh_core_calculator_constructor import build_fresh_core  # noqa: E402
import english_ordered_begin_cap64_v1 as cap64  # noqa: E402

BOS, EOS = 1, 7
PROMPTS = [
    ('group_induct', 'Question time. Group A: 40, 78, 60. Group B: 27, 69, 81. Which group does 54 belong to?', 'A'),
    ('group_induct', 'Group A: 20, 68, 80. Group B: 81, 79, 27. Which group does 60 belong to?', 'A'),
    ('group_induct', 'Group A: 12, 30, 44. Group B: 15, 33, 51. Which group does 21 belong to?', 'B'),
    ('group_induct', 'Try this. Group A: 9, 27, 45. Group B: 10, 32, 50. Which group does 64 belong to?', 'B'),
    ('seq_cycle', 'Next problem: The pattern t w q i repeats forever. What is item number 9?', 't'),
    ('seq_cycle', 'A small challenge: The pattern m r c repeats forever. What is item number 9?', 'c'),
    ('seq_cycle', 'The pattern a s e repeats forever. What is item number 10?', 'a'),
    ('seq_cycle', 'u e c t u e c t u e c ? What comes next?', 't'),
    ('chain_story2', 'Solve this. Vic has 46 beads. Then Vic uses up 31. Then Vic loses 13. How many beads does Vic have at the end?', '2'),
    ('chain_story2', 'Zoe has 10 boxes with 3 pencils in each. Then Zoe gives away 24 of the pencils. How many pencils does Zoe have now?', '6'),
    ('chain_story2', 'Ana has 25 shells. Then Ana finds 17 more. Then Ana gives away 9. How many shells does Ana have at the end?', '33'),
    ('chain_story2', 'Tom has 8 bags with 4 apples in each. Then Tom eats 5 of the apples. How many apples does Tom have now?', '27'),
    ('fewshot_number_rule', 'Examples: 22 -> 44; 23 -> 45; 25 -> 47. Now 8 -> ? Be brief.', '30'),
    ('fewshot_number_rule', 'Quick one: Examples: 28 -> 58; 9 -> 39. Now 18 -> ?', '48'),
    ('fewshot_number_rule', 'Try this problem. Examples: (47, 16) -> 63; (26, 12) -> 38. Now (47, 16) -> ?', '63'),
    ('fewshot_number_rule', 'Examples: 3 -> 12; 5 -> 20; 7 -> 28. Now 6 -> ?', '24'),
    ('cipher_map', 'Code: e=4, h=2, a=5, b=1. Write beb as numbers.', '1 4 1'),
    ('cipher_map', 'Code: d=7, a=6, c=3. Write dac as numbers.', '7 6 3'),
    ('cipher_map', 'Code: k=9, m=2, o=8. Write mok as numbers.', '2 8 9'),
    ('cipher_map', 'Code: r=5, s=1, t=6. Write tsr as numbers.', '6 1 5'),
    ('state_update', 'A jar holds 32 marbles. 4 are removed. 7 are added. How many marbles are in the jar now?', '35'),
    ('state_update', 'A box holds 18 coins. 6 are added. 9 are removed. How many coins are in the box now?', '15'),
    ('state_update', 'A shelf holds 40 books. 12 are removed. 5 are added. How many books are on the shelf now?', '33'),
    ('state_update', 'A tank holds 21 fish. 8 are added. 3 are removed. How many fish are in the tank now?', '26'),
    ('var_chain', 'Here is a puzzle. Facts: q = 8. p = q * 4. n = p + 9. Question: What is n?', '41'),
    ('var_chain', 'Facts: a = 5. b = a + 7. c = b * 2. Question: What is c?', '24'),
    ('var_chain', 'Facts: x = 30. y = x - 12. z = y / 3. Question: What is z?', '6'),
    ('var_chain', 'Facts: m = 6. k = m * 6. j = k - 10. Question: What is j?', '26'),
    ('chain_ops', 'Start with 10. Subtract 5. Multiply by 5. What is the result?', '25'),
    ('chain_ops', 'Start with 7. Add 9. Multiply by 2. What is the result?', '32'),
    ('chain_ops', 'Start with 50. Divide by 5. Add 13. What is the result?', '23'),
    ('chain_ops', 'Start with 12. Multiply by 3. Subtract 20. What is the result?', '16'),
]


class Reader(nn.Module):  # HumanInputProjection(2048, 256, hidden=32)
    def __init__(self):
        super().__init__()
        self.proj = nn.Sequential(nn.LayerNorm(2048), nn.Linear(2048, 32), nn.GELU(), nn.Linear(32, 256))

    def forward(self, f, valid):
        return (self.proj(f.float()) * valid[..., None]).unsqueeze(1)


class StatePrefix(nn.Module):  # sol_translator_english_v6.StatePrefix, copied
    def __init__(self):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(256))
        self.bias = nn.Parameter(torch.zeros(256))
        self.project = nn.Sequential(nn.Linear(259, 32), nn.GELU(), nn.Linear(32, 2048))

    def forward(self, state, slots, cols):
        h = state.float()
        mean = h.mean(-1, keepdim=True)
        var = (h - mean).square().mean(-1, keepdim=True)
        normalized = (h - mean) * torch.rsqrt(var + 1e-5)
        r = torch.zeros(cols)
        c = torch.arange(cols).float() / max(cols - 1, 1)
        geom = torch.stack((r, c), -1)[None]
        x = self.project(torch.cat((normalized * self.scale + self.bias, geom, slots[..., None].float()), -1))
        return torch.nn.functional.adaptive_avg_pool1d(x[0].T[None], 8)[0].T[None]


def main():
    tok = AutoTokenizer.from_pretrained(S / 'lfm')
    lm = AutoModelForCausalLM.from_pretrained(S / 'lfm', dtype=torch.float32, attn_implementation='eager')
    lm.eval().requires_grad_(False)
    emb = lm.get_input_embeddings()
    att_layers = [i for i, t in enumerate(lm.config.layer_types) if t == 'full_attention']
    vocab_norm = float(emb.weight.norm(dim=1).mean())
    out = {'vocab_mean_embedding_norm': round(vocab_norm, 4), 'attention_layers': att_layers, 'n_prompts': len(PROMPTS)}

    # bare LM: natural norms (BOS + question), for reference
    bare = []
    for fam, p, a in PROMPTS[::4]:
        ids = torch.tensor([[BOS] + tok.encode(p, add_special_tokens=False)])
        hs = lm(input_ids=ids, output_hidden_states=True).hidden_states
        bare.append([[float(h[0, 0].norm()), float(h[0, 1:].norm(dim=-1).mean())] for h in hs])
    out['bare_lm_norm_by_layer'] = {'BOS': [round(sum(b[l][0] for b in bare) / len(bare), 1) for l in range(len(bare[0]))],
                                    'question_tokens': [round(sum(b[l][1] for b in bare) / len(bare), 1) for l in range(len(bare[0]))]}

    for ck_name in ('parent0', 'main2'):
        saved = torch.load(S / 'ck' / (ck_name + '.pt'), map_location='cpu', weights_only=True)
        core = build_fresh_core('shallow', 0, 'cpu')
        core.load_state_dict(saved['core'], strict=True)
        cap64.bind_english_cap64(core)
        reader, prefix = Reader(), StatePrefix()
        reader.load_state_dict(saved['reader'], strict=True)
        prefix.load_state_dict(saved['prefix'], strict=True)
        for m in (core, reader, prefix):
            m.eval().requires_grad_(False)
        recs = []
        for fam, p, a in PROMPTS:
            ids = torch.tensor([tok.encode(p, add_special_tokens=False) + [EOS]])
            n = ids.shape[1]
            mask = torch.ones(1, n, dtype=torch.bool)
            with torch.no_grad():
                f = lm.model(input_ids=ids, attention_mask=mask.long(), position_ids=torch.arange(n)[None],
                             use_cache=False).last_hidden_state
                q = reader(f, mask)
                st = core.begin_latent(q, None, query_mask=mask)
                for _ in range(4):
                    st = core.advance_latent(st)
                h, _ = core.read_latent(st)
                pref = prefix(h, mask, n)  # [1, 8, 2048]
            ans = tok.encode(' # ' + a if False else a, add_special_tokens=False) + [EOS]
            tgt = torch.tensor([ans])
            shifted = torch.cat([torch.tensor([[BOS]]), tgt[:, :-1]], 1)
            pref_leaf = pref.clone().requires_grad_(True)
            pe = emb(ids).detach().clone().requires_grad_(True)
            x = torch.cat([pref_leaf, pe, emb(shifted)], 1)
            o = lm(inputs_embeds=x, output_hidden_states=True, output_attentions=True, use_cache=False)
            P, A0 = 8, 8 + n  # prefix positions [0,8), question [8, 8+n), answer from A0 (BOS) on
            logits = o.logits[:, A0:].float()
            ce = torch.nn.functional.cross_entropy(logits.transpose(1, 2), tgt)
            ce.backward()
            hs = o.hidden_states
            x0 = hs[0][0]
            rec = {'family': fam, 'n': n, 'ce': float(ce), 'pref_norm_each': [float(v) for v in pref[0].norm(dim=-1)],
                   'q_emb_norm': float(pe[0].norm(dim=-1).mean()), 'bos_emb_norm': float(emb.weight[BOS].norm()),
                   'pref_flat': pref[0].flatten(),
                   'layer_norm_prefix': [float(hl[0, :P].norm(dim=-1).mean()) for hl in hs],
                   'layer_norm_question': [float(hl[0, P:A0].norm(dim=-1).mean()) for hl in hs],
                   'layer_norm_bos': [float(hl[0, A0].norm()) for hl in hs],
                   'cos_to_input_prefix': [float(torch.nn.functional.cosine_similarity(hl[0, :P], x0[:P], dim=-1).mean()) for hl in hs],
                   'cos_to_input_question': [float(torch.nn.functional.cosine_similarity(hl[0, P:A0], x0[P:A0], dim=-1).mean()) for hl in hs],
                   'attn_to_prefix': [float(at[0, :, A0:, :P].sum(-1).mean()) for at in o.attentions],
                   'attn_to_question': [float(at[0, :, A0:, P:A0].sum(-1).mean()) for at in o.attentions],
                   'grad_prefix_each': float(pref_leaf.grad[0].norm(dim=-1).mean()),
                   'grad_question_each': float(pe.grad[0].norm(dim=-1).mean()),
                   'grad_prefix_radial_cos': float(torch.nn.functional.cosine_similarity(pref_leaf.grad[0], pref[0], dim=-1).abs().mean())}
            recs.append(rec)
            print(ck_name, fam, 'ce %.3f' % rec['ce'], 'pref %.0f' % (sum(rec['pref_norm_each']) / 8), flush=True)
        Pm = torch.stack([r['pref_flat'] for r in recs])
        Pn = torch.nn.functional.normalize(Pm, dim=1)
        cos = Pn @ Pn.T
        fams = [r['family'] for r in recs]
        same = [float(cos[i, j]) for i in range(len(recs)) for j in range(len(recs)) if i < j and fams[i] == fams[j]]
        diff = [float(cos[i, j]) for i in range(len(recs)) for j in range(len(recs)) if i < j and fams[i] != fams[j]]
        mean_pref = Pm.mean(0)
        dev_rel = float(((Pm - mean_pref).norm(dim=1) / Pm.norm(dim=1)).mean())

        def avg(key):
            return [round(sum(r[key][i] for r in recs) / len(recs), 3) for i in range(len(recs[0][key]))]
        out[ck_name] = {
            'update': saved.get('update'),
            'front_vector_norm_mean': round(sum(sum(r['pref_norm_each']) / 8 for r in recs) / len(recs), 1),
            'front_vector_norm_min_max': [round(min(min(r['pref_norm_each']) for r in recs), 1), round(max(max(r['pref_norm_each']) for r in recs), 1)],
            'question_word_vector_norm_mean': round(sum(r['q_emb_norm'] for r in recs) / len(recs), 4),
            'bos_vector_norm': round(recs[0]['bos_emb_norm'], 4),
            'ratio_front_to_word': round(sum(sum(r['pref_norm_each']) / 8 for r in recs) / sum(r['q_emb_norm'] for r in recs), 1),
            'answer_ce_mean': round(sum(r['ce'] for r in recs) / len(recs), 3),
            'hidden_norm_by_layer_front': avg('layer_norm_prefix'),
            'hidden_norm_by_layer_question': avg('layer_norm_question'),
            'hidden_norm_by_layer_bos': avg('layer_norm_bos'),
            'cos_to_own_input_by_layer_front': avg('cos_to_input_prefix'),
            'cos_to_own_input_by_layer_question': avg('cos_to_input_question'),
            'answer_attention_on_front_by_attn_layer': avg('attn_to_prefix'),
            'answer_attention_on_question_by_attn_layer': avg('attn_to_question'),
            'grad_norm_per_front_vector': sum(r['grad_prefix_each'] for r in recs) / len(recs),
            'grad_norm_per_question_word_vector': sum(r['grad_question_each'] for r in recs) / len(recs),
            'grad_front_abs_cos_with_vector': round(sum(r['grad_prefix_radial_cos'] for r in recs) / len(recs), 4),
            'front_cos_same_family_mean': round(sum(same) / len(same), 4),
            'front_cos_diff_family_mean': round(sum(diff) / len(diff), 4),
            'front_rel_deviation_from_global_mean': round(dev_rel, 4),
        }
        out[ck_name]['grad_ratio_word_over_front'] = round(out[ck_name]['grad_norm_per_question_word_vector'] / out[ck_name]['grad_norm_per_front_vector'], 1)
    (S / 'probe_prefix_cpu.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
