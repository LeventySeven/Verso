# tests/test_skills_scaffolds.py
from verso import Scaffold, find_scaffolds, load_skills
from verso.memory.store import Memory
from verso.memory.types import MemoryType
from verso.scaffolds import _SCAFFOLD_RE


# --- load_skills -------------------------------------------------------------

async def test_load_skills_renders_permanent_records_under_header():
    m = Memory.sqlite(path=":memory:", scope="proj", clock=lambda: 1000.0)
    await m.remember("prefer pgbouncer for pooling", type=MemoryType.FACT, importance=0.9)
    await m.remember("run migrations before deploy", type=MemoryType.PROCEDURAL, importance=0.9)

    prefix = await load_skills(m, scope="proj")
    assert prefix.startswith("Learned context (from memory):")
    assert "- prefer pgbouncer for pooling" in prefix
    assert "- run migrations before deploy" in prefix


async def test_load_skills_empty_memory_is_byte_identical_empty_string():
    m = Memory.sqlite(path=":memory:", scope="proj", clock=lambda: 1000.0)
    base = "You are a helpful agent."
    assert await load_skills(m, scope="proj") == ""        # byte-identical-when-empty
    assert base + await load_skills(m, scope="proj") == base


async def test_load_skills_defaults_scope_to_memory_scope_and_filters_types():
    m = Memory.sqlite(path=":memory:", scope="proj", clock=lambda: 1000.0)
    await m.remember("durable fact", type=MemoryType.FACT, importance=0.9)
    await m.remember("ephemeral note", type=MemoryType.EPISODIC, importance=0.9)

    prefix = await load_skills(m)                            # scope=None -> memory.scope ("proj")
    assert "durable fact" in prefix
    assert "ephemeral note" not in prefix                    # EPISODIC excluded by default types

    # a different scope sees nothing -> empty string
    assert await load_skills(m, scope="other") == ""


async def test_load_skills_respects_limit():
    m = Memory.sqlite(path=":memory:", scope="proj", clock=lambda: 1000.0)
    for i in range(5):
        await m.remember(f"fact {i}", type=MemoryType.FACT, importance=0.5)
    prefix = await load_skills(m, scope="proj", limit=2)
    assert prefix.count("\n- ") == 2                         # header + 2 bullets -> 2 "\n- " joins


# --- scaffolds ---------------------------------------------------------------

def test_find_scaffolds_returns_the_tagged_jsonish_scaffold():
    scaffolds = find_scaffolds("verso")
    assert scaffolds, "expected at least one tagged scaffold in the verso package"
    assert all(isinstance(s, Scaffold) for s in scaffolds)

    hit = next((s for s in scaffolds if s.weakness == "malformed-json"), None)
    assert hit is not None, "the jsonish lenient-fallback scaffold should be found"
    assert hit.file.endswith("verso/tools/jsonish.py")
    assert hit.line > 0
    assert "lenient" in hit.note

    # sorted by (file, line)
    assert scaffolds == sorted(scaffolds, key=lambda s: (s.file, s.line))


def test_find_scaffolds_parses_a_temp_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text(
        "x = 1\n"
        "    # SCAFFOLD(flaky-tool): retry budget compensates for tools that loop\n"
        "y = 2\n",
        encoding="utf-8",
    )
    scaffolds = find_scaffolds(str(tmp_path))
    assert len(scaffolds) == 1
    s = scaffolds[0]
    assert s.weakness == "flaky-tool"
    assert s.note == "retry budget compensates for tools that loop"
    assert s.line == 2
    assert s.file.endswith("sample.py")


def test_scaffold_regex_ignores_non_scaffold_comments():
    assert _SCAFFOLD_RE.search("# just a normal comment") is None
    assert _SCAFFOLD_RE.search("# SCAFFOLDING is a word, not the tag") is None
    m = _SCAFFOLD_RE.search("    foo()  # SCAFFOLD(x): trailing-code form")
    assert m and m.group("weakness") == "x" and m.group("note") == "trailing-code form"
