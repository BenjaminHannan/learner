"""CPU test of packed.py on a tiny Qwen3_5Moe built from the real Qwen3.6-35B-A3B config (shrunk). python speed/qwen36_mem/test_packed.py  -> one JSON line; asserts the bitwise claims.
(i) pack/unpack == sleepb.q4_fake bit for bit (bf16 / fp32, 4 / 8 bit, 2-D / 3-D, constant group, tiny values); (ii) every packed weight == the q4_apply qdq copy; (iii) logits and LoRA grads of the packed model
vs the bf16 qdq model; (iv) what autograd saves for backward (dense expert weights vs none); (v) parameter bytes before / after."""
import copy, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "../../backbone/sleep/brain"), os.path.join(HERE, "../../backbone")]
import torch
import packed as P
import sleepb

DT = torch.bfloat16  # the dtype on the GPU (scale / bias are stored in it)


def tiny(vocab=512, layers=4):
    from transformers import AutoConfig, Qwen3_5MoeForCausalLM
    try:
        c = AutoConfig.from_pretrained("Qwen/Qwen3.6-35B-A3B").text_config
    except Exception:  # offline: the same numbers by hand
        from transformers import Qwen3_5MoeTextConfig as C
        c = C(hidden_act="silu", rms_norm_eps=1e-6, linear_conv_kernel_dim=4, rope_parameters={"mrope_interleaved": True, "mrope_section": [11, 11, 10], "partial_rotary_factor": 0.25, "rope_theta": 10000000, "rope_type": "default"})
    c.update(dict(vocab_size=vocab, hidden_size=256, num_hidden_layers=layers, layer_types=["linear_attention"] * (layers - 1) + ["full_attention"], num_attention_heads=4, num_key_value_heads=2, head_dim=64,
                  linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=64, linear_value_head_dim=64, moe_intermediate_size=128, shared_expert_intermediate_size=128, num_experts=8,
                  num_experts_per_tok=2, mtp_num_hidden_layers=0, max_position_embeddings=512, tie_word_embeddings=False, eos_token_id=1, pad_token_id=0, bos_token_id=1))
    torch.manual_seed(0)
    lm = Qwen3_5MoeForCausalLM(c).to(DT).eval()
    for p in lm.parameters():
        p.requires_grad_(False)
    lm.set_experts_implementation("grouped_mm")
    return lm


def pack_math(out):
    g = torch.Generator().manual_seed(1)
    n = 0
    for dt in (torch.bfloat16, torch.float32):
        for bits in (4, 8):
            for shape in ((8, 128), (3, 5, 192), (2, 64)):
                w = (torch.randn(*shape, generator=g) * torch.rand(shape[0], *[1] * (len(shape) - 1), generator=g) * 3).to(dt)
                w[0, ..., :64] = 0.5  # a constant group (max == min)
                w[-1, ..., 64:128] *= 1e-30  # tiny values
                ref = sleepb.q4_fake(w, 64, bits)
                for chunk in (1 << 26, 100):  # one piece / many slices
                    c, s, b = P.pack(w, 64, bits, chunk)
                    assert torch.equal(P.unpack(c, s, b, bits, 64, dt, chunk), ref), (dt, bits, shape, chunk)
                n += 1
    assert P.pack(torch.randn(4, 100), 64, 4) is None
    out["pack_math_cases_bitwise_equal"] = n


def saved_bytes(fn):
    """Run fn() under saved_tensors_hooks; (total bytes of tensors autograd saved, bytes of those with >= 3 dims and >= 50k elements = dense expert weights)."""
    tot = [0, 0]
    def hook(t):
        tot[0] += t.numel() * t.element_size()
        if t.dim() >= 3 and t.numel() >= 50000 and t.shape[0] == 8:
            tot[1] += t.numel() * t.element_size()
        return t
    with torch.autograd.graph.saved_tensors_hooks(hook, lambda t: t):
        return fn(), tot


def main():
    out = {"torch": torch.__version__}
    pack_math(out)
    base = tiny()
    ref = copy.deepcopy(base)
    sleepb.q4_apply(ref, 64, 4, sleepb.Q4_MLX_MOE_BITS, sleepb.Q4_MLX_MOE_PARAMS)  # today's qdq copy
    pk = copy.deepcopy(base)
    st = P.pack_model(pk, min_numel=0)  # min_numel 0: pack every Linear that can be
    out["pack_model"] = st
    # (ii) weights
    dv = P.dense_view(pk)
    rsd = {n: p for n, p in ref.named_parameters()}
    nbad = nchk = 0
    for n, w in dv.items():
        nchk += 1
        nbad += not torch.equal(w, rsd[n].data)
    for n, p in pk.named_parameters():  # dense leftovers (embedding, routers, shared_expert_gate, ...)
        nchk += 1
        nbad += not torch.equal(p.data, rsd[n].data)
    assert nbad == 0, nbad
    out["weights_checked_bitwise_equal"] = nchk
    out["param_bytes"] = {"qdq_bf16": sum(p.numel() * 2 for p in ref.parameters()), "packed": st["bytes_after"]}
    out["packed_tensors"] = {"experts": st["packed_experts"], "linear": st["packed_linear"], "dense": st["dense_qdq"]}
    # (iii) forward + LoRA grads
    from peft import LoraConfig, get_peft_model
    from train import LORA_TARGETS
    cfg = LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, target_modules=LORA_TARGETS + r"|.*\.layers\.\d+\.mlp\.shared_expert\.(gate_proj|up_proj|down_proj)", bias="none")
    pm_r, pm_p = get_peft_model(ref, cfg), get_peft_model(pk, cfg)
    g = torch.Generator().manual_seed(2)
    dp = dict(pm_p.named_parameters())
    for n, a in pm_r.named_parameters():
        if a.requires_grad:
            b = dp[n]
            v = torch.randn(a.shape, generator=g) * 0.05
            a.data.copy_(v)
            b.data.copy_(v)
    ntrain = sum(p.numel() for p in pm_p.parameters() if p.requires_grad)
    out["lora_params"] = ntrain
    ids = torch.randint(2, 512, (2, 48), generator=g)
    tgt = torch.randint(2, 512, (2, 48), generator=g)

    def run(pm):
        pm.zero_grad()
        lg = pm(input_ids=ids).logits
        loss = torch.nn.functional.cross_entropy(lg.float().reshape(-1, lg.shape[-1]), tgt.reshape(-1))
        loss.backward()
        return lg.detach(), loss.item(), {n: p.grad.clone() for n, p in pm.named_parameters() if p.requires_grad and p.grad is not None}
    (lp, ls_p, gp) = run(pm_p)
    (lr_, ls_r, gr) = run(pm_r)
    assert gr.keys() == gp.keys() and len(gr) > 0
    out["logits_max_abs_diff"] = (lr_.float() - lp.float()).abs().max().item()
    out["logits_scale"] = lr_.float().abs().max().item()
    out["loss_ref_packed"] = [ls_r, ls_p]
    out["lora_grad_max_abs_diff"] = max((gr[k].float() - gp[k].float()).abs().max().item() for k in gr)
    out["lora_grad_max_abs"] = max(gr[k].float().abs().max().item() for k in gr)
    out["lora_grad_tensors"] = len(gr)
    out["lora_grad_nonzero_in_layer0"] = any(v.abs().max() > 0 for k, v in gr.items() if ".layers.0." in k)
    # (iv) what is saved for backward
    def fwd(pm):
        return pm(input_ids=ids).logits
    _, svr = saved_bytes(lambda: fwd(pm_r))
    _, svp = saved_bytes(lambda: fwd(pm_p))
    out["saved_for_backward_bytes"] = {"qdq": {"all": svr[0], "dense_expert_weights": svr[1]}, "packed": {"all": svp[0], "dense_expert_weights": svp[1]}}
    assert svp[1] == 0
    # no-grad generation path
    with torch.no_grad():
        out["nograd_logits_equal"] = bool(torch.equal(pm_r(input_ids=ids).logits, pm_p(input_ids=ids).logits))
    # compile (optional: needs a C++ compiler)
    try:
        c, s, b = P.pack(torch.randn(4, 3, 128).to(DT), 64, 4)
        out["compile_unpack_bitwise_equal"] = bool(torch.equal(P.unpack(c, s, b, 4, 64, DT, compile=True), P.unpack(c, s, b, 4, 64, DT)))
    except Exception as e:  # noqa: BLE001
        out["compile_unpack_bitwise_equal"] = f"not run: {repr(e)[:120]}"
    print(json.dumps(out))


if __name__ == "__main__":
    main()
