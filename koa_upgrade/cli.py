"""CLI non-PowerShell: python -m koa_upgrade.cli <action>."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from . import engine as e

def main(argv=None):
 p=argparse.ArgumentParser(description='kOA Orchestrateur Kristal — overlay non destructif')
 p.add_argument('--config',type=Path,default=None,help='JSON des chemins; sinon chemins du SmartDump 2026-11-19')
 sub=p.add_subparsers(dest='action',required=True)
 sub.add_parser('inventaire')
 sub.add_parser('kit-status')
 prep=sub.add_parser('preparer');prep.add_argument('--candidate',required=True,type=Path)
 for action in ('valider','diagnostiquer','installer','restaurer'):
  q=sub.add_parser(action);q.add_argument('--campagne',required=True)
  if action in ('installer','restaurer'):q.add_argument('--confirmer',action='store_true')
  if action=='installer':
   q.add_argument('--accepter-heritage-v6',action='store_true')
   q.add_argument('--accepter-discovery-perimee',action='store_true')
 a=p.parse_args(argv)
 try:
  conf=e.resolve_conf(a.config)
  if a.action=='inventaire':r=e.inventory(conf)
  elif a.action=='kit-status':r=e.kit_status(conf)
  elif a.action=='preparer':r=e.stage(conf,a.candidate)
  elif a.action=='valider':r=e.validate(conf,a.campagne)
  elif a.action=='diagnostiquer':r=e.diagnose(conf,a.campagne)
  elif a.action=='installer':r=e.install(conf,a.campagne,a.confirmer,a.accepter_heritage_v6,a.accepter_discovery_perimee)
  elif a.action=='restaurer':r=e.rollback(conf,a.campagne,a.confirmer)
  else:raise AssertionError(a.action)
  print(json.dumps(r,indent=2,ensure_ascii=False,default=str))
  return 0
 except (e.UpgradeError,OSError,ValueError,KeyError,FileNotFoundError) as err:
  print('[BLOQUÉ]',str(err),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
