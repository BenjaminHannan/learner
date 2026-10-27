"""Durable day-use capture and admission to actual ordered row_graph training.
No optimization. Model-authored text is never an input to the training exporter.
"""
import hashlib,json,math,os,sqlite3,sys,time,uuid
from pathlib import Path
from sol_assistant_bundle import owned,sha,identity,verify_pin,Unavailable
SCHEMA='sol.assistant.day-batch.v3'
OPCODES={0:'sum',1:'product',2:'minimum',3:'maximum'}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evaluate(op,values):
    if type(op) is not int or op not in OPCODES or not isinstance(values,list) or not 1<=len(values)<=32:raise Unavailable('unsupported bounded numeric action')
    if any(type(x) is not int or abs(x)>10000 for x in values):raise Unavailable('bounded exact integers required; strings/formulas forbidden')
    result=(sum(values) if op==0 else math.prod(values) if op==1 else min(values) if op==2 else max(values))
    if abs(result)>10**12:raise Unavailable('outcome exceeds fixed numeric representation bound')
    return result

class DayStore:
    def __init__(self,directory,*,read_only=False):
        self.read_only=read_only
        if read_only:
            self.directory=owned(directory);self.blobs=self.directory/'sources';self.db=self.directory/'day.sqlite3'
            if not self.db.is_file() or not self.blobs.is_dir():raise Unavailable('actual existing capture store required')
            return
        self.directory=owned(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.blobs=self.directory/'sources';self.blobs.mkdir(exist_ok=True);self.db=self.directory/'day.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), activity REAL NOT NULL, revision INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO state VALUES(1,?,0)',(time.time(),))
            db.execute('CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, batch_path TEXT NOT NULL, batch_sha TEXT NOT NULL, revision INTEGER NOT NULL)')
    def connect(self):
        if self.read_only:return sqlite3.connect(self.db.as_uri()+'?mode=ro',uri=True,timeout=10)
        db=sqlite3.connect(self.db,timeout=10);db.execute('PRAGMA synchronous=FULL');return db
    def blob(self,data):
        digest=hashlib.sha256(data).hexdigest();p=self.blobs/digest
        try:
            with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        except FileExistsError:
            if sha(p)!=digest:raise Unavailable('source bytes corrupt')
        return {'path':str(p),'sha256':digest,'bytes':len(data)}
    def _append(self,body):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO events(body) VALUES(?)',(canonical(body),))
            db.execute('UPDATE state SET activity=?,revision=revision+1 WHERE id=1',(time.time(),))
        return body
    def activity(self):
        with self.connect() as db:db.execute('UPDATE state SET activity=?,revision=revision+1 WHERE id=1',(time.time(),))
    def typed(self,text,kind='question'):
        if not sys.stdin.isatty():raise Unavailable('genuine interactive CLI handler required; imports ineligible')
        if kind not in ('question','context','correction'):raise ValueError('human role')
        return self._append({'kind':'human','human_kind':kind,'origin':'interactive-cli','role':'user','source':self.blob(text.encode('utf-8')),'factual_ground_truth':False})
    def correction(self,question,context,target):
        # All three arguments are already captured human events, not arbitrary strings.
        for row,kind in ((question,'question'),(context,'context'),(target,'correction')):
            self._human(row,kind)
        return self._append({'kind':'human-correction','question':question,'context':context,'target':target,'label_semantics':'explicit human preferred response; factual truth unasserted'})
    def _human(self,row,kind=None):
        if row.get('kind')!='human' or row.get('origin')!='interactive-cli' or row.get('role')!='user' or (kind and row.get('human_kind')!=kind):raise Unavailable('human source role mismatch')
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM events WHERE body=?',(canonical(row),)).fetchone():raise Unavailable('human source not captured by this session')
        p=verify_pin(row['source'])
        if p.parent.resolve()!=self.blobs.resolve():raise Unavailable('imported source cannot gain human provenance')
        return p.read_text(encoding='utf-8')
    def numeric_tool(self,question,opcode,operands,observed):
        """Trusted tool handler passes ACTUAL execution outcome; no formula/code text.
        Recount against the bounded deterministic executor, independently of success flags.
        Does not act on any spreadsheet; caller integrates its numeric extraction.
        """
        self._human(question,'question');expected=evaluate(opcode,operands)
        if type(observed) is not int or observed!=expected:raise Unavailable('observed tool outcome disagrees with verifier')
        trace={'opcode':opcode,'operands':operands,'observed':observed}
        return self._append({'kind':'verified-numeric-tool','question':question,'trace':self.blob(canonical(trace).encode()),'verifier_sha256':sha(__file__),'origin':'tool-execution-recount','outcome':'success'})
    def snapshot(self,out,*,bundle_pin,idle_seconds,claim_id):
        verify_pin(bundle_pin)
        if type(idle_seconds) is not int or idle_seconds<1:raise Unavailable('bounded idle interval required')
        out=owned(out)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            activity,revision=db.execute('SELECT activity,revision FROM state WHERE id=1').fetchone()
            if time.time()-activity<idle_seconds:return {'ready':False,'reason':'human active'}
            if db.execute('SELECT 1 FROM claims WHERE id=?',(claim_id,)).fetchone():raise Unavailable('claim already consumed; no duplicate optimizer run')
            events=[json.loads(x[0]) for x in db.execute('SELECT body FROM events ORDER BY seq')]
            admitted=[x for x in events if x['kind'] in ('human-correction','verified-numeric-tool')]
            if not admitted:return {'ready':False,'reason':'no admitted day labels; never substitute static replay as day use'}
            b={'schema':SCHEMA,'bundle':bundle_pin,'capture_source_sha256':sha(__file__),'events':admitted,'claim':claim_id,'revision':revision,'activity_unix':activity,'state_dir':str(self.directory),'split':'TRAIN','assistant_text_included':False}
            # Admission checked before durable claim, and again on worker load.
            rows=rows_from_batch(b,self)
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('x',encoding='utf-8') as f:f.write(canonical(b)+'\n');f.flush();os.fsync(f.fileno())
            db.execute('INSERT INTO claims VALUES(?,?,?,?)',(claim_id,str(out),sha(out),revision))
        return {'ready':True,'batch':{'path':str(out),'sha256':sha(out)},'rows':len(rows),'revision':revision}
    def unchanged(self,revision):
        with self.connect() as db:return db.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]==revision

def rows_from_batch(batch,store):
    if batch['schema']!=SCHEMA or batch['capture_source_sha256']!=sha(__file__) or batch['split']!='TRAIN' or batch['assistant_text_included'] is not False:raise Unavailable('day batch binding differs')
    verify_pin(batch['bundle']);rows=[]
    for event in batch['events']:
        with store.connect() as db:
            if not db.execute('SELECT 1 FROM events WHERE body=?',(canonical(event),)).fetchone():raise Unavailable('experience absent from actual capture journal')
        q=store._human(event['question'],'question')
        if event['kind']=='human-correction':
            context=store._human(event['context'],'context');target=store._human(event['target'],'correction');origin='human-preferred-response-not-factual-certificate'
        elif event['kind']=='verified-numeric-tool':
            if event['verifier_sha256']!=sha(__file__):raise Unavailable('numeric verifier drift')
            trace=read(verify_pin(event['trace']))
            if set(trace)!={'opcode','operands','observed'} or type(trace['observed']) is not int or evaluate(trace['opcode'],trace['operands'])!=trace['observed']:raise Unavailable('invalid raw outcome')
            context=canonical({'opcode':trace['opcode'],'operands':trace['operands']});target=canonical(trace['observed']);origin='verified-symbolic-numeric-execution'
        else:raise Unavailable('unadmitted experience kind')
        if not q.strip() or not target.strip():raise Unavailable('empty question or target')
        rows.append({'id':'day-'+identity(event),'question':q,'context':context,'target_text':target,'split':'train','source_sha256':identity(event),'training_origin':origin,'origin':origin,'factual_ground_truth':False})
    if not rows:raise Unavailable('empty day experience')
    return rows

def load_day_rows(path,expected_sha256,*,state_dir,bundle_sha256,tokenizer=None):
    if sha(path)!=expected_sha256:raise Unavailable('day snapshot hash differs')
    b=read(path)
    if b['bundle']['sha256']!=bundle_sha256:raise Unavailable('day experience targets another checkpoint')
    rows=rows_from_batch(b,DayStore(state_dir,read_only=True))
    if tokenizer is not None:
        for row in rows:
            for key,cap in (('question',48),('context',512),('target_text',63)):
                if len(tokenizer.encode(row[key],add_special_tokens=False))>cap:raise Unavailable('day input exceeds exact runtime cap; no silent truncation/drop')
    return rows


def load_rows(path,expected_sha256):
    """James night-v2 public interface; tokenizer caps preflight remains caller duty."""
    if sha(path)!=expected_sha256:raise Unavailable('day snapshot hash differs')
    b=read(path)
    return load_day_rows(path,expected_sha256,state_dir=b['state_dir'],bundle_sha256=b['bundle']['sha256'])
