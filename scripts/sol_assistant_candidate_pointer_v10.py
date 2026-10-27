"""Transactional immutable-bundle pointer. Model safety remains owner-validator work.
No training, model copies, generation, or self-authored model acceptance.
"""
import json,sqlite3,time
from pathlib import Path
from sol_assistant_bundle import owned,pin,verify_pin,identity,Unavailable

class BundlePointer:
    def __init__(self,state_dir):
        self.directory=owned(state_dir);self.directory.mkdir(parents=True,exist_ok=True)
        self.db=self.directory/'active-bundle.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS current_bundle (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, record TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS history (revision INTEGER PRIMARY KEY, utc REAL NOT NULL, operation TEXT NOT NULL, previous TEXT, record TEXT NOT NULL, decision TEXT)')
    def connect(self):
        db=sqlite3.connect(self.db,timeout=10);db.execute('PRAGMA synchronous=FULL');return db
    def initialize(self,bundle_path,*,check_bundle):
        record=pin(bundle_path);check_bundle(record['path']);verify_pin(record)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT revision,record FROM current_bundle WHERE id=1').fetchone()
            if old:
                if json.loads(old[1])!=record:raise Unavailable('pointer already initialized to another bundle')
                return self.current(check_bundle=check_bundle)
            value=json.dumps(record,sort_keys=True)
            db.execute('INSERT INTO current_bundle VALUES(1,0,?)',(value,))
            db.execute('INSERT INTO history VALUES(0,?,?,NULL,?,NULL)',(time.time(),'initialize',value))
        return self.current(check_bundle=check_bundle)
    def current(self,*,check_bundle):
        with self.connect() as db:row=db.execute('SELECT revision,record FROM current_bundle WHERE id=1').fetchone()
        if row is None:raise Unavailable('no initialized active bundle')
        record=json.loads(row[1]);verify_pin(record);checked=check_bundle(record['path'])
        return dict(revision=row[0],bundle=record,checked=checked)
    def accept(self,candidate_path,*,expected_revision,decision_path,trusted_decision_sha256,check_bundle,check_decision):
        """check_decision is James-owned exact candidate validator, never an LLM judge.
        Called on the actual decision/current/candidate; must raise on rejection.
        This class supplies atomicity only and cannot manufacture its validation.
        """
        candidate=pin(candidate_path);check_bundle(candidate['path']);verify_pin(candidate)
        decision=pin(decision_path)
        if decision['sha256']!=trusted_decision_sha256:raise Unavailable('untrusted or changed candidate decision')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision,record FROM current_bundle WHERE id=1').fetchone()
            if row is None or row[0]!=expected_revision:raise Unavailable('active model changed since candidate started')
            previous=json.loads(row[1]);verify_pin(previous)
            result=check_decision(decision['path'],previous,candidate)
            if result is not True:raise Unavailable('owner did not validate candidate acceptance')
            verify_pin(candidate);verify_pin(decision)
            value=json.dumps(candidate,sort_keys=True);new_revision=row[0]+1
            db.execute('UPDATE current_bundle SET revision=?,record=? WHERE id=1',(new_revision,value))
            db.execute('INSERT INTO history VALUES(?,?,?,?,?,?)',(new_revision,time.time(),'accepted-candidate',row[1],value,json.dumps(decision,sort_keys=True)))
        return self.current(check_bundle=check_bundle)
    def rollback(self,*,expected_revision,check_bundle):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision,record FROM current_bundle WHERE id=1').fetchone()
            if row is None or row[0]!=expected_revision:raise Unavailable('stale rollback request')
            entry=db.execute('SELECT previous FROM history WHERE revision=?',(row[0],)).fetchone()
            if entry is None or entry[0] is None:raise Unavailable('no predecessor bundle')
            prior=json.loads(entry[0]);verify_pin(prior);check_bundle(prior['path']);verify_pin(prior)
            revision=row[0]+1
            db.execute('UPDATE current_bundle SET revision=?,record=? WHERE id=1',(revision,entry[0]))
            db.execute('INSERT INTO history VALUES(?,?,?,?,?,NULL)',(revision,time.time(),'rollback',row[1],entry[0]))
        return self.current(check_bundle=check_bundle)
