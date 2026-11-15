import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import readonly_mcp as bridge


def make_exact(path):
    c=sqlite3.connect(path)
    c.executescript('''
    CREATE TABLE collections(id INTEGER PRIMARY KEY,name TEXT,dimension INTEGER, created_at TEXT);
    CREATE TABLE documents(collection_id INTEGER,id TEXT,document TEXT,metadata_json TEXT,embedding BLOB,dim INTEGER,created_at TEXT,updated_at TEXT);
    CREATE VIRTUAL TABLE docs_fts USING fts5(collection_id UNINDEXED,doc_id UNINDEXED,document);
    ''')
    c.execute("INSERT INTO collections(id,name) VALUES(1,'mempalace_drawers')")
    for id,wing,content in [('match','lab','LAB-ORION-7319 exact match'),('other','private','LAB-ORION-7319 should be withheld')]:
        meta=json.dumps({'wing':wing,'room':'general','source_file':'test.md','line_start':1,'line_end':5})
        c.execute('INSERT INTO documents(collection_id,id,document,metadata_json) VALUES (1,?,?,?)',(id,content,meta))
        c.execute('INSERT INTO docs_fts(collection_id,doc_id,document) VALUES(1,?,?)',(id,content))
    c.commit();c.close()


def make_chroma(path):
    c=sqlite3.connect(path)
    c.executescript('''
    CREATE TABLE embeddings(id INTEGER PRIMARY KEY, segment_id TEXT,embedding_id TEXT,seq_id BLOB,created_at TEXT);
    CREATE TABLE embedding_metadata(id INTEGER,key TEXT,string_value TEXT,int_value INTEGER,float_value REAL,bool_value INTEGER,PRIMARY KEY(id,key));
    CREATE VIRTUAL TABLE embedding_fulltext_search USING fts5(string_value, tokenize='trigram');
    ''')
    for n,wing,s in [(1,'lab','LAB-ORION-7319 Chroma source'),(2,'private','LAB-ORION-7319 secret source')]:
        c.execute('INSERT INTO embeddings(id,embedding_id) VALUES(?,?)',(n,f'drawer-{n}'))
        for k,v in [('chroma:document',s),('wing',wing),('room','general'),('source_file','a.md')]:
            c.execute('INSERT INTO embedding_metadata(id,key,string_value) VALUES(?,?,?)',(n,k,v))
        c.execute('INSERT INTO embedding_metadata(id,key,int_value) VALUES(?,?,?)',(n,'line_start',1))
        c.execute('INSERT INTO embedding_fulltext_search(rowid,string_value) VALUES(?,?)',(n,s))
    c.commit();c.close()


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.config=self.root/'config.json'
        self.patch=patch.dict(os.environ,{'KHL_RECALL_CONFIG':str(self.config)})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def configure(self,backend='exact',wings=None):
        db=self.root/('chroma.sqlite3' if backend=='chroma' else 'sqlite_exact.sqlite3')
        if backend=='chroma':make_chroma(db)
        else:make_exact(db)
        self.config.write_text(json.dumps({'database':str(db),'allowed_wings':wings or ['lab']}),encoding='utf-8')
        return db

    def test_unconfigured_fail_closed(self):
        self.assertEqual(bridge.status()['state'],'unconfigured')
        data,err=bridge.search({'query':'ORION'})
        self.assertTrue(err)

    def test_exact_retrieval_and_filter(self):
        db=self.configure()
        before=hashlib.sha256(db.read_bytes()).hexdigest()
        self.assertEqual(bridge.status()['backend'],'sqlite_exact')
        data,err=bridge.search({'query':'LAB-ORION-7319'})
        self.assertFalse(err,data)
        self.assertEqual(data['count'],1)
        self.assertEqual(data['hits'][0]['id'],'match')
        self.assertEqual(data['hits'][0]['source_file'],'test.md')
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),before)

    def test_chroma_retrieval_and_filter(self):
        db=self.configure(backend='chroma')
        self.assertEqual(bridge.status()['backend'],'chroma')
        before=hashlib.sha256(db.read_bytes()).hexdigest()
        data,err=bridge.search({'query':'LAB-ORION-7319'})
        self.assertFalse(err,data)
        self.assertEqual(data['count'],1)
        self.assertEqual(data['hits'][0]['id'],'drawer-1')
        self.assertEqual(data['hits'][0]['verbatim'],'LAB-ORION-7319 Chroma source')
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),before)

    def test_disallowed_wing_is_rejected(self):
        self.configure()
        data,err=bridge.search({'query':'ORION','wing':'private'})
        self.assertTrue(err)
        self.assertNotIn('secret',json.dumps(data))

    def test_reject_arbitrary_paths_and_params(self):
        self.configure()
        for q in ({'query':'ORION','path':'/etc/passwd'}, {'query':'ORION','limit':100000}, {'query':'ORION\nDROP'}, {'query':'" OR *'}, {'query': 'ORION','limit':True}):
            with self.subTest(q=q):self.assertTrue(bridge.search(q)[1])

    def test_chroma_short_term_error(self):
        self.configure('chroma')
        result,err=bridge.search({'query':'ab'})
        self.assertTrue(err)
        self.assertIn('3 characters',result['message'])

    def test_mcp_stdio_protocol(self):
        self.configure()
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'smurf_recall_status','arguments':{}}},
            {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'smurf_recall_search','arguments':{'query':'ORION'}}}]
        p=subprocess.run([sys.executable,'-u',str(ROOT/'server'/'readonly_mcp.py')], input='\n'.join(map(json.dumps,messages))+'\n', text=True,capture_output=True,timeout=15,check=True)
        got=[json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(got),4)
        self.assertEqual([t['name'] for t in got[1]['result']['tools']],['smurf_recall_status','smurf_recall_search'])
        self.assertEqual(got[0]['result']['serverInfo']['name'], 'smurf-mempalace-connector')
        self.assertEqual(got[0]['result']['serverInfo']['version'], '0.3.0')
        self.assertFalse(got[3]['result']['isError'])
        result=json.loads(got[3]['result']['content'][0]['text'])
        self.assertEqual(result['count'],1)


if __name__ == '__main__':unittest.main()
