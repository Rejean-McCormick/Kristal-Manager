"""Build an additive private supplement to the completed V5217 dictionary."""
import argparse, hashlib, json, os, sqlite3, sys, time, uuid
from contextlib import closing
from pathlib import Path
BASE_SHA='45309e8e22c13df112fa5079efe7002405d3d17818936e0a55428535ec4a2a63'
SCAN_SHA='37018e3e9bfed3825b80e96dc418fcfa431e82990a4629e888771a38d835a34e'
COMPACT_SHA='c286b2fe49a93a7f77113808c287ce0e20df731324ddc461bb68f543409bf432'
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def j(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def run(base,scan,compact,partial,index,fast,dump,out,kristalizer,diag):
    sys.path[:0]=[str(kristalizer),str(diag)]
    from kristalizer.maintenance_fast_v52171 import safe,need,ro,discover,query,recover_partial
    base,scan,compact,partial,index,fast,dump,out=map(safe,(base,scan,compact,partial,index,fast,dump,out))
    for src in (base,scan,compact,partial,index,fast,dump):need(out!=src and src not in out.parents and out not in src.parents,'Output overlaps input')
    bp=base/'active.sqlite';mp=scan/'maintenance.sqlite';cp=compact/'repair.sqlite'
    for p,h in ((bp,BASE_SHA),(mp,SCAN_SHA),(cp,COMPACT_SHA)):need(sha(p)==h,'Pinned input drift: '+str(p))
    cr=json.loads((compact/'report.json').read_bytes());cd=json.loads((compact/'diagnostic.json').read_bytes());need(cr['database_sha256']==cd['database_sha256']==(compact/'COMPLETE').read_text()==COMPACT_SHA and cd['status']=='PASS_PRIVATE_OPERATIONAL_SCOPE' and cr['baseline_sha256']==BASE_SHA and cr['maintenance_sha256']==SCAN_SHA,'Invalid completed compact receipt')
    with closing(ro(mp)) as c:ids=[r[0] for r in c.execute('SELECT wid FROM alias_target UNION SELECT external_id FROM ambiguous ORDER BY 1')];pairs=list(c.execute('SELECT wid,lang,occurrences FROM alias_target ORDER BY 1,2'))
    print('TARGETS',len(ids),'distinct external IDs;',len(pairs),'ID/language pairs',flush=True)
    need(not out.exists(),'Output exists; use a new run directory');out.mkdir(parents=True);dbpath=out/'accelerated.sqlite';sources=[];observed=set();partial_data={};index_data={}
    def progress(label):
        return lambda n,total,found,elapsed:print(f'{label}: {n}/{total} ({100*n/max(total,1):.1f}%) | found {found} | {n/max(elapsed,.001):.1f} targets/s',flush=True)
    with closing(sqlite3.connect(dbpath)) as db:
        db.executescript('''CREATE TABLE target(wid TEXT PRIMARY KEY);CREATE TABLE alias_target(wid TEXT,lang TEXT,occurrences INTEGER,PRIMARY KEY(wid,lang));CREATE TABLE source(source_id TEXT PRIMARY KEY,record_json TEXT);CREATE TABLE observation(source_id TEXT,wid TEXT,record_json TEXT,PRIMARY KEY(source_id,wid));CREATE TABLE alias_observation(wid TEXT,lang TEXT,status TEXT,revision INTEGER,label TEXT,aliases_json TEXT,PRIMARY KEY(wid,lang));''')
        db.executemany('INSERT INTO target VALUES (?)',[(w,) for w in ids]);db.executemany('INSERT INTO alias_target VALUES (?,?,?)',pairs)
        def save(sid,info,data):
            info.update(source_id=sid,observed_ids=len(data));sources.append(info);db.execute('INSERT INTO source VALUES (?,?)',(sid,j(info)));db.executemany('INSERT INTO observation VALUES (?,?,?)',((sid,w,j(r)) for w,r in data.items()));db.commit();observed.update(data)
        # Recover committed partial evidence without reopening the bz2 stream.
        try:
            if (partial/'repair.sqlite').is_file():
                partial_data,info=recover_partial(partial/'repair.sqlite',dump,ids);save('partial_dump',{'status':'RECOVERED_COMMITTED_UNAUTHENTICATED',**info},partial_data);print('PARTIAL DUMP RECORDS',len(partial_data),flush=True)
            else:save('partial_dump',{'status':'NOT_FOUND'}, {})
        except (OSError,ValueError,KeyError,sqlite3.Error) as e:save('partial_dump',{'status':'BLOCKED','reason':str(e)}, {})
        candidates,skipped=discover(fast)
        print('FAST INDEX COMPATIBLE DATABASES',len(candidates),flush=True)
        # Probe fast indexes first; compact queried only for IDs lacking an indexed observation.
        for n,(p,_) in enumerate(candidates):
            sid='fast_'+str(n);remaining=set(ids)-set(index_data)
            if not remaining:break
            try:
                data,fp,contract=query(p,remaining,progress(sid));save(sid,{'status':'INDEX_OBSERVATIONS_UNAUTHENTICATED','fingerprint':fp,'contract':contract},data);index_data.update(data)
            except (OSError,ValueError,sqlite3.Error) as e:save(sid,{'status':'BLOCKED','path':str(p),'reason':str(e)}, {})
        remaining=set(ids)-set(index_data)
        if remaining:
            try:
                data,fp,contract=query(index,remaining,progress('compact'));save('compact',{'status':'INDEX_OBSERVATIONS_UNAUTHENTICATED','fingerprint':fp,'contract':contract},data);index_data.update(data)
            except (OSError,ValueError,sqlite3.Error) as e:save('compact',{'status':'BLOCKED','reason':str(e)}, {})
        # Preserve exact-language evidence; absence of a key is not evidence of historical empty aliases.
        for wid,lang,_ in pairs:
            d=partial_data.get(wid);v=index_data.get(wid,{})
            if d and lang!='und' and lang in d['aliases']:
                label=d['labels'].get(lang,{}).get('value');aliases=[x['value'] for x in d['aliases'][lang]];row=(wid,lang,'DUMP_REVISION_OBSERVATION_ONLY',d['source_revision'],label,j(aliases))
            else:
                label=v.get('label_'+lang) if lang in ('fr','en') else None;row=(wid,lang,'EXACT_LABEL_ONLY' if label else 'NO_EXACT_ALIAS_EVIDENCE',None,label,None)
            db.execute('INSERT INTO alias_observation VALUES (?,?,?,?,?,?)',row)
        db.commit();need(db.execute('PRAGMA integrity_check').fetchone()==('ok',),'Output integrity failed')
        counts={'distinct_targets':len(ids),'alias_pairs':len(pairs),'partial_dump_ids':len(partial_data),'indexed_ids':len(index_data),'observed_ids':len(observed),'unobserved_ids':len(ids)-len(observed),'pairs_with_dump_alias_observation':db.execute("SELECT count(*) FROM alias_observation WHERE aliases_json IS NOT NULL").fetchone()[0],'pairs_with_exact_label':db.execute("SELECT count(*) FROM alias_observation WHERE label IS NOT NULL AND label<>''").fetchone()[0],'historical_aliases_repaired':0}
    for p,h in ((bp,BASE_SHA),(mp,SCAN_SHA),(cp,COMPACT_SHA)):need(sha(p)==h,'Input changed during run')
    report={'format':'koa.kristal-accelerated-maintenance/0.1','status':'PRIVATE_ACCELERATED_OBSERVATIONS_READY','baseline_sha256':BASE_SHA,'maintenance_sha256':SCAN_SHA,'compact_sha256':COMPACT_SHA,'database_sha256':sha(dbpath),'counts':counts,'sources':sources,'fast_discovery':skipped,'policy':{'dump_stream_read':False,'network_used':False,'canonical_modified':False,'public_modified':False,'new_accepted_links':0,'historical_aliases_invented':False,'source_authenticated':False}}
    (out/'report.json').write_text(j(report),encoding='utf8')
    from kristaldiag.maintenance_accelerated_check_v52171 import verify
    result=verify(out,mp);(out/'diagnostic.json').write_text(j(result),encoding='utf8');(out/'COMPLETE').write_text(report['database_sha256'],encoding='ascii');return report

def main():
    p=argparse.ArgumentParser()
    for k in ('base','scan','compact','partial','index','fast','dump','out','kristalizer','diag'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(**vars(a)),ensure_ascii=True,indent=2));print('PRIVATE ACCELERATED OUTPUT:',a.out)
if __name__=='__main__':main()
