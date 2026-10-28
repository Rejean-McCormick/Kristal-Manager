from __future__ import annotations
from pathlib import Path
from .utils import write_json

def markdown_report(summary:dict, results:list[dict])->str:
    lines=[f"# KristalDiag report — {summary.get('verdict')}","",f"- Run: `{summary.get('run_id')}`",f"- Target: `{summary.get('target_root')}`",f"- Profile: `{summary.get('profile') or 'diagnostic'}`",f"- Kristal target: `{summary.get('kristal_standard_target')}`","",'## Levels','', '| Level | Verdict | Name |','|---|---|---|']
    for r in results:lines.append(f"| {r['level_id']} | **{r['verdict']}** | {r['level_name']} |")
    lines += ['', '## Findings', '']
    non=0
    for r in results:
        fs=[f for f in r.get('findings',[]) if f.get('verdict') not in {'PASS','SKIP'}]
        if not fs:continue
        non+=len(fs);lines += [f"### {r['level_id']} — {r['level_name']}",'']
        for f in fs:
            lines.append(f"#### {f.get('verdict')} `{f.get('id')}`")
            lines.append('');lines.append(f.get('message',''));lines.append('')
            if f.get('path'):lines.append(f"- Path: `{f['path']}`")
            if f.get('standard_ref'):lines.append(f"- Standard: {f['standard_ref']}")
            if f.get('impact'):lines.append(f"- Impact: {f['impact']}")
            if f.get('remediation'):lines.append(f"- Remediation: {f['remediation']}")
            if 'expected' in f:lines.append(f"- Expected: `{f['expected']}`")
            if 'observed' in f:lines.append(f"- Observed: `{f['observed']}`")
            if f.get('evidence') is not None:
                lines += ['','```json',__import__('json').dumps(f['evidence'],ensure_ascii=False,indent=2,default=str)[:12000],'```']
            lines.append('')
    if not non:lines += ['No non-PASS findings.','']
    lines += ['## Conformance','',f"Final verdict: **{summary.get('verdict')}**",'']
    return '\n'.join(lines)+'\n'

def write_reports(run_root:Path, summary:dict, results:list[dict], verdict:dict):
    write_json(run_root/'summary.json',summary)
    write_json(run_root/'conformance-verdict.json',verdict)
    (run_root/'report.md').write_text(markdown_report(summary,results),encoding='utf-8')
    text=[f"KristalDiag — {summary['verdict']}",f"Run: {summary['run_id']}",f"Target: {summary['target_root']}",f"Profile: {summary.get('profile') or '-'}",'']
    text += [f"{r['level_id']:>3}  {r['verdict']:<12} {r['level_name']}" for r in results]
    (run_root/'summary.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
