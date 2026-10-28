from __future__ import annotations

LEVELS = {
    'N00': {'name':'Diagnostic Integrity','depends_on':[],'parallel_safe':True,'timeout_seconds':60,'category':'diagnostics'},
    'N01': {'name':'Target Context','depends_on':['N00'],'parallel_safe':True,'timeout_seconds':60,'category':'context'},
    'N02': {'name':'Repository Inventory','depends_on':['N01'],'parallel_safe':True,'timeout_seconds':300,'category':'inventory'},
    'N03': {'name':'Repository Hygiene','depends_on':['N02'],'parallel_safe':True,'timeout_seconds':180,'category':'hygiene'},
    'N04': {'name':'Tooling Discovery','depends_on':['N02'],'parallel_safe':True,'timeout_seconds':120,'category':'tooling'},
    'N05': {'name':'Declared Validations','depends_on':['N01','N02'],'parallel_safe':False,'timeout_seconds':1800,'category':'validation'},
    'N06': {'name':'Security Hygiene','depends_on':['N02'],'parallel_safe':True,'timeout_seconds':180,'category':'security_hygiene'},
    'K00': {'name':'Control & Discovery','depends_on':['N00','N01','N02'],'parallel_safe':True,'timeout_seconds':120,'category':'v7'},
    'K01': {'name':'Repository & Static Integrity','depends_on':['K00','N03'],'parallel_safe':True,'timeout_seconds':120,'category':'v7'},
    'K02': {'name':'Kristal State v6','depends_on':['K00'],'parallel_safe':True,'timeout_seconds':180,'category':'v6'},
    'K03': {'name':'Kristall v7 Metadata','depends_on':['K00'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K04': {'name':'Canonicalization & Identity','depends_on':['K02','K03'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K05': {'name':'Assertion Families','depends_on':['K03'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K06': {'name':'Mesh','depends_on':['K03','K05'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K07': {'name':'Axes & Subjects','depends_on':['K03'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K08': {'name':'Surfaces & Projection Readiness','depends_on':['K06','K07'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K09': {'name':'Projection','depends_on':['K08','K02'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K10': {'name':'Semantic Resonance','depends_on':['K06'],'parallel_safe':True,'timeout_seconds':180,'category':'v7'},
    'K11': {'name':'Interoperability','depends_on':['K09'],'parallel_safe':False,'timeout_seconds':300,'category':'interop'},
    'K12': {'name':'Determinism & Reproducibility','depends_on':['K04'],'parallel_safe':False,'timeout_seconds':300,'category':'reproducibility'},
    'K13': {'name':'Negative & Adversarial Corpus','depends_on':['K04'],'parallel_safe':False,'timeout_seconds':300,'category':'negative'},
    'K14': {'name':'Conformance & Release Gate','depends_on':[],'parallel_safe':False,'timeout_seconds':60,'category':'gate'},
    'K15': {'name':'V9 Machine Contracts','depends_on':['K00','K01'],'parallel_safe':True,'timeout_seconds':180,'category':'v9'},
    'K16': {'name':'V9 Independent Logical Commitments','depends_on':['K15'],'parallel_safe':False,'timeout_seconds':300,'category':'v9'},
    'K17': {'name':'V9 State Snapshot Semantics','depends_on':['K15','K16'],'parallel_safe':True,'timeout_seconds':180,'category':'v9'},
    'K18': {'name':'V9 Derivations & Reproducibility','depends_on':['K15','K16'],'parallel_safe':True,'timeout_seconds':180,'category':'v9'},
    'K19': {'name':'V9 Materialization Binding','depends_on':['K15','K16'],'parallel_safe':True,'timeout_seconds':180,'category':'v9'},
    'K20': {'name':'V9 Exchange Binding','depends_on':['K15','K17'],'parallel_safe':True,'timeout_seconds':180,'category':'v9'},
    'K21': {'name':'V9 Build / Publish / Activate','depends_on':['K15','K17'],'parallel_safe':False,'timeout_seconds':240,'category':'v9'},
    'K22': {'name':'V9 Polymorphism Workloads','depends_on':['K15','K16'],'parallel_safe':False,'timeout_seconds':240,'category':'v9'},
    'K23': {'name':'V9 Negative & Invariance Corpus','depends_on':['K16'],'parallel_safe':False,'timeout_seconds':240,'category':'v9'},
    'K24': {'name':'V9 Inherited Compatibility Substrate','depends_on':['K15'],'parallel_safe':False,'timeout_seconds':300,'category':'compatibility'},
    'K25': {'name':'V10 Machine Contracts & Capabilities','depends_on':['K00','K01'],'parallel_safe':True,'timeout_seconds':180,'category':'v10'},
    'K26': {'name':'V10 Node / Binding Relations','depends_on':['K25'],'parallel_safe':True,'timeout_seconds':180,'category':'v10'},
    'K27': {'name':'V10 Publication Bundle Integrity','depends_on':['K25','K26'],'parallel_safe':False,'timeout_seconds':300,'category':'v10'},
    'K28': {'name':'V10 Directory & Discovery Semantics','depends_on':['K25','K26'],'parallel_safe':True,'timeout_seconds':180,'category':'v10'},
    'K29': {'name':'V10 GitHub Host Profile','depends_on':['K25','K26'],'parallel_safe':True,'timeout_seconds':1800,'category':'v10'},
    'K30': {'name':'V10 Semantic / Hosting Separation','depends_on':['K25'],'parallel_safe':False,'timeout_seconds':240,'category':'v10'},
    'K31': {'name':'V10 Negative & Adversarial Corpus','depends_on':['K25'],'parallel_safe':False,'timeout_seconds':240,'category':'v10'},
    'K32': {'name':'V10 Standard / Contract-Set Alignment','depends_on':['N02'],'parallel_safe':True,'timeout_seconds':180,'category':'compatibility'},
    'R00': {'name':'Documentation & Link Integrity','depends_on':['N02'],'parallel_safe':True,'timeout_seconds':240,'category':'release'},
    'R01': {'name':'Snapshot & Manifest Reproducibility','depends_on':['N02'],'parallel_safe':False,'timeout_seconds':300,'category':'release'},
    'R02': {'name':'Git & Release Identity','depends_on':['N01'],'parallel_safe':True,'timeout_seconds':120,'category':'release'},
    'R03': {'name':'Signature & Trust Surface','depends_on':['K02'],'parallel_safe':True,'timeout_seconds':180,'category':'release'},
    'R04': {'name':'Contract / TCK / Profile Consistency','depends_on':['N00','K04'],'parallel_safe':True,'timeout_seconds':180,'category':'release'},
}

CAMPAIGNS = {
    'baseline': ['N00','N01','N02','N03','N04','N06'],
    'standard': ['N00','N01','N02','N03','N04','N06','K00','K01','K02','K03','K04','K12','K13'],
    'v9': ['N00','N01','N02','N03','N04','N06','K00','K01'] + [f'K{i:02d}' for i in range(15,25)],
    'v10': ['N00','N01','N02','N03','N04','N06','K00','K01'] + [f'K{i:02d}' for i in range(25,32)],
    'deep': ['N00','N01','N02','N03','N04','N05','N06'] + [f'K{i:02d}' for i in range(14)] + [f'K{i:02d}' for i in range(15,33)],
    'release': ['N00','N01','N02','N03','N04','N05','N06'] + [f'K{i:02d}' for i in range(14)] + [f'K{i:02d}' for i in range(15,33)] + [f'R{i:02d}' for i in range(5)],
}


ORDER = list(LEVELS)


def closure(selected:list[str])->list[str]:
    wanted=set(selected)
    changed=True
    while changed:
        changed=False
        for lid in list(wanted):
            for dep in LEVELS.get(lid,{}).get('depends_on',[]):
                if dep not in wanted:
                    wanted.add(dep);changed=True
    return [x for x in ORDER if x in wanted and x!='K14']
