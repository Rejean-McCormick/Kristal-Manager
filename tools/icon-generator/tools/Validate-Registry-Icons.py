from __future__ import annotations
import argparse, json, re
from pathlib import Path

NATURES={'REF','COL','MOD','PRT','TWN','INV','SRC'}
UNESCO_URIS = {'1': 'http://vocabularies.unesco.org/thesaurus/domain1', '2': 'http://vocabularies.unesco.org/thesaurus/domain2', '3': 'http://vocabularies.unesco.org/thesaurus/domain3', '4': 'http://vocabularies.unesco.org/thesaurus/domain4', '5': 'http://vocabularies.unesco.org/thesaurus/domain5', '6': 'http://vocabularies.unesco.org/thesaurus/domain6', '7': 'http://vocabularies.unesco.org/thesaurus/domain7'}
COLOR=re.compile(r'^#[0-9A-Fa-f]{6}$')
CODE=re.compile(r'^[1-7]$')
FILENAME=re.compile(r'^KR-(REF|COL|MOD|PRT|TWN|INV|SRC)-UT[1-7](?:-UT[1-7]){0,2}-M[0-5]\.ico$')

def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def spec(entry):
    icon=((entry.get('presentation') or {}).get('icon') or {})
    if icon.get('classification',{}).get('scheme')!='UNESCO Thesaurus' or icon.get('classification',{}).get('kos_id')!='kos:unesco-thesaurus':return None
    if icon.get('nature') not in NATURES:return None
    m=icon.get('maturity')
    if not isinstance(m,int) or not 0<=m<=5:return None
    ds=icon.get('domains')
    if not isinstance(ds,list) or not 1<=len(ds)<=3:return None
    out=[]
    for d in ds:
        if not isinstance(d,dict):return None
        code=str(d.get('code') or '')
        color=str(d.get('color') or '')
        if not CODE.fullmatch(code) or not COLOR.fullmatch(color):return None
        if code not in UNESCO_URIS or d.get('uri')!=UNESCO_URIS[code] or d.get('icon_token')!=f'UT{code}':return None
        out.append((code,color.upper()))
    filename=((icon.get('rendering') or {}).get('filename') or (str(icon.get('icon_code') or '')+'.ico'))
    filename=f"KR-{icon['nature']}-{'-'.join('UT'+x[0] for x in out)}-M{m}.ico"
    return filename,(icon['nature'],m,tuple(out))

def main():
    ap=argparse.ArgumentParser(description='Validate Registry icon profiles for Kristal Icon Generator 2.6 (UNESCO Thesaurus).')
    ap.add_argument('catalog',type=Path)
    a=ap.parse_args(); data=load(a.catalog)
    if data.get('format') not in {'kristal-registry.catalog/1.0','kristal-registry.catalog/1.1'}:
        raise SystemExit(f"Unsupported Registry format: {data.get('format')}")
    entries=data.get('entries') or []
    groups={}; conflicts=[]; renderable=0
    for e in entries:
        s=spec(e)
        if not s: continue
        renderable+=1; name,sig=s
        if name in groups and groups[name][0]!=sig: conflicts.append(name)
        else: groups.setdefault(name,(sig,[]))[1].append(e.get('kristal_id'))
    normalized=sum(bool(e.get('normalization')) for e in entries)
    print(f'format={data.get("format")}')
    print(f'entries={len(entries)}')
    print(f'normalized={normalized}')
    print(f'renderable={renderable}')
    print(f'unique_ico={len(groups)}')
    print(f'conflicts={len(set(conflicts))}')
    if conflicts:
        for x in sorted(set(conflicts)): print('CONFLICT',x)
        return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
