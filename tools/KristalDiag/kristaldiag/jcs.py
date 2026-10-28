from __future__ import annotations
import copy, hashlib, json, math
from typing import Any

def _utf16_key(s:str):
    b=s.encode('utf-16-be','surrogatepass')
    return tuple(int.from_bytes(b[i:i+2],'big') for i in range(0,len(b),2))

def _string(s:str)->str:
    # Python's JSON escaping with ensure_ascii=False matches RFC8785 string escaping for valid Unicode.
    return json.dumps(s, ensure_ascii=False, separators=(',',':'))

def _number(n):
    if isinstance(n,bool): return 'true' if n else 'false'
    if isinstance(n,int): return str(n)
    if not math.isfinite(n): raise ValueError('non-finite number is not I-JSON')
    if n == 0: return '0'
    # Python repr is shortest-round-trip. Normalize exponent zeros/sign casing to ECMAScript/JCS shape.
    s=repr(float(n)).lower()
    if s.endswith('.0') and 'e' not in s: s=s[:-2]
    if 'e' in s:
        mant,exp=s.split('e',1)
        sign=''
        if exp.startswith(('+','-')):
            sign=exp[0]; exp=exp[1:]
        exp=exp.lstrip('0') or '0'
        if sign=='+': sign='+'
        s=f'{mant}e{sign}{exp}'
    return s

def canonicalize(value:Any)->str:
    if value is None:return 'null'
    if value is True:return 'true'
    if value is False:return 'false'
    if isinstance(value,(int,float)) and not isinstance(value,bool):return _number(value)
    if isinstance(value,str):return _string(value)
    if isinstance(value,list):return '['+','.join(canonicalize(x) for x in value)+']'
    if isinstance(value,dict):
        keys=sorted(value.keys(),key=_utf16_key)
        return '{'+','.join(_string(k)+':'+canonicalize(value[k]) for k in keys)+'}'
    raise TypeError(f'unsupported JSON type: {type(value).__name__}')

def remove_pointer(doc:Any,pointer:str):
    if pointer=='':raise ValueError('root exclusion unsupported')
    if not pointer.startswith('/'):raise ValueError(f'invalid JSON pointer: {pointer}')
    parts=[x.replace('~1','/').replace('~0','~') for x in pointer[1:].split('/')]
    cur=doc
    for part in parts[:-1]:
        if isinstance(cur,dict) and part in cur:cur=cur[part]
        elif isinstance(cur,list) and part.isdigit() and int(part)<len(cur):cur=cur[int(part)]
        else:return
    last=parts[-1]
    if isinstance(cur,dict):cur.pop(last,None)
    elif isinstance(cur,list) and last.isdigit() and int(last)<len(cur):cur.pop(int(last))

def digest(value:Any, exclusions=()):
    target=copy.deepcopy(value)
    for p in exclusions:remove_pointer(target,p)
    text=canonicalize(target)
    hx=hashlib.sha256(text.encode('utf-8')).hexdigest()
    return text,hx,'sha256:'+hx
