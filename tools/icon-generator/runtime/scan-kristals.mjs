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

const paletteDoc=readJson(palettePath)||{domains:[],aliases:{},legacy_to_isced:{}};
const palette=Array.isArray(paletteDoc.domains)?paletteDoc.domains:[];
const byCode=new Map(palette.map(d=>[String(d.code).toUpperCase(),d]));
const byNormName=new Map();
for(const d of palette){byNormName.set(compact(d.name),d);if(d.name_en)byNormName.set(compact(d.name_en),d);byNormName.set(compact(d.code),d);}
const aliases=Object.fromEntries(Object.entries(paletteDoc.aliases||{}).map(([k,v])=>[compact(k),String(v).toUpperCase()]));
const legacyToIsced=Object.fromEntries(Object.entries(paletteDoc.legacy_to_isced||{}).map(([k,v])=>[String(k).toUpperCase(),String(v).toUpperCase()]));

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

function explicitDomainCandidates(desktop,state){const vals=[];for(const k of ['Domain1','Domain2','Domain3'])if(desktop[k])vals.push(desktop[k]);function add(v){if(typeof v==='string')vals.push(v);else if(Array.isArray(v))for(const x of v)add(x);else if(v&&typeof v==='object')for(const k of ['code','name','domain','subdomain'])if(v[k])add(v[k]);}
  add(state?.domain);add(state?.domains);add(state?.applicability?.domain);add(state?.applicability?.subdomain);return vals;}
function paletteMatch(value){const c=String(value??'').trim().toUpperCase();if(byCode.has(c))return byCode.get(c);if(legacyToIsced[c]&&byCode.has(legacyToIsced[c]))return byCode.get(legacyToIsced[c]);const n=compact(value);if(byNormName.has(n))return byNormName.get(n);if(aliases[n]&&byCode.has(aliases[n]))return byCode.get(aliases[n]);return null;}
function scoreDomains(folderName,text,desktop,state){const picked=[];const scores=new Map();function score(d,n,why){if(!d)return;const code=d.code;const prev=scores.get(code)||{score:0,reasons:[]};prev.score+=n;prev.reasons.push(why);scores.set(code,prev);}for(const v of explicitDomainCandidates(desktop,state)){const d=paletteMatch(v);if(d)score(d,100,'explicit:'+v);}const suffix=folderName.replace(/^Kristal[-_ ]*/i,'');let d=paletteMatch(suffix);if(d)score(d,80,'folder:'+suffix);const ntext=' '+norm(`${suffix}\n${text}`)+' ';for(const [alias,code] of Object.entries(aliases)){const phrase=' '+norm(alias)+' ';if(ntext.includes(phrase)&&byCode.has(code))score(byCode.get(code),alias.length>=6?18:9,'keyword:'+alias);}for(const pd of palette){const nn=norm(pd.name);if(nn.length>=4&&ntext.includes(' '+nn+' '))score(pd,12,'palette-name:'+pd.name);}const ordered=[...scores.entries()].sort((a,b)=>b[1].score-a[1].score);for(const [code,meta] of ordered){if(picked.length>=3)break;if(meta.score<12&&picked.length)continue;picked.push({...byCode.get(code),confidence:clamp(meta.score/100,0.55,1),evidence:meta.reasons});}
  return picked;
}
function inferNature(text,desktop,state,files){const explicit=String(desktop.Nature||state?.nature||state?.icon_nature||'').toUpperCase();if(NATURES.has(explicit))return{value:explicit,confidence:1,evidence:['explicit-metadata']};const at=String(state?.artifact_type||'');const fmt=String(state?.format||'');const hay=`${text}\n${at}\n${fmt}`;if(!state&&files.some(p=>/source|bibliograph|references?/i.test(p)))return{value:'SRC',confidence:.88,evidence:['sources-only-structure']};for(const [value,re,c] of natureRules){if(re.test(hay))return{value,confidence:c,evidence:['semantic-keyword']};}if(/catalog|collection/i.test(at+fmt))return{value:'COL',confidence:.88,evidence:['artifact-type']};if(/protocol|procedure/i.test(at+fmt))return{value:'PRT',confidence:.9,evidence:['artifact-type']};if(/model/i.test(at+fmt))return{value:'MOD',confidence:.86,evidence:['artifact-type']};return{value:'REF',confidence:.68,evidence:['conservative-reference-default']};}
function inferMaturity(desktop,state,files,readme){const dm=Number(desktop.Maturity);if(Number.isInteger(dm)&&dm>=0&&dm<=5)return{value:dm,confidence:1,evidence:['desktop-explicit']};const sm=Number(state?.maturity);if(Number.isInteger(sm)&&sm>=0&&sm<=5)return{value:sm,confidence:1,evidence:['state-explicit']};const assertions=countArray(state,'assertions'),sources=countArray(state,'source_refs');const schema=parseFloat(String(state?.schema_version||'0'))||0;let v=0,reasons=[];if(files.length>0){v=1;reasons.push('package-present');}if(state||files.some(p=>/\.json$/i.test(p))){v=Math.max(v,2);reasons.push('structured-metadata');}if(state&&(assertions>=50||sources>=3||files.length>=8)){v=Math.max(v,3);reasons.push('mapped-structure');}if(state&&schema>=6&&assertions>=500&&sources>=10){v=Math.max(v,4);reasons.push('strong-structural-validation');}if(readme&&readme.length>1000&&state&&assertions>=100)v=Math.max(v,3);return{value:v,confidence:v>=3?.84:.76,evidence:reasons};}
function validDomain(d){return d&&/^[A-Z0-9]{2,8}$/.test(String(d.code||''))&&/^#[0-9A-F]{6}$/i.test(String(d.color||''));}
function validProfile(p){return p?.profile==='kristal-icon/1.0'&&NATURES.has(p.nature)&&Number.isInteger(p.maturity)&&p.maturity>=0&&p.maturity<=5&&Array.isArray(p.domains)&&p.domains.length>=1&&p.domains.length<=3&&p.domains.every(validDomain);}
function iconName(nature,domains,maturity){return `KR-${nature}-${domains.map(d=>d.code).join('-')}-M${maturity}.ico`;}

let oldRegistry={entries:[]};if(isFile(registryPath))oldRegistry=readJson(registryPath)||oldRegistry;const oldById=new Map((oldRegistry.entries||[]).map(e=>[e.kristal_id,e]));
const result={profile:'kristal-icon-auto-scan/1.1',generated_at:new Date().toISOString(),collection_root:collection,scanned:0,already_complete:0,generated:0,new_kristals:[],repaired_incomplete:[],unresolved_isced:[],items:[]};
if(!isDir(domainsRoot)){console.error(`domains introuvable: ${domainsRoot}`);process.exit(2);}
for(const ent of fs.readdirSync(domainsRoot,{withFileTypes:true}).filter(e=>e.isDirectory()&&e.name.startsWith('Kristal-')).sort((a,b)=>a.name.localeCompare(b.name))){
  result.scanned++;const dir=path.join(domainsRoot,ent.name),metaDir=path.join(dir,'.kristal'),profilePath=path.join(metaDir,'icon-profile.json'),scanPath=path.join(metaDir,'auto-scan.json');const existing=readJson(profilePath);const old=oldById.get(ent.name);const oldComplete=old&&validProfile(old?.presentation?.icon);const existingIsced=validProfile(existing)&&existing.domains.every(d=>byCode.has(String(d.code).toUpperCase()));const oldIsced=oldComplete&&old.presentation.icon.domains.every(d=>byCode.has(String(d.code).toUpperCase()));if(existingIsced||oldIsced){result.already_complete++;continue;}
  const files=walkFiles(dir,4);const statePath=chooseState(files);const state=statePath?readJson(statePath):null;const v9Path=path.join(dir,'.kristal','v9','state-snapshot.json');const v9State=isFile(v9Path)?readJson(v9Path):null;let readme='';for(const n of ['README.md','Readme.md','readme.md']){const rp=path.join(dir,n);if(isFile(rp)){try{readme=fs.readFileSync(rp,'utf8').slice(0,50000);}catch{}break;}}
  const desktop=parseDesktopIni(path.join(dir,'desktop.ini'));const stateMeta=state?metadataTextFromJson(state,20000):'';const fileNames=files.slice(0,200).map(p=>path.relative(dir,p)).join('\n');const v9Meta=v9State?metadataTextFromJson({state_ref:v9State.state_ref,scope:v9State.scope,members:v9State.members?.length,references:v9State.references?.length},4000):'';const text=`${ent.name}\n${desktop.Title||''}\n${readme}\n${stateMeta}\n${v9Meta}\n${fileNames}`;
  let domains=scoreDomains(ent.name,text,desktop,state).slice(0,3);const nat=inferNature(text,desktop,state,files);const mat=inferMaturity(desktop,state,files,readme);
  // Preserve explicit pieces, but normalize legacy domain codes into ISCED-F broad fields.
  if(existing&&Array.isArray(existing.domains)&&existing.domains.length){const converted=existing.domains.map(d=>paletteMatch(d?.code||d?.name||d)).filter(Boolean);if(converted.length)domains=[...new Map(converted.map(d=>[d.code,{...d,confidence:1,evidence:['partial-profile-explicit-isced-normalized']}])).values()].slice(0,3);}
  if(!domains.length){result.unresolved_isced.push(ent.name);result.items.push({kristal_id:ent.name,status:'unresolved_isced',reason:'No defensible ISCED-F 2013 broad field match; no residual field invented.'});continue;}
  const nature=NATURES.has(existing?.nature)?existing.nature:nat.value;const maturity=Number.isInteger(existing?.maturity)&&existing.maturity>=0&&existing.maturity<=5?existing.maturity:mat.value;
  const cleanDomains=domains.map(d=>({code:String(d.code).toUpperCase(),name:d.name||d.code,color:String(d.color).toUpperCase()}));const filename=iconName(nature,cleanDomains,maturity);const confidence=Math.min(existing?.nature?1:nat.confidence,existing?.maturity!==undefined?1:mat.confidence,...domains.map(d=>d.confidence??.5));
  const profile={profile:'kristal-icon/1.0',kristal_ref:ent.name,nature,maturity,domains:cleanDomains,rendering:{nature_icon_color:'#1e6864',sizes:SIZES,filename},classification:{origin:'kristal-icon-auto-scan/1.1',scheme:'ISCED-F 2013',level:'broad-field',publisher:'UNESCO Institute for Statistics',confidence:Number(confidence.toFixed(2)),policy:'explicit metadata > ISCED legacy mapping > structured metadata > deterministic semantic scan; unresolved cases are not forced into ISCED 00'}};
  const report={profile:'kristal-icon-auto-scan.record/1.1',generated_at:new Date().toISOString(),kristal_id:ent.name,status:'generated',was_in_registry:!!old,registry_profile_complete_before:!!oldComplete,state_file:statePath?path.relative(dir,statePath).replace(/\\/g,'/'):null,state_schema:state?.schema_version||null,v9_state_ref:v9State?.state_ref||null,v9_logical_commitment:v9State?.logical_commitment?.digest||null,assertions:countArray(state,'assertions'),sources:countArray(state,'source_refs'),file_count:files.length,inference:{nature:nat,maturity:mat,domains:domains.map(d=>({code:d.code,confidence:d.confidence,evidence:d.evidence}))},result:{nature,maturity,domains:cleanDomains,filename,confidence:Number(confidence.toFixed(2))}};
  mkdirp(metaDir);fs.writeFileSync(profilePath,JSON.stringify(profile,null,2)+'\n','utf8');fs.writeFileSync(scanPath,JSON.stringify(report,null,2)+'\n','utf8');result.generated++;if(!old)result.new_kristals.push(ent.name);else result.repaired_incomplete.push(ent.name);result.items.push(report);
}
mkdirp(path.join(collection,'_registry'));fs.writeFileSync(path.join(collection,'_registry','icon-scan-report.json'),JSON.stringify(result,null,2)+'\n','utf8');console.log(JSON.stringify(result,null,2));
