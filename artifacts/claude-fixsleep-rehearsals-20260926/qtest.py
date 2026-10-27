import sys, time; sys.path.insert(0,'scripts')
import claude_blurt2 as B2, claude_dl3_replay as R
M='/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc'
s=B2.Solver(M)
for ask in ["Write one question that a curious student might ask about science, history, cooking, travel, health, or daily life. Reply with the question only.",
            "Write one question someone might type into a search engine. Reply with the question only."]:
    R.ASK=ask; bad=R.panel_words(); s.torch.manual_seed(1)
    ids=R.chat_ids(s,ask).unsqueeze(0)
    out=s.model.generate(input_ids=ids.repeat(24,1),attention_mask=s.torch.ones_like(ids.repeat(24,1)),max_new_tokens=32,do_sample=True,temperature=1.0,top_p=0.95,pad_token_id=s.tok.eos_token_id)
    qs=[s.tok.decode(o[ids.shape[1]:],skip_special_tokens=True) for o in out]
    ok=[R.clean_question(q,bad) for q in qs]
    print(ask[:40], sum(1 for q in ok if q), len(set(q.lower() for q in ok if q)))
    for q in qs[:12]: print('  ',repr(q[:90]))
R.MAX_A=128
t=time.time(); n=0
for q in [q for q in ok if q][:4]:
    a=R.base_answer(s,q); n+=a is not None; print('A:',repr((a or 'NONE')[:120]))
print(n, time.time()-t)
