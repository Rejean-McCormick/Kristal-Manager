import json, shutil, sys, textwrap
from pathlib import Path
from kristaldiag.interop import run_interop
ROOT=Path(__file__).resolve().parents[1]

def _impl(root:Path,name:str):
    root.mkdir()
    fixture=json.loads((ROOT/'tck/v7/v6-compatible-projection.example.json').read_text())
    (root/'fixture.json').write_text(json.dumps(fixture),encoding='utf-8')
    script=textwrap.dedent('''
        import json, os, sys
        from pathlib import Path
        here=Path(__file__).resolve().parent
        action=sys.argv[1]
        if action=='export':
            p=here/'last.json'
            if not p.exists(): p=here/'fixture.json'
            print(p.read_text(encoding='utf-8'))
            raise SystemExit(0)
        if action=='import':
            src=Path(os.environ['KRISTALDIAG_INPUT'])
            obj=json.loads(src.read_text(encoding='utf-8'))
            (here/'last.json').write_text(json.dumps(obj),encoding='utf-8')
            print(json.dumps({'status':'ok'}))
            raise SystemExit(0)
        raise SystemExit(2)
    ''')
    (root/'driver_impl.py').write_text(script,encoding='utf-8')
    drv={'schema':'kristaldiag.driver.v1','implementation':name,'claimed_profile':'V7-Kristall','actions':{
        'interop_export':{'argv':[sys.executable,'driver_impl.py','export']},
        'interop_import':{'argv':[sys.executable,'driver_impl.py','import']},
        'self_test':{'argv':[sys.executable,'-c','print(1)']}
    }}
    (root/'kristaldiag-driver.json').write_text(json.dumps(drv),encoding='utf-8')

def test_a_b_a_interop_passes(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b';_impl(a,'A');_impl(b,'B')
    out=tmp_path/'interop.json'
    r=run_interop(a,b,repo_root=ROOT,output=out,allow_exec=True)
    assert r['verdict']=='PASS'
    assert r['artifact']['producer_identity']==r['artifact']['consumer_identity']
    assert out.is_file()
