import importlib.util
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'kristal_manager/unesco_registry_discovery_v16.py'
spec=importlib.util.spec_from_file_location('ud16',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RegistryDiscoverTests(unittest.TestCase):
    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            gate=Path(d)/'gate.py';gate.write_text('# safe fake')
            r=m.discover([Path(d)],gate)
            self.assertEqual((r['candidate_workspace_count'],r['branch_verified_workspace_count']),(0,0))
    def test_nested_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'branch'/'workspace';(p/'.kristal/v11').mkdir(parents=True)
            (p/'.kristal/v11/authoring.json').write_text('{}');(p/'kristal.workspace.json').write_text('{}')
            gate=root/'gate.py';gate.write_text('# safe fake')
            fake={'state':'KIT_V11_EXISTING_BRANCH_VERIFIED', 'report':{'workspace_branch_binding':'EXPLICIT_SLUG_MATCH'}}
            with patch.object(m,'_check_gate',return_value=fake):r=m.discover([root],gate)
            self.assertEqual(r['branch_verified_workspace_count'],1)
            self.assertEqual(r['selection_status'],'ONE_VERIFIED_EXISTING_WORKSPACE')
    def test_reject_unverified_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);gate=p/'gate.py';gate.write_text('# fake')
            (p/'.kristal/v11').mkdir(parents=True)
            (p/'.kristal/v11/authoring.json').write_text('{}');(p/'kristal.workspace.json').write_text('{}')
            with patch.object(m,'_check_gate',return_value={'state':'KIT_REJECTED','error':'x'}):r=m.discover([p],gate)
            self.assertEqual(r['branch_verified_workspace_count'],0)
    def test_multiple_does_not_select(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);gate=p/'gate.py';gate.write_text('#')
            for x in ('a','b'):
                w=p/x;(w/'.kristal/v11').mkdir(parents=True)
                (w/'.kristal/v11/authoring.json').write_text('{}');(w/'kristal.workspace.json').write_text('{}')
            with patch.object(m,'_check_gate',return_value={'state':'KIT_V11_EXISTING_BRANCH_VERIFIED','report':{}}):r=m.discover([p],gate)
            self.assertIsNone(r['selected_readonly_workspace'])
    def test_limit(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(12):(Path(d)/f'x{i}').mkdir()
            with self.assertRaises(m.DiscoveryError):m._paths(Path(d),limit=5)
    def test_oversized_root_is_not_treated_as_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);gate=p/'gate.py';gate.write_text('#')
            for i in range(12):(p/f'x{i}').mkdir()
            r=m.discover([p],gate,limit=5)
            self.assertEqual(r['branch_verified_workspace_count'],0)
            self.assertEqual(len(r['search_roots_skipped']),1)
    def test_fake_gate_is_never_authoritative(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);gate=p/'gate.py';gate.write_text('import json\nprint(json.dumps({"workspace_v11_status":"V11_PROFILE_ABSENT"}))\n')
            workspace=p/'w';workspace.mkdir()
            r=m.discover([],gate,explicit_workspace=workspace)
            self.assertEqual(r['selection_status'],'NO_EXISTING_VERIFIED_WORKSPACE')

if __name__=='__main__':unittest.main()
