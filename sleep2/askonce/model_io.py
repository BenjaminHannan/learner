"""Model / tokenizer loading and batched generation. K2-Horizon-3.7B (trust_remote_code, fp16 on a T4) or a tiny local Llama for CPU smoke runs.
Model name 'tiny:<dir>' loads a local tiny model (see make_tiny)."""
import json
import os
from pathlib import Path

import torch

from .config import MODEL_ID

SPECIALS = ["<|ifm|begin_of_text|>", "<|ifm|endoftext|>", "<|ifm|im_start|>", "<|ifm|im_end|>", "<ifm|think>", "</ifm|think>"]


def is_tiny(name):
    return str(name).startswith("tiny:")


def make_tiny(path, corpus, vocab=900, seed=0):
    """Build a tiny random Llama + a local byte-level BPE tokenizer with the K2 special tokens. No download. Returns the dir."""
    from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers
    from transformers import LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    tk = Tokenizer(models.BPE())
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    tr = trainers.BpeTrainer(vocab_size=vocab, special_tokens=SPECIALS, initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tk.train_from_iterator(corpus, tr)
    fast = PreTrainedTokenizerFast(tokenizer_object=tk, bos_token=SPECIALS[0], eos_token=SPECIALS[1], pad_token=SPECIALS[1], unk_token=None)
    fast.save_pretrained(path)
    torch.manual_seed(seed)
    cfg = LlamaConfig(vocab_size=len(fast), hidden_size=64, intermediate_size=128, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                      max_position_embeddings=2048, tie_word_embeddings=False, bos_token_id=fast.bos_token_id, eos_token_id=fast.eos_token_id, pad_token_id=fast.pad_token_id)
    LlamaForCausalLM(cfg).save_pretrained(path)
    return str(path)


def get_tokenizer(name):
    from transformers import AutoTokenizer
    if is_tiny(name):
        t = AutoTokenizer.from_pretrained(name[5:])
    else:
        t = AutoTokenizer.from_pretrained(name or MODEL_ID, trust_remote_code=True)
    t.padding_side = "left"
    if t.pad_token is None:
        t.pad_token = t.eos_token
    return t


def load_model(name, dtype=torch.float16, device="cuda", nf4=False):
    """nf4=True: bitsandbytes NF4 base weights (QLoRA) for 12 GB cards, where K2 LoRA at fp16/bf16 runs out of memory even at batch 1.
    peft's prepare_model_for_kbit_training is deliberately not called: it upcasts the embeddings and head to fp32 (+2.4 GiB on K2)."""
    from transformers import AutoModelForCausalLM
    kw = dict(trust_remote_code=True, attn_implementation="sdpa")
    src = name[5:] if is_tiny(name) else (name or MODEL_ID)
    if is_tiny(name):
        kw = {}
    elif str(device).startswith("cuda"):
        kw["device_map"] = {"": 0}  # load straight onto the GPU (CUDA_VISIBLE_DEVICES picks the lane's card); avoids ~10 GB of host RAM per lane
    nf4 = nf4 and not is_tiny(name)
    if nf4:
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True)
    try:
        m = AutoModelForCausalLM.from_pretrained(src, dtype=dtype, **kw)
    except TypeError:  # older transformers: torch_dtype
        m = AutoModelForCausalLM.from_pretrained(src, torch_dtype=dtype, **kw)
    if not nf4 and next(m.parameters()).device.type != str(device).split(":")[0]:  # a 4-bit model is placed by device_map and cannot be .to()'d
        m = m.to(device)
    m.config.use_cache = True
    return m


def stop_ids(tok):
    ids = [tok.convert_tokens_to_ids("<|ifm|im_end|>")]
    if tok.eos_token_id is not None:
        ids.append(tok.eos_token_id)
    return [i for i in ids if i is not None and i >= 0]


MOVE_WORDS = ("ACT", "ASK")
_DECODED = {}


def _decoded_vocab(tok):
    """Decoded text of every vocab id (cached per tokenizer object); ids whose text is empty/unknown stay ''."""
    key = id(tok)
    if key not in _DECODED:
        n = len(tok)
        out = []
        for a in range(0, n, 8192):
            out.extend(tok.batch_decode([[i] for i in range(a, min(n, a + 8192))], skip_special_tokens=False, clean_up_tokenization_spaces=False))
        _DECODED[key] = out
    return _DECODED[key]


class FirstWordProcessor:
    """LogitsProcessor: the reply must BEGIN with one of `words` (default ACT / ASK). While the text generated so far is a proper prefix of a
    keyword, only tokens that keep it a prefix of a keyword (or complete one, possibly with trailing text such as ' {') are allowed; once a keyword is
    complete the row is free. Stop tokens are not allowed before that. The model's own probabilities still choose ACT vs ASK.
    prompt_len = padded prompt length of the batch (left padding, so generated ids start at the same column in every row)."""

    def __init__(self, tok, prompt_len, words=MOVE_WORDS):
        self.tok, self.plen, self.words = tok, prompt_len, tuple(words)
        self.dec = _decoded_vocab(tok)
        self.done = {}
        self.allowed = {}

    def _ids(self, text):
        if text not in self.allowed:
            ok = []
            for i, d in enumerate(self.dec):
                if not d:
                    continue
                s = text + d
                if any(w.startswith(s) or s.startswith(w) for w in self.words):
                    ok.append(i)
            self.allowed[text] = torch.tensor(ok, dtype=torch.long)
        return self.allowed[text]

    def __call__(self, input_ids, scores):
        gen = input_ids[:, self.plen:]
        for r in range(scores.shape[0]):
            if self.done.get(r):
                continue
            text = self.tok.decode(gen[r].tolist(), skip_special_tokens=False, clean_up_tokenization_spaces=False) if gen.shape[1] else ""
            if any(text.startswith(w) for w in self.words):
                self.done[r] = True
                continue
            ids = self._ids(text).to(scores.device)
            if len(ids) == 0:
                continue
            keep = torch.full_like(scores[r], float("-inf"))
            keep[ids[ids < scores.shape[-1]]] = 0
            scores[r] = scores[r] + keep
        return scores


@torch.no_grad()
def generate(model, tok, prompts, max_new, temperature=0.0, seed=0, bs=8, log=None, first_words=None):
    """Batched generation with left padding; greedy when temperature == 0. Falls back to smaller batches on OOM / generate errors.
    first_words=("ACT","ASK") constrains the reply to start with one of them (assistant moves only; never the general/fact generations).
    Returns the decoded new text of every prompt (cut at the first <|ifm|im_end|>), in input order."""
    dev = next(model.parameters()).device
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    outs = [None] * len(prompts)
    stops = stop_ids(tok)
    i, cur_bs, k = 0, bs, 0
    was_training = model.training
    model.eval()
    use_cache_prev = getattr(model.config, "use_cache", True)
    model.config.use_cache = True
    while i < len(order):
        idx = order[i:i + cur_bs]
        enc = tok([prompts[j] for j in idx], return_tensors="pt", padding=True, add_special_tokens=False).to(dev)
        try:
            torch.manual_seed(seed * 1000003 + k)
            kwargs = dict(max_new_tokens=max_new, eos_token_id=stops, pad_token_id=tok.pad_token_id)
            if temperature > 0:
                kwargs.update(do_sample=True, temperature=temperature, top_p=1.0, top_k=0)
            else:
                kwargs.update(do_sample=False)
            if first_words:
                from transformers import LogitsProcessorList
                kwargs["logits_processor"] = LogitsProcessorList([FirstWordProcessor(tok, enc["input_ids"].shape[1], first_words)])
            g = model.generate(**enc, **kwargs)
        except (torch.OutOfMemoryError, RuntimeError) as e:
            if cur_bs == 1:
                raise
            if log:
                log(f"generate failed at bs={cur_bs} ({str(e)[:80]}); halving")
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            cur_bs = max(1, cur_bs // 2)
            continue
        new = g[:, enc["input_ids"].shape[1]:]
        for row, j in zip(new, idx):
            ids = row.tolist()
            cut = len(ids)
            for p, t in enumerate(ids):
                if t in stops:
                    cut = p
                    break
            outs[j] = tok.decode(ids[:cut], skip_special_tokens=False).replace(tok.pad_token or "", "")
        i += len(idx)
        k += 1
    model.config.use_cache = use_cache_prev
    if was_training:
        model.train()
    return outs


def gpu_info():
    if not torch.cuda.is_available():
        return "cpu"
    return f"{torch.cuda.get_device_name(0)} {torch.cuda.get_device_properties(0).total_memory / 2**30:.1f}GB"
