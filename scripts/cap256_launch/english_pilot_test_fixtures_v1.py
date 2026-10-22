"""Tiny CPU fixtures for the English pilot tests (fake tokenizer, fake frozen LM, fake parents).

The fake LM has the real LFM width (2048) so the real thin reader, real ordered
core, real StatePrefix and real tool module are exercised; only the frozen
language model and tokenizer are replaced. Nothing here is used by native runs.
"""
from pathlib import Path
import re
import sys
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for entry in (str(HERE), str(ROOT / 'scripts'), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

SERIALIZER_PATH = ROOT / ('artifacts/cap256-launch/contextual-input-compare-v1/'
                          'ENGLISH-PARAPHRASE-RECONSTRUCTION-CPU-FEASIBILITY-v1/'
                          'SMALL-TRAIN-QUALIFICATION-PREPARATION-v1')
VOCAB = 600
PIECE = re.compile(r'\s*(?:\w+|[^\w\s])|\s+$')


class FakeTokenizer:
    """Word-piece tokenizer with leading whitespace kept in the piece; exact round trip."""
    bos_token_id, eos_token_id, pad_token_id = 1, 7, 0

    def __init__(self):
        self.to_id, self.to_piece = {}, {}

    def _id(self, piece):
        if piece not in self.to_id:
            value = 8 + len(self.to_id)
            if value >= VOCAB:
                raise ValueError('fake vocabulary exhausted')
            self.to_id[piece], self.to_piece[value] = value, piece
        return self.to_id[piece]

    def pieces(self, text):
        found = PIECE.findall(text)
        if ''.join(found) != text:
            raise ValueError('fake tokenizer cannot round-trip this text')
        return found

    def encode(self, text, add_special_tokens=False):
        if add_special_tokens:
            raise ValueError('fixture admits add_special_tokens=False only')
        return [self._id(p) for p in self.pieces(text)]

    def decode(self, ids, skip_special_tokens=False):
        return ''.join(self.to_piece.get(int(i), '' if skip_special_tokens else '<%d>' % int(i)) for i in ids)

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        ids, offsets, position = [], [], 0
        for piece in self.pieces(text):
            ids.append(self._id(piece))
            start = position + (len(piece) - len(piece.lstrip())) if piece.strip() else position
            offsets.append((start, position + len(piece)))
            position += len(piece)
        result = {'input_ids': ids}
        if return_offsets_mapping:
            result['offset_mapping'] = offsets
        return result


def make_bank(passages=24):
    examples = []
    for p in range(passages):
        examples.append({
            'id': 'p%02d' % p, 'family': 'fixture',
            'source_text': 'Ana gave Ben %d red apples before lunch.' % (p + 2),
            'paraphrase': 'Before lunch, Ben got %d red apples from Ana.' % (p + 2),
            'questions': [
                {'question': 'Who gave the apples?', 'canonical_answer': 'Ana',
                 'accepted_answers': ['Ana'], 'type': 'who'},
                {'question': 'How many apples?', 'canonical_answer': str(p + 2),
                 'accepted_answers': [str(p + 2)], 'type': 'count'}],
            'all_asserted_facts': []})
    return {'examples': examples}


def load_serializer():
    import importlib.util
    spec = importlib.util.spec_from_file_location('_fixture_serializer_v2', SERIALIZER_PATH / 'english_clean_train_input_v2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_lm(torch, seed=55):
    nn = torch.nn

    class Backbone(nn.Module):
        def __init__(self, embedding):
            super().__init__()
            self.embed_tokens = embedding

        def forward(self, input_ids, **kwargs):
            x = self.embed_tokens(input_ids)
            steps = torch.arange(1, x.shape[1] + 1, device=x.device, dtype=x.dtype)[None, :, None]
            return types.SimpleNamespace(last_hidden_state=torch.tanh(x.cumsum(1) / steps))

    class FakeLM(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(VOCAB, 2048)
            self.model = Backbone(self.embedding)
            self.head = nn.Linear(2048, VOCAB)

        def get_input_embeddings(self):
            return self.embedding

        def forward(self, inputs_embeds, attention_mask=None, use_cache=False, **kwargs):
            steps = torch.arange(1, inputs_embeds.shape[1] + 1, device=inputs_embeds.device,
                                 dtype=inputs_embeds.dtype)[None, :, None]
            return types.SimpleNamespace(logits=self.head(torch.tanh(inputs_embeds.cumsum(1) / steps) * 4))

        def generate(self, inputs_embeds, attention_mask, max_new_tokens, do_sample, use_cache,
                     bos_token_id, eos_token_id, pad_token_id):
            x, out = inputs_embeds, []
            for _ in range(max_new_tokens):
                token = int(self.forward(x).logits[0, -1].argmax())
                out.append(token)
                if token == eos_token_id:
                    break
                x = torch.cat((x, self.embedding(torch.tensor([[token]], device=x.device))), 1)
            return torch.tensor([out], device=inputs_embeds.device, dtype=torch.long)

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        lm = FakeLM()
    return lm.eval().requires_grad_(False)


class Context:
    pass


def make_context(rt, tokenizer, bank, out=None, seed=55):
    """Frames, features, tensors, fake LM/decoder for CPU tests."""
    torch = rt.torch
    serializer = load_serializer()
    frames = serializer.build_all_frames(tokenizer, bank)
    lm = make_lm(torch, seed)
    dec = rt.FrozenEnglishDecoder(lm, 256, 1, 7, 32, 8)
    ctx = Context()
    ctx.lm, ctx.dec, ctx.device, ctx.out = lm, dec, 'cpu', out
    ctx.frames = frames
    ctx.frames_by_index = {f['frame_index']: f for f in frames}
    ctx.features = {}
    for f in frames:
        ids = torch.tensor(f['input_ids'], dtype=torch.long)
        mask = torch.tensor(f['input_mask'], dtype=torch.bool)
        ctx.features[f['frame_index']] = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
    import english_pilot_runtime_v1 as runtime
    ctx.tokens = runtime.frame_tensors(torch, frames, 'cpu')
    ctx.guard = lambda additional=0, check_wall=True: {}
    ctx.gpu_guard = lambda: {'device': 'cpu'}
    ctx.code = {'fixture': 'v1'}
    ctx.identity = {'schema': 'fixture'}
    ctx.config_sha256 = '0' * 64
    ctx.parent_update = 3

    def save_checkpoint(path, payload):
        with Path(path).open('xb') as handle:
            torch.save(payload, handle)
    ctx.save_checkpoint = save_checkpoint
    return ctx


def make_parent(rt, ctx, seed, updates=3):
    """A parent checkpoint with real modules, Adam moments (incl. tool params) and RNG."""
    import english_pilot_common_v1 as common
    import english_pilot_runtime_v1 as runtime
    torch = rt.torch
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(1000 + seed)
        modules = runtime.build_modules(rt, ctx.dec, seed, 'cpu')
        for _, m in modules:
            m.train().requires_grad_(True)
        parts = runtime.module_dict(modules)
        parts['core'].halt.requires_grad_(False)
        rt.cap64.bind_english_cap64(parts['core'])
        named = [(c + '.' + n, p) for c, m in modules for n, p in m.named_parameters() if p.requires_grad]
        opt = runtime.make_optimizer(torch, [p for _, p in named])
        participation = {}
        for step in range(updates):
            opt.zero_grad(set_to_none=True)
            index = [0, 2, 3][step % 3]
            _, mask, labels = ctx.tokens[index]
            h, _ = runtime.english_graph(rt, parts['core'], parts['reader'], ctx.features[index], mask)
            per, _, _ = runtime.english_loss(rt, ctx.lm, ctx.dec, h, mask, labels)
            per.mean().backward()
            for _, p in parts['tool'].named_parameters():
                p.grad = torch.full_like(p, 1e-3)  # parent trained the tool on arithmetic
            for name, p in named:
                if p.grad is not None:
                    participation[name] = participation.get(name, 0) + 1
            torch.nn.utils.clip_grad_norm_([p for _, p in named], 1)
            opt.step()
        del vars(parts['core'])['begin_latent']
        saved = {name: {k: v.detach().clone() for k, v in m.state_dict().items()} for name, m in modules}
        saved.update({'constructor': parts['core'].constructor(), 'tool_constructor': parts['tool'].constructor(),
                      'optimizer': opt.state_dict(), 'optimizer_parameter_names': [n for n, _ in named],
                      'participation': participation, 'update': updates})
    rng = common.rng_snapshot(torch)
    saved.update(rng)
    import copy
    return copy.deepcopy(saved)
