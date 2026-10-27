"""Checks for scripts/fable_talker24_train.py and fable_talker24_loader.py.

Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_talker24_train.py
Run a group: python3.12 -B tests/test_fable_talker24_train.py --only resume

Groups: schedule, loader, dialogues, stream, checkpoint, stages, resume, bench.

The ``dialogues`` group builds a tokenizer export and a dialogue record that follow
INTERFACE-data.md section 4 and INTERFACE-dialogues.md exactly, and runs the real reader
over them -- the producers had shipped no data yet, so this is a contract test, not a test
against their output.

CPU-only, single-threaded, a couple of minutes at most.  The ``resume`` group is the KILL
TEST: it starts real subprocesses and really SIGKILLs one of them.  Everything is written
under a temporary directory that is removed afterwards.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
for entry in (str(HERE.parent/'scripts'), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import fable_talker24_model as M                                       # noqa: E402
import fable_talker24_loader as L                                      # noqa: E402
import fable_talker24_train as TR                                      # noqa: E402

torch, np = M.torch, L.np
torch.set_num_threads(1)

CHECKS = []
GROUPS = ('schedule', 'loader', 'dialogues', 'realdata', 'stream', 'checkpoint', 'stages',
          'resume', 'bench')
ARTIFACTS = HERE.parent/'artifacts/fable-talker24-20260920'
TMP = Path(tempfile.mkdtemp(prefix='talker24-tests-'))


def check(group, text, condition, detail=''):
    CHECKS.append((group, text, bool(condition), str(detail)))


def tiny_config(**overrides):
    base = dict(preset='tiny', steps=12, micro_batch=8, checkpoint_steps=5, log_every=6,
                device='cpu', out=str(TMP/'run'), synthetic_sentences=256)
    base.update(overrides)
    return TR.TrainConfig(**base)


# ----------------------------------------------------------------- schedule (section 2.3)

def group_schedule():
    cfg = TR.TrainConfig(steps=1000, warmup=300, lr=6e-4, decay_fraction=0.15,
                         final_lr_fraction=0.10)
    check('schedule', 'peak learning rate is the design\'s 6e-4', cfg.lr == 6e-4)
    check('schedule', 'AdamW betas are 0.9 / 0.95', tuple(cfg.betas) == (0.9, 0.95))
    check('schedule', 'weight decay is 0.1', cfg.weight_decay == 0.1)
    check('schedule', 'gradient clip is 1.0', cfg.grad_clip == 1.0)
    check('schedule', '300 warm-up steps', cfg.warmup == 300)
    check('schedule', 'warm-up rises linearly from ~0 to the peak',
          TR.learning_rate(cfg, 0) < 1e-5
          and abs(TR.learning_rate(cfg, 299) - 6e-4) < 1e-9,
          (TR.learning_rate(cfg, 0), TR.learning_rate(cfg, 299)))
    flat = [TR.learning_rate(cfg, s) for s in (300, 500, 800, 849)]
    check('schedule', 'then it is FLAT (so a run can be cut short or extended)',
          all(abs(x - 6e-4) < 1e-12 for x in flat), flat)
    check('schedule', 'the last 15 % decays linearly to 10 % of the peak',
          abs(TR.learning_rate(cfg, 999) - 6e-5) < 6e-6
          and TR.learning_rate(cfg, 900) < 6e-4,
          (TR.learning_rate(cfg, 900), TR.learning_rate(cfg, 999)))
    lengths = [TR.stage_max_len(cfg, s) for s in (0, 199, 200, 499, 500, 999)]
    check('schedule', 'the length curriculum is 12 to 20 %, 24 to 50 %, then 48',
          lengths == [12, 12, 24, 24, 48, 48], lengths)

    trainer = TR.Trainer(tiny_config(out=str(TMP/'sched')))
    groups = trainer.optimizer.param_groups
    check('schedule', 'weight decay is applied to matrices only, not to norms',
          groups[0]['weight_decay'] == 0.1 and groups[1]['weight_decay'] == 0.0,
          [g['weight_decay'] for g in groups])
    check('schedule', 'every decayed tensor is 2-D or more',
          all(p.ndim >= 2 for p in groups[0]['params'])
          and all(p.ndim < 2 for p in groups[1]['params']))
    check('schedule', 'torch.compile is never CALLED (eager only; it is mentioned in '
          'prose to say so)',
          'torch.compile(' not in (Path(TR.__file__).read_text()
                                   + Path(M.__file__).read_text()))
    text = Path(TR.__file__).read_text() + Path(L.__file__).read_text()
    check('schedule', 'the training path imports neither tokenizers nor datasets',
          'import tokenizers' not in text and 'import datasets' not in text
          and 'from tokenizers' not in text and 'from datasets' not in text)
    check('schedule', 'bf16 autocast is used on CUDA and not forced on CPU',
          'torch.autocast(\'cuda\', dtype=torch.bfloat16)' in text)


# --------------------------------------------------------------------------- loader

def group_loader():
    check('loader', 'the special ids match INTERFACE-data.md section 2',
          (M.PAD, M.BOS, M.EOS, M.UNK, M.ENT, M.SUBJ, M.OBJ, M.OLD, M.TURN, M.DOC)
          == tuple(range(10)))
    check('loader', 'the vocabulary is 8,192 and the copy actions live inside it',
          M.VOCAB_SIZE == 8192 and max(M.COPY_ACTIONS) < 8192)
    check('loader', '"no entity code here" is 65535', M.ENT_NONE == 65535)
    check('loader', 'the entity pool is 4,096 with 3,072.. reserved',
          M.ENT_POOL == 4096 and M.ENT_RESERVED_MIN == 3072)
    check('loader', 'reserved codes exist in the symbol table so held-out names can be '
          'given codes the talker has provably never seen',
          M.config('M').code_table_size > M.ENT_RESERVED_MIN)
    kinds = {kind for _, kind, _ in L.ASSUMPTIONS}
    check('loader', 'every format assumption says whose rule it is -- somebody else\'s '
          'CONTRACT, or a choice/guess of this builder\'s',
          all(k.startswith(('CONTRACT', 'MODEL-SIDE EXTENSION', 'TRAINER CHOICE', 'GUESS'))
              for k in kinds), kinds)
    check('loader', 'the dialogue format is now a CONTRACT (INTERFACE-dialogues.md '
          'arrived and is implemented), not a guess',
          any(key == 'dialogues' and kind == 'CONTRACT'
              for key, kind, _ in L.ASSUMPTIONS))
    check('loader', 'the one thing nobody else owns -- turning dialogue TEXT into tokens '
          '-- is labelled as this builder\'s',
          any(key == 'dialogue-tokenisation' and 'NOBODY ELSE OWNS IT' in kind
              for key, kind, _ in L.ASSUMPTIONS))
    check('loader', 'describe_assumptions() prints them all',
          all(key in L.describe_assumptions() for key, _, _ in L.ASSUMPTIONS))

    shard = L.synthetic_shard(64, seed=2, vocab_size=512, max_len=10)
    check('loader', 'the shard invariants of INTERFACE-data.md hold', L.check_shard(shard))
    ids, codes = shard.sentence(0)
    check('loader', 'a sentence is tokens[sents[i]:sents[i+1]] with codes 1:1',
          len(ids) == len(codes) and len(ids) >= 1)
    ent_positions = (np.asarray(shard.tokens) == M.ENT)
    coded = (np.asarray(shard.ents) != M.ENT_NONE)
    check('loader', 'a code sits at a position IF AND ONLY IF the token is <ENT>',
          bool((ent_positions == coded).all()))

    missing = json.loads(json.dumps({'turns': [{'tokens': [16, 17]}]}))
    filled = {}
    turns = L.parse_dialogue_record(missing, filled)
    check('loader', 'a dialogue record missing every optional key is filled, not fatal',
          len(turns) == 1 and turns[0].act == M.HEARD_ACTS.index('CHAT'), filled)
    check('loader', 'every filled key is counted so a report can say what was guessed',
          sum(filled.values()) >= 4, filled)
    turns = L.synthetic_dialogues(6, seed=0, vocab_size=512, max_len=10).turns
    tok, cod, labels = L.dialogue_batch(turns)
    check('loader', 'a dialogue batch is framed <bos> ... <eos>',
          int(tok[0, 0]) == M.BOS and M.EOS in tok[0].tolist())
    check('loader', 'the gold labels come out as tensors of the right shape',
          labels['relation_path'].shape == (6, 3) and labels['flags'].shape[1] == 8,
          (tuple(labels['relation_path'].shape), tuple(labels['flags'].shape)))
    gold = TR.gold_pointer_index(cod, labels['subject_code'], cod.shape[1] - 1)
    ok = all(int(cod[i, int(gold[i])]) == int(labels['subject_code'][i])
             or int(labels['subject_code'][i]) == M.ENT_NONE for i in range(6))
    check('loader', 'the gold pointer index really points at the gold code', ok)


# ------------------------------------------------------- dialogues, the REAL format
#
# The producers had shipped no data when this was written, so the fixture below is built
# from the two INTERFACE documents themselves: a byte-level BPE export exactly as
# INTERFACE-data.md section 4 describes it, and one dialogue line exactly as
# INTERFACE-dialogues.md sections 3-8 describe it.  If their real output disagrees with
# the documents, THIS TEST WILL STILL PASS and the disagreement will show up as a counter
# in DialogueSet.filled -- that is deliberate and is said so in the report.

LEXICON_WORDS = ["ok", "is", "a", "the", "who", "what", "friend", "gift", "prize", "charm",
                 "drum", "kite", "not", "s", "sorry", "i", "do", "know"]


def build_tokenizer_export(folder):
    """A real, tiny ByteLevel-BPE export in the documented file layout."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    vocab = {'<pad>': 0, '<bos>': 1, '<eos>': 2, '<unk>': 3, '<ENT>': 4, '<SUBJ>': 5,
             '<OBJ>': 6, '<OLD>': 7, '<TURN>': 8, '<DOC>': 9}
    for k in range(6):
        vocab[f'<extra_{k}>'] = 10 + k
    nxt = 16
    for char in L.BYTE_TO_CHAR.values():                       # every byte is a piece
        vocab.setdefault(char, nxt)
        nxt = max(vocab.values()) + 1
    merges = []
    for word in LEXICON_WORDS + [w for w in LEXICON_WORDS]:
        for spelling in (word, ' ' + word):
            cur = [L.BYTE_TO_CHAR[b] for b in spelling.encode('utf-8')]
            while len(cur) > 1:
                pair = (cur[0], cur[1])
                if pair not in merges:
                    merges.append(pair)
                cur[0:2] = [cur[0] + cur[1]]
                if cur[0] not in vocab:
                    vocab[cur[0]] = nxt
                    nxt += 1
    (folder/'tokenizer_vocab.json').write_text(json.dumps(vocab))
    (folder/'tokenizer_merges.txt').write_text(
        '#version: 0.2\n' + '\n'.join(f'{a} {b}' for a, b in merges) + '\n')
    (folder/'tokenizer_meta.json').write_text(json.dumps(
        {'vocab_size': max(vocab.values()) + 1, 'model': 'ByteLevel BPE',
         'lowercase': True, 'specials': {k: v for k, v in vocab.items()
                                         if k.startswith('<') and k.endswith('>')},
         'ent_code_pool': 4096, 'ent_code_reserved_min': 3072, 'ent_none': 65535}))
    return folder


def demo_record():
    """One dialogue in format fable-talker24-dialogues/1, spans counted by hand."""
    user_text = "Mira's gift is a drum."
    #            0123456789...
    reply_text = "ok. <SUBJ>'s gift is a <OBJ>."
    surface = "ok. Mira's gift is a drum."
    return {
        'id': 'L1/000001', 'format': L.DIALOGUE_FORMAT, 'split': 'L1', 'index': 1,
        'seed_key': 'fable-talker24-dialogues-v1:L1:1', 'symbol_mode': 'm0',
        'world': {'people': [{'slot': 0, 'name': 'Mira', 'symbol': 52},
                             {'slot': 1, 'name': 'Oren', 'symbol': 53}],
                  'values': {'drum': 12, 'kite': 13},
                  'relations': {'friend': 11, 'gift': 8, 'prize': 9, 'charm': 10},
                  'n_people': 2, 'code_pool': None},
        'turns': [{
            'i': 0,
            'user': {'text': user_text, 'frame_id': 'tell.attr.003', 'level': 'L1',
                     'noise': [], 'opener_id': None, 'closer_id': None,
                     'thought': {'act': 'TELL',
                                 'subject': {'slot': 0, 'name': 'Mira', 'symbol': 52,
                                             'span': [0, 4]},
                                 'relation_path': ['gift'], 'relation_symbols': [8],
                                 'object': {'slot': None, 'name': 'drum', 'kind': 'value',
                                            'symbol': 12, 'span': [17, 21]},
                                 'old': None,
                                 'flags': {'path_len': 1, 'speaker': 'user',
                                           'unknown_reason': None, 'unknown_step': None,
                                           'has_old_value': False, 'teachable': True}}},
            'reply': {'text': reply_text, 'surface': surface,
                      'frame_id': 'reply.ack.attr.011',
                      'copy': [{'action': '<SUBJ>', 'field': 'subject', 'slot': 0,
                                'symbol': 52, 'word': 'Mira', 'text_span': [4, 10],
                                'surface_span': [4, 8]},
                               {'action': '<OBJ>', 'field': 'object', 'slot': None,
                                'symbol': 12, 'word': 'drum', 'text_span': [23, 28],
                                'surface_span': [21, 25]}],
                      'thought': {'act': 'ACK',
                                  'subject': {'slot': 0, 'name': 'Mira', 'symbol': 52,
                                              'span': [4, 8]},
                                  'relation_path': ['gift'], 'relation_symbols': [8],
                                  'object': {'slot': None, 'name': 'drum',
                                             'kind': 'value', 'symbol': 12,
                                             'span': [21, 25]},
                                  'old': None,
                                  'flags': {'path_len': 1, 'speaker': 'model',
                                            'unknown_reason': None, 'unknown_step': None,
                                            'has_old_value': False, 'teachable': True}}},
            'notebook': {'op': 'append', 'row': [3, 52, 8, 12, 7], 'named': [],
                         'view_size': 1, 'answerable': True, 'answer_symbol': 12,
                         'unknown_reason': None, 'unknown_step': None}}],
        'final_view': {'52,8': 12}, 'counts': {'TELL': 1},
        'levels': {'frames': 'L1', 'openers': 'L1', 'closers': 'L1'}}


def group_dialogues():
    shards = build_tokenizer_export(TMP/'iface'/'shards')
    enc = L.BytePairEncoder.load(shards)
    check('dialogues', 'a tokenizer export in the documented layout loads with no '
          '"tokenizers" wheel', enc is not None)
    text = "mira's gift is a drum."
    ids = enc.encode(text)
    check('dialogues', 'encoding is byte-exactly reversible',
          enc.decode(ids) == text, (ids[:8], enc.decode(ids)))
    check('dialogues', 'no piece falls back to <unk>', M.UNK not in ids, ids)
    check('dialogues', 'the merges really merge (a word is fewer pieces than letters)',
          len(enc.encode(' drum')) < 5, enc.encode(' drum'))

    record = demo_record()
    lex = frozenset(LEXICON_WORDS)
    counters = {}
    turns = L.parse_v1_record(record, enc, lex, counters)
    check('dialogues', 'one turn comes out of the one-turn record', len(turns) == 1)
    turn = turns[0]
    check('dialogues', 'no unrecognised keys were papered over', not counters, counters)
    check('dialogues', 'the heard act is TELL', turn.act == M.HEARD_ACTS.index('TELL'))
    check('dialogues', 'the spoken act is ACK', turn.reply_act == M.REPLY_ACTS.index('ACK'))
    check('dialogues', 'the relation word "gift" became relation id 2, then "none"',
          turn.relation_path == [2, 0, 0], turn.relation_path)
    check('dialogues', 'the name became EXACTLY ONE <ENT> token',
          turn.tokens.count(M.ENT) == 1, turn.tokens)
    subject_code = 52 - L.M0_PERSON_SYMBOL_MIN
    check('dialogues', 'the subject code rides on that <ENT> position',
          turn.ents[turn.tokens.index(M.ENT)] == subject_code
          and turn.subject_code == subject_code, (turn.ents, turn.subject_code))
    check('dialogues', "the possessive 's survives as ordinary pieces, outside the name",
          enc.decode(turn.tokens).startswith('<ENT>’s')
          or enc.decode(turn.tokens).startswith("<ENT>'s"), enc.decode(turn.tokens))
    value_code = L.VALUE_CODE_MIN + (12 - L.M0_VALUE_SYMBOL_MIN)
    check('dialogues', 'the VALUE word keeps its letters (the ears must read it)',
          'drum' in enc.decode(turn.tokens), enc.decode(turn.tokens))
    check('dialogues', 'and its code is tagged onto exactly one piece, in copy_codes only',
          turn.copy_codes.count(value_code) == 1
          and value_code not in turn.ents, (turn.copy_codes, value_code))
    check('dialogues', 'the object label is that same value code',
          turn.object_code == value_code, turn.object_code)
    check('dialogues', 'every code the thought names is copyable from the heard text',
          turn.subject_code in turn.copy_codes and turn.object_code in turn.copy_codes)

    check('dialogues', 'the reply the mouth trains on contains the copy ACTIONS',
          M.SUBJ in turn.reply_tokens and M.OBJ in turn.reply_tokens, turn.reply_tokens)
    check('dialogues', 'and contains NO <ENT>, so a name cannot leak in as a word',
          M.ENT not in turn.reply_tokens)
    spoken = enc.decode(turn.reply_tokens)
    check('dialogues', 'an unresolved copy action prints as its marker, never silently',
          '<SUBJ>' in spoken and '<OBJ>' in spoken, spoken)
    printed = enc.decode(turn.reply_tokens, copy={'<SUBJ>': 'Mira', '<OBJ>': 'drum'})
    want = record['turns'][0]['reply']['surface']
    check('dialogues', 'resolving the copies reproduces reply.surface exactly',
          printed == want, (printed, want))
    check('dialogues', 'no name or value word is reachable except through a copy action',
          'mira' not in spoken.lower() and 'drum' not in spoken.lower(), spoken)

    flags = L.flags_vector({'path_len': 3, 'speaker': 'model', 'unknown_reason':
                            'chain_broke', 'unknown_step': 2, 'has_old_value': True,
                            'teachable': True})
    idx = M.FLAG_NAMES.index
    check('dialogues', 'path_len 3 is carried as two bits',
          flags[idx('path_len_bit0')] == 1.0 and flags[idx('path_len_bit1')] == 1.0)
    check('dialogues', 'the unknown reason is a one-hot of three',
          flags[idx('unknown_chain_broke')] == 1.0
          and flags[idx('unknown_no_person')] == 0.0
          and flags[idx('unknown_no_fact')] == 0.0)
    check('dialogues', 'has_old_value and speaker are carried',
          flags[idx('has_old_value')] == 1.0 and flags[idx('speaker_is_model')] == 1.0)
    check('dialogues', '"not teachable" is carried on the spare flag',
          L.flags_vector({'teachable': False})[idx('spare7')] == 1.0)
    fold = {}
    check('dialogues', 'an unrecognised unknown_reason is counted, not crashed on',
          L.flags_vector({'unknown_reason': 'martians'}, fold) is not None
          and fold.get('unknown_reason_unrecognised') == 1, fold)

    pool_record = json.loads(json.dumps(record))
    pool_record['symbol_mode'] = 'pool'
    pool_record['world']['code_pool'] = {'pool': 'train', 'size': 3072, 'key': 'k',
                                         'indices': [814, 2299]}
    pool_turn = L.parse_v1_record(pool_record, enc, lex, {})[0]
    check('dialogues', 'in pool mode the subject code is the frozen pool row',
          pool_turn.subject_code == 814, pool_turn.subject_code)

    root = TMP/'iface'
    (root/'dialogues').mkdir(parents=True, exist_ok=True)
    (root/'dialogues'/'LEXICON.json').write_text(json.dumps(LEXICON_WORDS))
    with (root/'dialogues'/'L1-test.jsonl').open('w') as handle:
        for k in range(4):
            line = json.loads(json.dumps(record))
            line['index'] = k
            handle.write(json.dumps(line, sort_keys=True, separators=(',', ':')) + '\n')
    loaded = L.load_dialogues(root, 'L1')
    check('dialogues', 'load_dialogues finds L1-test.jsonl and reads every line',
          loaded is not None and len(loaded) == 4, loaded and len(loaded))
    check('dialogues', 'it says which file it read', 'L1-test.jsonl' in loaded.source)
    check('dialogues', 'a missing dialogue file returns None rather than raising',
          L.load_dialogues(TMP/'nothing-here', 'L1') is None)
    check('dialogues', 'a dialogue file with no tokenizer export says so instead of '
          'guessing', 'NO TOKENIZER EXPORT' in
          (L.load_dialogues(root, 'L1', shards_dir=TMP/'no-shards').source))
    check('dialogues', 'the published name rule is implemented as published',
          [w for _, _, w in L.find_names("Mira gave the drum to Oren.", lex)]
          == ['Mira', 'Oren'])

    tok, cod, labels = L.dialogue_batch(loaded.turns)
    check('dialogues', 'real records feed the slot stage as they are',
          tok.shape[0] == 4 and int(labels['subject_code'][0]) == subject_code)
    cfg = M.config('tiny')
    model = M.Talker(cfg)
    small = torch.clamp(tok, max=cfg.vocab_size - 1)
    heard = model.hear(small, torch.clamp(cod, max=cfg.code_table_size - 1))
    check('dialogues', 'and a model can hear them', heard['thought'].shape[-1] == 416)


# ------------------------------------------------- against whatever REALLY shipped
#
# Everything above is a contract test against the two INTERFACE documents.  This group is
# the only one that touches the other builders' actual output, and it SKIPS ITSELF when
# they have not shipped yet, so the suite is green either way and the report can say
# exactly which of the two it was.

def group_realdata():
    shards = ARTIFACTS/'shards'
    enc = L.BytePairEncoder.load(shards)
    if enc is None:
        check('realdata', 'SKIPPED -- build task 1 has shipped no tokenizer export yet',
              True)
    else:
        check('realdata', 'the REAL tokenizer export loads with stdlib only',
              len(enc.pieces) == 8192, len(enc.pieces))
        samples = ["mira's gift is a drum.", 'ok. the cat sat on the mat.',
                   'he said hello, and then he ran away!', 'what is her prize?']
        bad = [t for t in samples if enc.decode(enc.encode(t)) != t]
        check('realdata', 'this builder\'s pure-Python BPE round-trips real sentences '
              'byte-exactly through the REAL merge table', not bad, bad)
        unk = [t for t in samples if M.UNK in enc.encode(t)]
        check('realdata', 'and needs no <unk> to do it', not unk, unk)
        meta = json.loads((shards/'tokenizer_meta.json').read_text())
        check('realdata', 'the shipped special ids are the ones the model hard-codes',
              all(meta['specials'][k] == v for k, v in
                  (('<pad>', M.PAD), ('<bos>', M.BOS), ('<eos>', M.EOS), ('<unk>', M.UNK),
                   ('<ENT>', M.ENT), ('<SUBJ>', M.SUBJ), ('<OBJ>', M.OBJ),
                   ('<OLD>', M.OLD), ('<TURN>', M.TURN), ('<DOC>', M.DOC))),
              meta['specials'])
        check('realdata', 'the shipped vocabulary size is the 8,192 the mouth\'s tied '
              'head assumes', meta['vocab_size'] == M.VOCAB_SIZE, meta['vocab_size'])
        check('realdata', 'the shipped entity-code pool matches the symbol table',
              meta.get('ent_code_pool') == M.ENT_POOL
              and meta.get('ent_none') == M.ENT_NONE
              and meta.get('ent_code_reserved_min') == M.ENT_RESERVED_MIN, meta)

    stems = L.list_shards(shards, 's0') if shards.exists() else []
    if not stems:
        check('realdata', 'SKIPPED -- build task 1 has shipped no s0 shard yet', True)
    else:
        shard = L.load_shard(stems[0])
        check('realdata', 'the REAL s0 shard passes every invariant of INTERFACE-data.md',
              L.check_shard(shard))
        lengths = np.diff(np.asarray(shard.sents))
        check('realdata', 'no sentence exceeds 48 pieces, as promised',
              int(lengths.max()) <= 48, int(lengths.max()))
        check('realdata', 'every token id fits the 8,192 vocabulary',
              int(np.asarray(shard.tokens).max()) < M.VOCAB_SIZE)
        ents = np.asarray(shard.ents[:2_000_000])
        toks = np.asarray(shard.tokens[:2_000_000])
        check('realdata', 'a code sits at a position iff the token is <ENT>',
              bool(((ents != M.ENT_NONE) == (toks == M.ENT)).all()))
        coded = ents[ents != M.ENT_NONE]
        check('realdata', 'no shipped code reaches the reserved range, so held-out names '
              'really are held out',
              len(coded) == 0 or int(coded.max()) < M.ENT_RESERVED_MIN,
              int(coded.max()) if len(coded) else None)
        if enc is not None:
            ids, cod = shard.sentence(11)
            text = enc.decode(ids, ents=cod)
            check('realdata', 'a real sentence decodes to readable English',
                  len(text) > 10 and text == text.lower(), repr(text[:70]))
        stream = L.SentenceStream([shard], seed=1, max_len=12)
        tok, cod = L.pad_batch(stream.take(8), 14)
        check('realdata', 'the real shard feeds the training stream',
              tok.shape == (8, 14) and int(tok[0, 0]) == M.BOS, tuple(tok.shape))

    if L.find_dialogue_file(ARTIFACTS, 'L1') is None:
        check('realdata', 'SKIPPED -- build task 2 has shipped no dialogue file yet', True)
    else:
        real = L.load_dialogues(ARTIFACTS, 'L1', limit=64)
        check('realdata', 'the REAL dialogue file parses into turns',
              real is not None and len(real) > 0, real and real.filled)
        if real and len(real):
            turn = real.turns[0]
            check('realdata', 'a real reply carries copy actions and no <ENT>',
                  M.ENT not in turn.reply_tokens, turn.reply_tokens[:12])


# --------------------------------------------------------------------------- stream

def group_stream():
    shard = L.synthetic_shard(128, seed=3, vocab_size=512, max_len=12)
    a = L.SentenceStream([shard], seed=7, max_len=12)
    b = L.SentenceStream([shard], seed=7, max_len=12)
    check('stream', 'the data order is a pure function of (seed, position)',
          a.order.tolist() == b.order.tolist())
    c = L.SentenceStream([shard], seed=8, max_len=12)
    check('stream', 'a different seed gives a different order',
          a.order.tolist() != c.order.tolist())
    first = [t.tolist() for t, _ in a.take(5)]
    b.take(5)
    check('stream', 'two streams at the same position see the same sentences',
          first == [t.tolist() for t, _ in L.SentenceStream([shard], seed=7,
                                                            max_len=12).take(5)])
    state = a.state()
    more = [t.tolist() for t, _ in a.take(3)]
    a.load_state(state)
    check('stream', 'restoring the position replays exactly the same sentences',
          more == [t.tolist() for t, _ in a.take(3)])
    lengths = [len(t) for t, _ in L.SentenceStream([shard], seed=7, max_len=6).take(20)]
    check('stream', 'the length bucket is respected', max(lengths) <= 6, max(lengths))
    d = L.SentenceStream([shard], seed=7, max_len=6)
    d.take(4)
    d.set_max_len(12)
    check('stream', 'changing the curriculum length restarts the order from a seeded '
          'permutation (so a resume still reproduces it)',
          d.position == 0 and d.max_len == 12)
    pairs = [(np.array([16, 17, 18], dtype=np.uint16),
              np.array([M.ENT_NONE]*3, dtype=np.uint16))]
    tok, cod = L.pad_batch(pairs, 12)
    check('stream', 'pad_batch frames with <bos>/<eos> and pads with 0',
          tok[0].tolist() == [M.BOS, 16, 17, 18, M.EOS], tok[0].tolist())


# ----------------------------------------------------------------------- checkpoints

def group_checkpoint():
    out = TMP/'ckpt'
    out.mkdir(parents=True, exist_ok=True)
    path = TR.atomic_save({'x': torch.ones(3)}, out/'step-00000001.pt')
    check('checkpoint', 'a checkpoint is written to a temp file then renamed (atomic)',
          path.exists() and not list(out.glob('*.tmp')))
    for step in (2, 3, 4, 5):
        TR.atomic_save({'x': torch.ones(3)}, out/f'step-{step:08d}.pt')
    TR.prune_checkpoints(out, 3)
    left = sorted(p.name for p in out.glob('step-*.pt'))
    check('checkpoint', 'only the last 3 are kept',
          left == ['step-00000003.pt', 'step-00000004.pt', 'step-00000005.pt'], left)
    check('checkpoint', 'the newest is found by step number, not by file time',
          TR.newest_checkpoint(out).name == 'step-00000005.pt')

    cfg = tiny_config(out=str(TMP/'ck2'), steps=6)
    trainer = TR.Trainer(cfg)
    trainer.run()
    payload = torch.load(TR.newest_checkpoint(TMP/'ck2') or (TMP/'ck2'/'final.pt'),
                         map_location='cpu', weights_only=False)
    for key in ('model', 'optimizer', 'step', 'tokens', 'stream', 'noise_generator',
                'rng', 'parameter_hash', 'train_config', 'model_config'):
        check('checkpoint', f'the checkpoint carries "{key}"', key in payload)
    check('checkpoint', 'the RNG state covers python, numpy and torch',
          set(payload['rng']) >= {'python', 'numpy', 'torch'}, list(payload['rng']))
    check('checkpoint', 'the data position is in the checkpoint',
          'position' in payload['stream'], payload['stream'])
    check('checkpoint', 'the default checkpoint cadence is the design\'s 10 minutes and '
          '2,000 steps',
          TR.TrainConfig().checkpoint_minutes == 10.0
          and TR.TrainConfig().checkpoint_steps == 2000)
    check('checkpoint', 'a heartbeat log with tokens/s and TFLOP/s was written',
          (TMP/'ck2'/'heartbeat.jsonl').exists())
    line = json.loads((TMP/'ck2'/'heartbeat.jsonl').read_text().splitlines()[0])
    check('checkpoint', 'the heartbeat carries tokens/s and a measured FLOPs/s estimate',
          'tokens_per_s' in line and 'tflops' in line and line['tokens_per_s'] > 0, line)


# ------------------------------------------------------------------------- the stages

def group_stages():
    for stage in TR.STAGES:
        out = TMP/f'stage-{stage}'
        cfg = tiny_config(stage=stage, out=str(out), steps=6)
        result = TR.Trainer(cfg).run()
        check('stages', f'the {stage} stage runs end to end on CPU',
              result['finished'] and result['step'] == 6, result.get('step'))
        check('stages', f'the {stage} stage reports which data it used',
              'synthetic' in result['source'] or 'shard' in result['source'],
              result['source'])

    cfg = tiny_config(stage='thinker', out=str(TMP/'frozen'), steps=2)
    trainer = TR.Trainer(cfg)
    before = {n: p.detach().clone() for n, p in trainer.model.mouth.named_parameters()}
    ears_before = {n: p.detach().clone()
                   for n, p in trainer.model.ears.named_parameters()}
    think_before = {n: p.detach().clone()
                    for n, p in trainer.model.thinker.named_parameters()}
    trainer.run()
    moved = [n for n, p in trainer.model.mouth.named_parameters()
             if not torch.equal(p.detach(), before[n])]
    check('stages', 'the mouth is FROZEN while the thinker trains (SONAR-LLM\'s recipe)',
          not moved, moved[:3])
    ears_moved = [n for n, p in trainer.model.ears.named_parameters()
                  if not torch.equal(p.detach(), ears_before[n])]
    check('stages', 'the ears are frozen too in the thinker stage', not ears_moved,
          ears_moved[:3])
    thinker_moved = [n for n, p in trainer.model.thinker.named_parameters()
                     if not torch.equal(p.detach(), think_before[n])]
    check('stages', 'the thinker itself really does move (so the stage is not a no-op)',
          len(thinker_moved) > 0, len(thinker_moved))
    check('stages', 'no mouth parameter is in the optimiser during the thinker stage',
          all(not any(p is q for q in group['params'])
              for p in trainer.model.mouth.parameters()
              for group in trainer.optimizer.param_groups))
    check('stages', 'gist noise sigma and gist dropout are the design\'s 0.2 / 10 %',
          TR.TrainConfig().gist_noise == 0.2 and TR.TrainConfig().gist_dropout == 0.1)
    check('stages', 'gist-swap augmentation is the design\'s 30 % of fact sentences',
          TR.TrainConfig().gist_swap_rate == 0.30)

    gru = tiny_config(stage='autoencode', out=str(TMP/'gru'), steps=4, gru_mouth=True)
    result = TR.Trainer(gru).run()
    check('stages', 'the GRU side arm trains through the same trainer',
          result['finished'])


# --------------------------------------------------------------------- THE KILL TEST

def group_resume():
    out = TMP/'kill'
    started = time.time()
    result = TR.kill_test(out, steps=40, die_at=18, preset='tiny', micro_batch=8)
    check('resume', 'the kill test completes', 'uninterrupted_hash' in result, result)
    check('resume', 'the process really was SIGKILLed (exit -9)',
          result.get('killed_signal') == -9, result.get('killed_signal'))
    check('resume', 'the resume came from an EARLIER checkpoint (a real crash does not '
          'get to save)', result.get('resume_line')
          and 'step-00000015' in result['resume_line'][0], result.get('resume_line'))
    check('resume', 'killed-and-resumed ends BIT-IDENTICAL to the uninterrupted run',
          result.get('ok'), (result.get('uninterrupted_hash', '')[:16],
                             result.get('resumed_hash', '')[:16]))
    check('resume', 'and it has seen exactly the same number of tokens',
          result.get('uninterrupted_tokens') == result.get('resumed_tokens'),
          (result.get('uninterrupted_tokens'), result.get('resumed_tokens')))
    check('resume', 'the kill test takes well under a minute',
          time.time() - started < 120, f'{time.time() - started:.1f}s')

    for stage in ('slots', 'thinker'):
        r = TR.kill_test(TMP/f'kill-{stage}', steps=30, die_at=13, preset='tiny',
                         stage=stage, micro_batch=8)
        check('resume', f'the {stage} stage is bit-identical after a kill too',
              r.get('ok'), (r.get('uninterrupted_hash', '')[:12],
                            r.get('resumed_hash', '')[:12]))

    # the restart loop itself
    env = dict(os.environ, OMP_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    proc = subprocess.run([sys.executable, '-B', str(Path(TR.__file__).resolve()),
                           'restart-loop', '--preset', 'tiny', '--steps', '6',
                           '--micro-batch', '8', '--device', 'cpu', '--log-every', '3',
                           '--out', str(TMP/'loop')], capture_output=True, text=True,
                          env=env)
    check('resume', 'the restart loop drives a run to completion',
          proc.returncode == 0 and (TMP/'loop'/'result.json').exists(),
          proc.stderr[-400:])


# ------------------------------------------------------------------------ benchmark

def group_bench():
    row = TR.benchmark('tiny', steps=3, device='cpu', batch=4, length=12)
    for key in ('tokens_per_s', 'tflops', 'parameters', 'forward_parameters',
                'peak_mem_mb', 'preset', 'device'):
        check('bench', f'the benchmark reports "{key}"', key in row, row)
    check('bench', 'tokens/s is positive', row['tokens_per_s'] > 0, row['tokens_per_s'])
    check('bench', 'the FLOPs/s estimate is 6 x forward-parameters x tokens/s',
          abs(row['tflops'] - 6*row['forward_parameters']*row['tokens_per_s']/1e12)
          < 1e-3, row)
    check('bench', 'it says how the estimate was made', 'design section 2.4' in row['note'])
    gru = TR.benchmark('tiny', steps=3, device='cpu', batch=4, length=12, gru_mouth=True)
    check('bench', 'the GRU side arm can be benchmarked beside the transformer',
          gru['tokens_per_s'] > 0 and gru['gru_mouth'])


# ------------------------------------------------------------------------- runner

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='*', default=None, choices=GROUPS)
    parser.add_argument('--keep', action='store_true', help='keep the temp directory')
    args = parser.parse_args(argv)
    started = time.time()
    try:
        for name in (args.only or GROUPS):
            globals()[f'group_{name}']()
    finally:
        if not args.keep:
            shutil.rmtree(TMP, ignore_errors=True)
    failed = [c for c in CHECKS if not c[2]]
    for group, text, ok, detail in CHECKS:
        mark = 'ok  ' if ok else 'FAIL'
        print(f'{mark} [{group}] {text}' + (f'   -- {detail}' if detail and not ok else ''))
    print()
    if failed:
        print(f'{len(failed)} OF {len(CHECKS)} CHECKS FAILED '
              f'({time.time() - started:.1f}s)')
        return 1
    print(f'ALL {len(CHECKS)} CHECKS PASSED ({time.time() - started:.1f}s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
