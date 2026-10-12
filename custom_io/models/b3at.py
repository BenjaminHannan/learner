"""The agent-turn model (architecture/AT-BUILD-SPEC-2026-10-11.md and talker/B3AT-BUILD-NOTES-2026-10-11.md; design architecture/AGENT-TURNS-AND-NO-PLUG-2026-10-11.md; model 'b3at').
B3AT(B3G2) is B3 group 2 as G2f built it (the reader with fix 1, the thinker blocks, H1's stop head, ONE byte writer that reads only the thinker's vectors, the tool registry, the tape
as the transcript, progtext's as-written traces, the ST1 hooks) with the loop turned into Ben's agent: "this should be like an agent. So it does it's thinking, then it completes its
turn with an english output. the englihs output calls the tool, calculator, and the calculator returns whatever. the agent does a turn where it inputs the calculator's return and
processes that and gives a final answer after x turns" (project chat 10-11, 4:17 PM ET). B3G2 itself is not changed (it stays the G2f stepping stone); this class overrides run, _loss,
talk, generate, sample_traces' plumbing and call_evals, and reuses everything else (read, num_memory / slot_kv, tok_spots, kv_of, join_kv, tape_of / read_texts, think, step_emb,
dispatch / entry_text, make_gold / trace_of / train_golds, ans_pass, line_context, memory / writer_view / lesioned, forced_answer, extra_evals / g2_evals).

Ben's rules this model keeps, in his words and where the code keeps them.
Rule 1, "also for the calculator, it should be read by the reader. It is a fully external tool, just like minecraft.": a tool's reply reaches the model ONLY as text, `entry_text(line, reply)`,
which goes through read_texts (Gemma + the letter window) plus tape_emb[k] and is visible to the thinker from the NEXT turn. Nothing else in this file turns a reply into a vector (no
embedding lookup of reply text, no number parsed from it).
Rule 2, "the talker shouldn't get a pointer from the thinker, it just transcribes the thoughts of the thinker. So it should read the thoughts of the thinker, maybe at every step, but at
least the last, and answer in english from that. It literally is a math to language translator.": EVERY line, a tool call and the final answer alike, is written by the byte writer in mode 1
from Z only (line_context: an empty, fully masked context; no pointer, copy, feedback or layout code; the prompt, the tape and the replies never reach it). The harness, not the model's
vectors, decides by the line's first word whether it was a call. Mode 0 ("call?") of B3G2 is not used.
Rule 3, everything inside the model is learned: the only hand-written code on the path is inside the tools the model calls (the calculator, `note`) and the harness that splits a line at its
first space. The stop, the number of rounds, the call text and the answer text are all the model's.
Rule 4, no training target is ever truncated: a line that cannot be written in WCAP steps gets no target (counted `writer_over`, make_gold), a reply entry longer than LE is counted
(`tape_entry_over`, entry_text), a (row, turn) that would need a 17th line is counted (`turns_over`), a line with no EOS within WCAP is counted (`unended`); none is cut silently.

One question, free run (run). State kept across turns: Z (all thinker vectors, [B, 17, d]), the transcript (prompt X; tape entries 0..k-1, entry j written in turn j, visible from turn
j + 1). Turn j = 0 .. TURNS - 1 (TURNS = tape + 1 = 17 lines at most), for the rows still live, in lockstep:
  1. rounds r = 0 .. TCAP - 1 (TCAP = 32, H1's cap): Z = think(Z + step_emb[min(r, n_loops - 1)], ...) over [prompt; visible entries] exactly as B3G2.loop's context (slots none, tok_think as
     configured). The round index restarts every turn; there is no turn embedding (no new parameter). The learned stop (B3's head on ln_z(Z[:, 1]), P_STOP) ends the row's turn at the
     first round it fires, or at TCAP (`turn_cap`, reported). A row that stopped, or has finished, keeps its Z (torch.where: B3G2.run's keep logic, per turn).
  2. the talker writes ONE line from Z (talk_rounds 'last': the turn's last round; 'all': the turn's every round, each plus step_emb[min(r, n_loops - 1)], a stopped row keeping the memory of
     its stop round). No EOS within WCAP: counted `unended`, the row answers '' and ends.
  3. the harness splits the line at its first space. A known tool name (add sub mul div mod min max cmp, note): dispatch (the lesions noexec / opswap and the oracle exactly as B3G2.dispatch,
     the oracle called as oracle(i, turn, (name, a, b))), and the entry goes in the row's next tape slot (slot j: a live row has written j tool lines). Any other line (including '') is the
     final answer and the row is done. A tool line when the tape is full (turn 16): the row ends with the answer '' and counts `turns_over`.
run(batch, loops=K) forces K rounds in every turn (the stop head ignored; K = 0 means the talker reads each turn's start Z: the thinker-off check; K > 32 counts `turn_rounds_over`).
-> dict(Z, tape, calls, records, answers, rounds, turns, turn_rounds, tape_full, le, K, ...). calls [B][(turn, name, a, b, reply)] and records [B][(turn, line, reply)] hold the TOOL lines
(notes included), answers [B] the final lines; last_rounds = rounds per row summed over its turns, last_turns = lines written per row, last_tape_full = the rows that ended by `turns_over`.
state_of(o) = (Z, Xt, idt, vis) of each row's final turn (+ (mem, mem_mask) under 'all'); talk(state, batch) = the talker's greedy line from state[0] (Z) only (writer_view), '' for a line
that did not end; generate(batch, lesion) = the answers of a free run with the lesion (zero_state / shuffle_state act on the final turn's Z before the final line; noexec / opswap in dispatch;
nocopy a no-op; loops:K forced; ctl27 as B3G2).

Training (teacher forcing, _loss(batch, golds) with B3G2's golds): a row with L gold lines c_1..c_L (calls and notes, as written) and answer a: turn j < L targets c_{j+1}, turn L targets a.
The entries are the golds' tape (the tool's real reply; a drill row's drawn strings), entry j visible from turn j + 1. ONE R per batch is drawn from KS_T = (4, 8, 16, 32) with torch's
global generator (torch.randint, the stream B3G2 / H1 draw K from); then PER ROW R_i = min(R, max(1, TOTAL_CAP // (L_i + 1))), TOTAL_CAP = 96, and every row with R_i < R counts in
`turn_rounds_capped` (reported). Row i runs R_i rounds in each of its L_i + 1 turns; rows step turns in lockstep and a row past its R_i in a turn (or past its last turn) keeps its Z. The Z the next turn starts from is the row's Z after a round c_ij drawn uniformly from 1..R_i (one torch.randint call per turn, after R), so the next turn has seen a carried state from every round the learned stop can fire at; the turn still runs all R_i rounds with the line loss at each, and R per batch is unchanged (_turns carry='draw', used by _loss; evals and tests keep carry='last'). Loss per
row: the talker's teacher-forced NLL of the turn's target line at EVERY round of the turn (H1's rule, per turn), the mean over the row's (turn, round) pairs that have a target; summed
over rows / B. No w_noop (every turn has a target). Stop head: BCE on the 'settled' label per turn (right at round r and at every later round of that turn), input detached as in B3G2, only
on (row, turn) pairs with R_i = TCAP (label 'right': every pair). Gradients flow through Z across turns; rounds with global index (rounds so far in the batch) >= CKPT_FROM are
gradient-checkpointed, the thinker's and the talker's passes alike. aux: stop_pairs (the (row, turn, round) pairs the stop loss counted), line_acc (teacher-forced 'right' at the last round of each turn; line_acc_call / line_acc_ans separately), call / ans (the mean
NLL of the call lines / answer lines), stop, stop_acc, rounds (per row), turns, R, copy_share (always 0, key kept for the logs).
ST1: sample_traces(batch, temperature, generator) = a free run whose every line is sampled -> per row dict(calls=[(line, reply)], answer); trace_loss(batch, traces) = _loss on trace_gold(t).
Counters (capcount): turns_over, tape_entry_over, writer_over, unended, turn_rounds_over, steps_unparsed, no_trace, steps_over (faults: all read 0 on the sealed runs) and turn_cap,
turn_rounds_capped (reported)."""
import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from custom_io import capcount
from custom_io.models.b3g2 import B3G2, CKPT_FROM
from custom_io.models.ledger import N_CTRL, N_REG
from custom_io.models.tool import LE, Tool
from custom_io.models.tool_h1 import CAP as TCAP, P_STOP, settled

KS_T = (4, 8, 16, 32)       # rounds per turn drawn once per training batch (H1's loop lengths, FINISHED item 14)
TOTAL_CAP = 96              # rounds a row may spend over all its turns in training: R_i = min(R, max(1, TOTAL_CAP // (L_i + 1)))


class B3AT(B3G2):
    def __init__(self, vocab, **kw):
        super().__init__(vocab, **kw)
        self.TURNS = self.tape + 1          # lines a row may write: tape entries + the final line (17)
        self.last_turns = None

    # ---- shared pieces ----
    def question(self, batch):
        """The question read once for all turns (B3G2.loop's front): -> dict(X, xm, valid, km, kvx, kvs0). valid [B, 0] and kvs0 None under no_slots."""
        X, xm = self.read(batch, talker=True)
        ns, ne = (None, None) if self.no_slots else self.tokenize(batch)[:2]
        valid, S0 = self.num_memory(X, ns, ne)
        Xk, km = self.tok_spots(X, xm, batch) if self.tok_think else (X, xm)
        return dict(X=X, xm=xm, valid=valid, km=km, kvx=[b.kv_of(Xk + self.src.weight[1]) for b in self.core], kvs0=self.slot_kv(S0))

    def z0(self, B):
        return torch.cat([self.ctrl.weight, self.reader.place.weight[:N_REG]]).expand(B, -1, -1)

    def think(self, Z, kvs, kvx, mask, t):
        """One thinker round; t = the batch's GLOBAL round index (rounds so far over all turns): rounds with t >= CKPT_FROM are gradient-checkpointed (H1's rule, here over the whole row-batch)."""
        if self.training and torch.is_grad_enabled() and t >= CKPT_FROM:
            return checkpoint(Tool.think, self, Z, kvs, kvx, mask, t, use_reentrant=False)
        return Tool.think(self, Z, kvs, kvx, mask, t)

    def write_lines(self, Z, zm=None, rows=None, temperature=0.0, generator=None):
        """The talker's line (mode 1, ALWAYS: only the harness decides whether it is a call) for every row of Z [n, m, d] from Z alone (zm: its mask, None = all visible; under 'all' Z is the
        memory) -> (list of n id lists without EOS, ended [n] bool: wrote EOS within WCAP). `rows` = the batch row of each Z row; it is carried for callers that log or script lines and is not
        read: the writer sees Z only (line_context is empty)."""
        Xc, cmask, cids = self.line_context(Z)
        return self.writer.greedy(Z, self.zmask(Z, zm), Xc, cmask, cids, torch.ones(Z.shape[0], dtype=torch.long, device=Z.device), temperature=temperature, generator=generator)

    def line_logp(self, Z, inp, zm=None):
        """Teacher-forced log-probs of the talker (mode 1) for lines' input ids inp [n, L] from Z alone -> [n, L, V] (evals: the predicted bytes of a line)."""
        n = Z.shape[0]
        Xc, cmask, cids = self.line_context(Z)
        logp, _, _ = self.writer(Z, self.zmask(Z, zm), Xc, cmask, cids, torch.ones(n, dtype=torch.long, device=Z.device), inp, torch.zeros(n, inp.shape[1], 1, device=Z.device), False, None, 0)
        return logp

    # ---- the free run ----
    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False, oracle=None, each=None, force=None, temperature=0.0, generator=None):
        """The agent-turn free run (module docstring). loops = K forces K rounds in every turn (the stop head ignored); else the learned stop per turn. temperature > 0 samples every line (ST1).
        oracle(i, turn, (name, a, b)) -> reply replaces the calculator's reply for a two-token call (AT-1 1b). -> dict(Z, tape, calls, records, answers, rounds, turns, turn_rounds, ...)."""
        assert gold is None and force is None and not rounds and each is None, 'b3at trains through loss(); teacher forcing is internal, and a free run has no per-round callback'
        B, dev = batch['prompt_ids'].shape[0], batch['prompt_ids'].device
        c = self.question(batch)
        Z = self.z0(B)
        K, le, allr = self.tape, LE, self.talk_rounds == 'all'
        Xt, idt, mt, le = self.tape_of([[''] * K for _ in range(B)], dev, le)
        ent = torch.arange(K * le, device=dev) // le
        shown = torch.zeros(B, K, dtype=torch.bool, device=dev)
        kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
        kvs = self.join_kv(c['kvs0'], kvt)
        done = torch.zeros(B, dtype=torch.bool, device=dev)
        Zf = Z.clone()                                                      # each row's Z of its final turn (the state the final line was written from)
        answers, calls, recs, full_ev = [''] * B, [[] for _ in range(B)], [[] for _ in range(B)], []
        turn_rounds, lines, total_rounds = [[] for _ in range(B)], [0] * B, [0] * B
        fmem = []                                                           # 'all': (row ids, memory, mask) of the rows that finished in a turn
        g = 0
        for j in range(self.TURNS):
            live = ~done
            if not bool(live.any()):
                break
            vis = mt & shown.gather(1, ent.expand(B, -1))                   # entries written in turns < j
            mask = torch.cat([c['valid'], vis, c['km']], 1)
            n_r = TCAP if loops is None else loops
            if loops is not None and loops > TCAP:
                capcount.hit('turn_rounds_over', int(live.sum()))
            used = torch.zeros(B, dtype=torch.long, device=dev)             # rounds this turn; 0 = still running (learned stop)
            running, hist = live.clone(), []
            for r in range(n_r):
                Zn = self.think(Z + self.step_emb.weight[min(r, self.n_loops - 1)], kvs, c['kvx'], mask, g)
                g += 1
                if lesion == 'ctl27':
                    Zn = torch.cat([Zn[:, :2], torch.zeros_like(Zn[:, 2:N_CTRL]), Zn[:, N_CTRL:]], 1)
                Z = torch.where(running[:, None, None], Zn, Z)              # a row that stopped (or finished) keeps its Z
                if allr:
                    hist.append(Z)
                if loops is None:
                    fire = self.p_stop(self.ln_z(Z[:, 1])) >= P_STOP
                    new = running & (fire | (r + 1 >= TCAP))
                    if bool((new & ~fire).any()):
                        capcount.hit('turn_cap', int((new & ~fire).sum()))
                    used[new] = r + 1
                    running = running & ~new
                    if not bool(running.any()):
                        break
            if loops is not None:
                used[live] = loops
            M, mm = None, None
            if allr:
                M = self.memory(hist, len(hist) - 1) if hist else self.memory([Z], 0)
                mm = (torch.arange(M.shape[1], device=dev) // Z.shape[1])[None, :] < used.clamp(min=1)[:, None]
            sel = live.nonzero()[:, 0].tolist()
            full = len(sel) == B
            si = torch.tensor(sel, device=dev)
            pk = lambda x: x if full else x[si]
            outs, ended = self.write_lines(pk(M if allr else Z), pk(mm) if allr else None, sel, temperature, generator)
            ended = [bool(x) for x in ended.tolist()]
            ul = used.tolist()
            new, fin = [''] * B, torch.zeros(B, dtype=torch.bool, device=dev)
            for jj, i in enumerate(sel):
                turn_rounds[i].append(ul[i]); total_rounds[i] += ul[i]; lines[i] += 1
                if not ended[jj]:
                    capcount.hit('unended'); self.free_stats['unended'] += 1
                    fin[i] = True                                           # answers[i] stays ''
                    continue
                txt = self.vocab.decode(outs[jj])
                if txt.partition(' ')[0] not in self.tools:                 # the first word names no tool (including ''): the final answer
                    answers[i] = txt
                    fin[i] = True
                elif j >= self.tape:                                        # a tool line on a full tape: the row ends, no answer
                    capcount.hit('turns_over')
                    full_ev.append((i, j))
                    fin[i] = True
                else:
                    r_ = self.dispatch(txt, i, j, lesion, oracle)
                    calls[i].append(r_)
                    recs[i].append((j, txt, r_[4]))
                    new[i] = self.entry_text(txt, r_[4])
            if bool(fin.any()):
                Zf = torch.where(fin[:, None, None], Z, Zf)
                if allr:
                    fi = fin.nonzero()[:, 0]
                    fmem.append((fi, M[fi], mm[fi]))
                done = done | fin
            have = torch.tensor([bool(x) for x in new], device=dev)
            if bool(have.any()):                                            # the replies enter ONLY here: read_texts (Gemma + letter window) + tape_emb[j], visible from turn j + 1
                Xn, inn, mn = self.read_texts(new, dev, le)
                Xn = (Xn + self.tape_emb.weight[j].to(Xn.dtype)) * mn[..., None]
                sl = slice(j * le, (j + 1) * le)
                Xt, idt, mt = Xt.clone(), idt.clone(), mt.clone()
                Xt[:, sl] = torch.where(have[:, None, None], Xn.to(Xt.dtype), Xt[:, sl])
                idt[:, sl] = torch.where(have[:, None], inn, idt[:, sl])
                mt[:, sl] = torch.where(have[:, None], mn, mt[:, sl])
                shown[have, j] = True
                kvt = [b.kv_of(Xt + self.src.weight[1]) for b in self.core]
                kvs = self.join_kv(c['kvs0'], kvt)
        vis = mt & shown.gather(1, ent.expand(B, -1))
        self.last_rounds, self.last_turns = total_rounds, lines
        self.last_tape_full = [any(i == r_ for r_, _ in full_ev) for i in range(B)]
        out = dict(Z=Zf, X=c['X'], xm=c['xm'], tape=(Xt, idt, vis), calls=calls, records=recs, answers=answers, le=le, K=K, tape_full=full_ev, rounds=total_rounds, turns=lines, turn_rounds=turn_rounds)
        if allr:
            nz = Zf.shape[1]
            Mx = max(m.shape[1] for _, m, _ in fmem)
            mem, mmask = torch.zeros(B, Mx, Zf.shape[2], dtype=fmem[0][1].dtype, device=dev), torch.zeros(B, Mx, dtype=torch.bool, device=dev)
            for fi, m, mk in fmem:
                mem[fi, :m.shape[1]], mmask[fi, :m.shape[1]] = m, mk
            out.update(mem=mem, mem_mask=mmask)
        return out

    def state_of(self, o):
        return (o['Z'],) + o['tape'] + ((o['mem'], o['mem_mask']) if 'mem' in o else ())

    # ---- the talker ----
    def talk(self, state, batch, lesion=None, return_modes=False, temperature=0.0, generator=None):
        """The talker's greedy (or sampled) line from the state's Z ALONE (rule 2; `batch`, the state's tape and `lesion` are accepted for the callers' signature and not read: nocopy is a no-op),
        '' for a line that did not end. A donor's Z writes the donor's line. return_modes: also a mode per row (always 2: one writer, one mode)."""
        Z, zm = self.writer_view(state)
        outs, ended = self.write_lines(Z, zm, None, temperature, generator)
        out = [self.vocab.decode(o) if bool(e) else '' for o, e in zip(outs, ended.tolist())]
        return (out, [2] * len(out)) if return_modes else out

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        if lesion == 'ctl27':
            return self.run(batch, lesion='ctl27')['answers']
        name, arg = self.check_lesion(lesion)
        if name in ('noexec', 'opswap'):
            return self.run(batch, lesion=name)['answers']
        if name == 'loops':
            return self.run(batch, loops=arg)['answers']
        if name in ('zero_state', 'shuffle_state'):             # on Z (and the memory) before the final line
            return self.talk(self.lesioned(self.state_of(self.run(batch)), name), batch)
        return self.run(batch)['answers']                       # intact, and nocopy (a no-op: nothing copies)

    # ---- ST1 ----
    @torch.no_grad()
    def sample_traces(self, batch, temperature, generator):
        """ST1: a free run whose every line (calls and the answer) is SAMPLED from the writer -> per row dict(calls=[(line, reply)] for every tool line, answer=the final line)."""
        o = self.run(batch, temperature=temperature, generator=generator)
        return [dict(calls=[(txt, rep) for _, txt, rep in o['records'][i]], answer=o['answers'][i]) for i in range(len(o['answers']))]

    # ---- loss ----
    def _loss(self, batch, golds):
        R = KS_T[int(torch.randint(len(KS_T), (1,)))]
        total, aux, _ = self._turns(batch, golds, R, carry='draw')
        return total, {k: v.detach() if torch.is_tensor(v) else v for k, v in aux.items()}

    @staticmethod
    def carry_draw(Rt, dev):
        """c_ij for one turn: ONE torch.randint call of B values on the global generator, mapped to 1..R_i (modulo; the bias is below 1e-8). Tests may replace this method."""
        return (1 + torch.randint(0, 2 ** 31 - 1, (len(Rt),)).to(dev) % Rt).long()

    def _turns(self, batch, golds, R, count=True, names=False, carry='last'):
        """Teacher forcing over the turns with R rounds per turn before the per-row cut (module docstring) -> (total loss, aux, info). info['Z'] = each row's Z after its last turn; info['last_right'] = [(row, turn, 'call' | 'ans', right at the
        row's last round of the turn, first word right)] for every (row, turn) with a target (names: the first word is computed only when asked, one more no-grad pass); info['pred'] = {(row, turn): the teacher-forced argmax line} when names. count=False: the cap
        counters are left alone (evals).
        carry: which Z the next turn starts from. 'last' (evals, tests; the default) = the row's Z after its R_i rounds. 'draw' (_loss) = the row's Z after a round c_ij drawn uniformly from 1..R_i, so
        the next turn is trained on a carried state from every round the learned stop can fire at; the turn still runs all R_i rounds with the line loss at each, gradients flow through the carried Z.
        RNG order (torch's global generator): R (in _loss), then at the start of each turn ONE torch.randint call of B values (carry_draw), whether or not every row runs that turn. 'last' draws nothing."""
        assert carry in ('last', 'draw'), carry
        dev, B = batch['prompt_ids'].device, len(batch['rows'])
        Ls = [len(x['texts']) for x in golds]
        Ri = [min(R, max(1, TOTAL_CAP // (L + 1))) for L in Ls]
        if count and any(r < R for r in Ri):
            capcount.hit('turn_rounds_capped', sum(r < R for r in Ri))
        c, allr = self.question(batch), self.talk_rounds == 'all'
        K = max(1, max(Ls))
        Xt, idt, mt, le = self.tape_of([(list(x['tape']) + [''] * K)[:K] for x in golds], dev)
        ent = torch.arange(K * le, device=dev) // le
        kvs = self.join_kv(c['kvs0'], [b.kv_of(Xt + self.src.weight[1]) for b in self.core])
        Lt, Rt = torch.tensor(Ls, device=dev), torch.tensor(Ri, device=dev)
        Z = self.z0(B)
        acc, cnt = torch.zeros(B, device=dev), torch.zeros(B, device=dev)
        zero = torch.zeros((), device=dev)
        sl_, sn_, sa_, ys = zero, zero, zero, zero                          # stop loss sum / pairs / correct / label sum
        nll_s = dict(call=[0.0, 0], ans=[0.0, 0])
        hit = dict(call=[0, 0], ans=[0, 0])
        last_right, g, preds = [], 0, {}
        for j in range(max(Ls) + 1):
            act = Lt >= j
            tg = [(x['ids'][j] if j < L else x['ans_ids']) if L >= j else None for x, L in zip(golds, Ls)]
            te = self.answer_teacher(Z, tg)
            has = (te['tgt'] != -100).any(1)                                # over-long lines have no target (writer_over was counted in make_gold)
            mask = torch.cat([c['valid'], mt & (ent[None, :] < j), c['km']], 1)     # entries written in turns < j
            Rj = max(Ri[i] for i in range(B) if Ls[i] >= j)
            hist, zs, right, fr = [], [], torch.zeros(Rj, B, dtype=torch.bool, device=dev), None
            if carry == 'draw':
                cj, Zc = self.carry_draw(Rt, dev), Z                        # Zc: the Z the next turn starts from (rows not running keep theirs)
            for r in range(Rj):
                runm = act & (Rt > r)
                Zn = self.think(Z + self.step_emb.weight[min(r, self.n_loops - 1)], kvs, c['kvx'], mask, g)
                Z = torch.where(runm[:, None, None], Zn, Z)                # a row past its R_i in this turn, or past its last turn, keeps its Z
                if carry == 'draw':
                    Zc = torch.where((runm & (cj == r + 1))[:, None, None], Z, Zc)
                if allr:
                    hist.append(Z)
                    M = self.memory(hist, r)
                zs.append(self.ln_z(Z[:, 1].detach()))                      # the stop head reads the state detached: its loss trains ln_z and the head, never the loop
                sel = (runm & has).nonzero()[:, 0]
                if len(sel):
                    full = len(sel) == B
                    pk = lambda x: x if full else x[sel]
                    args = (pk(M if allr else Z), pk(te['inp']), pk(te['tgt']), pk(te['fb']))
                    if self.training and torch.is_grad_enabled() and g >= CKPT_FROM:
                        nll, rt, _, _ = checkpoint(self.ans_pass, *args, use_reentrant=False)
                    else:
                        nll, rt, _, _ = self.ans_pass(*args)
                    acc = acc + torch.zeros(B, device=dev).index_add(0, sel, nll.float())
                    cnt = cnt + torch.zeros(B, device=dev).index_add(0, sel, torch.ones(len(sel), device=dev))
                    right[r, sel] = rt
                    is_call = Lt[sel] > j
                    for kind, sub in (('call', is_call), ('ans', ~is_call)):
                        nll_s[kind][0] += float(nll.detach()[sub].sum()); nll_s[kind][1] += int(sub.sum())
                    fin_ = sel[Rt[sel] == r + 1]                            # rows whose turn ends at this round
                    if len(fin_):
                        ok_ = right[r, fin_].tolist()
                        nm_ = [False] * len(fin_)
                        if names:
                            with torch.no_grad():
                                zr = M[fin_] if allr else Z[fin_]
                                pred = self.line_logp(zr, te['inp'][fin_]).argmax(-1).cpu()
                            tgt_ = te['tgt'][fin_].cpu()
                            for q in range(len(fin_)):
                                w = lambda ids: self.vocab.decode([x for x in ids if x >= 0]).split(' ')[0]
                                n_ = int((tgt_[q] != -100).sum())
                                nm_[q] = w(pred[q][:n_].tolist()) == w(tgt_[q][:n_].tolist())
                                preds[(int(fin_[q]), j)] = self.vocab.decode(pred[q][:n_].tolist())      # the teacher-forced argmax line (decode stops at EOS; agreement checks)
                        for q, i in enumerate(fin_.tolist()):
                            kind = 'call' if j < Ls[i] else 'ans'
                            hit[kind][0] += ok_[q]; hit[kind][1] += 1
                            last_right.append((i, j, kind, bool(ok_[q]), nm_[q]))
                g += 1
            if carry == 'draw':
                Z = Zc                                                      # the next turn starts from the drawn round's Z
            # the stop head's loss for this turn: 'settled' (right now or no later round of the turn is right) on the pairs that ran the whole turn
            logit = self.stop(torch.stack(zs)).float()[..., 0]                # [Rj, B]
            y = (settled(right) if self.label == 'settled' else right).float()
            m = (act & has)[None, :] & (Rt[None, :] > torch.arange(Rj, device=dev)[:, None])
            if self.label == 'settled':
                m = m & (Rt >= TCAP)[None, :]
            sl_ = sl_ + (F.binary_cross_entropy_with_logits(logit, y, reduction='none') * m).sum()
            sn_ = sn_ + m.sum()
            sa_ = sa_ + (((logit >= 0).float() == y) & m).sum().float()
            ys = ys + (y * m).sum()
        lines = (acc / cnt.clamp(min=1)).sum() / B
        lstop = sl_ / sn_.clamp(min=1)
        total = lines + lstop
        pc = lambda d: d[0] / max(d[1], 1)
        aux = dict(call=pc(nll_s['call']), prog=pc(nll_s['call']), ans=pc(nll_s['ans']), lines=lines, stop=lstop, stop_y=ys / sn_.clamp(min=1), stop_acc=sa_ / sn_.clamp(min=1),
                   stop_w=float(bool(sn_ > 0)), stop_pairs=float(sn_), line_acc=(hit['call'][0] + hit['ans'][0]) / max(hit['call'][1] + hit['ans'][1], 1), line_acc_call=pc(hit['call']), line_acc_ans=pc(hit['ans']),
                   call_acc=pc(hit['call']), rounds=sum(r * (L + 1) for r, L in zip(Ri, Ls)) / B, turns=sum(L + 1 for L in Ls) / B, R=float(R), copy_share=0.0)
        if self.ans_drill:
            aux['drill_share'] = sum(x['drill'] for x in golds) / B
        return total, aux, dict(last_right=last_right, Z=Z, pred=preds)

    # ---- extra evals ----
    def call_evals(self, out, prows, batches, ctx):
        """Tool.extra_evals' call accuracy per TURN. Teacher forced: the golds' tape, R = TCAP rounds before the per-row cut, the line of every turn read at the row's last round of the turn; a
        call is right when its text equals the gold call text, `op` = its first word equals, a program is right when every call line is right. Free run (the learned stop per turn): a program
        is right when every tool line equals the gold line in order and no extra tool line is written; the final answer is the run's. Into out['op_acc'] (same keys as B3G2's), out['call_text']
        (stop_calling = the teacher-forced accuracy of the final-answer line, i.e. writing the answer rather than another call after the last call) and out['at_lines'] (accuracy by turn)."""
        from custom_io.evalx import is_hit, subsample
        dev, amp = ctx['device'], ctx['amp']
        sl = subsample(prows, 400)
        acc = {m: dict(calls=0, names=0, n_calls=0, prog=0) for m in ('teacher_forced', 'free_run')}
        fr_ans, ans_tf, by_turn = 0, [0, 0], {}
        for b in batches(sl):
            rows, B = b['rows'], len(b['rows'])
            golds = self.plain_golds(rows)
            with amp():
                _, _, info = self._turns(b, golds, TCAP, count=False, names=True)
            a, okrow = acc['teacher_forced'], [True] * B
            for i, j, kind, good, nm in info['last_right']:
                d = by_turn.setdefault(str(j), [0, 0])
                d[0] += good; d[1] += 1
                if kind == 'call':
                    a['calls'] += good; a['names'] += nm; a['n_calls'] += 1
                    okrow[i] &= good
                else:
                    ans_tf[0] += good; ans_tf[1] += 1
            a['prog'] += sum(okrow)
            with amp():
                o = self.run(b)
            a = acc['free_run']
            for i, (r, gd) in enumerate(zip(rows, golds)):
                rec = o['records'][i]
                good = True
                for k, txt in enumerate(gd['texts']):
                    w = k < len(rec) and rec[k][1] == txt
                    a['calls'] += w; a['names'] += k < len(rec) and rec[k][1].split(' ')[0] == txt.split(' ')[0]; a['n_calls'] += 1
                    good &= w
                a['prog'] += good and len(rec) == len(gd['texts'])
                fr_ans += is_hit(o['answers'][i], r)
        n = len(sl)
        pc = lambda x, d: 100 * x / max(d, 1)
        out['op_acc'] = {m: dict(op=pc(a['names'], a['n_calls']), call=pc(a['calls'], a['n_calls']), program=pc(a['prog'], n)) for m, a in acc.items()}
        out['op_acc']['n'] = n
        out['op_acc']['free_run']['answer'] = pc(fr_ans, n)
        out['call_text'] = dict(n_calls=acc['teacher_forced']['n_calls'], stop_calling=pc(ans_tf[0], ans_tf[1]), n_stop_rounds=ans_tf[1])
        out['at_lines'] = dict(by_turn={k: dict(n=v[1], right=pc(v[0], v[1])) for k, v in sorted(by_turn.items(), key=lambda x: int(x[0]))}, rounds=TCAP, note='teacher forced, R = TCAP before the per-row cut, right at the last round of the turn')

    @torch.no_grad()
    def extra_evals(self, ctx):
        """B3G2's evals (Tool / H1 / B3 / g2: the agreement table of teacher-forced right vs the greedy final answer, extra['talker'] on this model's free runs; they run through this class's run /
        state_of / talk / forced_answer) with call_evals above counting per turn, plus extra['at'] (at_evals: turns and rounds per turn and per family)."""
        out = super().extra_evals(ctx)
        out['at'] = self.at_evals(ctx)
        return out

    @torch.no_grad()
    def at_evals(self, ctx):
        """Report-only, the agent turns' own numbers on the dev rows (the same rows as g2_evals' agreement table): lines per row, rounds per turn (B3-4 / B3-5 by turn: mean, median, share
        at TCAP, by the turn index), total rounds per row, turns and rounds per family (by_family: lines and rounds per row, rounds per turn, share of turns at TCAP), and the cap counters (faults and reported). (h1's 'rounds' for b3at are TOTAL rounds over all turns, last_rounds.)"""
        import statistics
        from custom_io.data import DEV_SPLITS, collate, Dataset, to_device
        from custom_io.evalx import _dev_rows, subsample
        was = self.training
        self.eval()
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        rows, seen = [], set()
        for sp in DEV_SPLITS:
            for r in _dev_rows(ctx['data'], sp, None):
                if r['id'] not in seen:
                    seen.add(r['id'])
                    rows.append(r)
        sample = subsample(rows, 600)
        per_turn, turns, tot, fam = {}, {}, [], {}
        for s in range(0, len(sample), bs):
            ch = sample[s:s + bs]
            b = to_device(collate([Dataset(ch, self.vocab, strict=False)[i] for i in range(len(ch))]), dev)
            with amp():
                o = self.run(b)
            for r, tr, nt, rr in zip(b['rows'], o['turn_rounds'], o['turns'], o['rounds']):
                turns[str(nt)] = turns.get(str(nt), 0) + 1
                tot.append(rr)
                f = fam.setdefault(r['family'], dict(n=0, lines=0, rounds=0, turns_at_cap=0))
                f['n'] += 1; f['lines'] += nt; f['rounds'] += rr; f['turns_at_cap'] += sum(u >= TCAP for u in tr)
                for j, u in enumerate(tr):
                    per_turn.setdefault(j, []).append(u)
        st = lambda us: dict(n=len(us), mean=sum(us) / len(us), median=statistics.median(us), at_cap=100 * sum(u >= TCAP for u in us) / len(us))
        out = dict(n=len(sample), tcap=TCAP, total_cap=TOTAL_CAP, turns=self.TURNS, lines_per_row=dict(sorted(turns.items(), key=lambda x: int(x[0]))),
                   rounds_by_turn={str(j): st(us) for j, us in sorted(per_turn.items())}, rounds_per_row=st(tot) if tot else dict(n=0),
                   by_family={k: dict(n=v['n'], lines_per_row=v['lines'] / v['n'], rounds_per_row=v['rounds'] / v['n'], rounds_per_turn=v['rounds'] / max(v['lines'], 1),
                                      turn_cap_share=100 * v['turns_at_cap'] / max(v['lines'], 1)) for k, v in sorted(fam.items())}, counters=capcount.snapshot(),
                   free_unended=self.free_stats['unended'])
        self.train(was)
        return out
