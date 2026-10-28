from __future__ import annotations
import os, shlex, subprocess, time
from pathlib import Path

SECRET_PATTERNS = ('TOKEN','SECRET','PASSWORD','API_KEY','ACCESS_KEY')

def normalize_command(command):
    if isinstance(command,str): return shlex.split(command,posix=(os.name!='nt'))
    if isinstance(command,list) and all(isinstance(x,str) for x in command): return command
    raise ValueError('command must be a string or list of strings')

def _redact(text:str)->str:
    # Conservative line-level redaction for evidence. Do not attempt to preserve secret values.
    out=[]
    for line in text.splitlines():
        if any(k in line.upper() for k in SECRET_PATTERNS) and ('=' in line or ':' in line):
            head=line.split('=',1)[0] if '=' in line else line.split(':',1)[0]
            out.append(head+'=<REDACTED>')
        else: out.append(line)
    return '\n'.join(out)

def run_command(command,*,cwd:Path,timeout_seconds:int=120,capture_limit_kb:int=256,env=None,redact_output:bool=True):
    argv=normalize_command(command)
    if not argv: raise ValueError('empty command')
    started=time.monotonic()
    try:
        cp=subprocess.run(argv,cwd=str(cwd),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          text=True,encoding='utf-8',errors='replace',timeout=timeout_seconds,shell=False,check=False)
        timed_out=False;code=cp.returncode;out=cp.stdout or '';err=cp.stderr or ''
    except subprocess.TimeoutExpired as e:
        timed_out=True;code=None
        out=e.stdout.decode('utf-8','replace') if isinstance(e.stdout,bytes) else (e.stdout or '')
        err=e.stderr.decode('utf-8','replace') if isinstance(e.stderr,bytes) else (e.stderr or '')
    if redact_output: out,err=_redact(out),_redact(err)
    limit=max(1,int(capture_limit_kb))*1024
    return {'argv':argv,'cwd':str(cwd),'exit_code':code,'timed_out':timed_out,'duration_seconds':round(time.monotonic()-started,3),
            'stdout_tail':out[-limit:],'stderr_tail':err[-limit:]}
