#!/usr/bin/env python3
"""One claim, N renderings, one gate.

Every claim in this repository already exists at several bandwidths: the
registry record, a film, a device record, a page. Each surface has its own
gate — the film a receipt, the device an audit, the page a drift check — and
not one of them knows the others exist. ``verify_facts.py`` binds numerals
*within* a page. Nothing binds them *across* surfaces: change a claim's
identified set and the film, the device record and the screening-room card
keep saying the old number, each passing its own gate.

``spine.yaml`` declares the renderings, the claims each one asserts, where
its text lives, the numerals it speaks — as phrasings with ``{key}``
placeholders, so the spine carries no second copy of any value — and the
strongest sentence it says out loud. This script enforces four rules:

  S1  Numeral agreement. Every phrasing a rendering is declared to speak
      must occur in the rendering, and every numeral it carries must equal
      the key it names in the claim's ``expected`` block, or a derivation
      shown in ``spine.yaml``. A phrasing that names no key fails. A
      phrasing the rendering no longer says fails. On hand-authored prose
      (``sweep: true`` sources) every other numeral must be either bound or
      excused with a reason: an unbound numeral fails.
  S2  No rendering outruns the claim. A rendering may not introduce a
      scope-widening token from the lexicon in ``spine.yaml`` that the
      claim's own proposition and scope never use affirmatively. Lexical
      and crude, and it fires on the failure this program says it fears:
      the explanation outrunning the weakest surviving sentence.
  S3  Non-claims travel. Every rendering carries each asserted claim's
      non-claims, verbatim, in the same artifact.
  S4  Coverage is reported, never optimised. Renderings per claim are
      printed. The number is a fact about the repository, not a target.

``--check`` runs S1–S3 and prints S4. ``--explain CLAIM`` prints every
rendering of one claim and its agreement. ``--test`` runs the adversarial
fixtures: in memory it moves every value every rendering speaks and
confirms that rendering fails, injects a widening token and confirms S2
fires, drops a non-claim and confirms S3 fires — because a gate nobody has
watched fail is not a gate. ``--mutate CLAIM.key=value`` applies one live
mutation to the loaded registry and runs the check, so the failure can be
watched on the real renderings.

Exit 1 on any failure. A green spine means the renderings agree with each
other; it says nothing about whether any claim is true.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import html as html_lib
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-9

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20,
}
NUM_WORDS = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
NUM = rf"(?:\d+(?:\.\d+)?|{NUM_WORDS})"
# A numeral token in prose: digits with an optional decimal part, or a
# spelled-out number, standing alone (a decimal's fractional part is not a token). "one" is left out of the sweep — it is
# an article or a pronoun far more often than a count — and that is stated
# here rather than hidden in the lexicon.
SWEEP_WORDS = "|".join(w for w in sorted(WORD_NUMBERS, key=len, reverse=True) if w != "one")
SWEEP_TOKEN = re.compile(rf"(?<!\w)(?<!\d\.)(\d+(?:\.\d+)?|{SWEEP_WORDS})(?![\w])", re.I)
CLAIM_ID = re.compile(r"^[A-Z]{2,4}-\d{3}$")
# Numerals that are never claim quantities: identifiers, dates, hashes,
# versions, clock times, powers. Blanked before the sweep.
NOT_A_QUANTITY = [
    re.compile(r"\b[A-Z]{2,4}-\d{3}\b"),                   # claim ids
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:]+Z?)?\b"),    # ISO dates
    re.compile(r"\b(?:19|20)\d{2}\b"),                     # years
    re.compile(r"\b[0-9a-f]{7,}\b"),                       # hashes
    re.compile(r"\bv?\d+\.\d+\.\d+\b"),                    # versions
    re.compile(r"\b\d{1,2}:\d{2}\b"),                      # clock times
    re.compile(r"\b\d+\^\d+\b"),                           # powers
    re.compile(r"\b[A-Z]-\d{3}\b"),                        # device ids
]
TRANSLATE = str.maketrans({
    "–": "-", "—": "-", "−": "-", "‑": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
})
SEP = " ¶ "


# ------------------------------------------------------------------ text
def norm(text: str) -> str:
    """One normal form for templates and renderings alike.

    NFKC folds the ellipsis and full-width forms; dashes and quotes are
    unified; whitespace collapses. Both sides pass through this, so a
    template written with an em-dash matches a rendering typed with a
    hyphen, and neither side has to guess which the other used.
    """
    t = unicodedata.normalize("NFKC", text).translate(TRANSLATE)
    return re.sub(r"\s+", " ", t).strip()


def visible_text(html_text: str) -> str:
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_text)
    t = re.sub(r"<[^>]+>", " ", t)
    return html_lib.unescape(t)


def yaml_strings(node) -> list[str]:
    """Every scalar string in a YAML tree, in document order."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in yaml_strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in yaml_strings(v)]
    return []


def yaml_field(node, path: str) -> list[str]:
    """Strings at a dotted path; ``[]`` descends a list, ``*`` every key."""
    nodes = [node]
    for part in path.split("."):
        nxt = []
        for n in nodes:
            if part.endswith("[]"):
                seq = n.get(part[:-2], []) if isinstance(n, dict) else []
                nxt.extend(seq if isinstance(seq, list) else [])
            elif part == "*":
                nxt.extend(n.values() if isinstance(n, dict) else [])
            elif isinstance(n, dict) and part in n:
                nxt.append(n[part])
        nodes = nxt
    return [s for n in nodes for s in yaml_strings(n)]


def select_record(data, selector: str | None):
    """``devices[id=D-006]`` → the item of ``data['devices']`` whose id matches."""
    if not selector:
        return data
    m = re.fullmatch(r"(\w+)\[(\w+)=([^\]]+)\]", selector)
    if not m:
        raise ValueError(f"unreadable selector {selector!r}")
    key, field, value = m.groups()
    for item in data.get(key, []):
        if str(item.get(field)) == value:
            return item
    raise KeyError(f"selector {selector!r} matches nothing")


def as_number(token: str) -> float | int | None:
    t = token.strip().lower()
    if t in WORD_NUMBERS:
        return WORD_NUMBERS[t]
    try:
        return int(t) if re.fullmatch(r"\d+", t) else float(t)
    except ValueError:
        return None


def literal_regex(text: str) -> str:
    """A normalized literal, with each whitespace run matching any run or none."""
    return r"\s*".join(re.escape(x) for x in norm(text).split(" "))


# ---------------------------------------------------------------- template
def template_regex(template: str) -> tuple[re.Pattern, list[str]]:
    """``'{key} worlds'`` → a regex capturing one numeral per placeholder.

    ``{{`` and ``}}`` are literal braces. Whitespace in the template matches
    any run of whitespace, including none, so ``{0 ... 12}`` and ``{0...12}``
    are the same phrasing.
    """
    parts = re.split(r"(\{\{|\}\}|\{[^{}]+\})", norm(template))
    out: list[str] = []
    keys: list[str] = []
    for p in parts:
        if p == "{{":
            out.append(re.escape("{"))
        elif p == "}}":
            out.append(re.escape("}"))
        elif p.startswith("{") and p.endswith("}"):
            keys.append(p[1:-1].strip())
            out.append(rf"(?<!\w)(?<!\d\.)({NUM})(?![\w])")
        elif p:
            # not literal_regex(): a fragment's leading or trailing space is
            # the seam between a numeral and a word, and must survive
            out.append(r"\s*".join(re.escape(x) for x in p.split(" ")))
    if not keys:
        raise ValueError(f"phrasing {template!r} names no key")
    return re.compile("".join(out), re.I), keys


# ---------------------------------------------------------------- registry
class Registry:
    """claims.yaml ``expected`` blocks, the census arithmetic, and the
    derivations spine.yaml shows out loud."""

    ID_IN_EXPR = re.compile(r"[A-Z]{2,4}-\d{3}(?:\.[\w-]+)+")
    FUNCS = {"round": round, "min": min, "max": max, "abs": abs, "len": len}

    def __init__(self, claims: dict, derived: dict[str, str]):
        self.claims = claims
        self.derived = derived
        self._census: dict | None = None

    def census(self) -> dict:
        """MC-001's quantities are computed from census.yaml by the one
        arithmetic the site already trusts (scripts/facts.registry)."""
        if self._census is None:
            sys.path.insert(0, str(ROOT / "scripts"))
            import facts  # noqa: E402
            self._census = facts.registry()
        return self._census

    def lookup(self, full: str):
        if full in self.derived:
            return self.evaluate(self.derived[full])
        cid, _, path = full.partition(".")
        if cid not in self.claims:
            raise KeyError(f"{full}: no claim {cid}")
        node = self.claims[cid].get("expected")
        try:
            if node is None:
                raise KeyError
            for part in path.split("."):
                if isinstance(node, list):
                    node = node[int(part)]
                elif isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    raise KeyError
            return node
        except (KeyError, IndexError, ValueError):
            if cid == "MC-001" and full in self.census():
                return self.census()[full]
            raise KeyError(f"{full}: no such key under {cid}.expected"
                           + (" or the census registry" if cid == "MC-001" else ""))

    def resolve(self, key: str, claim_id: str) -> tuple[str, float]:
        full = key if CLAIM_ID.match(key.split(".", 1)[0]) else f"{claim_id}.{key}"
        value = self.lookup(full)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{full} is {type(value).__name__}, not a numeral")
        return full, value

    def inputs(self, full: str) -> set[str]:
        """The raw registry keys a key depends on (itself, when it is raw)."""
        if full not in self.derived:
            return {full}
        out: set[str] = set()
        for m in self.ID_IN_EXPR.finditer(self.derived[full]):
            out |= self.inputs(m.group(0))
        return out

    def evaluate(self, expr: str):
        """A derivation: arithmetic over registry ids and nothing else."""
        values: list = []

        def sub(m: re.Match) -> str:
            values.append(self.lookup(m.group(0)))
            return f"_v[{len(values) - 1}]"
        tree = ast.parse(self.ID_IN_EXPR.sub(sub, expr), mode="eval")
        allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call,
                   ast.Name, ast.Load, ast.Subscript, ast.Add, ast.Sub, ast.Mult,
                   ast.Div, ast.Pow, ast.USub, ast.Tuple)
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise ValueError(f"derivation {expr!r} uses {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id != "_v" and node.id not in self.FUNCS:
                raise ValueError(f"derivation {expr!r} names {node.id!r}")
        return eval(compile(tree, "<derivation>", "eval"),  # noqa: S307 — AST whitelisted above
                    {"__builtins__": {}}, {"_v": values, **self.FUNCS})


# ---------------------------------------------------------------- sources
class Source:
    """One place a rendering's text lives, resolved to normalized text.

    ``text`` is what S1 and S2 read (the declared fields or region);
    ``artifact`` is what S3 reads (the whole record or page).
    """

    def __init__(self, spec: dict, root: Path, claim: dict | None):
        self.spec = spec
        self.kind = spec["kind"]
        self.path = spec.get("path")
        self.sweep = bool(spec.get("sweep", False))
        self.notes: list[str] = []
        self.text, self.artifact = self._load(root, claim)

    def where(self) -> str:
        if self.kind == "claim_fields":
            return f"claims.yaml:{'/'.join(self.spec['fields'])}"
        return f"{self.path}" + (f" [{self.spec['select']}]" if self.spec.get("select") else "")

    def _load(self, root: Path, claim: dict | None) -> tuple[str, str]:
        s = self.spec
        if self.kind == "claim_fields":
            if claim is None:
                raise ValueError("claim_fields source needs a claim")
            text = " ".join(str(claim[f]) for f in s["fields"])
            return norm(text), norm(" ".join(yaml_strings(claim)))
        p = root / self.path
        if not p.exists():
            raise FileNotFoundError(f"{self.path} does not exist")
        if self.kind == "yaml":
            record = select_record(yaml.safe_load(p.read_text(encoding="utf-8")), s.get("select"))
            fields = s.get("fields")
            text = " ".join(x for f in fields for x in yaml_field(record, f)) if fields \
                else " ".join(yaml_strings(record))
            return norm(text), norm(" ".join(yaml_strings(record)))
        if self.kind == "html":
            raw = p.read_text(encoding="utf-8")
            region = raw
            if s.get("region_start"):
                start = raw.find(s["region_start"])
                if start < 0:
                    raise ValueError(f"{self.path}: region start {s['region_start']!r} not found")
                end = raw.find(s["region_end"], start + len(s["region_start"])) if s.get("region_end") else -1
                region = raw[start:end if end >= 0 else len(raw)]
            return norm(visible_text(region)), norm(visible_text(raw))
        if self.kind == "text":
            raw = p.read_text(encoding="utf-8")
            return norm(raw), norm(raw)
        if self.kind == "world_labels":
            receipt = json.loads(p.read_text(encoding="utf-8"))
            prefix = s.get("prefix", "")
            bodies = [lbl["body"] for lbl in receipt["labels"] if lbl["name"].startswith(prefix)]
            if not bodies:
                raise ValueError(f"{self.path}: no labels with prefix {prefix!r}")
            blend = Path(receipt["blend"]["path"])
            blend = blend if blend.is_absolute() else root.parent / blend
            if blend.exists():
                digest = hashlib.sha256(blend.read_bytes()).hexdigest()
                if digest != receipt["blend"]["sha256"]:
                    raise ValueError(f"{self.path}: the world file changed since the receipt "
                                     f"({digest[:12]} != {receipt['blend']['sha256'][:12]}); re-probe")
                self.notes.append(f"world file present; sha256 matches the receipt ({digest[:12]})")
            else:
                self.notes.append("world file not present on this host; labels taken as the receipt recorded them")
            text = " | ".join(bodies)
            return norm(text), norm(text)
        raise ValueError(f"unknown source kind {self.kind!r}")


# ---------------------------------------------------------------- spine
def load_spine(root: Path) -> dict:
    return yaml.safe_load((root / "spine.yaml").read_text(encoding="utf-8"))


def load_claims(root: Path) -> dict:
    data = yaml.safe_load((root / "claims.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["claims"]}


class Rendering:
    def __init__(self, spec: dict, root: Path, claims: dict):
        self.id = spec["id"]
        self.surface = spec["surface"]
        self.claim_ids: list[str] = list(spec["claims"])
        self.primary = self.claim_ids[0]
        self.spec = spec
        self.sources = [Source(s, root, claims.get(s.get("claim", self.primary))) for s in spec["sources"]]
        self.rebuild()
        self.bound: dict[str, tuple] = {}   # full key -> (spoken, expected)

    def rebuild(self) -> None:
        self.text = SEP.join(s.text for s in self.sources)
        self.artifact = SEP.join(s.artifact for s in self.sources)

    def label(self) -> str:
        return f"{self.surface}:{self.id} [{', '.join(self.claim_ids)}]"


# ---------------------------------------------------------------- lexicon
class Lexicon:
    def __init__(self, spec: dict):
        self.wideners = [norm(w).lower() for w in spec["scope_wideners"]]
        self.negations = [norm(w).lower() for w in spec["negation_cues"]]
        self.proper_nouns = [norm(w) for w in spec.get("proper_nouns", [])]
        self._widener_re = {w: re.compile(rf"(?<!\w){literal_regex(w)}(?!\w)", re.I) for w in self.wideners}
        self._negation_re = re.compile(
            r"(?<!\w)(?:" + "|".join(literal_regex(n) for n in self.negations) + r")(?!\w)", re.I)

    def blank_proper_nouns(self, text: str) -> str:
        for noun in self.proper_nouns:
            text = re.sub(re.escape(noun), " " * len(noun), text, flags=re.I)
        return text

    @staticmethod
    def sentences(text: str) -> list[str]:
        # Crude on purpose: split at sentence punctuation, semicolons, spaced
        # dashes and source seams. A finer parser would be a second thing to trust.
        return [s for s in re.split(r"(?<=[.;!?])\s+|\s+-\s+|\s*¶\s*|\s*\|\s*", text) if s.strip()]

    def affirmative_hits(self, text: str) -> dict[str, str]:
        """widener → the first affirmative sentence it appears in."""
        hits: dict[str, str] = {}
        for sentence in self.sentences(self.blank_proper_nouns(text)):
            if self._negation_re.search(sentence):
                continue
            for w, rx in self._widener_re.items():
                if w not in hits and rx.search(sentence):
                    hits[w] = sentence.strip()
        return hits


# ---------------------------------------------------------------- checks
class Spine:
    def __init__(self, root: Path, claims: dict | None = None, spine: dict | None = None):
        self.root = root
        self.spine = spine or load_spine(root)
        self.claims = claims or load_claims(root)
        self.registry = Registry(self.claims, self.spine.get("derived", {}))
        self.lexicon = Lexicon(self.spine["lexicon"])
        self.renderings: list[Rendering] = []
        self.load_errors: list[str] = []
        for spec in self.spine["renderings"]:
            missing = [c for c in spec["claims"] if c not in self.claims]
            if missing:
                self.load_errors.append(f"{spec['surface']}:{spec['id']} asserts {missing}, not in claims.yaml")
                continue
            try:
                self.renderings.append(Rendering(spec, root, self.claims))
            except Exception as exc:  # a rendering whose source is gone is a failure, not a crash
                self.load_errors.append(f"{spec.get('surface')}:{spec.get('id')}: {exc}")
        # An exclusion is a finding about an artifact; the artifact's receipt
        # is still loaded, so the finding cannot outlive the thing it is about.
        self.excluded: dict[str, Source] = {}
        for x in self.spine.get("not_renderings", []):
            try:
                self.excluded[x["id"]] = Source(x["source"], root, None)
            except Exception as exc:
                self.load_errors.append(f"excluded {x['id']}: {exc}")

    def find(self, rid: str) -> Rendering:
        return next(r for r in self.renderings if r.id == rid)

    # -- S1 -------------------------------------------------------------
    def s1(self, r: Rendering) -> list[str]:
        failures: list[str] = []
        spans: list[tuple[int, int]] = []
        r.bound = {}
        for phrase in r.spec.get("speaks", []):
            template = phrase["says"]
            try:
                rx, keys = template_regex(template)
                resolved = [self.registry.resolve(k, r.primary) for k in keys]
            except (KeyError, TypeError, ValueError) as exc:
                failures.append(f"S1 {r.label()}: phrasing {template!r} does not resolve — {exc}")
                continue
            matches = list(rx.finditer(r.text))
            if not matches:
                failures.append(f"S1 {r.label()}: no longer says {template!r} — the spine is stale "
                                f"or the rendering changed what it says")
                continue
            for m in matches:
                spans.append(m.span())
                for (full, expected), token in zip(resolved, m.groups()):
                    spoken = as_number(token)
                    r.bound.setdefault(full, (spoken, expected))
                    if spoken is None or abs(spoken - expected) > TOL:
                        failures.append(
                            f"S1 {r.label()}: says {token!r} where {full} = {expected} — "
                            f"…{r.text[max(0, m.start() - 40):m.end() + 40]}…")
        excused = []
        for item in r.spec.get("unbound_ok", []):
            rx = re.compile(item["pattern"], re.I) if "pattern" in item else re.compile(literal_regex(item["says"]), re.I)
            excused.append(rx)
        offset = 0
        for src in r.sources:
            seg = src.text
            if src.sweep:
                blanked = seg
                for rx in NOT_A_QUANTITY:
                    blanked = rx.sub(lambda m: " " * len(m.group(0)), blanked)
                excused_spans = [m.span() for rx in excused for m in rx.finditer(blanked)]
                for m in SWEEP_TOKEN.finditer(blanked):
                    a, b = m.start() + offset, m.end() + offset
                    if any(s <= a and b <= e for s, e in spans):
                        continue
                    if any(s <= m.start() and m.end() <= e for s, e in excused_spans):
                        continue
                    failures.append(
                        f"S1 {r.label()}: unbound numeral {m.group(1)!r} in {src.where()} — "
                        f"…{seg[max(0, m.start() - 50):m.end() + 50]}… (bind it to a key or excuse it with a reason)")
            offset += len(seg) + len(SEP)
        strongest = r.spec.get("strongest")
        if strongest and norm(strongest).lower() not in r.text.lower():
            failures.append(f"S1 {r.label()}: the declared strongest sentence is not in the rendering: {strongest!r}")
        return failures

    # -- S2 -------------------------------------------------------------
    def licensed(self, claim_id: str) -> set[str]:
        c = self.claims[claim_id]
        own = norm(" ".join(str(c.get(f, "")) for f in ("proposition", "scope")))
        return set(self.lexicon.affirmative_hits(own))

    def s2(self, r: Rendering) -> list[str]:
        failures = []
        hits = self.lexicon.affirmative_hits(r.text)
        for cid in r.claim_ids:
            licensed = self.licensed(cid)
            for token, sentence in hits.items():
                if token not in licensed:
                    failures.append(f"S2 {r.label()}: speaks {token!r}, which {cid}'s own text never "
                                    f"licenses — “{sentence[:160]}”")
        return failures

    # -- S3 -------------------------------------------------------------
    def s3(self, r: Rendering) -> list[str]:
        failures = []
        artifact = r.artifact.lower()
        for cid in r.claim_ids:
            for nc in self.claims[cid].get("non_claims", []):
                if norm(nc).lower() not in artifact:
                    failures.append(f"S3 {r.label()}: does not carry {cid} non-claim “{norm(nc)[:90]}…”")
        return failures

    # -- S4 -------------------------------------------------------------
    def coverage(self) -> list[tuple[str, int, list[str], list[str]]]:
        """Per claim: renderings binding at least one of its numerals, and
        film manifests whose evidence binds it outside the spine."""
        elsewhere: dict[str, set[str]] = {}
        for mpath in sorted((self.root / "films").glob("*/manifest.yaml")):
            m = yaml.safe_load(mpath.read_text(encoding="utf-8"))
            for e in m.get("evidence", []):
                cid = str(e.get("fact", "")).split(".", 1)[0]
                elsewhere.setdefault(cid, set()).add(mpath.parent.name)
        registered = {r.id for r in self.renderings}
        rows = []
        for cid in self.claims:
            mine = [r for r in self.renderings if cid in r.claim_ids and r.surface != "registry"
                    and any(k.startswith(cid + ".") for k in r.bound)]
            films = sorted(f for f in elsewhere.get(cid, set()) if f not in registered)
            rows.append((cid, len(mine), [f"{r.surface}:{r.id}" for r in mine], films))
        return rows

    def run(self) -> list[str]:
        failures = list(self.load_errors)
        for r in self.renderings:
            failures += self.s1(r) + self.s2(r) + self.s3(r)
        return failures


# ---------------------------------------------------------------- output
def print_coverage(spine: Spine) -> None:
    print("S4    renderings per claim — a fact about the repository, not a target")
    for cid, n, labels, films in spine.coverage():
        extra = f"   (bound by film evidence outside the spine: {', '.join(films)})" if films else ""
        print(f"      {cid:<9} {n:>2}  {', '.join(labels)}{extra}")
    for x in spine.spine.get("not_renderings", []):
        print(f"      excluded  {x['id']} — {x['finding']}")


def explain(spine: Spine, claim_id: str) -> int:
    if claim_id not in spine.claims:
        print(f"FAIL  {claim_id} is not in claims.yaml")
        return 1
    c = spine.claims[claim_id]
    print(f"{claim_id} — {' '.join(str(c['proposition']).split())[:160]}…")
    print(f"licensed scope tokens: {sorted(spine.licensed(claim_id)) or '—'}")
    failures = []
    for r in [r for r in spine.renderings if claim_id in r.claim_ids]:
        f = spine.s1(r) + spine.s2(r) + spine.s3(r)
        failures += f
        print(f"\n[{r.surface}] {r.id}  ·  {'; '.join(s.where() for s in r.sources)}")
        for s in r.sources:
            for note in s.notes:
                print(f"    note: {note}")
        if r.spec.get("strongest"):
            print(f"    strongest: “{norm(r.spec['strongest'])}”")
        for full, (spoken, expected) in sorted(r.bound.items()):
            mark = "=" if spoken is not None and abs(spoken - expected) <= TOL else "≠"
            print(f"    {full:<56} says {spoken!s:>7} {mark} {expected}")
        carried = sum(norm(nc).lower() in r.artifact.lower() for nc in c.get("non_claims", []))
        print(f"    non-claims carried: {carried}/{len(c.get('non_claims', []))}")
        for line in f:
            print(f"    FAIL {line}")
    for x in spine.spine.get("not_renderings", []):
        if claim_id in x.get("named_for", []):
            print(f"\n[excluded] {x['id']}  ·  {x['source']['path']}")
            src = spine.excluded.get(x["id"])
            if src is not None:
                for note in src.notes:
                    print(f"    note: {note}")
                print(f"    labels: {src.text[:200]}")
            print(f"    finding: {norm(x['finding'])}")
    print()
    print_coverage(spine)
    return 1 if failures else 0


# ---------------------------------------------------------------- fixtures
def set_key(claims: dict, full: str, value) -> None:
    cid, _, path = full.partition(".")
    node = claims[cid]["expected"]
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def run_tests(root: Path) -> list[str]:
    failures: list[str] = []
    base = Spine(root)

    def check(name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"ok    fixture: {name}")
        else:
            failures.append(f"fixture {name} failed{': ' + detail if detail else ''}")

    live = base.run()
    check("the live spine is green before any mutation", not live, "; ".join(live[:3]))
    if live:
        return failures

    # 1. Every registry value every rendering speaks: move it, and that
    #    rendering must fail, while a rendering that never speaks it must
    #    not. Run on every key rather than one, so no surface is exempt.
    for r in base.renderings:
        for full, (spoken, expected) in sorted(r.bound.items()):
            if full in base.registry.derived or full.startswith("MC-001."):
                continue  # derived and census values move through their inputs
            moved = copy.deepcopy(base.claims)
            set_key(moved, full, expected + 1)
            mutated = Spine(root, claims=moved, spine=base.spine)
            target = mutated.find(r.id)
            check(f"{r.label()} fails when {full} moves {expected}→{expected + 1}",
                  any(f"where {full} =" in f for f in mutated.s1(target)))
            silent = [o for o in base.renderings
                      if not any(full in base.registry.inputs(k) for k in o.bound)]
            if silent:
                other = mutated.find(silent[0].id)
                check(f"  and {other.label()}, which never speaks {full.split('.', 1)[1]}, stays green",
                      not mutated.s1(other), "; ".join(mutated.s1(other)[:2]))

    # 2. The brief's acceptance test, in memory: move the identified set's
    #    upper endpoint and its size; every surface that speaks it must fail.
    for full, new, need in (("MC-003.identified_set_upper", 13, {"film", "device", "page", "registry"}),
                            ("MC-003.identified_set_size", 14, {"film", "device", "page"})):
        moved = copy.deepcopy(base.claims)
        set_key(moved, full, new)
        mutated = Spine(root, claims=moved, spine=base.spine)
        failing = sorted({f"{r.surface}:{r.id}" for r in mutated.renderings
                          if "MC-003" in r.claim_ids and mutated.s1(r)})
        surfaces = {x.split(":")[0] for x in failing}
        check(f"{full}→{new}: {', '.join(sorted(need))} renderings all fail ({', '.join(failing)})",
              need <= surfaces, f"only {sorted(surfaces)} failed")

    # 3. A rendering that outruns the registry: the film says fourteen while
    #    the claim still says thirteen.
    film = base.find("thirteen-worlds")
    kept = film.text
    film.text = kept.replace("thirteen worlds", "fourteen worlds")
    check("a rendering that changes its number fails against the unchanged claim",
          any("says 'fourteen'" in f for f in base.s1(film)))

    # 4. A phrasing the rendering no longer says fails rather than passing by silence.
    film.text = kept.replace("thirteen worlds", "many worlds")
    check("a phrasing the rendering stopped saying fails", any("no longer says" in f for f in base.s1(film)))
    film.text = kept

    # 5. A phrasing naming no expected key fails.
    ghost = Rendering({"id": "ghost", "surface": "test", "claims": ["MC-003"],
                       "sources": [{"kind": "claim_fields", "fields": ["proposition"]}],
                       "speaks": [{"says": "{identified_set_sise} worlds"}]}, root, base.claims)
    check("a phrasing naming an unknown key fails", any("does not resolve" in f for f in base.s1(ghost)))

    # 6. The unbound sweep: a numeral nobody bound fails; a year does not.
    dev = base.find("D-006")
    src = dev.sources[0]
    kept_src = src.text
    src.text = kept_src + " and 41 more prompts"
    dev.rebuild()
    check("an unbound numeral in hand-authored prose fails", any("unbound numeral '41'" in f for f in base.s1(dev)))
    src.text = kept_src + " as of 2025"
    dev.rebuild()
    check("a year is not swept as a quantity", not any("unbound numeral" in f for f in base.s1(dev)))
    src.text = kept_src
    dev.rebuild()

    # 7. S2, the brief's example. MC-002 speaks of "the five specialized
    #    supervisors on the released file"; a rendering that says "guardrails"
    #    widens it. The negated form does not fire; the product name "NeMo
    #    Guardrails" does not fire; MC-003, whose proposition says
    #    "guardrails", licenses the word for its own renderings.
    loo = base.find("leave-one-out")
    kept_loo = loo.text
    loo.text = kept_loo + SEP + "guardrails fail together."
    check("S2 fires on 'guardrails' in an MC-002 rendering",
          any("'guardrails'" in f and "MC-002" in f for f in base.s2(loo)))
    loo.text = kept_loo + SEP + "not a claim that guardrails in general fail together."
    check("S2 does not fire on the negated non-claim form", not base.s2(loo), "; ".join(base.s2(loo)[:2]))
    loo.text = kept_loo + SEP + "NeMo Guardrails flagged 70."
    check("S2 does not fire on the product name NeMo Guardrails", not base.s2(loo))
    loo.text = kept_loo + SEP + "this is what deployed stacks do in production."
    hits = base.s2(loo)
    check("S2 fires on 'deployed', 'stacks' and 'production'",
          {"'deployed'", "'stacks'", "'production'"} <= {re.search(r"speaks ('\w+')", h).group(1) for h in hits},
          "; ".join(hits))
    loo.text = kept_loo
    kept_film = film.text
    film.text = kept_film + SEP + "for k guardrails this is the identified set."
    verdicts = base.s2(film)
    check("S2 lets MC-003, whose proposition says 'guardrails', license it — and fires for MC-002, which the same film also asserts",
          any("which MC-002's own text" in f for f in verdicts) and not any("which MC-003's own text" in f for f in verdicts),
          "; ".join(verdicts))
    film.text = kept_film

    # 8. S3: drop one non-claim from the artifact and the rendering fails.
    kept_art = dev.artifact
    dev.artifact = kept_art.replace(norm(base.claims["MC-003"]["non_claims"][1]), "")
    check("a rendering that loses a non-claim fails S3", any("S3" in f for f in base.s3(dev)))
    dev.artifact = kept_art

    # 9. S4 never fails: coverage is a printed fact, and the honest current
    #    state includes claims with no registered rendering.
    rows = base.coverage()
    check("S4 reports a row for every claim", len(rows) == len(base.claims))
    check("S4 reports at least one claim with zero registered renderings",
          any(n == 0 for _, n, _, _ in rows))
    return failures


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="enforce S1–S3, print S4")
    ap.add_argument("--explain", metavar="CLAIM", help="print every rendering of one claim and its agreement")
    ap.add_argument("--test", action="store_true", help="run the adversarial fixtures")
    ap.add_argument("--mutate", metavar="CLAIM.key=value", action="append", default=[],
                    help="apply a live mutation to the loaded registry before checking (watch the gate fail)")
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root to check (default: this one)")
    args = ap.parse_args(argv)
    root = args.root.resolve()

    if args.test:
        failures = run_tests(root)
        for f in failures:
            print(f"FAIL  {f}")
        print("Spine binding holds under adversarial fixtures." if not failures else f"{len(failures)} fixture(s) failed.")
        return 1 if failures else 0

    claims = load_claims(root)
    for m in args.mutate:
        full, _, value = m.partition("=")
        set_key(claims, full, as_number(value))
        print(f"mutate {full} := {as_number(value)}")
    spine = Spine(root, claims=claims)

    if args.explain:
        return explain(spine, args.explain)

    failures = spine.run()
    for r in spine.renderings:
        if not any(r.label() in f for f in failures):
            keys = " ".join(f"{k.split('.', 1)[1]}={v[1]}" for k, v in sorted(r.bound.items()))
            print(f"ok    {r.label()} — {len(r.bound)} numerals agree ({keys[:100]}{'…' if len(keys) > 100 else ''})")
    for f in failures:
        print(f"FAIL  {f}")
    print_coverage(spine)
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    n = sum(1 for r in spine.renderings if r.surface != "registry")
    print(f"ok    spine: {n} renderings agree with claims.yaml across "
          f"{len({c for r in spine.renderings for c in r.claim_ids})} claims; "
          f"a green spine says nothing about whether any claim is true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
