"""Generate WF3: full-text read the 80 founder/product/GTM/design/distribution/leverage/YC sources."""
import json, re
from pathlib import Path

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
items = json.loads((BASE / "WF3_rest_text.json").read_text(encoding="utf-8"))

def kebab(s):
    s = re.sub(r"[^\x00-\x7F]+", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

for s in items:
    s["section_slug"] = kebab(s["section"])
    s["slug"] = kebab(s["title"])[:60]
    s["note_path"] = f"{BASE}/notes/{s['section_slug']}/{s['slug']}.md"

items.sort(key=lambda s: (s["section"], s["rating"] != "MUST", s["title"]))
BATCH = 4
batches = [items[i:i+BATCH] for i in range(0, len(items), BATCH)]

VERSO = """You are investigating founder/product/GTM/design/distribution sources for VERSO, a Python agent framework, focused on its POSITIONING, GO-TO-MARKET, PRODUCT TASTE, and FOUNDER-OPERATING layer (not its internal architecture). You have FULL tool access: WebFetch, WebSearch, Read, Write, Bash. "Extract findings"/"do not implement" restrict OUTPUT only; you MUST WebFetch to read full sources.

VERSO IN ONE PARAGRAPH: a Python agent framework whose bet is that the agent loop is ~10 lines and not where anyone competes — the product is the harness (context engineering + evals/reliability + a tactical<->durable seam: one flag promotes an ephemeral agent to event-sourced checkpoint/resume + HITL, never a rewrite, never a forced graph). Counter-position: "we don't force the graph." Personal-infra, dogfood-first, OSS-ready. Primary persona: the structurally-aware senior / AI engineer (the ~50M software engineers becoming AI engineers), NOT the ML researcher and NOT the non-technical vibe-coder.

WHAT THIS PASS IS FOR (map findings to these):
- §1 the bet / moat / defensibility (7 Powers, aggregation theory, counter-positioning, switching costs at the seam).
- §2 non-goals / principled refusal (what Verso deliberately does NOT do).
- §7 / §12 the DEMO-ABLE WEDGE + product taste (the 3-line side-by-side; the one-flag durable diff; agent.inspect() as a taste surface) and DESIGN/UX taste.
- §12 positioning + GTM: category design + POV, naming, the anti-framework counter-position, channel (X build-in-public + Show HN), cold-start, launch-in-hours, distribution loops, becoming-hunted/leverage.
- FOUNDER-OS layer: operating principles / high-agency / leverage / YC-a16z game — these feed research/04_bad_guide_full (the founder-OS index), NOT the PRD's product sections. Tag them founder_os.

ALREADY ESTABLISHED by prior passes (report DELTAS, do NOT re-confirm these): harness-is-the-moat is now CONSENSUS (so positioning must win on the specific shape, not the claim); name a category + POV, ban "-er-than-LangChain" Better-Trap language; the anti-framework triumvirate (Anthropic "use the APIs directly" + Chase "we traded power for ease of use" + Ronacher "build your own abstraction"); embedded in-process evals vs LangChain's monetize-LangSmith model; "why not DSPy" = evals are the gradient, optimization stays in Python; Helmer 7-Powers test (counter-position real iff incumbent can't copy without self-destruction) + switching-costs-at-the-seam as the next power; LangChain's own Framework->Runtime->Harness tier vocabulary (seam collapses framework->runtime); measured harness lift (v0 +29pp, Sierra 61%/35%, Glean 0.9^10); march-of-nines + 35M-times context-density + the OS analogy; intellectual-honesty register ("decade not year", no magic box, "explain it without AI"); primary persona = structurally-aware senior/AI engineer; DX-led organic GTM (no sales motion, superconsumer-first); the demo-able wedge (3-line side-by-side / one-flag durable diff / inspect()); Aggregation-Theory eval-corpus flywheel; invariants-as-taste."""

INSTR = """FOR EACH source:
1. WebFetch the URL and READ THE FULL TEXT (re-fetch/paginate if long; if blocked, WebSearch for a mirror or the author's canonical copy). If a source is a video/podcast page with no transcript and no substantive text, set status "unreachable" and say so — DO NOT invent.
2. WRITE A DETAILED NOTE (a full investigation, not a summary) to the EXACT note_path: (a) a faithful digest of the source's actual argument with load-bearing specifics — frameworks, numbers, 4-8 verbatim quotes; (b) a "## VERSO RELEVANCE" section mapping concrete findings to §1/§2/§7/§12 or the founder-OS layer, each tagged [CONFIRMS]/[CONTRADICTS]/[SHARPENS]/[NEW-IDEA]; (c) a one-line no-overkill verdict per finding (adopt-now / lock-defer / sharpen / resist / confirm). Cite the URL. Most of these sources inform POSITIONING/GTM/TASTE, not framework primitives — but if a source genuinely sharpens a §5/§6 primitive, surface it.
3. Create the parent directory if needed.

RETURN (compact): per source {title, url, status (read_full|read_partial|unreachable), note_path, themes (subset of: bet_moat, positioning, gtm_distribution, product_taste, founder_os), top_deltas (up to 3 NEW/CONTRADICT/SHARPEN findings as {finding, tag, prd_section})}. Skip pure confirmations in the RETURN (record them in the note)."""

SYNTH = """Consolidate the VERSO-relevant findings for ONE theme from the reader note files given (READ each in full). WRITE a synthesis to the given synthesis_path: cross-source picture; genuinely NEW/CONTRADICTING findings deduped (with source + verbatim quote); precisely what should change in the PRD (§1/§2/§7/§12) vs what the prior passes already established (do NOT re-list those); and — for founder_os — what should land in research/04_bad_guide_full as operating-principle material rather than the PRD. Apply no-overkill / no-bullshit ruthlessly: most findings resolve to confirm or sharpen, and GTM-execution apparatus must NOT leak into the PRD's product scope. RETURN {theme, synthesis_path, deltas:[{finding,tag,prd_section,recommendation,source}], resist:[...]}."""

js = []
js.append("export const meta = {")
js.append("  name: 'bad-guide-founder-product-gtm-fulltext',")
js.append("  description: 'Full-text read the founder/product/GTM/design/distribution sources in The Bad Guide; extract Verso positioning/GTM/taste deltas',")
js.append("  phases: [{ title: 'Read', detail: 'fetch+read full text per source, write a note' }, { title: 'Synthesize', detail: 'thematic synthesizers consolidate positioning/GTM/founder-OS vs prior passes' }],")
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
    note_path:{type:'string'}, themes:{type:'array', items:{type:'string', enum:Object.keys(THEMES)}},
    top_deltas:{type:'array', items:{ type:'object', required:['finding','tag'], additionalProperties:false,
      properties:{ finding:{type:'string'}, tag:{type:'string', enum:['CONFIRMS','CONTRADICTS','SHARPENS','NEW-IDEA']}, prd_section:{type:'string'} } } } } } } } };
const SYNTH_SCHEMA = { type:'object', required:['theme','synthesis_path','deltas','resist'], additionalProperties:false, properties:{
  theme:{type:'string'}, synthesis_path:{type:'string'},
  deltas:{type:'array', items:{ type:'object', required:['finding','tag','recommendation'], additionalProperties:false,
    properties:{ finding:{type:'string'}, tag:{type:'string'}, prd_section:{type:'string'}, recommendation:{type:'string', enum:['adopt-now','lock-defer','sharpen','resist','confirm']}, source:{type:'string'} } } },
  resist:{type:'array', items:{type:'string'}} } };

function srcLine(s){ return '- ' + s.title + '  [' + (s.rating||'-') + ']  <' + s.url + '>\\n    section: ' + s.section + '\\n    meta: ' + (s.meta||'') + '\\n    guide-note: ' + (s.note||'') + '\\n    WRITE NOTE TO (exact): ' + s.note_path; }
function readPrompt(b,i){ return VERSO + '\\n\\n## Your assigned sources (batch ' + i + ') — read the FULL text of each\\n' + b.map(srcLine).join('\\n\\n') + '\\n\\n## Instructions\\n' + INSTR; }
function synthPrompt(k,label,notes){ const p = OUTDIR + '/_SYNTHESIS_WF3_' + k + '.md'; return VERSO + '\\n\\n## Theme: ' + label + '\\nsynthesis_path: ' + p + '\\n\\n## Note files (read each in full)\\n' + notes.map(n=>'- ' + n.title + '  ->  ' + n.note_path).join('\\n') + '\\n\\n## Instructions\\n' + SYNTH; }

phase('Read');
log('WF3: reading ' + BATCHES.flat().length + ' founder/product/GTM full-text sources across ' + BATCHES.length + ' batches');
const reads = await parallel(BATCHES.map((b,i)=>()=> agent(readPrompt(b,i), { label:'read:b'+i, phase:'Read', schema:BATCH_SCHEMA, model:'sonnet', agentType:'general-purpose' }).catch(()=>null)));
const all = reads.filter(Boolean).flatMap(r=>r.sources||[]);
const unreached = all.filter(s=>s.status==='unreachable');
log('read ' + all.length + '; unreachable ' + unreached.length);
const byTheme = {}; for(const k of Object.keys(THEMES)) byTheme[k]=[];
for(const s of all){ if(s.status==='unreachable'||!s.note_path) continue; for(const t of (s.themes||[])) if(byTheme[t]) byTheme[t].push({title:s.title, note_path:s.note_path}); }
phase('Synthesize');
const synth = await parallel(Object.entries(THEMES).map(([k,label])=>()=>{ const n=byTheme[k]; if(!n||!n.length) return Promise.resolve(null); return agent(synthPrompt(k,label,n), { label:'synth:'+k, phase:'Synthesize', schema:SYNTH_SCHEMA, agentType:'general-purpose' }).catch(()=>null); }));
return { covered: all.length, unreachable: unreached.map(s=>({title:s.title,url:s.url})), notes: all.map(s=>({title:s.title,status:s.status,note_path:s.note_path})), syntheses: synth.filter(Boolean) };
""")
(BASE / "wf3.mjs").write_text("\n".join(js), encoding="utf-8")
print(f"wrote wf3.mjs ({sum(len(x) for x in js)} chars)")
print(f"sources: {len(items)}  batches: {len(batches)} of ~{BATCH}")
from collections import Counter
print(f"by section: {dict(Counter(s['section'] for s in items))}")
