"""Build WF1 target set: all full-text agent/Anthropic/frontier sources, batched for fan-out."""
import json
import re
from pathlib import Path

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
sources = json.loads((BASE / "_sources.json").read_text(encoding="utf-8"))

# Sources already fully read + noted in 08_raw_recheck (clusters 1-4) — exclude from WF1.
ALREADY = {
    "anthropic.com/engineering/effective-harnesses-for-long-running-agents",
    "lucumr.pocoo.org/2025/11/21/agents-are-hard/",
    "ampcode.com/notes/how-to-build-an-agent",
    "anthropic.com/engineering/effective-context-engineering-for-ai-agents",
    "browser-use.com/posts/bitter-lesson-agent-frameworks",
    "ghuntley.com/ralph/",
    "seangoedecke.com/ai-agents-and-code-review/",
    "cursor.com/blog/instant-apply",
    "cursor.com/blog/real-time-rl-for-composer",
    "cognition.ai/blog/dont-build-multi-agents",
    "cognition.ai/blog/multi-agents-working",
    "ysymyth.github.io/the-second-half/",
    "hamel.dev/blog/posts/evals/",
    "latent.space/p/braintrust",
    "hebbia.com/blog/goodbye-rag-how-hebbia-solved-information-retrieval-for-llms",
}
def norm(u): return re.sub(r"^https?://(www\.)?", "", u).rstrip("/").lower()

CORE_SECTIONS = {
    "🔬 Frontier AI Research Taste",
    "🚀 Building Revolutionary Products (primitives, not wrappers)",
    "🛠️ The Modern CTO (director of machines)",
}
ANTH_HOSTS = ("anthropic.com", "transformer-circuits.pub", "darioamodei.com")

def is_anthropic(s):
    return any(h in s["host"] for h in ANTH_HOSTS)

def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]

target, deferred_video, already_hit = [], [], []
for s in sources:
    in_scope_section = s["section"] in CORE_SECTIONS or is_anthropic(s)
    if not in_scope_section:
        continue
    if norm(s["url"]) in ALREADY:
        already_hit.append(s)
        continue
    if s["type"] in ("text", "paper", "repo"):
        s["slug"] = slug(s["title"])
        target.append(s)
    else:
        deferred_video.append(s)

# Batch ~4 deep reads per agent. Keep section grouping where possible by sorting.
target.sort(key=lambda s: (s["section"], s["rating"] != "MUST", s["title"]))
BATCH = 4
batches = [target[i:i+BATCH] for i in range(0, len(target), BATCH)]

out = {
    "outdir": str(BASE / "notes"),
    "batches": [[{k: s[k] for k in ("section","title","url","host","rating","meta","note","slug")} for s in b] for b in batches],
}
(BASE / "wf1_batches.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

# also persist the deferred-video list so coverage is auditable (no silent drops)
(BASE / "wf1_deferred_video.json").write_text(
    json.dumps([{k: s[k] for k in ("section","title","url","rating","meta")} for s in deferred_video], indent=2, ensure_ascii=False),
    encoding="utf-8")

print(f"WF1 TARGET (full-text, agent/Anthropic/frontier): {len(target)} sources in {len(batches)} batches of ~{BATCH}")
print(f"  already-noted (excluded): {len(already_hit)}")
print(f"  video/AV in these sections (DEFERRED to WF2, logged): {len(deferred_video)}")
from collections import Counter
print(f"\nTarget by section: {dict(Counter(s['section'] for s in target))}")
print(f"Target by rating:  {dict(Counter(s['rating'] or '-' for s in target))}")
print(f"Target hosts (top): {dict(Counter(s['host'] for s in target).most_common(18))}")
print("\nFirst 3 batches preview:")
for bi, b in enumerate(batches[:3]):
    print(f"  batch {bi}: " + " | ".join(f"[{s['rating'] or '-'}] {s['title'][:42]}" for s in b))
