"""Generate the WF1 workflow script (.mjs) with batches embedded + deterministic note paths."""
import json
import re
from pathlib import Path

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
data = json.loads((BASE / "wf1_batches.json").read_text(encoding="utf-8"))
OUTDIR = data["outdir"]
batches = data["batches"]

def kebab(s):
    s = re.sub(r"[^\x00-\x7F]+", "", s)  # strip emoji/non-ascii
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

# precompute deterministic note_path per source
for b in batches:
    for s in b:
        sec_slug = kebab(s["section"])
        s["section_slug"] = sec_slug
        s["note_path"] = f"{OUTDIR}/{sec_slug}/{s['slug']}.md"

VERSO = """You are investigating ONE-or-few sources for VERSO, a Python agent framework. Read the FULL raw text of each and extract what matters for Verso's design. You have FULL tool access: WebFetch, WebSearch, Read, Write, Bash. The phrases "extract findings" / "do not implement" restrict OUTPUT actions only — use tools freely; you MUST WebFetch to read the full sources.

VERSO IN ONE PARAGRAPH: the agent loop is ~10 lines and is NOT where anyone competes; the product is the harness around it. Verso ships the boring durable core done right — one clean <200-line async ReAct loop — with the two things every other framework buries made first-class: CONTEXT ENGINEERING and EVALS+RELIABILITY. Organizing idea: the tactical<->durable seam — the same agent runs ephemeral-and-simple by default and is promoted to durable (event-sourced checkpoint/resume, human-in-the-loop) with ONE flag, never a rewrite, never a forced graph. Counter-position: "we don't force the graph."

HARD INVARIANTS (a finding that challenges one of these is HIGH VALUE — surface it loudly): no graph required for tactical agents; native Python @tool is THE tool path (MCP is a demoted opt-in adapter); Python-only, no Rust; the loop file stays <200 lines; "no overkill, no bullshit, simplicity" — every primitive must earn its place; build for the durable layer, stay ruthlessly simple in the tactical layer.

PRD SECTION MAP (tag each finding with one): §1 the bet · §2 non-goals · §4 the seam/architecture · §5.1 loop · §5.2 context-engineering · §5.3 tools · §5.4 memory · §5.5 evals · §6.1 durable runtime · §6.2 multi-agent · §6.3 safety/hooks · §6.4 model/provider · §12 positioning/GTM.

THEME KEYS (tag each source with the subset it touches): context, evals, model, memory, multiagent, loop_harness, strategy.

ALREADY KNOWN (the harvest already captured these — do NOT merely re-confirm; spend your words on what is NEW, CONTRADICTS, or SHARPENS): KV-cache static/dynamic prefix discipline; observation-masking compaction (N=10); append-only history; {data,error,ok} dispatch that never raises; named StopReason enum; cross-model (not same-model) failover; role-tiered models (cheap loop / mid retry / reasoning synthesis); think/done builtins; RunContext typed injection; ContextBundle inspect(); RRF k=60 + asymmetric embeddings; 4-tier typed memory + temporal versioning; judge-panel evals + define_outcome(bounded); just-in-time retrieval; the bitter lesson (tactical workarounds churn ~1-2yr; durable architecture persists 3+ model generations)."""

READ_INSTR = """FOR EACH source assigned to you:
1. WebFetch the URL and READ THE FULL TEXT — not a skim, not the meta line. If the page is long/paginated, fetch again or fetch sub-pages until you have the whole thing. If it is a GitHub repo, fetch the README and the most important files. If a fetch is blocked or truncated, try WebSearch for a full-text mirror or the author's canonical copy, and also check whether a transcript already exists under /Users/seventyleven/Desktop/Verso/research/02_core/ . If it is a video/podcast page with NO transcript and no substantive text, set status "unreachable" and say so plainly — DO NOT invent content.
2. WRITE A DETAILED NOTE (this durable artifact IS the deliverable — a full investigation, never a one-line summary) to the EXACT note_path given for that source. The note must contain: (a) a faithful digest of the source's actual argument with its load-bearing specifics — exact mechanisms, numbers, and 4-8 verbatim quotes; (b) a "## VERSO RELEVANCE" section mapping concrete findings to PRD sections, each tagged [CONFIRMS §x] / [CONTRADICTS §x] / [SHARPENS §x] / [NEW-IDEA]; (c) a one-line no-overkill verdict per finding: adopt-now / lock-interface-defer / sharpen / resist / confirm. Cite the URL. A stub or empty note is a failure — write real content grounded in the fetched text.
3. Create the parent directory if needed (the note_path is absolute and deterministic).

RETURN (structured + compact — the notes hold the detail): for each source {title, url, status (read_full|read_partial|unreachable), note_path, themes (subset of the 7 theme keys), top_deltas (up to 3 of the most important NEW/CONTRADICT/SHARPEN findings as {finding, tag, prd_section})}. Skip pure confirmations in the RETURN (still record them in the note). Be honest about partial/unreachable sources."""

SYNTH_INSTR = """You are consolidating the VERSO-relevant findings for ONE theme. You are given the note files (produced by the readers) for the sources that touch this theme. READ each note file IN FULL with the Read tool. Then WRITE a theme synthesis to the given synthesis_path containing: the cross-source picture for this theme; the genuinely NEW or CONTRADICTING findings deduped across sources (each with its source + a verbatim quote); precisely what should change in the Verso PRD vs what is already covered; and an explicit RESIST list (source ideas that would be overkill/bullshit for a v1 personal-infra framework). Apply the no-overkill / no-bullshit / simplicity rule ruthlessly — most findings should resolve to confirm or sharpen, not new machinery.

RETURN: {theme, synthesis_path, deltas: [{finding, tag (CONFIRMS|CONTRADICTS|SHARPENS|NEW-IDEA), prd_section, recommendation (adopt-now|lock-defer|sharpen|resist|confirm), source}], resist: [strings]}. Lead with the highest-value deltas; cap at ~10."""

js = []
js.append("export const meta = {")
js.append("  name: 'bad-guide-agents-anthropic-fulltext',")
js.append("  description: 'Full-text read every agent/Anthropic/frontier source in The Bad Guide; extract Verso-relevant deltas to disk',")
js.append("  phases: [{ title: 'Read', detail: 'fetch + read full text per source, write a detailed note' }, { title: 'Synthesize', detail: 'thematic synthesizers consolidate deltas vs the PRD' }],")
js.append("}")
js.append(f"const OUTDIR = {json.dumps(OUTDIR)};")
js.append(f"const BATCHES = {json.dumps(batches, ensure_ascii=False)};")
js.append(f"const VERSO = {json.dumps(VERSO)};")
js.append(f"const READ_INSTR = {json.dumps(READ_INSTR)};")
js.append(f"const SYNTH_INSTR = {json.dumps(SYNTH_INSTR)};")
js.append("""
const THEMES = {
  context: 'Context engineering (§5.2)',
  evals: 'Evals + verification (§5.5)',
  model: 'Model / provider / routing (§6.4)',
  memory: 'Memory + retrieval (§5.4)',
  multiagent: 'Multi-agent / orchestration (§6.2)',
  loop_harness: 'Loop, tools, durable runtime, safety (§5.1/§5.3/§6.1/§6.3/§4)',
  strategy: 'The bet, non-goals, positioning (§1/§2/§12)',
};

const BATCH_SCHEMA = {
  type: 'object', required: ['sources'], additionalProperties: false,
  properties: { sources: { type: 'array', items: {
    type: 'object', required: ['title','url','status','note_path','themes','top_deltas'], additionalProperties: false,
    properties: {
      title: { type: 'string' }, url: { type: 'string' },
      status: { type: 'string', enum: ['read_full','read_partial','unreachable'] },
      note_path: { type: 'string' },
      themes: { type: 'array', items: { type: 'string', enum: Object.keys(THEMES) } },
      top_deltas: { type: 'array', items: {
        type: 'object', required: ['finding','tag'], additionalProperties: false,
        properties: { finding: { type: 'string' }, tag: { type: 'string', enum: ['CONFIRMS','CONTRADICTS','SHARPENS','NEW-IDEA'] }, prd_section: { type: 'string' } } } },
    } } } },
};

const SYNTH_SCHEMA = {
  type: 'object', required: ['theme','synthesis_path','deltas','resist'], additionalProperties: false,
  properties: {
    theme: { type: 'string' }, synthesis_path: { type: 'string' },
    deltas: { type: 'array', items: {
      type: 'object', required: ['finding','tag','recommendation'], additionalProperties: false,
      properties: { finding: { type: 'string' }, tag: { type: 'string' }, prd_section: { type: 'string' },
        recommendation: { type: 'string', enum: ['adopt-now','lock-defer','sharpen','resist','confirm'] }, source: { type: 'string' } } } },
    resist: { type: 'array', items: { type: 'string' } },
  },
};

function srcLine(s) {
  return '- ' + s.title + '  [' + (s.rating || '-') + ']  <' + s.url + '>\\n' +
         '    meta: ' + (s.meta || '') + '\\n' +
         '    guide-note: ' + (s.note || '') + '\\n' +
         '    WRITE NOTE TO (exact): ' + s.note_path;
}
function readPrompt(batch, idx) {
  return VERSO + '\\n\\n## Your assigned sources (batch ' + idx + ') — read the FULL text of each\\n' +
    batch.map(srcLine).join('\\n\\n') + '\\n\\n## Instructions\\n' + READ_INSTR;
}
function synthPrompt(key, label, notes) {
  const synthPath = OUTDIR + '/_SYNTHESIS_' + key + '.md';
  return VERSO + '\\n\\n## Theme: ' + label + '\\nsynthesis_path (write here): ' + synthPath +
    '\\n\\n## Note files to read (produced by the readers; read each in full)\\n' +
    notes.map(n => '- ' + n.title + '  ->  ' + n.note_path).join('\\n') +
    '\\n\\n## Instructions\\n' + SYNTH_INSTR;
}

phase('Read');
log('WF1: reading ' + BATCHES.flat().length + ' full-text sources across ' + BATCHES.length + ' batches');
const reads = await parallel(BATCHES.map((batch, i) => () =>
  agent(readPrompt(batch, i), { label: 'read:b' + i, phase: 'Read', schema: BATCH_SCHEMA, model: 'sonnet', agentType: 'general-purpose' })
    .catch(() => null)
));
const allSources = reads.filter(Boolean).flatMap(r => r.sources || []);
const unreachable = allSources.filter(s => s.status === 'unreachable');
log('read ' + allSources.length + ' sources; ' + unreachable.length + ' unreachable');

// bucket note paths by theme (only readable notes)
const byTheme = {};
for (const k of Object.keys(THEMES)) byTheme[k] = [];
for (const s of allSources) {
  if (s.status === 'unreachable' || !s.note_path) continue;
  for (const t of (s.themes || [])) if (byTheme[t]) byTheme[t].push({ title: s.title, note_path: s.note_path });
}

phase('Synthesize');
const synth = await parallel(Object.entries(THEMES).map(([key, label]) => () => {
  const notes = byTheme[key];
  if (!notes || notes.length === 0) return Promise.resolve(null);
  return agent(synthPrompt(key, label, notes), { label: 'synth:' + key, phase: 'Synthesize', schema: SYNTH_SCHEMA, agentType: 'general-purpose' })
    .catch(() => null);
}));

return {
  covered: allSources.length,
  unreachable: unreachable.map(s => ({ title: s.title, url: s.url })),
  notes: allSources.map(s => ({ title: s.title, status: s.status, note_path: s.note_path })),
  syntheses: synth.filter(Boolean),
};
""")

(BASE / "wf1.mjs").write_text("\n".join(js), encoding="utf-8")
print(f"wrote wf1.mjs  ({len('chr'.join(js))} chars)")
print(f"batches: {len(batches)}  sources: {sum(len(b) for b in batches)}")
print(f"sample note_path: {batches[0][0]['note_path']}")
