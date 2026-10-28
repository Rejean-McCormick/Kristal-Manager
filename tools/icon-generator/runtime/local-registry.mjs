/** Read-only UNESCO icon preview catalogue for Manager's local Kristals.
 * No Registry, icon profile, desktop.ini, or shell attributes are created here.
 * Workspaces are authoritative; historic ISCED presentation hints are never mapped.
 */
import fs from 'node:fs';
import path from 'node:path';

const NATURES = new Set(['REF','COL','MOD','PRT','TWN','INV','SRC']);
const SIZES=[16,20,24,32,40,48,64,96,128,256];
function jsonFile(filename) {
  try {
    if (fs.lstatSync(filename).isSymbolicLink() || fs.statSync(filename).size > 1024*1024) return null;
    return JSON.parse(fs.readFileSync(filename,'utf8'));
  } catch { return null; }
}
function accepted(value) { return typeof value==='string' ? [value] : Array.isArray(value) ? value.filter(v=>typeof v==='string') : []; }
function resolveCodes(value, codeMap, uriMap) {
  const result=[];const errors=[];
  for(const item of accepted(value)) {
    const v=item.trim(), code=codeMap.has(v) ? v : uriMap.get(v);
    if(!code) errors.push(v);
    else if(!result.includes(code)) result.push(code);
  }
  return {result,errors};
}
export function buildLocalRegistry(localsRoot, palettePath, profilePath) {
  const palette=jsonFile(palettePath), kos=jsonFile(profilePath);
  if(palette?.classification?.kos_id!=='kos:unesco-thesaurus' || kos?.domains?.length!==7)
    throw new Error('Référentiel Thésaurus UNESCO non disponible');
  const domains=new Map(palette.domains.map(d=>[d.code,d]));
  const domainUris=new Map(palette.domains.map(d=>[d.uri,d.code]));
  const micros=new Map(kos.domains.flatMap(d=>d.microthesauri.map(m=>[m.notation,d.notation])));
  const microUris=new Map(kos.domains.flatMap(d=>d.microthesauri.map(m=>[m.uri,m.notation])));
  const root=fs.realpathSync(localsRoot);
  const entries=[],unresolved=[];
  for(const ent of fs.readdirSync(root,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name,'fr'))) {
    if(!ent.isDirectory() || !/^Kristal-[A-Za-z0-9][A-Za-z0-9._-]*$/.test(ent.name)) continue;
    const folder=path.join(root,ent.name);
    // Never traverse symlinks/junctions outside the selected local root.
    if(!fs.realpathSync(folder).startsWith(root+path.sep)) continue;
    const workspace=jsonFile(path.join(folder,'kristal.workspace.json'));
    if(!workspace || typeof workspace!=='object' || Array.isArray(workspace)) continue;
    const u=workspace.classification?.unesco_thesaurus || workspace.classification?.unesco || workspace.subject?.unesco_thesaurus || workspace.subject?.unesco;
    let reason='missing_explicit_unesco_classification'; let profile=null;
    if(u && typeof u==='object' && !Array.isArray(u) && (!u.kos_id || u.kos_id==='kos:unesco-thesaurus') &&
       !['candidate','unverified','rejected'].includes(u.mapping_status)) {
      const ds=resolveCodes(u.domains??u.domain??u.domain_notations,domains,domainUris);
      const ms=resolveCodes(u.microthesauri??u.microthesaurus??u.microthesaurus_notations,micros,microUris);
      const inferred=[...new Set(ms.result.map(code=>micros.get(code)))];
      const codes=ds.result.length ? ds.result : inferred;
      if(ds.errors.length||ms.errors.length) reason='unknown_unesco_code';
      else if(ds.result.length && inferred.some(code=>!ds.result.includes(code))) reason='domain_microthesaurus_mismatch';
      else if(codes.length<1||codes.length>3) reason='unclassified_or_too_many_domains';
      else {
        const oldProfile=jsonFile(path.join(folder,'.kristal','icon-profile.json'));
        const nature=NATURES.has(oldProfile?.nature) ? oldProfile.nature : 'REF';
        const maturity=Number.isInteger(oldProfile?.maturity) && oldProfile.maturity>=0 && oldProfile.maturity<=5 ? oldProfile.maturity : 1;
        const selected=codes.map(code=>domains.get(code));
        const filename=`KR-${nature}-${selected.map(d=>d.icon_token).join('-')}-M${maturity}.ico`;
        profile={profile:'kristal-icon/1.0',kristal_ref:workspace.state_ref||ent.name,
          nature,maturity,domains:selected.map(d=>({code:d.code,name:d.name,icon_token:d.icon_token,uri:d.uri,color:d.color})),
          rendering:{nature_icon_color:'#1e6864',sizes:SIZES,filename},
          classification:{scheme:'UNESCO Thesaurus',kos_id:'kos:unesco-thesaurus',origin:'explicit-local-workspace',
            mapping_status:u.mapping_status||'declared',domain_uris:selected.map(d=>d.uri),microthesauri:ms.result}};
      }
    } else if(u?.mapping_status==='candidate') reason='unesco_candidate_review_required';
    if(!profile) unresolved.push({folder:ent.name,reason});
    entries.push({kristal_id:ent.name,kristal_ref:workspace.state_ref||ent.name,
      title:workspace.title||ent.name,kind:'domain',locator:ent.name,availability:'present',
      presentation:profile?{icon:profile}:{},bindings:{},metrics:{},
      observed_at:new Date().toISOString()});
  }
  return {catalog:{format:'kristal-registry.catalog/1.1',generated_at:new Date().toISOString(),
    scope:'local-preview-read-only',entries},unresolved,scanned:entries.length};
}
