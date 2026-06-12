"""Generate WF4: transcript-hunt the 91 founder/product/GTM video/podcast sources."""
import json, re
from pathlib import Path

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
items = json.loads((BASE / "WF4_rest_AV.json").read_text(encoding="utf-8"))

def kebab(s):
    s = re.sub(r"[^\x00-\x7F]+", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

for s in items:
    s["section_slug"] = kebab(s["section"])
    s["slug"] = kebab(s["title"])[:60]
    s["note_path"] = f"{BASE}/notes/{s['section_slug']}/{s['slug']}.md"

items.sort(key=lambda s: (s["section"], s["rating"] != "MUST", s["title"]))
BATCH = 3
batches = [items[i:i+BATCH] for i in range(0, len(items), BATCH)]

VERSO = """You are investigating founder/product/GTM video/podcast sources for VERSO (a Python agent framework) by HUNTING FOR TRANSCRIPTS — focused on its POSITIONING, GO-TO-MARKET, PRODUCT TASTE, and FOUNDER-OPERATING layer (not internal architecture). You have FULL tool access: WebFetch, WebSearch, Read, Write, Bash. "Extract findings"/"do not implement" restrict OUTPUT only.

VERSO: a Python agent framework whose bet is that the agent loop is ~10 lines and not where anyone competes — the product is the harness (context engineering + evals/reliability + a tactical<->durable seam: one flag promotes an ephemeral agent to event-sourced checkpoint/resume + HITL, never a rewrite, never a forced graph). Counter-position: "we don't force the graph." Personal-infra, dogfood-first, OSS-ready. Primary persona: the structurally-aware senior / AI engineer (the lead choosing a harness for their 2nd/3rd production agent), NOT the ML researcher and NOT the vibe-coder.

MAP findings to: §1 bet/moat/defensibility · §2 non-goals/principled-refusal · §7+§12 demo-able wedge + product/design taste · §12 positioning + GTM (category+POV, channel, cold-start, launch, becoming-hunted) · or the FOUNDER-OS layer (operating principles / leverage / YC-a16z — feeds research/04_bad_guide_full, tag founder_os). THEME KEYS: bet_moat, positioning, gtm_distribution, product_taste, founder_os.

ALREADY ESTABLISHED by prior passes (report DELTAS, do NOT re-confirm): harness-is-moat is CONSENSUS (win on the specific shape, not the claim); name a category + POV, ban "-er-than-LangChain"; the anti-framework triumvirate; embedded in-process evals vs monetize-LangSmith; "why not DSPy" = evals are the gradient; Helmer 7-Powers test + switching-costs-at-seam; Framework->Runtime->Harness tier vocabulary; measured harness lift (v0 +29pp, Sierra 61%/35%, Glean 0.9^10); march-of-nines + 35M-times context-density + OS analogy; intellectual-honesty register ("decade not year", no magic box, "explain without AI"); persona = structurally-aware senior/AI engineer; DX-led organic GTM (no sales motion, superconsumer-first); the demo-able wedge (3-line side-by-side / one-flag durable diff / inspect()); eval-corpus aggregation flywheel; invariants-as-taste; SCHLEP-AS-MOAT; feature-vs-structural-moat firewall; legibility ceiling; non-goals-are-evidence-updatable-not-identity; knives-not-avocado-slicers; inspect()-as-data-viewer; wedge-is-epistemic; competitor-is-doing-nothing / struggling-moment; "harness" is the internal word (external word unvalidated); cold-start Stage-1 / atomic network = ~5 vocal production leads; Frequency x Novelty taste filter; Grossmann/Einstein test."""

INSTR = """FOR EACH source (a talk/podcast/video):
1. FIND A TRANSCRIPT — videos cannot be watched. (a) FIRST check whether a transcript/notes already exist under /Users/seventyleven/Desktop/Verso/research/02_core/ and /Users/seventyleven/Desktop/Verso/research/04_bad_guide_full/ (grep for the speaker/title). (b) WebSearch for an official transcript, show-notes, a Latent Space/Dwarkesh/Sequoia/Lenny/YC writeup, or a transcript mirror; WebFetch the best one and READ IT. If you find only a short description or nothing substantive, set status "unreachable" and say exactly what you searched — DO NOT invent or infer content you didn't read.
2. WRITE A NOTE to the EXACT note_path: a faithful digest of what the speaker actually argues (frameworks, numbers, 3-6 verbatim quotes if a transcript is available) + a "## VERSO RELEVANCE" section mapping concrete findings to §1/§2/§7/§12 or the founder-OS layer, each tagged [CONFIRMS]/[CONTRADICTS]/[SHARPENS]/[NEW-IDEA], + a one-line no-overkill verdict per finding. If unreachable, still write a short note recording the source, what you searched, and that no transcript was found. Most of these inform POSITIONING/GTM/TASTE/founder-OS, not framework primitives.
3. Honesty over coverage: a flagged "unreachable" is correct; a fabricated digest is a failure.

RETURN (compact): per source {title, url, status (read_full|read_partial|unreachable), note_path, source_found (where the transcript came from, or "none"), themes (subset of the 5 keys), top_deltas (up to 3 NEW/CONTRADICT/SHARPEN findings as {finding, tag, prd_section})}."""

SYNTH = """Consolidate the VERSO-relevant findings for ONE theme from the reader note files given (READ each in full). WRITE a synthesis to the given synthesis_path: cross-source picture; genuinely NEW/CONTRADICTING findings deduped (with source + quote); what should change in the PRD (§1/§2/§7/§12) vs what ALL prior passes already established (do NOT re-list those — the established list is long); and — for founder_os — what lands in research/04_bad_guide_full rather than the PRD. Apply no-overkill ruthlessly: most findings will be confirm; GTM-execution apparatus must NOT leak into the PRD. Note unreachable sources for coverage honesty. RETURN {theme, synthesis_path, deltas:[{finding,tag,prd_section,recommendation,source}], resist:[...], unreachable_count}."""

js = []
js.append("export const meta = {")
js.append("  name: 'bad-guide-founder-product-AV-transcripts',")
js.append("  description: 'Transcript-hunt the founder/product/GTM video+podcast sources in The Bad Guide; extract Verso positioning/GTM/taste deltas',")
js.append("  phases: [{ title: 'Transcript-hunt', detail: 'find+read transcript per AV source, write a note (flag unreachable)' }, { title: 'Synthesize', detail: 'thematic synthesizers consolidate vs all prior passes' }],")
js.append("}")
js.append(f"const OUTDIR = {json.dumps(str(BASE / 'notes'))};")
js.append(f"const BATCHES = {json.dumps(batches, ensure_ascii=False)};")
js.append(f"const VERSO = {json.dumps(VERSO)};")
js.append(f"const INSTR = {json.dumps(INSTR)};")
js.append(f"const SYNTH = {json.dumps(SYNTH)};")
js.append("""
const THEMES = {
  bet_moat: 'The bet / moat / defensibility (§1)',
  positioning: 'Positioning, category, counter-position, persona (§12)',
  gtm_distribution: 'Go-to-market, distribution, launch, cold-start (§12)',
  product_taste: 'Product & design/UX taste + the demo-able wedge (§2/§7/§12)',
  founder_os: 'Founder-OS operating principles / leverage / YC-a16z (feeds research/04_bad_guide_full)',
};
const BATCH_SCHEMA = { type:'object', required:['sources'], additionalProperties:false, properties:{ sources:{ type:'array', items:{
  type:'object', required:['title','url','status','note_path','themes','top_deltas'], additionalProperties:false, properties:{
    title:{type:'string'}, url:{type:'string'}, status:{type:'string', enum:['read_full','read_partial','unreachable']},
    note_path:{type:'string'}, source_found:{type:'string'}, themes:{type:'array', items:{type:'string', enum:Object.keys(THEMES)}},
    top_deltas:{type:'array', items:{ type:'object', required:['finding','tag'], additionalProperties:false,
      properties:{ finding:{type:'string'}, tag:{type:'string', enum:['CONFIRMS','CONTRADICTS','SHARPENS','NEW-IDEA']}, prd_section:{type:'string'} } } } } } } } };
const SYNTH_SCHEMA = { type:'object', required:['theme','synthesis_path','deltas','resist'], additionalProperties:false, properties:{
  theme:{type:'string'}, synthesis_path:{type:'string'},
  deltas:{type:'array', items:{ type:'object', required:['finding','tag','recommendation'], additionalProperties:false,
    properties:{ finding:{type:'string'}, tag:{type:'string'}, prd_section:{type:'string'}, recommendation:{type:'string', enum:['adopt-now','lock-defer','sharpen','resist','confirm']}, source:{type:'string'} } } },
  resist:{type:'array', items:{type:'string'}}, unreachable_count:{type:'number'} } };

function srcLine(s){ return '- ' + s.title + '  [' + (s.rating||'-') + ']  <' + s.url + '>\\n    section: ' + s.section + '\\n    meta: ' + (s.meta||'') + '\\n    guide-note: ' + (s.note||'') + '\\n    WRITE NOTE TO (exact): ' + s.note_path; }
function readPrompt(b,i){ return VERSO + '\\n\\n## Your assigned AV sources (batch ' + i + ') — hunt a transcript for each\\n' + b.map(srcLine).join('\\n\\n') + '\\n\\n## Instructions\\n' + INSTR; }
function synthPrompt(k,label,notes){ const p = OUTDIR + '/_SYNTHESIS_WF4_' + k + '.md'; return VERSO + '\\n\\n## Theme: ' + label + '\\nsynthesis_path: ' + p + '\\n\\n## Note files (read each in full)\\n' + notes.map(n=>'- ' + n.title + '  ->  ' + n.note_path).join('\\n') + '\\n\\n## Instructions\\n' + SYNTH; }

phase('Transcript-hunt');
log('WF4: hunting transcripts for ' + BATCHES.flat().length + ' founder/product/GTM AV sources across ' + BATCHES.length + ' batches');
const reads = await parallel(BATCHES.map((b,i)=>()=> agent(readPrompt(b,i), { label:'av:b'+i, phase:'Transcript-hunt', schema:BATCH_SCHEMA, model:'sonnet', agentType:'general-purpose' }).catch(()=>null)));
const all = reads.filter(Boolean).flatMap(r=>r.sources||[]);
const unreached = all.filter(s=>s.status==='unreachable');
log('AV read ' + all.length + '; unreachable ' + unreached.length);
const byTheme = {}; for(const k of Object.keys(THEMES)) byTheme[k]=[];
for(const s of all){ if(s.status==='unreachable'||!s.note_path) continue; for(const t of (s.themes||[])) if(byTheme[t]) byTheme[t].push({title:s.title, note_path:s.note_path}); }
phase('Synthesize');
const synth = await parallel(Object.entries(THEMES).map(([k,label])=>()=>{ const n=byTheme[k]; if(!n||!n.length) return Promise.resolve(null); return agent(synthPrompt(k,label,n), { label:'synth:'+k, phase:'Synthesize', schema:SYNTH_SCHEMA, agentType:'general-purpose' }).catch(()=>null); }));
return { covered: all.length, unreachable: unreached.map(s=>({title:s.title,url:s.url})), notes: all.map(s=>({title:s.title,status:s.status,note_path:s.note_path,source_found:s.source_found})), syntheses: synth.filter(Boolean) };
""")
(BASE / "wf4.mjs").write_text("\n".join(js), encoding="utf-8")
print(f"wrote wf4.mjs ({sum(len(x) for x in js)} chars)")
print(f"AV sources: {len(items)}  batches: {len(batches)} of ~{BATCH}")
from collections import Counter
print(f"by section: {dict(Counter(s['section'] for s in items))}")
