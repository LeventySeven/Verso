"""Generate WF2: transcript-hunt the 89 video/podcast sources in the 3 technical sections."""
import json, re
from pathlib import Path

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
items = json.loads((BASE / "WF2_core_AV.json").read_text(encoding="utf-8"))

def kebab(s):
    s = re.sub(r"[^\x00-\x7F]+", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]
def slug(t): return kebab(t)[:60]

for s in items:
    s["section_slug"] = kebab(s["section"])
    s["slug"] = slug(s["title"])
    s["note_path"] = f"{BASE}/notes/{s['section_slug']}/{s['slug']}.md"

# Batch ~3 per agent (transcript hunting is heavier per source than reading an essay)
items.sort(key=lambda s: (s["section"], s["rating"] != "MUST", s["title"]))
BATCH = 3
batches = [items[i:i+BATCH] for i in range(0, len(items), BATCH)]

VERSO = """You are investigating video/podcast/talk sources for VERSO, a Python agent framework, by HUNTING FOR TRANSCRIPTS (you cannot watch video). You have FULL tool access: WebFetch, WebSearch, Read, Write, Bash. "Extract findings"/"do not implement" restrict OUTPUT only.

VERSO IN ONE PARAGRAPH: the agent loop is ~10 lines and is NOT where anyone competes; the product is the harness. Verso ships a clean <200-line async ReAct loop with CONTEXT ENGINEERING and EVALS+RELIABILITY first-class, and a tactical<->durable seam (one flag promotes an ephemeral agent to event-sourced checkpoint/resume + HITL, never a rewrite, never a forced graph). Counter-position: "we don't force the graph."

HARD INVARIANTS (challenging one is HIGH VALUE): no graph for tactical agents; native Python @tool is THE tool path (MCP demoted, opt-in); Python-only, no Rust; loop <200 lines; no overkill / no bullshit / simplicity; build for the durable layer, stay simple in the tactical layer.

PRD SECTION MAP: §1 bet · §2 non-goals · §4 seam · §5.1 loop · §5.2 context · §5.3 tools · §5.4 memory · §5.5 evals · §6.1 durable · §6.2 multi-agent · §6.3 safety · §6.4 model · §12 positioning.
THEME KEYS: context, evals, model, memory, multiagent, loop_harness, strategy.

ALREADY KNOWN (report DELTAS, not re-confirmations): KV-cache prefix discipline; observation-masking compaction (N=10); append-only history; {data,error,ok} dispatch; named StopReason; cross-model failover; role-tiered models; think/done builtins; RunContext + ContextBundle.inspect(); RRF k=60 + asymmetric embeddings; 4-tier typed memory + temporal versioning; judge-panel + define_outcome(bounded); just-in-time retrieval; bitter-lesson churn; reinforcement-on-tool-return; ACI tool-design; cache-cost-aware compaction; sub-agents as failure-quarantine + scheduler-offload; embedded in-process evals; the anti-framework triumvirate (Anthropic/Chase/Ronacher)."""

INSTR = """FOR EACH source (a talk/podcast/video):
1. FIND A TRANSCRIPT — videos cannot be watched, so: (a) FIRST check whether a transcript or detailed notes already exist under /Users/seventyleven/Desktop/Verso/research/02_core/ (grep the transcripts-*.md files for the speaker/title — the user already harvested many); (b) WebSearch for an official transcript, the show-notes page, a Latent Space / Dwarkesh / Sequoia writeup, or a YouTube transcript mirror; (c) WebFetch the best transcript/notes you find and READ IT. If you locate only a short description or nothing substantive, set status "unreachable" and say exactly what you could/couldn't find — DO NOT invent or infer content you didn't read.
2. WRITE A NOTE to the EXACT note_path: a faithful digest of what the speaker actually argues (mechanisms, numbers, 3-6 verbatim quotes from the transcript if available) + a "## VERSO RELEVANCE" section mapping concrete findings to PRD sections, each tagged [CONFIRMS §x]/[CONTRADICTS §x]/[SHARPENS §x]/[NEW-IDEA], + a one-line no-overkill verdict per finding. If unreachable, still write a short note recording the source, what you searched, and that no transcript was found.
3. Honesty over coverage: a flagged "unreachable" is correct and useful; a fabricated digest is a failure.

RETURN (compact): per source {title, url, status (read_full|read_partial|unreachable), note_path, source_found (where the transcript came from, or "none"), themes (subset of the 7 keys), top_deltas (up to 3 NEW/CONTRADICT/SHARPEN findings as {finding, tag, prd_section})}."""

SYNTH = """Consolidate the VERSO-relevant findings for ONE theme from the reader note files given (READ each in full). WRITE a synthesis to the given synthesis_path: cross-source picture, genuinely NEW/CONTRADICTING findings deduped (with source + quote), what should change in the PRD vs what's already covered (including what WF1's full-text pass already established — do not re-list those), and a RESIST list. Apply no-overkill ruthlessly. Note explicitly which sources were unreachable so coverage is honest. RETURN {theme, synthesis_path, deltas:[{finding,tag,prd_section,recommendation,source}], resist:[...], unreachable_count}."""

js = []
js.append("export const meta = {")
js.append("  name: 'bad-guide-technical-AV-transcripts',")
js.append("  description: 'Transcript-hunt + read the agent/Anthropic/frontier video+podcast sources in The Bad Guide; extract Verso deltas',")
js.append("  phases: [{ title: 'Transcript-hunt', detail: 'find+read transcript per AV source, write a note (flag unreachable)' }, { title: 'Synthesize', detail: 'thematic synthesizers consolidate vs WF1 + the PRD' }],")
js.append("}")
js.append(f"const OUTDIR = {json.dumps(str(BASE / 'notes'))};")
js.append(f"const BATCHES = {json.dumps(batches, ensure_ascii=False)};")
js.append(f"const VERSO = {json.dumps(VERSO)};")
js.append(f"const INSTR = {json.dumps(INSTR)};")
js.append(f"const SYNTH = {json.dumps(SYNTH)};")
js.append("""
const THEMES = {
  context: 'Context engineering (§5.2)', evals: 'Evals + verification (§5.5)',
  model: 'Model / provider / routing (§6.4)', memory: 'Memory + retrieval (§5.4)',
  multiagent: 'Multi-agent / orchestration (§6.2)',
  loop_harness: 'Loop, tools, durable runtime, safety (§5.1/§5.3/§6.1/§6.3/§4)',
  strategy: 'The bet, non-goals, positioning (§1/§2/§12)',
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

function srcLine(s){ return '- ' + s.title + '  [' + (s.rating||'-') + ']  <' + s.url + '>\\n    meta: ' + (s.meta||'') + '\\n    guide-note: ' + (s.note||'') + '\\n    WRITE NOTE TO (exact): ' + s.note_path; }
function readPrompt(b,i){ return VERSO + '\\n\\n## Your assigned AV sources (batch ' + i + ') — hunt a transcript for each\\n' + b.map(srcLine).join('\\n\\n') + '\\n\\n## Instructions\\n' + INSTR; }
function synthPrompt(k,label,notes){ const p = OUTDIR + '/_SYNTHESIS_AV_' + k + '.md'; return VERSO + '\\n\\n## Theme: ' + label + '\\nsynthesis_path: ' + p + '\\n\\n## Note files (read each in full)\\n' + notes.map(n=>'- ' + n.title + '  ->  ' + n.note_path).join('\\n') + '\\n\\n## Instructions\\n' + SYNTH; }

phase('Transcript-hunt');
log('WF2: hunting transcripts for ' + BATCHES.flat().length + ' AV sources across ' + BATCHES.length + ' batches');
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
(BASE / "wf2.mjs").write_text("\n".join(js), encoding="utf-8")
print(f"wrote wf2.mjs  ({sum(len(x) for x in js)} chars)")
print(f"AV sources: {len(items)}  batches: {len(batches)} of ~{BATCH}")
from collections import Counter
print(f"by section: {dict(Counter(s['section'] for s in items))}")
print(f"by host (top): {dict(Counter(s['host'] for s in items).most_common(10))}")
