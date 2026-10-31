#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arketype / keyword / UNESCO proposal triage from an existing Kristal Manager SQLite catalog.

READ ONLY for input data. Outputs proposals into a separate folder; never writes to Kristals,
never certifies Framework, Arketype, diK, UNESCO compliance or semantic truth.

Python >= 3.10, standard library only.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from html import escape as html_escape
import sqlite3
import sys
import unicodedata

ROOT=Path(__file__).resolve().parent / 'reference' / 'semantic'
VERSION='0.2.1-manager-integrated'
# Keywords here are exploratory *structural* signals, not an authoritative classifier.
# Distinguish structural evidence from subject/domain words.
ARK_SIGNALS={
 'referentiel-semantique':['semantic reference','knowledge base','reference knowledge','referentiel','concepts','relations typees','semantic dictionary','dictionnaire semantique','semantic_graph'],
 'federation-topologie':['federation','federe','federated','topology','topologie','shard','cross-kristal','noeuds','references epinglees'],
 'carte-jalons-preuves':['proof landmark','jalons','preuves longues','obligations de preuve','proof waypoint','carrefours','proof obligation'],
 'procedure-protocole':['procedure','protocole','workflow','branche conditionnelle','conditional branch','etapes','instructions','sop'],
 'compilation-collection':['collection','compilation','curated collection','catalogue','anthologie','repertoire','selection'],
 'memoire-recherche':['recherche','research memory','frontiere de recherche','hypothese','proof attempt','investigation','tentative'],
 'invariant-theorie':['invariant','theoreme','theory','theorie','formal proof','contre exemple','formalisations','axiom'],
 'diagnostic-causal':['diagnostic','cause','causal','fault','symptom','symptome','hypotheses concurrentes','troubleshoot','panne'],
 'modele-multiplexe':['multiplex','multi axis','multi_axis','multiscale','multicouche','layers','layered graph','coupled','couches relationnelles'],
 'parcours-pedagogique':['pedagogical pathway','parcours pedagogique','curriculum','apprentissage','learning path','enseignement','lesson sequence'],
 'registre-evenementiel':['event ledger','registre evenementiel','chronologie','event history','chronological events','timeline','horodatage','audit trail'],
 'interpretations-couches':['interpretations','interpretation','layered interpretation','regimes interpretatifs','hermeneutique','lecture interpretative'],
 'univers-oeuvres-medias':['medias','oeuvre','works','media universe','franchise','univers fictionnel','episodes','manifestations'],
 'simulation-transition':['simulation','transition','state transition','modelisation dynamique','scenario simulation','simulation de scenarios','machine a etats','dynamique'],
 'composition-hybride':['hybrid','hybride','composition','sous modeles','interface contracts','multi model','orchestration'],
 'deposition-temoignage':['temoignage','deposition','declarant','testimony','witness','transcription','chain of custody'],
 'taxonomie-classification':['taxonomie','taxon','taxonomy','classification','arbre taxonomique','hierarchie','phylogen','specimens'],
 'etat-systemes':['system state','system_status','observability','monitoring','metriques','etat systeme','status matrix','composants etats'],
 'dossier-suivi':['casefile','dossier de suivi','dossier patient','dossier scolaire','case management','suivi','case record'],
}
# Bilingual cue phrases for likely microthesauri. They are *suggestions* only.
# Codes and English labels are read from the pinned UNESCO Thesaurus profile, never invented.
UNESCO_CUES={
 '1.05':['pedagogie','didactique','learning theory','sciences education'],
 '1.30':['education system','systeme scolaire','school system'],
 '1.35':['universite','university','school','ecole','college','campus'],
 '1.40':['curriculum','programme scolaire','programmes scolaires'],
 '1.60':['enseignement','teaching','training','formation','apprentissage'],
 '2.15':['mathematiques','mathematics','statistics','statistiques','algebre','theoreme'],
 '2.20':['physique','physics','thermodynamique','quantique','quantum'],
 '2.25':['chimie','chemistry','molecule','molecules','chemical'],
 '2.30':['astronomy','astronomie','astronomique','galaxy','galaxie','etoile','star','nebuleuse','cosmologie','cosmology','astrophysics'],
 '2.35':['geologie','geology','tectonique','earth science','sciences de la terre'],
 '2.40':['geography','geographie','oceanographie','cartographie','cartography'],
 '2.45':['meteorologie','meteorology','atmosphere','weather','climatology'],
 '2.50':['hydrologie','hydrology','hydrologique','groundwater'],
 '2.55':['ecologie','ecology','ecosystem','ecosysteme','environmental science'],
 '2.60':['pollution','disaster','catastrophe','hazard','risque environnemental'],
 '2.65':['natural resource','ressource naturelle','foresterie','forestry'],
 '2.70':['biologie','biology','genetique','genetics','botany','botanique','biodiversite','species','espece','fungi'],
 '2.80':['medicine','medical','medecine','patient','clinical','clinique','human body','anatomie','anatomy'],
 '2.85':['pathology','pathologie','disease','maladie','infection'],
 '3.15':['philosophy','philosophie','ethique','ethics','epistemology','epistemologie'],
 '3.20':['religion','religieux','catho','catholic','bible','biblical','theologie','theology','mythologie'],
 '3.25':['history','histoire','historique','archaeology','archeologie'],
 '3.30':['linguistique','linguistics','phonologie','syntax','syntaxe'],
 '3.35':['langues','languages','langue','language','translation','traduction'],
 '3.40':['litterature','literature','roman','poesie','poetry'],
 '3.45':['art','arts','artist','artiste','creation artistique'],
 '3.50':['design','graphisme','visual arts','photography','photographie'],
 '3.55':['theatre','dance','danse','spectacle','music','musique'],
 '3.65':['jeu','games','sport','loisir','recreation'],
 '4.10':['psychology','psychologie','comportement','cognition'],
 '4.15':['society','societe','social organisation','organisation sociale','anthropology','anthropologie'],
 '4.25':['sante publique','social welfare','aide sociale','social policy'],
 '4.35':['population','demography','demographie','aging','vieillissement'],
 '4.40':['famille','family','parenthood'],
 '4.45':['urbanisme','urbanism','land use','habitat','ville','housing'],
 '5.05':['information science','science de information','information sciences'],
 '5.15':['data management','gestion de information','gestion des donnees'],
 '5.25':['documentary','documentaire','document management','bibliotheque'],
 '5.40':['software','logiciel','internet','informatique','computing','cybersecurity','cybersecurite','artificial intelligence','intelligence artificielle','programming'],
 '5.45':['hardware','electronique','electronics','computer hardware','microprocesseur'],
 '6.05':['law','legal','droit','juridique','constitution','legislation'],
 '6.10':['human rights','droits humains','droits de homme'],
 '6.15':['politics','politique','government','gouvernance','governance'],
 '6.20':['international law','droit international','international relations','diplomatie'],
 '6.25':['economics','economie','economique','market','macroeconomics','microeconomics'],
 '6.30':['development','developpement economique','transition sociale'],
 '6.35':['agriculture','agricole','farming','agronomy','agronomie'],
 '6.40':['industrie','industry','industrialisation'],
 '6.45':['civil engineering','ingenierie civile','infrastructure','construction','mining'],
 '6.50':['transport','automobile','vehicule','automotive','aerospace','aerospatial','aeronautique','logistics','logistique'],
 '6.55':['materials','materiaux','metallurgie','product materials'],
 '6.60':['equipment','equipement','facilities','installations'],
 '6.65':['services','service public','public services'],
 '6.70':['finance','financier','financial','accounting','comptabilite','commerce','monetary','monetaire'],
 '6.75':['management','gestion organisation','organisational','organisation management'],
 '6.80':['personnel','human resources','ressources humaines','hr management'],
 '6.85':['travail','labour','emploi','employment'],
}
DOMAIN_CUES={
 '1':['education','educational','scolaire','pedagogie','ecole','enseignement','didactique'],
 '2':['science','scientific','astronomy','astronomie','biology','biologie','chemistry','chimie','physique','physics','mathematics','mathematiques','genetics','genetique','ecology','ecologie','geology','geologie'],
 '3':['culture','cultural','history','histoire','philosophie','philosophy','ethique','ethics','religion','linguistics','litterature','literature','art','musique'],
 '4':['social','society','societe','psychology','psychologie','anthropology','anthropologie','population','demography','demographie'],
 '5':['information','software','computing','informatique','internet','communication','data','cybersecurity','cybersecurite','electronics'],
 '6':['law','droit','politics','politique','economics','economie','agriculture','industry','industrie','finance','accounting','comptabilite','engineering','ingenierie','transport','governance'],
 # UNESCO domain 7 is normally an optional place facet, not a blanket topical category.
}

# Keep UNESCO 3-7 categories grounded: add matches to profile labels, not invented codes.
STOP=set('''the and that this with from into about their than which where during after before into
for is are have has not was were will shall can could have more less or of on in as to by a an at
le la les un une des du de dans en et ou au aux pour par sur est sont ses son cette ces plus mais
comme avec sans entre depuis vers tous toute toutes tout entre vers dont vous nous il elle ils elles
qui que quoi voici aussi doit devra peut peuvent leur leurs ces cet ce car ni pas encore ont etre
être avoir fait faire action status state model models source sources data donnees données reference
references list table items schema graph graphe node nodes kristal kristals item entity entities
kq kp ka ks id uri urn sha hash payload draft v11 v10 v9 active local record type kind
metadata meta domain properties property semantic semantics dictionnaire dictionary lexical
system systems système systèmes provenance described description unknown none verified true false wikidata v11 v10 v9 projections projection canon legacy generated generees generee
observations observed registry registre property format value term values root files file
'''.split())
TECH_PREFIX=('urn:','http:','https:','sha256:','dik:metadata','kristal.','wikidata:', 'urn_', 'kristal:')
OPAQUE=re.compile(r'^(?:K[QPAS]\d+|[QP]\d+|[0-9a-f]{16,})$',re.I)
TOK=re.compile(r"[\wÀ-ÿ]+",re.UNICODE)

def norm(s):
 s=unicodedata.normalize('NFKD',str(s).casefold())
 return ''.join(c for c in s if not unicodedata.combining(c))

def lexical(s):
 s=str(s)
 s=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',s)
 s=re.sub(r'[_:/\\|()\[\].;,]+',' ',s)
 return norm(s)

def words(s):
 return [x for x in TOK.findall(lexical(s)) if len(x)>=3 and x not in STOP and not x.isnumeric() and not OPAQUE.fullmatch(x)]

def usable_term(t):
 t=t.strip()
 if len(t)<3 or len(t)>100 or any(t.lower().startswith(x) for x in TECH_PREFIX):return False
 if OPAQUE.fullmatch(t) or '://' in t:return False
 w=words(t)
 return 0<len(w)<=9 and len(t)<110

def phrase_present(haystack,cue):
 c=lexical(cue).strip()
 if not c:return False
 return re.search(r'(?<!\w)'+re.escape(c)+r'(?!\w)',haystack) is not None

def digest_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def get_references():
 archetypes=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'arketype/archetypes').glob('*.json'))]
 profile=json.loads((ROOT.parent/'unesco-thesaurus-profile.json').read_text(encoding='utf-8'))
 assert len(archetypes)==19,'Expected Arketype reference set of 19 source definitions'
 mt={m['notation']:(d['notation'],d['label_en'],m['label_en'],m['uri']) for d in profile['domains'] for m in d['microthesauri']}
 assert len(mt)==88,'Expected pinned 88 UNESCO microthesauri'
 return archetypes,profile,mt

def read_catalogue(path):
 # immutable=1 avoids SQLite -wal or -shm side effects and enforces read-only.
 uri=path.resolve().as_uri()+'?mode=ro&immutable=1'
 return sqlite3.connect(uri,uri=True)

def keywords_for(terms,title,descriptor,subjects,relations):
 counter=Counter(); evidence=defaultdict(set); phrases=Counter()
 # Labels are lexical observations; frequency of repeated aliases does not imply factual significance.
 for lang,term in terms:
  if not usable_term(term):continue
  ww=words(term)
  weight=3 if lang in ('fr','en','fr-CA') else 1
  for x in set(ww):
   counter[x]+=weight;evidence[x].add('dictionary_term:'+str(lang))
  if len(ww)>=2 and len(ww)<=5:phrases[' '.join(ww)]+=weight
 for kind,txt,weight in [('title',title,2),('descriptor',descriptor,4),('top_subjects',subjects,3),('top_relations',relations,2)]:
  for x in set(words(txt)):
   counter[x]+=weight;evidence[x].add(kind)
 # Keep tokens with real lexical evidence and avoid reporting digits or opaque identifiers.
 keys=[{'term':w,'weight':c,'evidence':sorted(evidence[w])} for w,c in counter.most_common(20)]
 return keys,phrases

def arketype_candidates(archetypes,native_kind,descriptor,subjects,relations,keywords):
 contexts={
  'native_kind':lexical(native_kind),
  'semantic_ownership':lexical(descriptor),
  'relations':lexical(relations),
  'subjects':lexical(subjects),
  'keywords':lexical(' '.join(k['term'] for k in keywords[:15])),
 }
 candidates=[]
 for a in archetypes:
  slug=a['slug'];matches=[];score=0
  # Candidate's own structural label can be strong when literally represented in native kind.
  cues=ARK_SIGNALS.get(slug,[])
  for cue in dict.fromkeys(lexical(c) for c in cues):
   for field,weight in [('native_kind',6),('semantic_ownership',3),('relations',3),('subjects',1),('keywords',1)]:
    if phrase_present(contexts[field],cue):
     matches.append({'where':field,'cue':cue,'weight':weight});score+=weight
  # General reference is a broad base class, so it takes more evidence to win.
  if slug=='referentiel-semantique':score=round(score*0.55,2)
  if score>0:candidates.append({'arketype_id':a['id'],'slug':slug,'name':a['name'],'score':score,'evidence':sorted(matches,key=lambda x:-x['weight'])[:8]})
 candidates.sort(key=lambda x:(-x['score'],x['arketype_id']))
 top=candidates[0] if candidates else None
 margin=top['score']-(candidates[1]['score'] if len(candidates)>1 else 0) if top else 0
 # No categorical classification without sufficiently corroborated structural evidence.
 evidence_types={x['where'] for x in top['evidence']} if top else set()
 decision=('candidate_to_review' if top and top['score']>=8 and margin>=3 and
           ('native_kind' in evidence_types or len(evidence_types)>=2) else 'insufficient_or_ambiguous_evidence')
 return {'status':decision,'primary_candidate':top if decision=='candidate_to_review' else None,
         'candidates':candidates[:4], 'margin':margin,
         'caveat':'ARK IDs are suggestions about design structure, not declared classifications or validation.'}

def unesco_candidates(mt,keywords,title,descriptor,subjects):
 # Source grouping to avoid double counting a phrase repeated thousands of times in a large graph.
 contexts={'keywords':lexical(' '.join(k['term'] for k in keywords[:20])),
           'title':lexical(title),'descriptor':lexical(descriptor),'subjects':lexical(subjects)}
 out=[]
 for code,(domain,dlabel,label,uri) in mt.items():
  phrases=[label]+UNESCO_CUES.get(code,[])
  signals=[];score=0
  for phrase in phrases:
   for field,weight in [('keywords',3),('title',1),('descriptor',2),('subjects',2)]:
    if phrase_present(contexts[field],phrase):
     signals.append({'where':field,'phrase':phrase,'weight':weight});score+=weight
  if score:
   out.append({'microthesaurus_code':code,'microthesaurus_label_en':label,
               'domain_code':domain,'domain_label_en':dlabel,'uri':uri,
               'score':score,'evidence':sorted(signals,key=lambda x:-x['weight'])[:8]})
 out.sort(key=lambda x:(-x['score'],x['microthesaurus_code']))
 # Domain suggestions can be broader than a defensible microthesaurus choice.
 domain_scores=Counter();domain_signals=defaultdict(list)
 domain_labels={v[0]:v[1] for v in mt.values()}
 for code,cues in DOMAIN_CUES.items():
  for cue in cues:
   for field,weight in [('keywords',2),('title',1),('descriptor',2),('subjects',1)]:
    if phrase_present(contexts[field],cue):
     domain_scores[code]+=weight
     if len(domain_signals[code])<7:domain_signals[code].append({'where':field,'phrase':cue})
 for x in out:
  if x['score']>=4:domain_scores[x['domain_code']]+=min(6,x['score'])
 independent_domains=[{'domain_code':d,'domain_label_en':domain_labels[d], 'score':v,
                     'evidence':domain_signals[d]} for d,v in domain_scores.most_common(3) if v>=3]
 status='candidates_to_review' if out and out[0]['score']>=4 else 'insufficient_evidence'
 # A microthesaurus has exactly one parent in the pinned UNESCO reference.
 # Present its real parent alongside the micro code, never an unrelated
 # independently scored domain (e.g. 2 / 4.35).
 domain_candidates=independent_domains
 if status=='candidates_to_review':
  primary=out[0]
  matching=next((x for x in independent_domains if x['domain_code']==primary['domain_code']),None)
  domain_candidates=[matching or {'domain_code':primary['domain_code'],
                     'domain_label_en':primary['domain_label_en'],
                     'score':primary['score'],'evidence':[{'where':'microthesaurus_parent','phrase':primary['microthesaurus_code']}] }]
  domain_candidates += [x for x in independent_domains if x['domain_code']!=primary['domain_code']][:2]
 return {'status':status,'domain_candidates':domain_candidates,
         'independent_domain_candidates':independent_domains,'candidates':out[:4], 'mapped':False,
         'caveat':'Microthesaurus parent is pinned to UNESCO reference; competing broad domains remain visible as independent suggestions. No endorsed taxonomy, accepted concept URI or canonical assertion.'}

def main(argv=None, *, quiet=False):
 p=argparse.ArgumentParser(description='Read-only batch triage from Kristal Manager content catalog (Arketype, keywords, UNESCO, diK).')
 p.add_argument('--catalogue',type=Path,required=True,help='kristal-contenu-global.sqlite3')
 p.add_argument('--audit',type=Path,help='Optional manager UNESCO audit JSON')
 p.add_argument('--out',type=Path,required=True,help='A NEW report directory (will not overwrite)')
 args=p.parse_args(argv)
 if not args.catalogue.is_file():raise ValueError('Catalogue SQLite introuvable')
 if args.audit and not args.audit.is_file():raise ValueError('Audit JSON introuvable')
 if args.out.exists():raise ValueError('Output directory already exists. Choose a new path (no overwrite).')
 archetypes,profile,mt=get_references()
 conn=read_catalogue(args.catalogue)
 try:
  mandatory={'workspaces','terms','nodes','assertions'}
  found={x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if not mandatory<=found:raise ValueError('Catalogue schema incompatible; missing tables: '+repr(sorted(mandatory-found)))
  records=conn.execute('SELECT id,path,summary FROM workspaces ORDER BY path').fetchall()
  allterms=defaultdict(list)
  for wid,lang,term in conn.execute('SELECT workspace,language,term FROM terms'):
   allterms[wid].append((lang or 'und',term or ''))
 finally:conn.close()
 audit={}
 if args.audit:
  obj=json.loads(args.audit.read_text(encoding='utf-8'))
  if obj.get('format')!='kristal.manager-unesco-audit/0.1':raise ValueError('Unexpected UNESCO audit schema')
  audit={x['path'].casefold():x for x in obj.get('entries',[]) if isinstance(x,dict) and isinstance(x.get('path'),str)}
 reports=[];tally=Counter()
 for wid,path,summary in records:
  s=json.loads(summary)
  desc=s.get('descriptors') or {}
  native=desc.get('native_model') or {}
  ownership=desc.get('semantic_ownership') or {}
  # These texts are descriptive metadata, NOT assertions about correctness.
  descriptor=' '.join([str(native.get('description','')),str(native.get('key_distinction','')),
             ' '.join(str(x) for x in ownership.get('owns',[])[:8])])
  subjects=' '.join(str(x.get('label','')) for x in s.get('top_subjects',[]) if isinstance(x,dict))
  relations=' '.join(str(x.get('label','')) for x in s.get('top_relations',[]) if isinstance(x,dict))
  kws,phrases=keywords_for(allterms[wid],s.get('title',''),descriptor,subjects,relations)
  ark=arketype_candidates(archetypes,s.get('native_kind','') or native.get('kind',''),descriptor,subjects,relations,kws)
  unesco=unesco_candidates(mt,kws,s.get('title',''),descriptor,subjects)
  metrics=s.get('metrics') or {}
  a=audit.get(path.casefold(),{})
  observed_langs=metrics.get('dictionary_languages') or sorted({lang for lang,term in allterms[wid]})
  wissues=list(s.get('issues') or [])
  if a and a.get('state_ref')!=s.get('state_ref'):wissues.append('Audit state_ref differs from catalog state_ref')
  if a and a.get('unesco',{}).get('status')!='Not mapped':wissues.append('Existing UNESCO mapping must be reviewed before adopting new suggestions')
  # A legacy-v6 entity key is not a KQ identity. Never use the v11 KQ
  # dictionary coverage gate against a registered historical v6 graph.
  # The historical graph remains observed, but diK has NOT been qualified.
  catalog_mode=s.get('mode')
  if s.get('content_status') not in ('observed','native_observed'):
   wissues.append('Catalog did not completely observe selected content: content inference limited')
  if catalog_mode=='active_v11' and metrics.get('entities') and not metrics.get('entities_with_descriptive_labels'):
   wissues.append('Active v11 graph lacks counted descriptive KQ labels: diK lexical coverage must be reviewed')
  report={
   'format':'kristal.manager-semantic-triage/0.1-prototype','generated_at':datetime.now(timezone.utc).isoformat(),
   'state_ref':s.get('state_ref'),'path':path,'title':s.get('title'),
   'status':{'catalog_readiness':s.get('readiness'),'content_status':s.get('content_status'),
             'catalog_mode':s.get('mode'),'unesco_audit_status':a.get('unesco',{}).get('status','not_supplied'),
             'qualification':'NOT_EVALUATED'},
   'keyword_summary':{'keywords':kws[:12],
                      'top_phrases':[{'phrase':t,'weight':v} for t,v in phrases.most_common(7)],
                      'resume_exploratoire':'Libelles dominants observes : '+', '.join(k['term'] for k in kws[:7])+'. Description exploratoire, non validee.',
                      'method':'Derived from recorded dictionary terms and catalog descriptors; statistical weights are not importance or truth.'},
   'arketype_inference':ark,'unesco_proposal':unesco,
   'dik_alignment_observations':{'namespace_id':s.get('namespace_id'),
        'dictionary_languages_reported':observed_langs,
        'entities_with_descriptive_labels_reported':metrics.get('entities_with_descriptive_labels'),
        'properties_with_descriptive_labels_reported':metrics.get('properties_with_descriptive_labels'),
        'entities_reported':metrics.get('entities'),'properties_reported':metrics.get('properties'),
        'accepted_external_equivalences_reported':metrics.get('wikidata_accepted_exact',None),
        'status':('LEGACY_V6_DIK_NOT_EVALUATED' if catalog_mode=='registered_legacy_v6'
                  else 'NATIVE_FORMAT_DIK_NOT_EVALUATED' if catalog_mode in ('unsupported','registered_native_embedded','registered_native_structured','registered_native_reference')
                  else 'LEXICAL_REVIEW_NOT_SEMANTIC_VERIFICATION'),
        'native_legacy_labels_observed':metrics.get('legacy_descriptive_labels_observed'),
        'rule':'No word-to-KQ/KP identity, new crosswalk, accepted exactMatch, translation or graph edit.'},
   'issues_to_review':wissues,
   'limitations':['Input is a selected-content catalog snapshot, not a fresh filesystem scan.',
                  'Unsupported content remains unknown, not empty.',
                  'Domain subject and structural Arketype are orthogonal.',
                  'No C1/C2/C3, diK qualification, UNESCO endorsement or publication is established.']}
  reports.append(report)
  tally['total']+=1;tally['catalog:'+str(s.get('content_status'))]+=1
  tally['ark:'+ark['status']]+=1;tally['unesco:'+unesco['status']]+=1
  if wissues:tally['with_issues']+=1
 args.out.mkdir(parents=True,exist_ok=False)
 sub=args.out/'kristals';sub.mkdir()
 used=set();csvrows=[];review=[]
 for r in reports:
  name=norm(r['path'].replace('\\','/').rstrip('/').split('/')[-1])
  name=re.sub(r'[^a-z0-9_-]+','-',name).strip('-') or 'kristal'
  if name in used:name=name+'-'+hashlib.sha256(r['path'].encode('utf-8')).hexdigest()[:8]
  used.add(name)
  (sub/(name+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  ark=r['arketype_inference'];u=r['unesco_proposal'];di=r['dik_alignment_observations']
  csvrows.append({'title':r['title'],'state_ref':r['state_ref'],'catalog_status':r['status']['content_status'],
  'catalog_readiness':r['status']['catalog_readiness'],'arketype_status':ark['status'],
  'arketype_top':ark['candidates'][0]['arketype_id'] if ark['candidates'] else '',
  'arketype_top_score':ark['candidates'][0]['score'] if ark['candidates'] else 0,
  'unesco_status':u['status'],'unesco_top':u['candidates'][0]['microthesaurus_code'] if u['candidates'] else '',
  'unesco_domain_candidate':u['domain_candidates'][0]['domain_code'] if u['domain_candidates'] else '',
  'unesco_top_score':u['candidates'][0]['score'] if u['candidates'] else 0,
  'keywords':'; '.join(x['term'] for x in r['keyword_summary']['keywords'][:8]),
  'locales':'; '.join(di['dictionary_languages_reported']),
  'issues':'; '.join(r['issues_to_review'][:4]),'detail_file':'kristals/'+name+'.json'})
  if r['issues_to_review'] or ark['status']!='candidate_to_review' or u['status']!='candidates_to_review':
   review.append({'title':r['title'],'state_ref':r['state_ref'],'detail_file':'kristals/'+name+'.json',
     'review_reasons':r['issues_to_review'][:4]+([ark['status']] if ark['status']!='candidate_to_review' else [])+([u['status']] if u['status']!='candidates_to_review' else [])})
 with (args.out/'vue_globale.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
 # Report is fully offline, no network, and all observed values are HTML-escaped.
 hrows=[]
 for x in csvrows:
  cells=[]
  for k in ('title','catalog_status','arketype_status','arketype_top','unesco_domain_candidate','unesco_top','keywords','issues'):
   value=str(x[k]); cells.append('<td>'+html_escape(value)+'</td>')
  hrows.append('<tr>'+''.join(cells)+'</tr>')
 html='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Kristal — triage de propositions</title>
 <style>body{font:14px system-ui;margin:25px auto;max-width:1600px;color:#223;background:#f9fafc}
 table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #ddd;text-align:left;padding:7px;vertical-align:top}
 th{background:#e9edf4;position:sticky;top:0}tr:nth-child(even){background:#fafbfd}small{color:#555}
 input{font-size:16px;padding:10px;width:90%;margin:12px 0}</style>
 <h1>Propositions de classification — non validées</h1>
 <p>Arketype structurel et UNESCO thématique sont des axes indépendants. Les valeurs ne prouvent aucune conformité.
 Ouvrir le JSON individuel pour les preuves détaillées.</p>
 <label>Recherche dans les résultats : <input id="q" placeholder="Filtrer la table" oninput="f()"></label>
 <table id="t"><thead><tr><th>Kristal</th><th>Contenu</th><th>Arketype statut</th><th>Top ARK</th><th>Domaine UNESCO</th><th>Micro UNESCO</th><th>Mots-clés</th><th>Observations</th></tr></thead><tbody>'''+''.join(hrows)+'''</tbody></table>
 <script>function f(){const s=document.getElementById('q').value.toLocaleLowerCase();
 for(const r of document.querySelectorAll('#t tbody tr')) r.hidden=!r.textContent.toLocaleLowerCase().includes(s);}</script>
 </html>'''
 (args.out/'rapport.html').write_text(html,encoding='utf-8')
 result={'format':'kristal.manager-semantic-triage-index/0.1-prototype','version':VERSION,
  'generated_at':datetime.now(timezone.utc).isoformat(),'source_catalogue':str(args.catalogue),
  'source_catalogue_sha256':digest_file(args.catalogue),
  'source_unesco_audit':str(args.audit) if args.audit else None,
  'counts':dict(tally),'candidates_review_only':True,
  'sources':{'arketype':'19 definitions from supplied arketype snapshot 2026-10-28',
             'unesco':'pinned UNESCO Thesaurus profile from supplied Kristal Manager snapshot',
             'dik':'requirements interpreted from diK docs; no diK executable called'},
  'warnings':['Read-only input; reports are noncanonical proposals, never automatic classifications.',
  'diK alignment is a preliminary coverage observation, not a diK coverage_report.',
  'To update canonical classifications, use the owner-approved Authoring Kit workflow after human review.']}
 (args.out/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (args.out/'a_examiner.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 notes=['KRISTAL SEMANTIC TRIAGE — CANDIDATES ONLY',f"Kristals: {len(reports)}",'']
 notes +=[f'{k}: {v}' for k,v in sorted(tally.items())]
 notes +=['','Input catalog and referenced source snapshots are not modified.','Arketype and UNESCO are only proposed; diK and Framework not formally evaluated.','']
 (args.out/'LISEZ_MOI.txt').write_text('\n'.join(notes),encoding='utf-8')
 if not quiet:
  print('Rapport:',args.out,'| Kristals:',len(reports),'| A examiner:',len(review))
  print('Arketype candidats:',tally['ark:candidate_to_review'],'| UNESCO candidats:',tally['unesco:candidates_to_review'])
 return 0

if __name__=='__main__':
 try:sys.exit(main())
 except (sqlite3.Error,ValueError,OSError,json.JSONDecodeError) as e:
  print('ERREUR:',e,file=sys.stderr);sys.exit(2)
