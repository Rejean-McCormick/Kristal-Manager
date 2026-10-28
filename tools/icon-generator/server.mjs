import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import os from 'node:os';
import { buildLocalRegistry } from './runtime/local-registry.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const VERSION = '2.7.0';
const DEFAULT_COLLECTION = 'C:\\mycode\\Kristal\\Kristal-Kollection';
const args = process.argv.slice(2);
const manualMode = args.includes('--manual');
function argValue(name){ const i=args.indexOf(name); return i>=0 && args[i+1] ? args[i+1] : null; }
const localsMode = !!argValue('--locals');
const localApplyEnabled = localsMode && args.includes('--enable-local-apply');
const collectionRoot = path.resolve(localsMode ? argValue('--locals') : (argValue('--collection') || process.env.KRISTAL_COLLECTION_ROOT || DEFAULT_COLLECTION));
const registryRoot = localsMode ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), '.config'), 'Kristal-Manager', 'icon-reports') : path.join(collectionRoot, '_registry');
const registryPath = localsMode ? null : path.join(registryRoot, 'knowledge-base', 'registry', 'kristal-registry.catalog.json');
const builderPath = path.join(here, 'runtime', 'registry-builder.py');
const overlayPath = path.join(here, 'runtime', 'Kristal-v8-full-normalization-overlay.zip');
const scannerPath = path.join(here, 'runtime', 'scan-kristals.mjs');
const palettePath = path.join(here, 'runtime', 'kristal-domain-palette.json');
const bootstrapRegistry = path.join(here, 'runtime', 'bootstrap', 'kristal-registry.catalog.json');
const iconLibrary = localsMode ? null : path.join(registryRoot, 'icons', 'ico');
const unescoPalette=JSON.parse(fs.readFileSync(palettePath,'utf8'));
const unescoCodes=new Map(unescoPalette.domains.map(d=>[d.code,d]));

function isFile(p){ try{return fs.statSync(p).isFile();}catch{return false;} }
function isDir(p){ try{return fs.statSync(p).isDirectory();}catch{return false;} }
function mkdirp(p){ fs.mkdirSync(p,{recursive:true}); }
function inside(base,target){ const b=path.resolve(base)+path.sep; const t=path.resolve(target); return t===path.resolve(base)||t.startsWith(b); }
function readTextAuto(p){
  const b=fs.readFileSync(p);
  if(b.length>=2 && b[0]===0xff && b[1]===0xfe) return b.subarray(2).toString('utf16le');
  if(b.length>=3 && b[0]===0xef && b[1]===0xbb && b[2]===0xbf) return b.subarray(3).toString('utf8');
  return b.toString('utf8');
}
function writeUtf16Ini(p,text){
  const body=String(text).replace(/\r?\n/g,'\r\n');
  fs.writeFileSync(p,Buffer.concat([Buffer.from([0xff,0xfe]),Buffer.from(body,'utf16le')]));
}
function lineValue(v){ return String(v??'').replace(/[\r\n]+/g,' ').trim(); }
function updateIniSection(text,section,updates){
  let lines=String(text||'').replace(/\r\n/g,'\n').replace(/\r/g,'\n').split('\n');
  while(lines.length && lines[lines.length-1]==='') lines.pop();
  const wanted=section.toLowerCase();
  let start=-1,end=lines.length;
  for(let i=0;i<lines.length;i++){
    const m=lines[i].match(/^\s*\[([^\]]+)\]\s*$/);
    if(!m)continue;
    if(start>=0){end=i;break;}
    if(m[1].trim().toLowerCase()===wanted) start=i;
  }
  if(start<0){
    if(lines.length) lines.push('');
    lines.push(`[${section}]`);
    for(const [k,v] of Object.entries(updates)) if(v!==null && v!==undefined && v!=='') lines.push(`${k}=${lineValue(v)}`);
    return lines.join('\n')+'\n';
  }
  const keys=new Map(Object.keys(updates).map(k=>[k.toLowerCase(),k]));
  const seen=new Set();
  const out=[];
  for(let i=0;i<lines.length;i++){
    if(i<=start || i>=end){out.push(lines[i]);continue;}
    const m=lines[i].match(/^\s*([^;#][^=]*)=(.*)$/);
    if(!m){out.push(lines[i]);continue;}
    const lk=m[1].trim().toLowerCase();
    if(!keys.has(lk)){out.push(lines[i]);continue;}
    if(seen.has(lk)) continue;
    seen.add(lk);
    const canonical=keys.get(lk), value=updates[canonical];
    if(value!==null && value!==undefined && value!=='') out.push(`${canonical}=${lineValue(value)}`);
  }
  const missing=[];
  for(const [k,v] of Object.entries(updates)) if(!seen.has(k.toLowerCase()) && v!==null && v!==undefined && v!=='') missing.push(`${k}=${lineValue(v)}`);
  if(missing.length) out.splice(end,0,...missing);
  return out.join('\n')+'\n';
}
function run(cmd,cmdArgs){
  try{return spawnSync(cmd,cmdArgs,{cwd:here,encoding:'utf8',windowsHide:true,timeout:180000});}catch(e){return {status:1,stderr:e.message,stdout:''};}
}
function runKristalScanner(){
  if(!isDir(collectionRoot)) throw new Error(`Kristal-Kollection introuvable: ${collectionRoot}`);
  if(!isFile(scannerPath)) return {ok:false,generated:0,new_kristals:[],repaired_incomplete:[],warning:'scanner_missing'};
  const r=run(process.execPath,[scannerPath,'--collection',collectionRoot,'--palette',palettePath]);
  if(r.status!==0) return {ok:false,generated:0,new_kristals:[],repaired_incomplete:[],warning:(r.stderr||r.stdout||'scanner_failed').trim()};
  try{return {ok:true,...JSON.parse(r.stdout||'{}')};}
  catch{return {ok:true,generated:0,new_kristals:[],repaired_incomplete:[],warning:'scanner_output_unreadable'};}
}

function tryRebuildRegistry(){
  if(!isDir(collectionRoot)) throw new Error(`Kristal-Kollection introuvable: ${collectionRoot}`);
  mkdirp(registryRoot);
  const common=[builderPath,'--root',collectionRoot,'--meta-overlay',overlayPath,'--out',registryRoot];
  const attempts = process.platform==='win32'
    ? [['py',['-3',...common]],['python',common],['python3',common]]
    : [['python3',common],['python',common]];
  for(const [cmd,a] of attempts){
    const r=run(cmd,a);
    if(r.status===0 && isFile(registryPath)) return {rebuilt:true,engine:cmd,log:(r.stdout||'').trim()};
  }
  if(isFile(registryPath)) return {rebuilt:false,engine:null,log:'Registry existant conservé (rebuild indisponible).'};
  if(!isFile(bootstrapRegistry)) throw new Error('Aucun Registry disponible et bootstrap absent.');
  mkdirp(path.dirname(registryPath));
  fs.copyFileSync(bootstrapRegistry,registryPath);
  return {rebuilt:false,engine:'bootstrap',log:'Registry bootstrap installé; aucune interaction requise.'};
}

let scanSummary,preparation,registryCatalog,registryFallbackMerges=0;
if (localsMode) {
  if(!isDir(collectionRoot)) { console.error(`Dossier locals introuvable: ${collectionRoot}`); process.exit(2); }
  // Startup is strictly read-only, independent of the apply opt-in.
  const local=buildLocalRegistry(collectionRoot,palettePath,path.join(here,'runtime','unesco-thesaurus-profile.json'));
  registryCatalog=local.catalog;
  scanSummary={ok:true,scanned:local.scanned,generated:0,unresolved_unesco:local.unresolved.map(x=>x.folder),
    unresolved_details:local.unresolved,new_kristals:[],repaired_incomplete:[]};
  preparation={rebuilt:false,engine:null,log:'Locals : aperçu en mémoire, aucune écriture au démarrage.'};
} else {
  try { scanSummary=runKristalScanner(); }
  catch(e){ scanSummary={ok:false,generated:0,new_kristals:[],repaired_incomplete:[],warning:e.message}; }
  try { preparation=tryRebuildRegistry(); }
  catch(e){ console.error(`[Kristal Icon Generator] ${e.message}`); process.exit(2); }
  try { registryCatalog=JSON.parse(fs.readFileSync(registryPath,'utf8')); }
  catch(e){ console.error(`[Kristal Icon Generator] Registry illisible: ${e.message}`); process.exit(3); }
  registryFallbackMerges=mergeEmbeddedScansIntoRegistry(registryCatalog);
}

function completeIconProfile(i){
  return i?.profile==='kristal-icon/1.0' && i.classification?.scheme==='UNESCO Thesaurus' &&
    i.classification?.kos_id==='kos:unesco-thesaurus' && /^(REF|COL|MOD|PRT|TWN|INV|SRC)$/.test(String(i.nature||'')) &&
    Number.isInteger(i.maturity) && i.maturity>=0 && i.maturity<=5 &&
    Array.isArray(i.domains) && i.domains.length>=1 && i.domains.length<=3 &&
    i.domains.every(d=>d && unescoCodes.has(String(d.code||'')) && d.uri===unescoCodes.get(String(d.code)).uri &&
    d.icon_token===unescoCodes.get(String(d.code)).icon_token && /^#[0-9A-Fa-f]{6}$/.test(String(d.color||'')));
}
function normalizeProfileForRegistry(profile){
  if(!completeIconProfile(profile)) return null;
  const out=structuredClone(profile);
  const fn=`KR-${out.nature}-${out.domains.map(d=>d.icon_token).join('-')}-M${out.maturity}.ico`;
  out.rendering={...(out.rendering||{}),nature_icon_color:out.rendering?.nature_icon_color||'#1e6864',sizes:out.rendering?.sizes||[16,20,24,32,40,48,64,96,128,256],filename:fn};
  out.icon_code=fn.replace(/\.ico$/i,'');
  out.classification_origin=out.classification?.origin||'embedded.icon-profile';
  return out;
}
function recomputeRegistryCounts(catalog){
  const entries=catalog.entries||[], byKind={}, byNature={}, byAvailability={};let desktop=0,mediatheque=0,normalized=0,renderable=0;
  for(const e of entries){byKind[e.kind]=(byKind[e.kind]||0)+1;const n=e?.presentation?.icon?.nature||'UNCLASSIFIED';byNature[n]=(byNature[n]||0)+1;byAvailability[e.availability]=(byAvailability[e.availability]||0)+1;if(e?.bindings?.desktop)desktop++;if(e?.bindings?.mediatheque)mediatheque++;if(e.normalization)normalized++;if(completeIconProfile(e?.presentation?.icon))renderable++;}
  catalog.counts={total:entries.length,by_kind:byKind,by_nature:byNature,by_availability:byAvailability,bindings:{desktop,mediatheque},meta:{normalized,renderable_icons:renderable}};
}
function mergeEmbeddedScansIntoRegistry(catalog){
  const domainsRoot=path.join(collectionRoot,'domains'); if(!isDir(domainsRoot))return 0;
  const byId=new Map((catalog.entries||[]).map(e=>[e.kristal_id,e]));let changed=0;
  for(const d of fs.readdirSync(domainsRoot,{withFileTypes:true}).filter(x=>x.isDirectory()&&x.name.startsWith('Kristal-'))){
    const profile=normalizeProfileForRegistry((()=>{try{return JSON.parse(fs.readFileSync(path.join(domainsRoot,d.name,'.kristal','icon-profile.json'),'utf8'));}catch{return null;}})()); if(!profile)continue;
    let e=byId.get(d.name);
    if(!e){
      let title=d.name;try{const txt=fs.readFileSync(path.join(domainsRoot,d.name,'README.md'),'utf8');const m=txt.match(/^#\s+(.+)$/m);if(m)title=m[1].trim();}catch{}
      e={kristal_id:d.name,kristal_ref:profile.kristal_ref||d.name,title,kind:'domain',locator:`domains/${d.name}`,parent_kristal_ref:null,availability:'present',state_observation:{},metrics:{},presentation:{icon:profile},bindings:{},relations:[{predicate:'member_of_collection',object:'Kristal-Kollection'}],observed_at:new Date().toISOString()};
      catalog.entries.push(e);byId.set(d.name,e);changed++;continue;
    }
    if(!completeIconProfile(e?.presentation?.icon)){e.presentation=e.presentation||{};e.presentation.icon=profile;changed++;}
  }
  if(changed){catalog.entries.sort((a,b)=>String(a.kind).localeCompare(String(b.kind))||String(a.title).localeCompare(String(b.title),'fr'));recomputeRegistryCounts(catalog);catalog.generated_at=new Date().toISOString();try{fs.writeFileSync(registryPath,JSON.stringify(catalog,null,2)+'\n','utf8');}catch{}}
  return changed;
}

const natureLabels={REF:'Référence',COL:'Collection',MOD:'Modèle',PRT:'Protocole',TWN:'Twin',INV:'Investigation',SRC:'Sources'};
function iconFilename(entry){
  const i=entry?.presentation?.icon||{};
  const f=`KR-${i.nature}-${(i.domains||[]).map(d=>d.icon_token).join('-')}-M${i.maturity}.ico`;
  return completeIconProfile(i) && /^KR-(REF|COL|MOD|PRT|TWN|INV|SRC)-UT[1-7](?:-UT[1-7]){0,2}-M[0-5]\.ico$/.test(f) ? f : null;
}
const iconConsumers=new Map();
for(const entry of registryCatalog.entries||[]){
  const filename=iconFilename(entry); if(!filename) continue;
  if(!iconConsumers.has(filename)) iconConsumers.set(filename,[]);
  iconConsumers.get(filename).push(entry);
}
const generatedIcons=new Set();

function targetDir(entry){
  const rel=String(entry?.locator||'').replace(/\//g,path.sep);
  if(!rel) return null;
  const target=path.resolve(collectionRoot,rel);
  if(!inside(collectionRoot,target) || !isDir(target)) return null;
  if(localsMode) {
    try { if(!inside(fs.realpathSync(collectionRoot),fs.realpathSync(target)) || fs.realpathSync(target)===fs.realpathSync(collectionRoot)) return null; }
    catch { return null; }
    if(!/^Kristal-[A-Za-z0-9][A-Za-z0-9._-]*$/.test(entry.locator||'')) return null;
  }
  return target;
}
function volumeCounts(entry){
  const d=entry?.bindings?.desktop||{}, m=entry?.metrics||{};
  const a=Number.isInteger(d.assertions)?d.assertions:(Number.isInteger(m.assertions)?m.assertions:null);
  const s=Number.isInteger(d.sources)?d.sources:(Number.isInteger(m.sources)?m.sources:null);
  return {assertions:a,sources:s};
}
function infoTip(entry){
  const i=entry.presentation.icon, d=entry?.bindings?.desktop||{};
  const title=lineValue(d.title||entry.title||entry.kristal_id);
  const nature=natureLabels[i.nature]||i.nature;
  const domainNames=(i.domains||[]).map(x=>typeof x==='string'?x:(x.name||x.code)).filter(Boolean);
  const domainCodes=(i.domains||[]).map(x=>typeof x==='string'?x:(x.code||x.id)).filter(Boolean);
  const baseParts=[title,nature,domainNames.join(' / '),`Maturité ${i.maturity}/5`].filter(Boolean);
  const {assertions,sources}=volumeCounts(entry);
  const volume=[];
  if(assertions!==null && assertions>0) volume.push(`${assertions.toLocaleString('fr-CA')} ${assertions===1?'assertion':'assertions'}`);
  if(sources!==null) volume.push(`${sources.toLocaleString('fr-CA')} ${sources===1?'source':'sources'}`);
  let tip=[...baseParts, volume.length?volume.join(' · '):null].filter(Boolean).join(' • ');
  if(tip.length>180) tip=baseParts.join(' • ');
  if(tip.length>180) tip=[title,nature,domainCodes.join(' / '),`Maturité ${i.maturity}/5`].filter(Boolean).join(' • ');
  if(tip.length>180){ const excess=tip.length-177; const shortTitle=title.length>excess+12 ? title.slice(0,title.length-excess-1)+'…' : title; tip=[shortTitle,nature,domainCodes.join(' / '),`Maturité ${i.maturity}/5`].filter(Boolean).join(' • '); }
  return tip;
}
function clearDesktopIniAttributes(ini){
  if(process.platform!=='win32' || !isFile(ini)) return;
  // desktop.ini is normally Hidden/System and may also be Read-only.
  // Node can receive EPERM while truncating a Read-only file, so make it writable first.
  run('attrib',['-r','-h','-s',ini]);
}
function restoreDesktopIniAttributes(ini){
  if(process.platform!=='win32' || !isFile(ini)) return;
  // Keep it writable for future regenerations, but restore the Windows shell attributes.
  run('attrib',['+h','+s',ini]);
}

function desktopUpdates(entry,filename){
  const icon=entry.presentation.icon, desktop=entry?.bindings?.desktop||{}, counts=volumeCounts(entry);
  const domains=(icon.domains||[]).map(x=>typeof x==='string'?x:(x.code||x.id)).filter(Boolean);
  return {
    shell:{IconResource:`.kristal\\${filename},0`,InfoTip:infoTip(entry)},
    kristal:{
      Profile:'kristal-desktop/1.0', IconProfile:'kristal-icon/1.0', IconCode:filename.replace(/\.ico$/i,''),
      Title:desktop.title||entry.title||entry.kristal_id, KristalRef:entry.kristal_ref||icon.kristal_ref||entry.kristal_id,
      Nature:icon.nature, DomainScheme:'UNESCO Thesaurus', DomainLevel:'domain', Domain1:domains[0]||null, Domain2:domains[1]||null, Domain3:domains[2]||null,
      Maturity:icon.maturity, Assertions:counts.assertions, Sources:counts.sources, Generator:`Kristal-Icon-Generator/${VERSION}`
    }
  };
}
function applyDesktopIni(entry,filename){
  const dir=targetDir(entry); if(!dir) return {status:'skipped',reason:'locator_not_directory'};
  const ini=path.join(dir,'desktop.ini');

  // Hotfix 2.2.2: neutralize Windows file attributes BEFORE both reading and rewriting.
  // Existing desktop.ini files may be +R +H +S; +R causes fs.writeFileSync to fail with EPERM.
  clearDesktopIniAttributes(ini);

  let text='; Generated by Kristal Icon Generator. Regenerable local binding.\n';
  if(isFile(ini)){ try{text=readTextAuto(ini);}catch{} }
  const u=desktopUpdates(entry,filename);
  text=updateIniSection(text,'.ShellClassInfo',u.shell);
  text=updateIniSection(text,'Kristal',u.kristal);

  try{
    writeUtf16Ini(ini,text);
  } finally {
    // If creation succeeded, restore shell attributes. Never re-add Read-only so future runs remain writable.
    restoreDesktopIniAttributes(ini);
  }

  if(process.platform==='win32'){
    // Required for Explorer to honor folder customization from desktop.ini.
    run('attrib',['+r',dir]);
  }
  return {status:'applied',path:ini,infotip:u.shell.InfoTip};
}
function cleanupOldIcons(dir,current){
  const kd=path.join(dir,'.kristal'); if(!isDir(kd)) return;
  for(const name of fs.readdirSync(kd)){
    if(/^KR-.*\.ico$/i.test(name) && name!==current){ try{fs.unlinkSync(path.join(kd,name));}catch{} }
  }
}
function send(res,code,body,type='text/plain; charset=utf-8'){
  res.writeHead(code,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}); res.end(body);
}
function sendJson(res,code,obj){ send(res,code,JSON.stringify(obj,null,2),'application/json; charset=utf-8'); }
function safeStaticPath(urlPath){
  const rel=decodeURIComponent(urlPath.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  const full=path.resolve(here,rel);
  return inside(here,full)?full:null;
}
function readBody(req,max=8*1024*1024){
  return new Promise((resolve,reject)=>{let chunks=[],n=0;req.on('data',c=>{n+=c.length;if(n>max){reject(new Error('payload_too_large'));req.destroy();}else chunks.push(c);});req.on('end',()=>resolve(Buffer.concat(chunks)));req.on('error',reject);});
}
function refreshExplorer(){
  if(process.platform!=='win32') return;
  try{spawnSync('ie4uinit.exe',['-show'],{windowsHide:true,timeout:10000,stdio:'ignore'});}catch{}
}

const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.md':'text/markdown; charset=utf-8','.ico':'image/x-icon','.png':'image/png','.css':'text/css; charset=utf-8'};
let finalReport=null;
let shutdownTimer=null;
const server=http.createServer(async (req,res)=>{
  const u=new URL(req.url,'http://127.0.0.1');
  try{
    if(req.method==='POST' && req.headers.origin && req.headers.origin!==`http://127.0.0.1:${port}`)
      return sendJson(res,403,{error:'cross_origin_write_rejected'});
    if(u.pathname==='/api/status') return sendJson(res,200,{version:VERSION,mode:localsMode?'locals':'collection',local_apply_enabled:localApplyEnabled,registry_found:true,registry_display:localsMode?'Aperçu en mémoire (aucun Registry écrit)':registryPath,collection_root:collectionRoot,registry_root:localsMode?null:registryRoot,registry_rebuilt:preparation.rebuilt,registry_engine:preparation.engine,scan:{ok:!!scanSummary?.ok,scanned:scanSummary?.scanned||0,generated:scanSummary?.generated||0,already_complete:scanSummary?.already_complete||0,new_kristals:scanSummary?.new_kristals||[],repaired_incomplete:scanSummary?.repaired_incomplete||[],unresolved_unesco:scanSummary?.unresolved_unesco||[],warning:scanSummary?.warning||null,fallback_registry_merges:registryFallbackMerges},autorun:false,ui_action_required:true,renderable_entries:[...iconConsumers.values()].reduce((n,x)=>n+x.length,0),unique_icons:iconConsumers.size});
    if(u.pathname==='/api/registry') return send(res,200,localsMode?JSON.stringify(registryCatalog):fs.readFileSync(registryPath),'application/json; charset=utf-8');
    if(u.pathname==='/api/icon' && req.method==='POST'){
      if(localsMode && !localApplyEnabled) return sendJson(res,403,{error:'local_folder_icons_disabled'});
      const filename=path.basename(u.searchParams.get('filename')||'');
      if(!iconConsumers.has(filename)) return sendJson(res,400,{error:'unknown_icon',filename});
      const bytes=await readBody(req);
      if(bytes.length<32 || bytes.length>8*1024*1024 || bytes.readUInt16LE(0)!==0 || bytes.readUInt16LE(2)!==1 || bytes.readUInt16LE(4)<1) return sendJson(res,400,{error:'invalid_icon_payload'});
      if(iconLibrary) { mkdirp(iconLibrary); fs.writeFileSync(path.join(iconLibrary,filename),bytes); }
      let copied=0,skipped=0;
      for(const entry of iconConsumers.get(filename)){
        const dir=targetDir(entry); if(!dir){skipped++;continue;}
        const kd=path.join(dir,'.kristal'); mkdirp(kd);
        if(!localsMode) cleanupOldIcons(dir,filename); // Do not delete historical local icons.
        fs.writeFileSync(path.join(kd,filename),bytes); copied++;
      }
      generatedIcons.add(filename);
      return sendJson(res,200,{ok:true,filename,copied,skipped});
    }
    if(u.pathname==='/api/finalize' && req.method==='POST'){
      if(localsMode && !localApplyEnabled) return sendJson(res,403,{error:'local_folder_icons_disabled'});
      let client={}; try{client=JSON.parse((await readBody(req,4*1024*1024)).toString('utf8')||'{}');}catch{}
      if(!localsMode) {
        mkdirp(registryRoot);
        if(client.manifest) fs.writeFileSync(path.join(registryRoot,'manifest.json'),JSON.stringify(client.manifest,null,2)+'\n','utf8');
        if(client.bindings) fs.writeFileSync(path.join(registryRoot,'registry-icon-bindings.json'),JSON.stringify(client.bindings,null,2)+'\n','utf8');
      }
      const results=[];
      for(const [filename,entries] of iconConsumers){
        if(!generatedIcons.has(filename)) continue;
        for(const entry of entries){
          try{
            const result=applyDesktopIni(entry,filename);
            if(localsMode && result.status==='applied') {
              const folder=targetDir(entry);
              // Cache presentation metadata only after explicit application. No canonical state writes.
              fs.writeFileSync(path.join(folder,'.kristal','icon-profile.json'),JSON.stringify(entry.presentation.icon,null,2)+'\n','utf8');
            }
            results.push({kristal_id:entry.kristal_id,locator:entry.locator,icon:filename,...result});
          }
          catch(e){ results.push({kristal_id:entry.kristal_id,locator:entry.locator,icon:filename,status:'error',error:e.message}); }
        }
      }
      const counts={generated_unique_icons:generatedIcons.size,applied:results.filter(x=>x.status==='applied').length,skipped:results.filter(x=>x.status==='skipped').length,errors:results.filter(x=>x.status==='error').length};
      finalReport={profile:'kristal-icon-auto-apply/1.1',generator_version:VERSION,generated_at:new Date().toISOString(),collection_root:collectionRoot,registry_path:registryPath,registry_format:registryCatalog.format,scan:scanSummary,counts,results};
      mkdirp(registryRoot);
      fs.writeFileSync(path.join(registryRoot,'icon-generation-report.json'),JSON.stringify(finalReport,null,2)+'\n','utf8');
      refreshExplorer();
      sendJson(res,200,{ok:counts.errors===0,counts,report:path.join(registryRoot,'icon-generation-report.json'),registry_root:registryRoot});
      if(!manualMode && !shutdownTimer) shutdownTimer=setTimeout(()=>server.close(()=>process.exit(0)),12000);
      return;
    }
    if(u.pathname==='/api/final-report') return sendJson(res,200,finalReport||{pending:true});
    const full=safeStaticPath(u.pathname); if(!full || !isFile(full)) return send(res,404,'Not found');
    send(res,200,fs.readFileSync(full),mime[path.extname(full).toLowerCase()]||'application/octet-stream');
  }catch(e){ sendJson(res,500,{error:e.message}); }
});

let port=8765;
function listen(){
  server.once('error',err=>{if(err.code==='EADDRINUSE'&&port<8775){port++;listen();}else throw err;});
  server.listen(port,'127.0.0.1',()=>{
    const url=`http://127.0.0.1:${port}/`; 
    console.log(`Kristal Icon Generator ${VERSION}`);
    console.log(`Collection: ${collectionRoot}`);
    console.log(`Registry:   ${registryPath||'mémoire seulement (locals)'}`);
    if(scanSummary?.ok) console.log(`Scan:       ${scanSummary.scanned||0} domaines · ${scanSummary.generated||0} profil(s) généré(s) · ${(scanSummary.new_kristals||[]).length} nouveau(x)`);
    else if(scanSummary?.warning) console.log(`Scan:       avertissement: ${scanSummary.warning}`);
    console.log(preparation.log||'');
    console.log(`Ouverture:  ${url}`);
    if(process.platform==='win32') spawn('cmd',['/c','start','',url],{detached:true,stdio:'ignore'}).unref();
    else if(process.platform==='darwin') spawn('open',[url],{detached:true,stdio:'ignore'}).unref();
  });
}
listen();
