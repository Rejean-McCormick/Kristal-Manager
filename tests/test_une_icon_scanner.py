"""End-to-end classification tests for UNESCO-only icon scanner."""
import json
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCANNER=ROOT/'tools/icon-generator/runtime/scan-kristals.mjs'
PALETTE=ROOT/'tools/icon-generator/runtime/kristal-domain-palette.json'

@pytest.mark.skipif(not shutil.which('node'),reason='Node required')
def test_icon_generator_uses_only_explicit_unesco(tmp_path):
    collection=tmp_path/'collection'
    documents={
        'Kristal-Catho':{'classification':{'unesco_thesaurus':{'kos_id':'kos:unesco-thesaurus','microthesauri':['3.20'],'mapping_status':'reviewed'}}},
        'Kristal-Legacy':{'classification':{'isced_f2013':{'codes':['02']}}},
        'Kristal-Conflict':{'classification':{'unesco_thesaurus':{'domains':['2'],'microthesauri':['3.20']}}},
        'Kristal-Candidate':{'classification':{'unesco_thesaurus':{'domains':['3'],'mapping_status':'candidate'}}},
    }
    for name,workspace in documents.items():
        folder=collection/'domains'/name
        folder.mkdir(parents=True)
        (folder/'kristal.workspace.json').write_text(json.dumps(workspace),encoding='utf-8')
    legacy=collection/'domains/Kristal-Legacy/.kristal'
    legacy.mkdir()
    (legacy/'icon-profile.json').write_text(json.dumps({'profile':'kristal-icon/1.0','domains':[{'code':'02','color':'#A85AA3'}],
        'classification':{'scheme':'ISCED-F 2013'}}))
    cp=subprocess.run(['node',str(SCANNER),'--collection',str(collection),'--palette',str(PALETTE)],capture_output=True,text=True,timeout=25)
    assert cp.returncode==0,cp.stderr
    report=json.loads(cp.stdout)
    assert report['scanned']==4 and report['generated']==1
    assert set(report['unresolved_unesco'])=={'Kristal-Legacy','Kristal-Conflict','Kristal-Candidate'}
    icon=json.loads((collection/'domains/Kristal-Catho/.kristal/icon-profile.json').read_text())
    assert icon['domains'][0]['code']=='3'
    assert icon['domains'][0]['uri']=='http://vocabularies.unesco.org/thesaurus/domain3'
    assert icon['rendering']['filename'].startswith('KR-REF-UT3-M')
    assert icon['classification']['scheme']=='UNESCO Thesaurus'
    assert json.loads((legacy/'icon-profile.json').read_text())['classification']['scheme']=='ISCED-F 2013'
    cp2=subprocess.run(['node',str(SCANNER),'--collection',str(collection),'--palette',str(PALETTE)],capture_output=True,text=True,timeout=25)
    assert cp2.returncode==0,cp2.stderr
    assert json.loads(cp2.stdout)['already_complete']==1


def test_icon_palette_is_pinned_framework_7_domains_88_microthesauri():
    palette=json.loads(PALETTE.read_text())
    profile=json.loads((ROOT/'tools/icon-generator/runtime/unesco-thesaurus-profile.json').read_text())
    assert len(profile['domains'])==len(palette['domains'])==7
    assert sum(len(x['microthesauri']) for x in profile['domains'])==88
    assert [(x['code'],x['uri']) for x in palette['domains']]==[(x['notation'],x['uri']) for x in profile['domains']]
    assert [x['icon_token'] for x in palette['domains']]==[f'UT{i}' for i in range(1,8)]
