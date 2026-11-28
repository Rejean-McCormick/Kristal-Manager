"""Orchestrate exact EncyK lookups with independently validated, resumable batches."""
import argparse, hashlib, json, os, sqlite3, sys, time, uuid
from contextlib import closing
from pathlib import Path
SCAN_SHA='37018e3e9bfed3825b80e96dc418fcfa431e82990a4629e888771a38d835a34e'
BASE_SHA='45309e8e22c13df112fa5079efe7002405d3d17818936e0a55428535ec4a2a63'
def run(scan,base,root,factory,private,kristalizer,diag,batch_size=250,timeout=600):
    sys.path[:0]=[str(kristalizer),str(diag)]
    from kristalizer.maintenance_fast_v52171 import safe,need,ro,query,ID
    from kristalizer.encyk_indexed_v5218 import binding,worker,validate_batch,canonical,load,sha,QID
    scan,base,root,factory,private=map(safe,(scan,base,root,factory,private));need(1<=batch_size<=1000 and 10<=timeout<=3600,'Invalid batch settings')
    need(private!=root and private not in root.parents and root not in private.parents and private!=factory and private not in factory.parents and factory not in private.parents,'Overlapping source/output')
    need(sha(scan)==SCAN_SHA and sha(base)==BASE_SHA,'Pinned maintenance/baseline drift')
    dump=root/'10_sources/wikidata/dumps/current/wikidata-20260922-all.json.bz2';index=root/'30_working/wikidata/wikidata.compact.sqlite';b=binding(factory,root,dump,index)
    with closing(ro(scan)) as c:
        ids=sorted({r[0] for r in c.execute('SELECT wid FROM alias_target UNION SELECT external_id FROM ambiguous')});pairs=list(c.execute('SELECT wid,lang,occurrences FROM alias_target ORDER BY wid,lang'))
    need(all(ID.fullmatch(w) for w in ids),'Invalid external ID');qs=sorted((w for w in ids if QID.fullmatch(w)),key=lambda w:int(w[1:]));ps=sorted(set(ids)-set(qs));
    key=hashlib.sha256(canonical([b,SCAN_SHA,batch_size,qs]).encode()).hexdigest()[:24]
    cache=safe(private/'maintenance'/'indexed_cache_v5218'/key);cache.mkdir(parents=True,exist_ok=True)
    batches=[];obs={};start=time.monotonic();reused=0
    print(f'TARGETS {len(qs)} QIDs, {len(ps)} PIDs; cache {key}',flush=True)
    # Each batch independently durable. A failure leaves earlier batches untouched.
    for i in range(0,len(qs),batch_size):
        targets=qs[i:i+batch_size];name=f'batch_{i//batch_size:05d}';dest=safe(cache/name)
        if dest.is_dir():
            need(load(safe(dest/'binding.json').read_bytes())==[b,targets],'Cache binding mismatch');data,receipt=validate_batch(dest,targets,b);need(load(safe(dest/'receipt.json').read_bytes())==receipt,'Cache receipt mismatch');reused+=1;mode='CACHED'
        else:
            stage=safe(cache/(name+'_stage_'+uuid.uuid4().hex));stage.mkdir();data,receipt=worker(factory,root,dump,index,stage,targets,b,timeout)
            (stage/'binding.json').write_text(canonical([b,targets]),encoding='utf8');(stage/'receipt.json').write_text(canonical(receipt),encoding='utf8');need(not dest.exists(),'Concurrent batch collision');stage.rename(dest);mode='INDEXED'
        obs.update(data);batches.append({'batch':name,**receipt});done=min(i+batch_size,len(qs));elapsed=time.monotonic()-start
        print(f'{mode} {done}/{len(qs)} ({100*done/max(1,len(qs)):.1f}%) | found {len(obs)} | {done/max(elapsed,.001):.1f} targets/s',flush=True)
    remaining=set(ids)-set(obs)
    def progress(n,t,f,e):print(f'COMPACT {n}/{t} | found {f} | {n/max(e,.001):.1f}/s',flush=True)
    compact,fp,contract=query(index,remaining,progress) if remaining else ({},b['files'][str(index)],None)
    need(binding(factory,root,dump,index)==b and sha(scan)==SCAN_SHA and sha(base)==BASE_SHA,'Input changed during run')
    out=safe(private/'maintenance'/('INDEXED_V5218_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]));out.mkdir();p=out/'indexed.sqlite'
    with closing(sqlite3.connect(p)) as db:
        db.executescript('''CREATE TABLE target(wid TEXT PRIMARY KEY,kind TEXT NOT NULL);CREATE TABLE indexed_entity(wid TEXT PRIMARY KEY,record_json TEXT NOT NULL);CREATE TABLE compact_entity(wid TEXT PRIMARY KEY,record_json TEXT NOT NULL);CREATE TABLE alias_target(wid TEXT,lang TEXT,occurrences INTEGER,PRIMARY KEY(wid,lang));CREATE TABLE pair_observation(wid TEXT,lang TEXT,status TEXT,revision INTEGER,label TEXT,aliases_json TEXT,PRIMARY KEY(wid,lang));CREATE TABLE batch_receipt(batch TEXT PRIMARY KEY,record_json TEXT);''')
        db.executemany('INSERT INTO target VALUES (?,?)',((w,'item' if w.startswith('Q') else 'property') for w in ids));db.executemany('INSERT INTO indexed_entity VALUES (?,?)',((w,canonical(v)) for w,v in obs.items()));db.executemany('INSERT INTO compact_entity VALUES (?,?)',((w,canonical(v)) for w,v in compact.items()));db.executemany('INSERT INTO alias_target VALUES (?,?,?)',pairs);db.executemany('INSERT INTO batch_receipt VALUES (?,?)',((r['batch'],canonical(r)) for r in batches))
        for w,l,_ in pairs:
            d=obs.get(w);v=compact.get(w,{});label=None;aliases=None;rev=None;status='NO_EXACT_OBSERVATION'
            if l=='und':status='UNDETERMINED_LANGUAGE'
            elif d:
                label=(d['labels'] or {}).get(l);aliases=(d['aliases'] or {}).get(l);rev=d['revision'];status='INDEXED_DUMP_LANGUAGE_OBSERVATION' if label is not None or aliases is not None else 'NO_EXPLICIT_LANGUAGE_IN_DUMP'
            elif l in ('fr','en') and v.get('label_'+l):label=v['label_'+l];status='COMPACT_LABEL_REVISION_UNKNOWN'
            db.execute('INSERT INTO pair_observation VALUES (?,?,?,?,?,?)',(w,l,status,rev,label,canonical(aliases) if aliases is not None else None))
        db.commit();need(db.execute('PRAGMA integrity_check').fetchone()==('ok',),'DB integrity failed')
        counts={'targets':len(ids),'qid_targets':len(qs),'pid_targets':len(ps),'indexed_qids':len(obs),'compact_fallback_ids':len(compact),'observed_ids':len(set(obs)|set(compact)),'unobserved_ids':len(set(ids)-set(obs)-set(compact)),'alias_pairs':len(pairs),'pairs_with_explicit_alias_list':db.execute('SELECT count(*) FROM pair_observation WHERE aliases_json IS NOT NULL').fetchone()[0],'pairs_with_exact_label':db.execute("SELECT count(*) FROM pair_observation WHERE label IS NOT NULL AND label<>''").fetchone()[0],'und_pairs':sum(l=='und' for w,l,n in pairs),'batches':len(batches),'reused_batches':reused}
    report={'format':'koa.kristal-encyk-indexed-maintenance/0.1','status':'PRIVATE_INDEXED_OBSERVATIONS_READY','maintenance_sha256':SCAN_SHA,'baseline_sha256':BASE_SHA,'database_sha256':sha(p),'source_binding':b,'cache_path':str(cache),'compact_fingerprint':fp,'compact_contract':contract,'counts':counts,'policy':{'network_used':False,'full_dump_scan':False,'index_rebuilt':False,'canonical_modified':False,'public_modified':False,'historical_aliases_repaired':0,'new_accepted_links':0,'source_authenticated':False}}
    (out/'report.json').write_text(canonical(report),encoding='utf8')
    from kristaldiag.encyk_indexed_check_v5218 import verify
    result=verify(out,scan,base);(out/'diagnostic.json').write_text(canonical(result),encoding='utf8');(out/'COMPLETE').write_text(report['database_sha256'],encoding='ascii');print(json.dumps(report,indent=2,ensure_ascii=True));print('PRIVATE INDEXED OUTPUT:',out,flush=True);return out

def main():
    p=argparse.ArgumentParser()
    for k in ('scan','base','root','factory','private','kristalizer','diag'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--batch-size',type=int,default=250);p.add_argument('--timeout',type=int,default=600);a=p.parse_args();out=run(**vars(a));print('OUTPUT_PATH='+str(out),flush=True)
if __name__=='__main__':main()
