"""Pretrained-LM baseline on the skills rows: fine-tune an open HF causal LM, or few-shot it, and score with evalx.
  python3 -m custom_io.hf_baseline --hf-id EleutherAI/pythia-70m --mode finetune --steps 3000 --batch 64 --out runs/p70 --final-eval
  python3 -m custom_io.hf_baseline --hf-id EleutherAI/pythia-70m --mode fewshot --shots 8 --out runs/p70fs
Text: f"{prompt}\\nAnswer:" then " {answer}\\n" (+eos when training). No checkpoint is saved (the weights come from the hub).
--target steps (8A spec addendum A4; default `answer` = the text above, unchanged): the target after "Answer:" is plain_tf_steps' text,
models.plain_tf_steps.target_text(row) = the worked steps, ' # ', the answer (the answer alone for rows without steps), and a decoded text is
scored on what follows its last '#' (final_answer). --calc (with --target steps): the final eval also runs the `calc` lesion, the same weights with
the exact result forced in as tokens whenever the text ends with 'a op b =' (plain_tf_steps.calc_fill), stored under lesions['calc']."""
import argparse, contextlib, json, os, random, time, zlib
import numpy as np
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor, LogitsProcessorList, StoppingCriteria, StoppingCriteriaList
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.evalx import eval_all, short
from custom_io.models.base import Model
from custom_io.models.plain_tf_steps import calc_fill, final_answer, target_text
from custom_io.train import jprint, lr_at

MAX_NEW = 16
MAX_NEW_STEPS = 96       # --target steps: the steps + ' # ' + answer text is up to 76 chars, a digit-per-token tokenizer (SmolLM2) needs about that many tokens
POLICY = ("k train rows solved in the same format, joined by blank lines; sampled per eval row with "
          "RandomState(crc32('seed:rowid')) from the SAME family in train if it exists there (topped up with random train rows if "
          "fewer than k), else random train rows; the eval row's own prompt is excluded; oldest shots are dropped if the "
          "prompt + 16 new tokens would not fit the model context")


def ask(prompt):
    return f'{prompt}\nAnswer:'


def pad(seqs, value, left=False):
    T = max(map(len, seqs))
    out = torch.full((len(seqs), T), value, dtype=torch.long)
    for i, s in enumerate(seqs):
        a = T - len(s) if left else 0
        out[i, a:a + len(s)] = torch.tensor(s)
    return out


class StopAtNewline(StoppingCriteria):
    """Row is done when its last token contains a newline (HF's stop_strings rebuilds a vocab table on every generate call)."""

    def __init__(self, tok):
        self.ids = torch.tensor([i for i in range(len(tok)) if '\n' in tok.decode([i])])

    def __call__(self, input_ids, scores, **kw):
        return torch.isin(input_ids[:, -1], self.ids.to(input_ids.device))


class CalcForcer(LogitsProcessor):
    """Greedy-decode helper for the `calc` lesion: when a row's generated text ends with 'a op b =' (models.plain_tf_steps.calc_fill), the exact result is
    forced in, token by token, ahead of the model's own choice. Same trigger rule as PlainTFSteps.generate: a step that emitted a forced token never starts a new fill."""

    def __init__(self, lm, prompt_len):
        self.lm, self.pl, self.q, self.fp = lm, prompt_len, None, None

    def __call__(self, input_ids, scores):
        B = input_ids.shape[0]
        if self.q is None:
            self.q, self.fp = [[] for _ in range(B)], [False] * B
        gen = input_ids[:, self.pl:]
        for i in range(B):
            if not self.q[i] and not self.fp[i] and gen.shape[1] > 0:
                f = calc_fill(self.lm.tok.decode(gen[i], skip_special_tokens=True))
                if f:
                    self.q[i] = self.lm.ids(f)
            self.fp[i] = False
            if self.q[i]:
                t = self.q[i].pop(0)
                scores[i, :] = float('-inf')
                scores[i, t] = 0.0
                self.fp[i] = True
        return scores


class HFLM(Model):
    """Adapter over an HF causal LM following models/base.py: loss(batch) and generate(batch, lesion=None) -> list[str]
    (greedy, <=16 new tokens, cut at the first newline). Both read only batch['rows'] (prompt, answer), never the char ids.
    target='steps': the target is plain_tf_steps' target_text, decoded up to MAX_NEW_STEPS tokens and scored after the last '#'; lesion 'calc' = CalcForcer."""
    LESIONS = ['calc']

    def __init__(self, vocab, hf_id, revision=None, shots=0, train_rows=(), seed=0, target='answer'):
        super().__init__(vocab)
        assert target in ('answer', 'steps'), target
        self.target = target
        self.tok = AutoTokenizer.from_pretrained(hf_id, revision=revision)
        try:                    # transformers >= 4.56 takes dtype=; older versions (e.g. on Ben's machines) torch_dtype=
            self.lm = AutoModelForCausalLM.from_pretrained(hf_id, revision=revision, dtype=torch.float32)
        except TypeError:
            self.lm = AutoModelForCausalLM.from_pretrained(hf_id, revision=revision, torch_dtype=torch.float32)
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        bos = self.tok.bos_token_id
        self.pre = [bos] if bos is not None and self.tok('a').input_ids[:1] == [bos] else []   # BOS only if the tokenizer adds one
        self.ctx = getattr(self.lm.config, 'max_position_embeddings', None) or 2048
        self.k, self.seed, self.pool_rows = shots, seed, train_rows
        self.fam = {}
        for i, r in enumerate(train_rows if shots else ()):
            self.fam.setdefault(r['family'], []).append(i)
        self.n_seen, self.n_fewer, self.stop = 0, 0, StoppingCriteriaList([StopAtNewline(self.tok)])

    def ids(self, s):                   # prompt and answer are tokenised separately and concatenated (same in train and decode)
        return self.tok(s, add_special_tokens=False).input_ids

    def n_params_non_embedding(self):
        emb = {id(p) for m in (self.lm.get_input_embeddings(), self.lm.get_output_embeddings()) if m is not None for p in m.parameters()}
        return sum(p.numel() for p in self.parameters() if id(p) not in emb)

    def shots(self, row):
        rng = np.random.RandomState(zlib.crc32(f"{self.seed}:{row['id']}".encode()))
        pool = self.fam.get(row['family'], [])
        pick = [int(i) for i in rng.choice(pool, min(self.k + 1, len(pool)), replace=False)] if pool else []
        while len(pick) < self.k + 1:
            pick.append(int(rng.randint(len(self.pool_rows))))
        return [e for e in (self.pool_rows[i] for i in pick) if e['prompt'] != row['prompt']][:self.k]

    def prompt_ids(self, row):
        ex = self.shots(row) if self.k else []
        while True:
            ids = self.pre + self.ids('\n\n'.join([f"{e['prompt']}\nAnswer: {e['answer']}" for e in ex] + [ask(row['prompt'])]))
            if len(ids) + MAX_NEW <= self.ctx or not ex:
                break
            ex = ex[1:]
        self.n_seen += 1
        self.n_fewer += len(ex) < self.k
        return ids

    def loss(self, batch):              # loss only on " {answer}\n" + eos
        seqs, labs = [], []
        for r in batch['rows']:
            p = self.pre + self.ids(ask(r['prompt']))
            a = self.ids(f" {target_text(r) if self.target == 'steps' else r['answer']}\n") + [self.tok.eos_token_id]
            seqs.append(p + a)
            labs.append([-100] * len(p) + a)
        dev = self.lm.device
        return self.lm(input_ids=pad(seqs, self.tok.pad_token_id).to(dev), attention_mask=pad([[1] * len(s) for s in seqs], 0).to(dev),
                       labels=pad(labs, -100).to(dev)).loss

    def generate(self, batch, lesion=None):
        name, _ = self.check_lesion(lesion)
        assert name != 'calc' or self.target == 'steps', "the calc lesion needs --target steps"
        seqs, dev = [self.prompt_ids(r) for r in batch['rows']], self.lm.device
        x = pad(seqs, self.tok.pad_token_id, left=True).to(dev)
        steps = self.target == 'steps'
        kw = dict(logits_processor=LogitsProcessorList([CalcForcer(self, x.shape[1])])) if name == 'calc' else {}
        out = self.lm.generate(input_ids=x, attention_mask=pad([[1] * len(s) for s in seqs], 0, left=True).to(dev), do_sample=False,
                               max_new_tokens=MAX_NEW_STEPS if steps else MAX_NEW, pad_token_id=self.tok.pad_token_id, eos_token_id=self.tok.eos_token_id,
                               stopping_criteria=self.stop, **kw)
        txt = [t.split('\n')[0].strip() for t in self.tok.batch_decode(out[:, x.shape[1]:], skip_special_tokens=True)]
        return [final_answer(t) for t in txt] if steps else txt


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--hf-id', required=True, help='e.g. EleutherAI/pythia-70m, HuggingFaceTB/SmolLM2-135M')
    ap.add_argument('--revision', help='hub revision / branch / commit (e.g. a pythia stepN branch)')
    ap.add_argument('--mode', choices=['finetune', 'fewshot'], required=True)
    ap.add_argument('--shots', type=int, default=8, help='fewshot: solved examples per prompt')
    ap.add_argument('--data', default=DEFAULT_DATA, help='dir with train.jsonl and dev/')
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--warmup', type=int, default=300)
    ap.add_argument('--grad-clip', type=float, default=1.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--order', choices=['shuffled', 'curriculum'], default='shuffled')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--bf16', action='store_true', help='autocast bf16 (cuda only)')
    ap.add_argument('--log-every', type=int, default=100)
    ap.add_argument('--final-eval', action='store_true', help='finetune: eval after training (fewshot always evals)')
    ap.add_argument('--target', choices=['answer', 'steps'], default='answer', help="steps: train to write plain_tf_steps' steps then ' # ' then the answer, score after the last '#'")
    ap.add_argument('--calc', action='store_true', help='with --target steps and an eval: also score the calc lesion (exact results forced in after "a op b =")')
    ap.add_argument('--caps', help='caps.json (g8a.caps): sizes the prompt/answer caps and the generation length from the data')
    ap.add_argument('--eval-max', type=int, help='cap rows per dev split')
    ap.add_argument('--eval-batch', type=int, default=64, help='fewshot prompts are ~10x longer than a plain prompt: keep it modest')
    ap.add_argument('--minutes', type=float, help='wall-clock cap on training; still evals afterwards')
    ap.add_argument('--out', help='dir for RESULT.json (no checkpoint is written)')
    args = ap.parse_args(argv)
    if args.caps:
        global MAX_NEW, MAX_NEW_STEPS
        from custom_io.g8a import caps as _caps
        _c = _caps.apply(json.load(open(args.caps)))
        MAX_NEW, MAX_NEW_STEPS = max(MAX_NEW, _c['max_ans'] + 8), max(MAX_NEW_STEPS, 2 * (_c['plain_target'] + _c['max_ans'] + 4))
    ft = args.mode == 'finetune'
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if args.bf16 and device.type == 'cuda' else contextlib.nullcontext
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    transformers.logging.set_verbosity_error(); transformers.logging.disable_progress_bar()
    t_start = time.time()

    rows = load_rows(os.path.join(args.data, 'train.jsonl'))
    vocab = CharVocab.get(args.data, None, rows)           # only so evalx can build its char batches; the LM never sees them
    assert args.target == 'answer' or ft, '--target steps is for --mode finetune'
    assert not args.calc or args.target == 'steps', '--calc needs --target steps'
    model = HFLM(vocab, args.hf_id, args.revision, 0 if ft else args.shots, rows, args.seed, args.target).to(device)
    batches = train_batches(Dataset(rows, vocab), args.batch, args.order, args.seed) if ft else None   # same row order as train.py
    n_params, n_ne = model.n_params(), model.n_params_non_embedding()
    jprint(event='start', hf_id=args.hf_id, mode=args.mode, n_params=n_params, n_params_non_embedding=n_ne, device=str(device), rows=len(rows))

    t0, step, run_loss, run_n, last_loss, status = time.time(), 0, 0.0, 0, None, 'ok'
    cap = args.minutes * 60 if args.minutes else None
    if ft:
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.0, fused=device.type == 'cuda')
        model.train()
    while ft and step < args.steps:
        elapsed = time.time() - t0
        if cap and elapsed >= cap:
            status = 'time_cap'
            break
        lr = lr_at(step, args.steps, args.warmup, args.lr, elapsed, cap)
        for g in opt.param_groups:
            g['lr'] = lr
        batch = to_device(next(batches), device)
        with amp():
            loss = model.loss(batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step(); opt.zero_grad(set_to_none=True)
        step += 1
        run_loss += loss.detach(); run_n += 1
        if step % args.log_every == 0 or step == args.steps:
            last_loss = float(run_loss) / run_n
            jprint(event='train', step=step, loss=round(last_loss, 5), lr=round(lr, 7), elapsed=round(time.time() - t0, 1))
            run_loss, run_n = 0.0, 0
            if not np.isfinite(last_loss):
                status = 'nonfinite_loss'
                break
    if device.type == 'cuda':
        torch.cuda.synchronize()
    train_s = (time.time() - t0) if ft else 0.0
    cfg = dict(vars(args), transformers=transformers.__version__, resolved_revision=getattr(model.lm.config, '_commit_hash', None),
               text_format='{prompt}\\nAnswer: -> " {answer}\\n" (+eos in training); greedy, 16 new tokens, cut at first newline',
               shots_policy=None if ft else POLICY)
    result = dict(config=cfg, n_params=n_params, n_params_non_embedding=n_ne, steps=step, status=status, final_train_loss=last_loss,
                  train_s=train_s, steps_per_s=step / max(train_s, 1e-9), final_eval=None, lesions={})

    def write():
        result['wall_s'] = time.time() - t_start
        if args.out:
            os.makedirs(args.out, exist_ok=True)
            json.dump(result, open(os.path.join(args.out, 'RESULT.json'), 'w'), indent=1)
    write()                                            # trained-model stats survive even if the eval below dies
    if args.final_eval or not ft:
        with amp():
            result['final_eval'] = eval_all(model, args.data, args.eval_max, None, args.eval_batch, device)
        if not ft:
            result['fewshot_rows_with_fewer_shots'] = f'{model.n_fewer}/{model.n_seen}'
        jprint(event='eval', lesion=None, **short(result['final_eval']))
        if args.calc:
            write()
            with amp():
                result['lesions']['calc'] = eval_all(model, args.data, args.eval_max, 'calc', args.eval_batch, device)
            jprint(event='eval', lesion='calc', **short(result['lesions']['calc']))
    write()
    jprint(event='done', steps=step, status=status, steps_per_s=round(result['steps_per_s'], 3), wall_s=round(result['wall_s'], 1),
           **(short(result['final_eval']) if result['final_eval'] else {}))
    return result


if __name__ == '__main__':
    main()
