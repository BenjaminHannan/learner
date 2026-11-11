import json,urllib.request,time
out=[];off=0
while off<20000:
    u=f"https://datasets-server.huggingface.co/rows?dataset=Muennighoff/babi&config=default&split=test&offset={off}&length=100"
    for a in range(5):
        try: j=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'x'}),timeout=60)); break
        except Exception as e: time.sleep(3); j=None
    if not j: print('FAIL',off); break
    out+=[{'passage':r['row']['passage'],'question':r['row']['question'],'task':r['row']['task']} for r in j['rows']]; off+=100
open('spec/babi_test.jsonl','w').write(''.join(json.dumps(x)+'\n' for x in out)); print(len(out))
