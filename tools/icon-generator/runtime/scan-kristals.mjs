import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2);
function arg(name,def=null){const i=args.indexOf(name);return i>=0&&args[i+1]?args[i+1]:def;}
const collection=path.resolve(arg('--collection','C:\\mycode\\Kristal\\Kristal-Kollection'));
const palettePath=path.resolve(arg('--palette',path.join(here,'kristal-domain-palette.json')));
const registryPath=path.join(collection,'_registry','knowledge-base','registry','kristal-registry.catalog.json');
const domainsRoot=path.join(collection,'domains');
const NATURES=new Set(['REF','COL','MOD','PRT','TWN','INV','SRC']);
const SIZES=[16,20,24,32,40,48,64,96,128,256];

function readJson(p){try{return JSON.parse(fs.readFileSync(p,'utf8'));}catch{return null;}}
function isDir(p){try{return fs.statSync(p).isDirectory();}catch{return false;}}
function isFile(p){try{return fs.statSync(p).isFile();}catch{return false;}}
function mkdirp(p){fs.mkdirSync(p,{recursive:true});}
function norm(s){return String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}
function compact(s){return norm(s).replace(/\s+/g,'');}
function clamp(n,a,b){return Math.max(a,Math.min(b,n));}

const paletteDoc=readJson(palettePath)||{domains:[]};
const kosProfile=readJson(path.join(here,'unesco-thesaurus-profile.json'));
if(paletteDoc.classification?.kos_id!=='kos:unesco-thesaurus'||kosProfile?.domains?.length!==7)throw new Error('Pinned UNESCO Thesaurus reference missing or invalid');
const validMicros=new Map(kosProfile.domains.flatMap(d=>d.microthesauri.map(m=>[m.notation,{...m,domain:d.notation}])));
const palette=Array.isArray(paletteDoc.domains)?paletteDoc.domains:[];
const byCode=new Map(palette.map(d=>[String(d.code).toUpperCase(),d]));
const domainUris=new Map(palette.map(d=>[d.uri,d.code]));
const microUris=new Map([...validMicros.entries()].map(([code,m])=>[m.uri,code]));
function values(v){return typeof v==='string'?[v]:Array.isArray(v)?v.filter(x=>typeof x==='string'):[];}
function resolveNotations(codes,uris,requested){const result=[];const unknown=[];for(const raw of values(requested)){const val=String(raw).trim();const code=codes.has(val)?val:uris.get(val);if(code){if(!result.includes(code))result.push(code);}else unknown.push(val);}return {result,unknown};}
function declaredUnesco(workspace){
 const c=workspace?.classification||{};const u=c.unesco_thesaurus||c.unesco||workspace?.subject?.unesco_thesaurus||workspace?.subject?.unesco;
 if(!u||typeof u!=='object'||(u.kos_id&&u.kos_id!=='kos:unesco-thesaurus'))return {domains:[],issues:['missing_explicit_unesco_classification']};
 if(u.mapping_status==='candidate')return {domains:[],issues:['unesco_mapping_candidate_requires_review']};
 const ds=resolveNotations(byCode,domainUris,u.domains||u.domain||u.domain_notations);
 const ms=resolveNotations(validMicros,microUris,u.microthesauri||u.microthesaurus||u.microthesaurus_notations);
 const issues=[...ds.unknown.map(x=>`unknown_unesco_domain:${x}`),...ms.unknown.map(x=>`unknown_unesco_microthesaurus:${x}`)];
 if(issues.length)return {domains:[],issues};
 const implied=[...new Set(ms.result.map(x=>validMicros.get(x).domain))];
 if(ds.result.length&&implied.some(code=>!ds.result.includes(code)))return {domains:[],issues:['unesco_domain_microthesaurus_mismatch']};
 const codes=ds.result.length?ds.result:implied;
 if(codes.length>3)return {domains:[],issues:['more_than_three_unesco_domains_requires_review']};
 return {domains:codes.slice(0,3).map(code=>byCode.get(code)),microthesauri:ms.result,issues:codes.length?[]:['unesco_domain_not_declared']};
}

const natureRules=[
  ['SRC',/(^|\b)(sources?|source material|bibliograph|raw corpus|evidence library|catalogue de sources|references brutes)(\b|$)/i,0.96],
  ['TWN',/(^|\b)(digital twin|jumeau numerique|twin|mirror of (a )?real|representation of (a )?real evolving)(\b|$)/i,0.98],
  ['INV',/(^|\b)(investigation|enquete active|research notebook|proof attempt|hypothesis|experiment|demonstration en cours)(\b|$)/i,0.9],
  ['PRT',/(^|\b)(protocol|protocole|procedure|workflow|decision flow|playbook|operational rules|regles d action|ops manual)(\b|$)/i,0.9],
  ['MOD',/(^|\b)(model|modele|system model|architecture model|network model|circuit|simulation|diagnostic model|state machine)(\b|$)/i,0.86],
  ['COL',/(^|\b)(collection|catalog|catalogue|atlas|library|bibliotheque|media library|mediatheque|recipes|recettes|inventory|inventaire|list of|liste de)(\b|$)/i,0.84],
];

function parseDesktopIni(p){if(!isFile(p))return{};let b=fs.readFileSync(p),txt;if(b[0]===0xff&&b[1]===0xfe)txt=b.subarray(2).toString('utf16le');else txt=b.toString('utf8');let sec='',out={};for(const raw of txt.replace(/\r/g,'').split('\n')){const line=raw.trim();if(!line||line.startsWith(';')||line.startsWith('#'))continue;const sm=line.match(/^\[([^\]]+)\]$/);if(sm){sec=sm[1].toLowerCase();continue;}if(sec!=='kristal')continue;const m=line.match(/^([^=]+)=(.*)$/);if(m)out[m[1].trim()]=m[2].trim();}return out;}

function walkFiles(root,maxDepth=4){const out=[];function rec(dir,depth){if(depth>maxDepth)return;let ents=[];try{ents=fs.readdirSync(dir,{withFileTypes:true});}catch{return;}for(const e of ents){if(e.name==='_registry'||e.name==='node_modules'||e.name==='.git')continue;const p=path.join(dir,e.name);if(e.isFile())out.push(p);else if(e.isDirectory())rec(p,depth+1);}}rec(root,0);return out;}
function stateRank(p){const n=path.basename(p).toLowerCase();if(n.endsWith('.kristal-state.json')||n==='kristal_state.json')return 0;if(n.includes('structured-epistemic-state'))return 1;if(n.endsWith('.semantic.json'))return 2;return 9;}
function chooseState(files){const c=files.filter(p=>/\.json$/i.test(p)&&(/kristal[-_]state|structured[-_]epistemic[-_]state|\.semantic\.json/i.test(path.basename(p))));c.sort((a,b)=>stateRank(a)-stateRank(b)||a.length-b.length);return c[0]||null;}
function metadataTextFromJson(obj,limit=20000){const parts=[];let used=0;const skip=new Set(['assertions','source_refs','provenance','evidence','records','items','edges','nodes','referents','entities']);function rec(v,key='',depth=0){if(used>limit||depth>5)return;if(typeof v==='string'){if(v.length<=500){parts.push(key+' '+v);used+=v.length;}return;}if(typeof v==='number'||typeof v==='boolean'){parts.push(key+' '+String(v));used+=20;return;}if(Array.isArray(v)){if(skip.has(key))return;for(const x of v.slice(0,20))rec(x,key,depth+1);return;}if(v&&typeof v==='object'){for(const [k,x] of Object.entries(v)){if(skip.has(k))continue;rec(x,k,depth+1);}}}rec(obj);return parts.join('\n').slice(0,limit);}
function countArray(obj,key){return Array.isArray(obj?.[key])?obj[key].length:0;}

function inferNature(text,desktop,state,files){const explicit=String(desktop.Nature||state?.nature||state?.icon_nature||'').toUpperCase();if(NATURES.has(explicit))return{value:explicit,confidence:1,evidence:['explicit-metadata']};const at=String(state?.artifact_type||'');const fmt=String(state?.format||'');const hay=`${text}\n${at}\n${fmt}`;if(!state&&files.some(p=>/source|bibliograph|references?/i.test(p)))return{value:'SRC',confidence:.88,evidence:['sources-only-structure']};for(const [value,re,c] of natureRules){if(re.test(hay))return{value,confidence:c,evidence:['semantic-keyword']};}if(/catalog|collection/i.test(at+fmt))return{value:'COL',confidence:.88,evidence:['artifact-type']};if(/protocol|procedure/i.test(at+fmt))return{value:'PRT',confidence:.9,evidence:['artifact-type']};if(/model/i.test(at+fmt))return{value:'MOD',confidence:.86,evidence:['artifact-type']};return{value:'REF',confidence:.68,evidence:['conservative-reference-default']};}
function inferMaturity(desktop,state,files,readme){const dm=Number(desktop.Maturity);if(Number.isInteger(dm)&&dm>=0&&dm<=5)return{value:dm,confidence:1,evidence:['desktop-explicit']};const sm=Number(state?.maturity);if(Number.isInteger(sm)&&sm>=0&&sm<=5)return{value:sm,confidence:1,evidence:['state-explicit']};const assertions=countArray(state,'assertions'),sources=countArray(state,'source_refs');const schema=parseFloat(String(state?.schema_version||'0'))||0;let v=0,reasons=[];if(files.length>0){v=1;reasons.push('package-present');}if(state||files.some(p=>/\.json$/i.test(p))){v=Math.max(v,2);reasons.push('structured-metadata');}if(state&&(assertions>=50||sources>=3||files.length>=8)){v=Math.max(v,3);reasons.push('mapped-structure');}if(state&&schema>=6&&assertions>=500&&sources>=10){v=Math.max(v,4);reasons.push('strong-structural-validation');}if(readme&&readme.length>1000&&state&&assertions>=100)v=Math.max(v,3);return{value:v,confidence:v>=3?.84:.76,evidence:reasons};}
function validDomain(d){return d&&byCode.has(String(d.code||''))&&byCode.get(String(d.code)).uri===d.uri&&/^#[0-9A-F]{6}$/i.test(String(d.color||''));}
function validProfile(p){return p?.profile==='kristal-icon/1.0'&&NATURES.has(p.nature)&&Number.isInteger(p.maturity)&&p.maturity>=0&&p.maturity<=5&&Array.isArray(p.domains)&&p.domains.length>=1&&p.domains.length<=3&&p.classification?.scheme==='UNESCO Thesaurus'&&p.classification?.kos_id==='kos:unesco-thesaurus'&&p.domains.every(validDomain);}
function iconName(nature,domains,maturity){return `KR-${nature}-${domains.map(d=>d.icon_token).join('-')}-M${maturity}.ico`;}

let oldRegistry={entries:[]};if(isFile(registryPath))oldRegistry=readJson(registryPath)||oldRegistry;const oldById=new Map((oldRegistry.entries||[]).map(e=>[e.kristal_id,e]));
const result={profile:'kristal-icon-auto-scan/1.2',generated_at:new Date().toISOString(),collection_root:collection,scanned:0,already_complete:0,generated:0,new_kristals:[],repaired_incomplete:[],unresolved_unesco:[],items:[]};
if(!isDir(domainsRoot)){console.error(`domains introuvable: ${domainsRoot}`);process.exit(2);}
for(const ent of fs.readdirSync(domainsRoot,{withFileTypes:true}).filter(e=>e.isDirectory()&&e.name.startsWith('Kristal-')).sort((a,b)=>a.name.localeCompare(b.name))){
  result.scanned++;
  const dir=path.join(domainsRoot,ent.name),metaDir=path.join(dir,'.kristal'),profilePath=path.join(metaDir,'icon-profile.json'),scanPath=path.join(metaDir,'auto-scan.json');
  const existing=readJson(profilePath);const old=oldById.get(ent.name);
  const oldComplete=validProfile(old?.presentation?.icon);
  // The old ISCED-F profile is NEVER a source of UNESCO classification.
  const workspace=readJson(path.join(dir,'kristal.workspace.json'));
  const mapping=declaredUnesco(workspace);
  if(!mapping.domains.length){result.unresolved_unesco.push(ent.name);result.items.push({kristal_id:ent.name,status:'unresolved_unesco',issues:mapping.issues});continue;}
  const domains=mapping.domains;
  const existingUnesco=validProfile(existing)&&existing.domains.map(d=>d.code).join(',')===domains.map(d=>d.code).join(',')&&existing.rendering?.filename===iconName(existing.nature,domains,existing.maturity);
  if(existingUnesco){result.already_complete++;continue;}
  const files=walkFiles(dir,4);const statePath=chooseState(files);const state=statePath?readJson(statePath):null;
  let readme='';for(const n of ['README.md','Readme.md','readme.md']){const rp=path.join(dir,n);if(isFile(rp)){try{readme=fs.readFileSync(rp,'utf8').slice(0,50000);}catch{}break;}}
  const desktop=parseDesktopIni(path.join(dir,'desktop.ini'));
  const text=`${ent.name}\n${desktop.Title||''}\n${readme}\n${metadataTextFromJson(state||{},20000)}`;
  const nat=inferNature(text,desktop,state,files);const mat=inferMaturity(desktop,state,files,readme);
  const nature=NATURES.has(existing?.nature)?existing.nature:nat.value;
  const maturity=Number.isInteger(existing?.maturity)&&existing.maturity>=0&&existing.maturity<=5?existing.maturity:mat.value;
  const cleanDomains=domains.map(d=>({code:d.code,icon_token:d.icon_token,name:d.name,uri:d.uri,color:d.color.toUpperCase()}));
  const filename=iconName(nature,domains,maturity);
  const parsed=workspace?.classification?.unesco_thesaurus||workspace?.classification?.unesco||workspace?.subject?.unesco_thesaurus||workspace?.subject?.unesco||{};
  const profile={profile:'kristal-icon/1.0',kristal_ref:ent.name,nature,maturity,domains:cleanDomains,
    rendering:{nature_icon_color:'#1e6864',sizes:SIZES,filename},
    classification:{origin:'kristal-icon-auto-scan/unesco-1.0',scheme:'UNESCO Thesaurus',kos_id:'kos:unesco-thesaurus',level:'domain',publisher:'UNESCO',domain_uris:domains.map(d=>d.uri),microthesauri:mapping.microthesauri||[],mapping_status:parsed.mapping_status||'declared',policy:'only explicit, internally consistent UNESCO workspace declarations; no ISCED-F fallback'}};
  const report={profile:'kristal-icon-auto-scan.record/1.2',generated_at:new Date().toISOString(),kristal_id:ent.name,status:'generated',was_in_registry:!!old,registry_profile_complete_before:!!oldComplete,
    state_file:statePath?path.relative(dir,statePath).replace(/\\/g,'/'):null,assertions:countArray(state,'assertions'),sources:countArray(state,'source_refs'),file_count:files.length,
    inference:{nature:nat,maturity:mat,domains:{source:'explicit-unesco-workspace',codes:domains.map(d=>d.code)}},result:{nature,maturity,domains:cleanDomains,filename}};
  mkdirp(metaDir);fs.writeFileSync(profilePath,JSON.stringify(profile,null,2)+'\n','utf8');fs.writeFileSync(scanPath,JSON.stringify(report,null,2)+'\n','utf8');
  result.generated++;if(!old)result.new_kristals.push(ent.name);else result.repaired_incomplete.push(ent.name);result.items.push(report);
}
mkdirp(path.join(collection,'_registry'));fs.writeFileSync(path.join(collection,'_registry','icon-scan-report.json'),JSON.stringify(result,null,2)+'\n','utf8');console.log(JSON.stringify(result,null,2));
