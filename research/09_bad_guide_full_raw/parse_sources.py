"""Parse BAD_GUIDE.md into a structured source manifest (no summaries lost)."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

SRC = Path("/Users/seventyleven/Desktop/BAD_GUIDE.md")
OUT = Path("/Users/seventyleven/Desktop/Verso/research/09_bad_guide_full_raw/_sources.json")

lines = SRC.read_text(encoding="utf-8").splitlines()

# A source bullet: - **[Title](URL)** — *meta* · `RATING`
BULLET = re.compile(r"^\s*-\s*\*\*\[(?P<title>.+?)\]\((?P<url>https?://[^)]+)\)\*\*\s*(?:—\s*\*(?P<meta>.+?)\*)?(?:\s*·\s*`(?P<rating>[A-Z]+)`)?\s*$")
H2 = re.compile(r"^##\s+(?P<title>.+?)\s*$")

def classify(url: str, meta: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    m = (meta or "").lower()
    if "arxiv.org" in host:
        return "paper"
    if "youtube.com" in host or "youtu.be" in host:
        return "video"
    if any(k in m for k in ("podcast", "talk", "video", "interview", "course", "keynote", "lecture")):
        return "av"
    if any(k in m for k in ("essay", "article", "blog", "paper", "book", "playbook", "gallery", "publication", "repo", "manifesto", "post", "guide")):
        return "text"
    # default by host
    if host in ("github.com",):
        return "repo"
    return "text"

sources = []
section = None
i = 0
while i < len(lines):
    line = lines[i]
    h = H2.match(line)
    if h:
        section = h.group("title").strip()
        i += 1
        continue
    b = BULLET.match(line)
    if b and section:
        # capture the description = following indented non-empty line(s) until blank or next bullet
        desc_parts = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.strip() == "" or BULLET.match(nxt) or nxt.startswith("#") or re.match(r"^\s*-\s", nxt):
                break
            desc_parts.append(nxt.strip())
            j += 1
        url = b.group("url")
        meta = (b.group("meta") or "").strip()
        sources.append({
            "section": section,
            "title": b.group("title").strip(),
            "url": url,
            "host": (urlparse(url).hostname or "").lower().replace("www.", ""),
            "meta": meta,
            "rating": b.group("rating") or "",
            "type": classify(url, meta),
            "note": " ".join(desc_parts)[:600],
        })
        i = j
        continue
    i += 1

# de-dupe by (url) keeping first occurrence's section, but record all sections it appears in
seen = {}
for s in sources:
    key = s["url"]
    if key not in seen:
        seen[key] = s
        s["also_in"] = []
    else:
        if s["section"] not in (seen[key]["section"], *seen[key]["also_in"]):
            seen[key]["also_in"].append(s["section"])
deduped = list(seen.values())

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")

# ---- report ----
from collections import Counter
by_section = Counter(s["section"] for s in deduped)
by_type = Counter(s["type"] for s in deduped)
by_rating = Counter(s["rating"] or "-" for s in deduped)
anthropic = [s for s in deduped if "anthropic.com" in s["host"] or "transformer-circuits" in s["host"] or "darioamodei" in s["host"]]

print(f"TOTAL unique sources: {len(deduped)}  (raw bullets: {len(sources)})")
print(f"\nBY TYPE: {dict(by_type)}")
print(f"\nBY RATING: {dict(by_rating)}")
print(f"\nANTHROPIC-family sources: {len(anthropic)}")
for s in anthropic:
    print(f"   [{s['rating'] or '-':4}] {s['title'][:70]}  <{s['host']}>")
print(f"\nBY SECTION:")
for sec, n in by_section.most_common():
    print(f"   {n:3}  {sec}")
print(f"\nFully-readable TEXT/PAPER/REPO sources: {sum(by_type[t] for t in ('text','paper','repo'))}")
print(f"VIDEO/AV sources (limited via fetch): {sum(by_type[t] for t in ('video','av'))}")
