#!/usr/bin/env python3
from __future__ import annotations
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LINK=re.compile(r'\[[^\]]*\]\(([^)]+)\)')
bad=[];checked=0
for p in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
    if not p.is_file():continue
    text=p.read_text(encoding='utf-8')
    for raw in LINK.findall(text):
        link=raw.strip().split('#',1)[0]
        if not link or link.startswith(('http://','https://','mailto:','#','data:')):continue
        if link.startswith('<') and link.endswith('>'):link=link[1:-1]
        checked+=1
        if not (p.parent/link).resolve(strict=False).exists():bad.append((p.relative_to(ROOT).as_posix(),raw))
if bad:
    for a,b in bad:print(f'BROKEN {a}: {b}')
    raise SystemExit(1)
print(f'Markdown links: PASS ({checked} local links checked)')
