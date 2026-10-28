#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from kristaldiag import VERSION,STANDARD_TARGET,FRAMEWORK_REPOSITORY,FRAMEWORK_COMMIT,FRAMEWORK_SNAPSHOT_SHA256,FRAMEWORK_PIN_STATUS
from kristaldiag.manifest import LEVELS,CAMPAIGNS
from kristaldiag.profiles import PROFILES
out={
 'schema':'kristaldiag.manifest.v4','suite':'KristalDiag','suite_version':VERSION,
 'kristal_standard_target':STANDARD_TARGET,
 'framework_pin':{'repository':FRAMEWORK_REPOSITORY,'commit':FRAMEWORK_COMMIT,'snapshot_sha256':FRAMEWORK_SNAPSHOT_SHA256,'status':FRAMEWORK_PIN_STATUS},
 'repository_mode':'external-target-harness','control_dir_default':'.kristaldiag',
 'consolidates':['levelupdiag_kristal@0.6.0','kristaldiag@0.2.0','kristaldiag@0.7.0','kristaldiag@0.9.0'],
 'levels':[{'id':k,**v} for k,v in LEVELS.items()],
 'campaigns':CAMPAIGNS,
 'profiles':PROFILES,
 'authority':{'qualification_only':True,'authority_granted':False},
}
(ROOT/'kristaldiag_manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(f'kristaldiag_manifest.json: {len(LEVELS)} levels / {len(PROFILES)} profiles')
