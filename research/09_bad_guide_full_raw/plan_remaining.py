"""Bucket ALL 319 sources into sequenced workflows so coverage is auditable (no silent drops)."""
import json, re
from pathlib import Path
from collections import Counter

BASE = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw")
sources = json.loads((BASE / "_sources.json").read_text(encoding="utf-8"))
wf1 = json.loads((BASE / "wf1_batches.json").read_text(encoding="utf-8"))
wf1_urls = {s["url"] for b in wf1["batches"] for s in b}

CORE = {
    "🔬 Frontier AI Research Taste",
    "🚀 Building Revolutionary Products (primitives, not wrappers)",
    "🛠️ The Modern CTO (director of machines)",
}
ANTH = ("anthropic.com", "transformer-circuits.pub", "darioamodei.com")
def is_anth(s): return any(h in s["host"] for h in ANTH)
TEXT = ("text", "paper", "repo")

buckets = {"WF1_running": [], "WF1_already_noted": [], "WF2_core_AV": [], "WF3_rest_text": [], "WF4_rest_AV": []}
for s in sources:
    core = s["section"] in CORE or is_anth(s)
    if s["url"] in wf1_urls:
        buckets["WF1_running"].append(s); continue
    if core and s["type"] in TEXT:
        buckets["WF1_already_noted"].append(s)  # in-scope text but excluded => already noted in clusters 1-4
    elif core:
        buckets["WF2_core_AV"].append(s)
    elif s["type"] in TEXT:
        buckets["WF3_rest_text"].append(s)
    else:
        buckets["WF4_rest_AV"].append(s)

for name in ("WF2_core_AV", "WF3_rest_text", "WF4_rest_AV"):
    (BASE / f"{name}.json").write_text(
        json.dumps([{k: s[k] for k in ("section","title","url","host","rating","meta","type","note")} for s in buckets[name]],
                   ensure_ascii=False, indent=2), encoding="utf-8")

total = sum(len(v) for v in buckets.values())
print(f"TOTAL sources accounted for: {total} (manifest: {len(sources)})  -> {'OK no drops' if total==len(sources) else 'MISMATCH'}")
print()
print(f"{'bucket':22} {'n':>4}   contents")
print("-"*78)
desc = {
 "WF1_running":      "50 full-text agent/Anthropic/frontier  [RUNNING NOW]",
 "WF1_already_noted":"already fully read+noted in clusters 1-4 (08_raw_recheck)",
 "WF2_core_AV":      "video/podcast in the 3 technical sections (transcript-hunt)",
 "WF3_rest_text":    "full-text: Product/Founder/Design/Distribution/GTM/Leverage/YC",
 "WF4_rest_AV":      "video/podcast in those 7 sections (transcript-hunt)",
}
for name, items in buckets.items():
    print(f"{name:22} {len(items):>4}   {desc[name]}")
print()
print("WF3 (rest-text) by section:")
for sec, n in Counter(s["section"] for s in buckets["WF3_rest_text"]).most_common():
    print(f"   {n:3}  {sec}")
