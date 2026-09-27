#!/usr/bin/env python3
"""Runs the X5-X9 pairs (x_predeclared.json) against the distribute.py in a given checkout.

Usage: x_pairs.py <checkout> <out.json>

Nothing reaches X or GitHub: x_request, git, credentials and the signer fetch are
replaced by fixtures, and every ledger read or write goes to a temporary directory.
Works on the base and on the patched module; a check the base cannot express is
reported as its base behaviour.
"""
import copy, importlib.util, json, os, pathlib, sys, tempfile, unittest.mock as um

CHECKOUT = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("distribute", CHECKOUT / "scripts" / "distribute.py")
d = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(CHECKOUT / "scripts"))
spec.loader.exec_module(d)
PATCHED = hasattr(d, "observed_text")

APPROVED = ["Same scores, different worlds: https://cubits11.github.io/overlap/ shows why.",
            "Reproduce it: python3 scripts/reproduce_cc001.py & read the limits."]
POST = {"id": "fx-thread", "revision": "f" * 64, "posts": APPROVED, "post_type": "thread",
        "audience_hypothesis": "fixture", "topic": "fixture", "hook": "fixture", "visual": "none",
        "cta": "fixture", "thread_structure": "fixture"}
OWNER = {"id": "1000000001", "username": "PranavBhave_"}
OTHER = {"id": "2000000002", "username": "someone_else"}


def tco(text):
    """What X stores: each URL rewritten to a t.co link, & escaped as &amp;."""
    out, ents = text, []
    for word in text.split():
        if word.startswith("https://"):
            short = "https://t.co/" + format(abs(hash(word)) % 10**10, "010d")
            ents.append({"url": short, "expanded_url": word, "display_url": word[8:40]})
            out = out.replace(word, short)
    return out.replace("&", "&amp;"), ents


class FakeX:
    def __init__(self, me, fail_on_post=None, store=None):
        self.me, self.fail_on_post, self.store = me, fail_on_post, store or {}
        self.posts, self.calls, self.n = [], [], 0

    def __call__(self, method, path, creds, body=None, query=None):
        self.calls.append((method, path))
        if (method, path) == ("GET", "/users/me"):
            return {"data": dict(self.me)}
        if (method, path) == ("POST", "/tweets"):
            self.n += 1
            if self.fail_on_post == self.n:
                raise ValueError("X API 503 on POST /tweets: fixture failure")
            ident = str(3000000000000000000 + self.n)
            text, ents = tco(self.store.get(self.n, body["text"]))
            self.posts.append({"id": ident, "text": text, "entities": {"urls": ents}, "author_id": self.me["id"]})
            return {"data": {"id": ident, "text": text}}
        if (method, path) == ("GET", "/tweets"):
            ids = (query or {}).get("ids", "").split(",")
            return {"data": [p for p in self.posts if p["id"] in ids]}
        raise AssertionError(f"unexpected {method} {path}")


KEYDIR = pathlib.Path(tempfile.mkdtemp())
def keygen(name):
    import subprocess
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(KEYDIR / name)], check=True)
    return KEYDIR / name
OWNER_KEY, STRANGER_KEY = (keygen("owner"), keygen("stranger")) if PATCHED else (None, None)
OWNER_PUB = (KEYDIR / "owner.pub").read_text().strip() if PATCHED else None


def signature(key, post, who):
    import subprocess
    f = KEYDIR / "payload.json"
    f.write_bytes(d.approval_payload(post, who))
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(key), "-n", d.NAMESPACE, str(f)], check=True, capture_output=True)
    sig = (KEYDIR / "payload.json.sig").read_text()
    (KEYDIR / "payload.json.sig").unlink()
    return sig


def run(fake, *, approval=True, principal=None, signed=None, env=True, keys="owner"):
    """Publish POST in a sandbox; returns (outcome, receipt rows, fake)."""
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        if approval:
            row = {"draft_id": POST["id"], "draft_revision": POST["revision"], "basis": "fixture",
                   "approved_at": "2026-09-27T00:00:00Z", "posts_sha256": d.digest(POST["posts"])}
            if signed:
                row["signature"] = signed
            (base / "approvals.json").write_text(json.dumps([row]))
        if principal is not None:
            (base / "principal.json").write_text(json.dumps(principal))
        patches = [um.patch.object(d, "BASE", base), um.patch.object(d, "draft", return_value=[copy.deepcopy(POST)]),
                   um.patch.object(d, "verify", return_value=True), um.patch.object(d, "x_request", fake),
                   um.patch.object(d, "git", side_effect=lambda *a: {"rev-parse": "a" * 40, "status": "", "branch": "origin/fixture"}[a[0]])]
        if env:
            patches.append(um.patch.object(d, "credentials", return_value=("k", "ks", "t", "ts")))
        if PATCHED:
            if keys == "unreachable":
                patches.append(um.patch.object(d, "owner_signing_keys", side_effect=ValueError("Cannot read Cubits11's SSH signing keys from GitHub (fixture); dispatch refuses")))
            else:
                patches.append(um.patch.object(d, "owner_signing_keys", return_value=[OWNER_PUB]))
        for p in patches:
            p.start()
        try:
            try:
                d.publish(POST["id"])
                outcome = "published"
            except Exception as e:  # noqa: BLE001
                outcome = f"refused: {e}"
            rows = json.loads((base / "publications.json").read_text()) if (base / "publications.json").exists() else []
            again = None
            if rows or fake.posts:
                try:
                    d.dispatch_preconditions(copy.deepcopy(POST))
                    again = "re-dispatch admitted"
                except Exception as e:  # noqa: BLE001
                    again = f"re-dispatch refused: {e}"
            return outcome, rows, fake, again
        finally:
            for p in reversed(patches):
                p.stop()


R = {"checkout": str(CHECKOUT), "patched": PATCHED}
principal = {"username": "PranavBhave_", "account_id": OWNER["id"]}
OWNER_SIG = signature(OWNER_KEY, POST, principal) if PATCHED else None
_run = run
def run(fake, **kw):
    kw.setdefault("signed", OWNER_SIG)
    return _run(fake, **kw)

# X5 identity
o0, r0, f0, _ = run(FakeX(OWNER), principal=principal)
o1, r1, f1, _ = run(FakeX(OTHER), principal=principal)
R["X5"] = {"W0": {"outcome": o0, "posts_sent": len(f0.posts), "source_url": r0[0]["source_url"] if r0 else None},
           "W1": {"outcome": o1, "posts_sent": len(f1.posts), "source_url": r1[0]["source_url"] if r1 else None}}

# X6 read-back: W0 stores the approved text (t.co-wrapped), W1 stores a different second post
w1_store = {2: "Reproduce it: python3 scripts/reproduce_cc001.py and trust the result."}
o0, r0, f0, _ = run(FakeX(OWNER), principal=principal)
o1, r1, f1, _ = run(FakeX(OWNER, store=w1_store), principal=principal)
import hashlib
naive = lambda posts: [hashlib.sha256(p["text"].encode()).hexdigest() == hashlib.sha256(a.encode()).hexdigest()
                       for p, a in zip(posts, APPROVED)]
R["X6"] = {"naive_rule": {"W0_equal": naive(f0.posts), "W1_equal": naive(f1.posts)},
           "receipt": {"W0": r0[0].get("readback") if r0 else None, "W1": r1[0].get("readback") if r1 else None,
                       "W0_ok": r0[0].get("readback_ok") if r0 else None, "W1_ok": r1[0].get("readback_ok") if r1 else None}}

# X7 issuer: the same row written by the owner (signed) or by an agent (unsigned, or signed with its own key)
o_owner, _, f_owner, _ = run(FakeX(OWNER), principal=principal)
o_agent, _, f_agent, _ = run(FakeX(OWNER), principal=principal, signed=None)
R["X7"] = {"W0_owner_signed": o_owner, "W1_agent_unsigned": o_agent,
           "posts_sent": [len(f_owner.posts), len(f_agent.posts)]}
if PATCHED:
    other_rev = dict(POST, revision="e" * 64)
    o_key, *_ = run(FakeX(OWNER), principal=principal, signed=signature(STRANGER_KEY, POST, principal))
    o_rev, *_ = run(FakeX(OWNER), principal=principal, signed=signature(OWNER_KEY, other_rev, principal))
    o_acct, *_ = run(FakeX(OWNER), principal=principal, signed=signature(OWNER_KEY, POST, {"username": "someone_else", "account_id": OTHER["id"]}))
    o_net, *_ = run(FakeX(OWNER), principal=principal, keys="unreachable")
    o_nop, *_ = run(FakeX(OWNER), principal=None)
    R["X7"].update(stranger_key=o_key, signed_other_revision=o_rev, signed_other_account=o_acct,
                   github_unreachable=o_net, no_principal_recorded=o_nop)

# X8 custody: publish in a process without the four variables
os.environ.pop("X_API_KEY", None)
o8, _, f8, _ = run(FakeX(OWNER), principal=principal, env=False)
R["X8"] = {"no_credentials_in_caller": o8, "posts_sent": len(f8.posts)}

# X9 partial thread
o9, r9, f9, again = run(FakeX(OWNER, fail_on_post=2), principal=principal)
R["X9"] = {"outcome": o9, "posts_live": len(f9.posts), "receipt_rows": len(r9),
           "receipt_status": r9[0].get("status") if r9 else None, "second_attempt": again}

OUT.write_text(json.dumps(R, indent=1) + "\n")
print(json.dumps(R, indent=1))
