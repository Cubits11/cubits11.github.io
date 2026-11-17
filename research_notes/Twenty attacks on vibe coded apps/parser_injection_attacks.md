# Parser and injection attacks on vibe-coded apps: ReDoS (#7), prototype pollution (#16), template injection (#17), XXE file read (#18)

Research date: 2026-11-17. Defensive orientation: mechanisms, detection probes and fixes only. There are no exploit payloads, gadget chains or DoS tooling.

Source-status legend. Each finding carries one of two tags.
- **[V]** means I checked the finding this session against the cited page, or against a search-engine extract of that page.
- **[K]** means the source is the canonical advisory or document for a fact I know from before this session. I could not re-fetch it, because WebFetch in this session reached only github.com. These hosts failed DNS: `advisories.gitlab.com`, `blog.cloudflare.com` and `stackstatus.tumblr.com`. The report writer should treat [K] items as needing one confirmation click before publication.

Some facts are confirmed only by a secondary aggregator such as Snyk, Wiz, Miggo or releasealert. Those say so inline.

---

## (7) ReDoS — regular-expression denial of service

### Takeaway
ReDoS happens when a backtracking regex engine meets an *ambiguous* pattern and an input that almost matches. Matching time then grows exponentially or polynomially with input length. In Node one such match blocks the whole event loop, so a single request can stall every user.

The durable fix is to make the regex unambiguous, or to run it on a linear-time engine such as RE2, Rust `regex` or Go `regexp`. Cap input length before matching, and gate CI on a detector (eslint-plugin-regexp, recheck, CodeQL). Most 2024–2026 ReDoS exposure in real apps arrives through dependencies rather than hand-written patterns: path-to-regexp/Express, micromatch, brace-expansion, python-multipart, transformers and fast-xml-parser. Keeping lockfiles patched is half of the fix.

### Cited Findings

**(a) Mechanism**
- Several engines decide matches by depth-first backtracking over an NFA: V8's Irregexp, PCRE, Python `re`, Java, .NET by default, and Ruby before 3.2. When a pattern is ambiguous, a failing match retries every split before giving up. "Ambiguous" means one substring can be consumed in many ways, as with nested quantifiers like `(a+)+` or adjacent overlapping quantifiers like `\d+\d*` or `.*.*=`. Nested ambiguity gives exponential time; overlapping sequential quantifiers give polynomial time (O(n²), O(n³)…). — [OWASP ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS) [K]; [eslint-plugin-regexp `no-super-linear-backtracking`](https://ota-meshi.github.io/eslint-plugin-regexp/rules/no-super-linear-backtracking.html) [V]. The rule doc says such patterns "almost always" give exponential or polynomial worst-case runtime, and that in its default "certain" mode the rule reports only cases where it can prove a rejecting suffix exists.
- There is a second, separate quadratic class: an unanchored pattern whose match attempt is retried at every start position. One example is `\s+$` scanning a long run of spaces that ends in a non-space. eslint-plugin-regexp detects this as "super-linear move". — [`no-super-linear-move`](https://ota-meshi.github.io/eslint-plugin-regexp/rules/no-super-linear-move.html) [V]
- Precondition: attacker-influenced input reaches a vulnerable pattern on a backtracking engine. The input needs no special characters — repetition plus a final mismatching character is enough. Impact on Node/Bun/Deno is total, because one request's match runs synchronously on the single JS thread. Python async servers (FastAPI/Starlette) stall the event loop the same way. — python-multipart advisory text: a crafted Content-Type "can stall the event loop" — [GitLab advisory CVE-2024-24762](https://advisories.gitlab.com/pkg/pypi/python-multipart/CVE-2024-24762) [V via search extract]

**(b) Incidents and CVEs**
- *Stack Overflow, 20 July 2016 (historical).* The site was down 34 minutes. A post with about 20,000 consecutive whitespace characters hit a regex meant to trim Unicode whitespace from the start and end of a line. That regex was quadratic: it re-scanned the whitespace run from every start offset. The postmortem's conclusion was "This regular expression has been replaced with a substring function." The breakdown was about 10 minutes to find the cause, 14 to write the fix and 10 to deploy. — [ADTmag](https://adtmag.com/Blogs/Dev-Watch/2016/07/stack-overflow-crash.aspx) [V]; [Michael Tsai summary](https://mjtsai.com/blog/2016/07/21/this-regular-expression-has-been-replaced-with-a-substring-function) [V]. The primary [Stack Exchange postmortem](https://stackstatus.tumblr.com/post/147710624694/outage-postmortem-july-20-2016) could not be fetched; its host is blocked in this session.
- *Cloudflare, 2 July 2019 (historical).* A new WAF Managed Rule "caused CPUs to become exhausted on every CPU core that handles HTTP/HTTPS traffic" across the network. Secondary sources date the outage to about 27 minutes, 13:42–14:09 UTC; some say about 30. The WAF used PCRE through Lua, and the culprit was a backtracking sub-expression of the `.*(?:.*=.*)` shape. Announced remediation included moving the WAF from PCRE to RE2 or the Rust regex engine and adding CPU-time protections. — [Cloudflare post-mortem](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/) [K, page stub only]; [InfoQ](https://www.infoq.com/news/2019/07/waf-causes-outage/) [V]; [Simon Willison notes](https://blog.simonwillison.net/2019/Jul/12/details-cloudflare-outage-july-2-2019/) [V]; [Acunetix](https://www.acunetix.com/blog/web-security-zone/regular-expressions-waf-cloudflare/) [V]
- *path-to-regexp CVE-2024-45296 (Sept 2024).* This is the route matcher used by Express. The generated regex backtracks when one path segment has two parameters separated by something other than a period (e.g. `/:a-:b`). The advisory measured average latency of about 600 ms against 1 ms under Express v4 with 10 concurrent connections. Fixed in 0.1.10 and 8.0.0. — [Red Hat Bugzilla 2310908](https://bugzilla.redhat.com/show_bug.cgi?id=2310908) [V]; [OSV](https://api.osv.dev/v1/vulns/CVE-2024-45296) [V]
- *path-to-regexp CVE-2024-52798 (Dec 2024).* The 0.1.x fix was incomplete; versions through 0.1.11 are affected and 0.1.12 fixes it. Express 4 depends on the 0.1.x line, so check `npm ls path-to-regexp` resolves to ≥0.1.12. — [NVD CVE-2024-52798](https://nvd.nist.gov/vuln/detail/CVE-2024-52798) [V]
- *micromatch CVE-2024-4067 (May 2024).* ReDoS in `micromatch.braces()`, fixed in 4.0.8. Severity scores vary by vendor: 7.5 at Checkmarx, 5.3 at Mend. — [NVD](https://nvd.nist.gov/vuln/detail/cve-2024-4067) [V]
- *brace-expansion CVE-2025-5889 (June 2025).* ReDoS in `expand()`, rated low (2.3) by Snyk; fixed in 1.1.12, 2.0.2, 3.0.1 and 4.0.1. npm 10 bundled a vulnerable copy that `npm audit fix` reported as unfixable. — [Miggo](https://www.miggo.io/vulnerability-database/cve/CVE-2025-5889) [V]; [Snyk](https://security.snyk.io/vuln/SNYK-JS-BRACEEXPANSION-9789073) [V]; [npm/cli #8366](https://github.com/npm/cli/issues/8366) [V]
- *python-multipart CVE-2024-24762 (Feb 2024).* A regex parses the Content-Type header and options, and a crafted header stalls the event loop. It matters only when the app parses form data, which FastAPI does via python-multipart. — [GitLab advisory](https://advisories.gitlab.com/pkg/pypi/python-multipart/CVE-2024-24762) [V via search extract]. The fixed version (0.0.7, which FastAPI 0.109.1 pinned) is [K].
- *transformers CVE-2025-6921.* ReDoS through `_do_use_weight_decay`; fixed in 4.53.0, per Snyk (aggregator). — [Snyk](https://security.snyk.io/vuln/SNYK-PYTHON-TRANSFORMERS-13018959) [V]
- *fast-xml-parser CVE-2023-34104.* Entity names from a DOCTYPE were placed into a regex without escaping, so a crafted name could stall the parser. Affected 4.1.3 up to 4.2.4, fixed in 4.2.4; the workaround is `processEntities: false`. — [GHSA-6w63-h3fj-q4vw](https://github.com/advisories/GHSA-6w63-h3fj-q4vw) [V]; [Snyk](https://security.snyk.io/vuln/SNYK-JS-FASTXMLPARSER-5668858) [V]
- *cross-spawn CVE-2024-21538* is a ReDoS fixed in 7.0.5 and 6.0.6 — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-21538) [K]. *SheetJS `xlsx` CVE-2024-22363* is a ReDoS fixed in 0.20.2, which is not published to the npm registry; the npm-registry `xlsx` is stuck at 0.18.5 — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-22363) [K].

**(c) Why vibe-coded apps are prone**
- AI assistants often emit hand-written validators: email, URL, phone, password strength, slug, Markdown, "strip HTML tags". A widely copied email regex ends in `([a-zA-Z0-9]{2,4})+$`, a repeated bounded quantifier that is ambiguous and backtracks exponentially on a near-miss. That is my analysis — run it through recheck to confirm (see Inferences).
- Generated Express code uses multi-parameter route segments like `/:from-:to`, the exact precondition of CVE-2024-45296 — [Red Hat Bugzilla](https://bugzilla.redhat.com/show_bug.cgi?id=2310908) [V]
- FastAPI apps generated with `Form(...)`/`UploadFile` pull in python-multipart; AI-generated lockfiles often pin old versions. — [python-multipart advisory](https://advisories.gitlab.com/pkg/pypi/python-multipart/CVE-2024-24762) [V]
- `xlsx` (SheetJS) installed from npm stays at 0.18.5, with known PP and ReDoS issues; current builds ship only from cdn.sheetjs.com. — [NVD CVE-2024-22363](https://nvd.nist.gov/vuln/detail/CVE-2024-22363) [K]; [NVD CVE-2023-30533](https://nvd.nist.gov/vuln/detail/CVE-2023-30533) [K]

**(d) Safe self-testing**
- **eslint-plugin-regexp.** Rules `regexp/no-super-linear-backtracking` and `regexp/no-super-linear-move`. The maintainers note the detection is "very simplistic" and misses many cases, so do not treat silence as proof. — [rule doc](https://ota-meshi.github.io/eslint-plugin-regexp/rules/no-super-linear-backtracking.html) [V]; [npm](https://npmjs.com/package/eslint-plugin-regexp) [V]
- **recheck** (makenowjust-labs). An automata-plus-fuzzing ReDoS checker, available as a library and as the ESLint plugin `eslint-plugin-redos`. It produces its own witness strings, so you never need to hand-craft one. — [recheck as ESLint plugin](https://makenowjust-labs.github.io/recheck/docs/usage/as-eslint-plugin) [V]
- **CodeQL** queries `js/redos` (exponential) and `js/polynomial-redos` (polynomial), plus the Python equivalents. These run free on public repos via GitHub code scanning. — [CodeQL js/redos](https://codeql.github.com/codeql-query-help/javascript/js-redos/) [K]
- **Others.** SonarSource rule S5852 (super-linear regex hotspot) — [RSPEC-5852](https://rules.sonarsource.com/javascript/type/Security%20Hotspot/RSPEC-5852) [V]. js-regex-security-scanner — [GitHub](https://github.com/ericcornelissen/js-regex-security-scanner) [V]. safe-regex2 is fastify's star-height heuristic, with high false-negative and false-positive rates; regexploit (Doyensec) does Python/JS pattern extraction — both [K].
- **Dependency side.** `npm audit` / `pip-audit` / Dependabot cover the CVEs above. The npm-10 bundled brace-expansion case shows that audit can report a finding you cannot fix within your own tree. — [npm/cli #8366](https://github.com/npm/cli/issues/8366) [V]

**(e) Fix — TypeScript/Node first**
```ts
// 1) Cap length BEFORE matching (cheap, engine-independent).
const MAX_EMAIL = 254;
// 2) Prefer an unambiguous pattern: each character has one way to be consumed.
const EMAIL_SHAPE = /^[^\s@]{1,64}@[^\s@.]{1,63}(?:\.[^\s@.]{1,63}){1,8}$/;
export function looksLikeEmail(s: string): boolean {
  if (typeof s !== "string" || s.length > MAX_EMAIL) return false;
  return EMAIL_SHAPE.test(s); // real validation = send a confirmation link
}

// 3) For patterns you cannot prove safe (user-supplied search regex, WAF-like rules),
//    use a linear-time engine. node-re2 is a native binding to Google RE2.
import RE2 from "re2";               // npm i re2
const userPattern = new RE2(untrustedSource, "u"); // throws on backreferences/lookaround
userPattern.test(input);
```
- node-re2 (`re2` on npm) exposes a RegExp-compatible `RE2` class backed by Google RE2. It guarantees linear time and does not support backreferences or lookaround. — [uhop/node-re2](https://github.com/uhop/node-re2) [K]
- V8's own linear engine shipped in V8 8.8 as **experimental**. The `/l` flag is accepted only with `--enable-experimental-regexp-engine`, and patterns it cannot handle throw at construction. A V8 source check suggests the gate is still present. A TC39 "linear matching" proposal exists only at Stage 0. As of Nov 2026 this is not a production defense for Node apps. — [V8 blog](https://v8.dev/blog/non-backtracking-regexp) [V]; [TC39 proposal](https://tc39.es/proposal-linear-matching/) [V]; [V8 js-regexp.h](https://chromium.googlesource.com/v8/v8.git/+/refs/heads/main/src/objects/js-regexp.h) [V via search extract]. The automatic fallback flag `--enable-experimental-regexp-engine-on-excessive-backtracks` is described in the V8 blog [K].
- *Timeouts in Node:* `RegExp.prototype.test` is synchronous, so `Promise.race` with a timer cannot interrupt it. Isolate untrusted matching in a `worker_threads` Worker and `terminate()` it on deadline, or use RE2. This is my inference from the single-threaded execution model; see (f).

```python
# Python
import re
MAX = 254
EMAIL_SHAPE = re.compile(r"^[^\s@]{1,64}@[^\s@.]{1,63}(?:\.[^\s@.]{1,63}){1,8}\Z")
def looks_like_email(s: str) -> bool:
    return isinstance(s, str) and len(s) <= MAX and EMAIL_SHAPE.match(s) is not None

# Python >= 3.11: atomic groups (?>...) and possessive quantifiers (*+, ++, ?+) in `re`
# remove backtracking into a sub-expression.
TOKEN = re.compile(r"(?>[A-Za-z0-9_]+)-\d+")

# Untrusted patterns: linear-time RE2 binding, or `regex` with a timeout.
import re2                      # pip install google-re2
re2.compile(untrusted).search(text)
import regex                    # pip install regex
regex.search(pattern, text, timeout=0.05)   # raises TimeoutError
```
- The Python 3.11 `re` module added atomic grouping and possessive quantifiers — [Python re docs](https://docs.python.org/3/library/re.html) [K]. The `regex` module's `timeout=` argument and google-re2 — [K].
- *Other stacks.* Go `regexp` and Rust `regex` guarantee linear time and reject backreferences — [Go regexp](https://pkg.go.dev/regexp) [K]; [Rust regex](https://docs.rs/regex/latest/regex/) [K]. .NET supports a per-Regex `matchTimeout` and `RegexOptions.NonBacktracking` (.NET 7+) — [.NET regex best practices](https://learn.microsoft.com/en-us/dotnet/standard/base-types/best-practices-regex) [K]. Ruby 3.2 added match memoization and `Regexp.timeout` — [Ruby 3.2 release](https://www.ruby-lang.org/en/news/2022/12/25/ruby-3-2-0-released/) [K].
- *Defense in depth.* Request-body size limits (Express `express.json({ limit: '100kb' })` is the default), per-field max lengths in the schema (zod `.max()`), rate limits, and a request deadline at the proxy. Lockfile hygiene: patch path-to-regexp ≥0.1.12 for Express 4 or ≥8.0.0, micromatch ≥4.0.8, brace-expansion patched lines, python-multipart ≥0.0.7, transformers ≥4.53.0, and fast-xml-parser ≥4.2.4 (≥5.5.7 for the 2026 entity issues; see XXE). Version sources are listed in (b).

**(f) Incorrect or incomplete fixes**
- *Promise-based or `setTimeout` timeouts around a regex.* These do nothing: the match never yields to the event loop (inference from the synchronous API).
- *Capping length after matching,* or only on the client. The server still runs the expensive match.
- *Rewriting `+` as `{1,}`, or swapping greedy for lazy (`.*?`).* Laziness changes the search order, not the ambiguity, so the worst case is unchanged. — [OWASP ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS) [K]
- *Trusting "safe-regex" star-height checks* or a quiet linter run. eslint-plugin-regexp itself warns it misses many cases. — [rule doc](https://ota-meshi.github.io/eslint-plugin-regexp/rules/no-super-linear-backtracking.html) [V]
- *Patching only the direct dependency.* path-to-regexp's first fix (0.1.10) was incomplete, and 0.1.12 was needed. — [NVD CVE-2024-52798](https://nvd.nist.gov/vuln/detail/CVE-2024-52798) [V]
- *Testing only with realistic inputs.* Stack Overflow's regex had worked for years until one post with 20,000 spaces arrived. — [ADTmag](https://adtmag.com/Blogs/Dev-Watch/2016/07/stack-overflow-crash.aspx) [V]

**(g) Verify the fix (fails before, passes after)**
```ts
// vitest / jest
import { checkSync } from "recheck";            // npm i -D recheck
import { EMAIL_SHAPE } from "../src/validate";
test("email regex has no super-linear backtracking", () => {
  const r = checkSync(EMAIL_SHAPE.source, EMAIL_SHAPE.flags);
  expect(r.status).toBe("safe");               // 'vulnerable' for the old ([a-z0-9]{2,4})+$ pattern
});
test("validator rejects oversized input fast", () => {
  const t0 = performance.now();
  looksLikeEmail("a".repeat(100_000));          // length cap returns before matching
  expect(performance.now() - t0).toBeLessThan(5);
});
```
```python
# pytest
import time
from app.validate import looks_like_email
def test_long_input_is_rejected_quickly():
    t0 = time.perf_counter()
    assert looks_like_email("a" * 100_000) is False
    assert time.perf_counter() - t0 < 0.01
```
The `checkSync` API name and the `status` values `"safe" | "vulnerable" | "unknown"` are [K]; confirm against the [recheck docs](https://makenowjust-labs.github.io/recheck/docs/usage/as-eslint-plugin). Add `regexp/no-super-linear-backtracking: "error"` to the ESLint config so the CI gate persists.

### Inferences
- I expect `^([a-zA-Z0-9_.-])+@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$` to be exponentially vulnerable. The trailing `([…]{2,4})+$` can split a run of letters in many ways before the `$` fails. Verify with recheck before quoting it as fact.
- Two things make ReDoS more damaging in vibe-coded Node apps than in typical Java apps. One is Node's single-threaded model; the other is serverless/edge deployment with tight CPU limits, where one blocked invocation is billed and retried.
- Dependency ReDoS (path-to-regexp, micromatch, brace-expansion) is the most likely exposure for apps that write no regexes at all, so Dependabot or Renovate is part of the ReDoS fix.

### Gaps
- I found no empirical study measuring how often AI coding assistants emit ReDoS-vulnerable regexes; the pattern claims in (c) are qualitative.
- I could not fetch the Cloudflare and Stack Overflow primary postmortems (hosts blocked). The full Cloudflare regex and its exact remediation list should be quoted from the primary page.
- V8's experimental engine status for Node 24/26 is not confirmed by a release note; the evidence is the V8 source gate plus the Stage 0 TC39 proposal.
- fast-xml-parser's "currency.js" ReDoS fix versions were reported inconsistently by aggregators; I omitted them.

---

## (16) Prototype pollution

### Takeaway
Prototype pollution happens when code writes attacker-chosen keys into objects by walking a path: deep-merge, clone, set-by-path, or nested query/body parsing. The key `__proto__`, or the pair `constructor` → `prototype`, then resolves to `Object.prototype`. Every object in the process inherits the injected property. That can flip authorization flags or crash the process, and through "gadgets" in libraries it can escalate to server-side code execution or client-side DOM XSS.

The robust fix is structural. Validate request bodies against strict schemas that drop or reject unknown keys, and use `Map` or `Object.create(null)` for dynamic keys. Never hand-roll recursive merge on request data. Add `--disable-proto=throw` and safe parsers as a backstop. Do not rely on a string denylist alone: lodash's 2025 fix for `_.unset`/`_.omit` was bypassed with array-wrapped paths (CVE-2026-2950).

### Cited Findings

**(a) Mechanism**
- JS objects inherit through `[[Prototype]]`, and `obj.__proto__` is an accessor on `Object.prototype`. `JSON.parse('{"__proto__":{"x":1}}')` creates an own property literally named `__proto__`. A naive recursive merge then reads `target["__proto__"]`, which is `Object.prototype`, and writes `x` onto it. The same works through `constructor.prototype`. — [PortSwigger Web Security Academy: server-side PP](https://portswigger.net/web-security/prototype-pollution/server-side) [V]; [OWASP Prototype Pollution Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html) [K]
- Preconditions:
  - a sink that assigns along an attacker-controlled key path (merge, extend, defaultsDeep, set, zipObjectDeep, nested `qs`-style parsers);
  - a later read of a property the code assumes is absent (a "gadget").
  
  Impacts by setting:
  - privilege or logic flags (`if (user.isAdmin)`);
  - DoS by shadowing `toString`/`hasOwnProperty`;
  - server-side RCE where a library reads unset options. Child-process spawning options and template-engine compile options are the classic families. Gadget specifics are deliberately omitted here.
  
  — [PortSwigger research: Server-side prototype pollution](https://portswigger.net/research/server-side-prototype-pollution) [V]

**(b) Incidents and CVEs**
- *lodash CVE-2019-10744 (historical).* `defaultsDeep` could be polluted through a `constructor` payload; fixed in 4.17.12. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-10744) [K]
- *lodash CVE-2020-8203 (historical).* `zipObjectDeep` pollution; the fix shipped in 4.17.19, though some trackers cite 4.17.20/4.17.21 as the safe floor. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2020-8203) [K]
- *Kibana CVE-2019-7609 (historical).* Prototype pollution in the Timelion visualizer let an authenticated user reach code execution through a child-process gadget. Fixed in 5.6.15 and 6.6.1. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-7609) [K]
- *jQuery CVE-2019-11358 (historical, client-side).* `$.extend(true, …)` deep-extend pollution, fixed in 3.4.0. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-11358) [K]
- *qs CVE-2022-24999 (historical).* A `__proto__` key in the query string could crash Express apps using qs before 6.10.3; Express 4.17.3 bumped the dependency. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2022-24999) [K]
- *lodash CVE-2025-13465.* Prototype pollution in `_.unset`/`_.omit`. It affects lodash 4.0.0–4.17.22 and the lodash-es and lodash-amd packages; CVSS 6.5, CWE-1321; fixed in 4.17.23. — [OSV](https://osv.dev/CVE-2025-13465) [V]; [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-13465) [V]
- *lodash CVE-2026-2950.* Debian describes it as an incomplete fix for CVE-2025-13465: the guard handled only string key members, so array-wrapped paths bypass it. Debian also lists CVE-2026-4800. One tracker treats everything below 4.18.0 as affected. **Uncertain:** I did not confirm the exact 4.18.x fix from lodash's own advisory. — [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-13465) [V]; [releasealert](https://releasealert.dev/github/sailshq/lodash/cves) [V, aggregator]
- *Elysia CVE-2025-66456 (Dec 2025, Critical).* The `mergeDeep` logic used when routes have multiple standalone validation schemas could pollute prototypes. The advisory says it chains with another advisory to reach RCE; fixed in 1.4.17. This is notable because Elysia is a Bun-first framework popular in AI-generated starters. — [GHSA-hxj9-33pp-j2cc](https://github.com/elysiajs/elysia/security/advisories/GHSA-hxj9-33pp-j2cc) [V]
- Other 2025 npm cases:
  - messageformat runtime 3.0.1, CVE-2025-57353 — [GHSA-6xv4-9cqp-92rh](https://github.com/advisories/GHSA-6xv4-9cqp-92rh) [V]
  - canvg, CVE-2025-25977, fixed in 4.0.3 and 3.0.11 — [GHSA-v2mw-5mch-w8c5](https://github.com/advisories/GHSA-v2mw-5mch-w8c5) [V]
  - js-object-utilities `set`, CVE-2025-28269, fixed in 2.2.1 — [GHSA-hpqf-m68j-2pfx](https://github.com/advisories/GHSA-hpqf-m68j-2pfx) [V]
  - content-security-policy-parser, CVE-2025-55164 (a `__proto__` policy name; "may lead to RCE"), fixed in 0.6.0 — [GitLab advisory](https://advisories.gitlab.com/npm/content-security-policy-parser/CVE-2025-55164/) [V via search extract]
  - expr-eval-fork, CVE-2025-13204, fixed in 2.0.2 — [GitLab advisory](https://advisories.gitlab.com/npm/expr-eval-fork/CVE-2025-13204/) [V via search extract]
  - min-document, CVE-2025-57352, fixed in 2.19.1 — [GHSA-rx8g-88g5-qh64](https://github.com/advisories/GHSA-rx8g-88g5-qh64) [V]
- *EJS CVE-2024-33883.* EJS before 3.1.10 lacked pollution protection, and exploitation needs a separate pollution vector. Fixed in 3.1.10. — [OSV](https://osv.dev/vulnerability/CVE-2024-33883) [V]
- *SheetJS `xlsx` CVE-2023-30533.* Prototype pollution when reading a crafted file; fixed in 0.19.3, which is not on the npm registry. — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2023-30533) [K]

**(c) Why vibe-coded apps are prone**
- Assistants frequently emit a 10-line recursive `deepMerge(target, source)` or `setByPath(obj, "a.b.c", v)` helper, to avoid a dependency or to "update user settings from the request body". These are textbook sinks when fed `req.body` or JSON from `request.json()`. The pattern is my inference; the sink class is from [PortSwigger](https://portswigger.net/web-security/prototype-pollution/server-side) [V].
- `app.use(express.urlencoded({ extended: true }))` is the snippet AI tools usually emit, and it turns `a[b][c]=` into nested objects via qs. Express 5 changed the **query** parser default from "extended" (qs) to "simple" (Node `querystring`, no nesting). A security fix also made extended-parsed `req.query` a plain object. — [Express 5 migration guide](https://expressjs.com/en/guide/migrating-5.html) [V via extract of the translated page](https://expressjs.com/id/guide/migrating-5.html). The plain-object hardening is from an advisory summary at [dbugs.ptsecurity PT-2025-48727](https://dbugs.ptsecurity.com/vulnerability/PT-2025-48727) [V, aggregator]. An open PR proposes removing built-in "extended" entirely; it is not confirmed as released — [expressjs/express#6865 mirror](https://github.com/expressjs/express/pull/6865) [V, status uncertain].
- Defaults of common stacks:
  - Express does **not** use a proto-safe JSON parser.
  - Fastify uses secure-json-parse with `onProtoPoisoning`/`onConstructorPoisoning` defaulting to `'error'` — [secure-json-parse](https://github.com/fastify/secure-json-parse) [K]; [Fastify server options](https://fastify.dev/docs/latest/Reference/Server/) [K].
  - Next.js route handlers and Server Actions call `JSON.parse` / form parsing with no merge, so exposure comes from app code that merges.
- Client side: AI-written "read config from URL hash/query and merge into defaults" code, combined with any library gadget, gives DOM XSS. PortSwigger's DOM Invader automates finding sources and gadgets. — [PortSwigger client-side PP](https://portswigger.net/web-security/prototype-pollution/client-side) [K]

**(d) Safe self-testing**
- *Unit probe for your own merge/set helpers.* Send a JSON body containing a `__proto__` object with a harmless unique key, and a second variant via `constructor` → `prototype`. Then assert that `({}).yourCanaryKey === undefined` in the same process. See (g).
- *Black-box probes that avoid DoS* (Gareth Heyes / PortSwigger):
  - **json spaces** — pollute Express's `json spaces` setting and watch response indentation change;
  - **status** — pollute a `status` value in the 400–599 range; outside it Node returns 500 regardless;
  - **charset**, exposed-headers and options-based reflection probes.
  
  The open-source Burp extension "Server-Side Prototype Pollution Scanner" (Burp ≥2021.9) implements them. Only run these against your own staging app: a polluted prototype persists until the process restarts. — [PortSwigger research paper](https://portswigger.net/research/server-side-prototype-pollution) [V]; [BApp](https://portswigger.net/bappstore/c1d4bd60626d4178a54d36ee802cf7e8) [V]; [blog](https://portswigger.net/blog/server-side-prototype-pollution-scanner) [V]; [Academy lab](https://portswigger.net/web-security/prototype-pollution/server-side/lab-detecting-server-side-prototype-pollution-without-polluted-property-reflection) [V]
- *Date caveat.* The brief says "PortSwigger's 2022 … techniques". I believe the whitepaper "Server-side prototype pollution: Black-box detection without the DoS" was published in early 2023, but I did not confirm the date this session.
- *Static analysis.* CodeQL `js/prototype-pollution` and `js/prototype-polluting-assignment` [K: [CodeQL query help](https://codeql.github.com/codeql-query-help/javascript/js-prototype-polluting-assignment/)], Semgrep's JS rules [K], and `npm audit` for library CVEs.

**(e) Fix — TypeScript/Node first**
```ts
// 1) Validate and reshape request bodies; never merge raw JSON.
import { z } from "zod";                       // zod 4
const SettingsPatch = z.strictObject({          // rejects unknown keys (incl. "__proto__", "constructor")
  theme: z.enum(["light", "dark"]).optional(),
  notifications: z.strictObject({ email: z.boolean().optional() }).optional(),
});
app.patch("/settings", (req, res) => {
  const patch = SettingsPatch.parse(req.body);  // throws -> 400
  const next = { ...current, ...patch, notifications: { ...current.notifications, ...patch.notifications } };
  // spread uses CreateDataProperty: no __proto__ setter is invoked
});

// 2) Dynamic keys: Map or null-prototype objects.
const byKey = new Map<string, unknown>();
const dict: Record<string, unknown> = Object.create(null);

// 3) If you must walk paths, guard EVERY segment and normalize array paths first.
const BLOCKED = new Set(["__proto__", "constructor", "prototype"]);
export function setPath(obj: Record<string, any>, path: string | (string | number)[], v: unknown) {
  const segs = (Array.isArray(path) ? path : path.split(".")).map(String);   // array-wrapped keys -> strings
  if (segs.some((s) => BLOCKED.has(s))) throw new Error("forbidden key");
  let cur = obj;
  for (const s of segs.slice(0, -1)) {
    if (!Object.hasOwn(cur, s) || typeof cur[s] !== "object" || cur[s] === null) cur[s] = Object.create(null);
    cur = cur[s];
  }
  cur[segs.at(-1)!] = v;
}

// 4) Parsers.
app.set("query parser", "simple");             // Express 4: opt into non-nesting parser (Express 5 default)
app.use(express.urlencoded({ extended: false, limit: "50kb" }));
import sjson from "secure-json-parse";         // for raw JSON outside Fastify
const data = sjson.parse(text, undefined, { protoAction: "error", constructorAction: "error" });
```
```bash
# 5) Runtime backstop (Node >= 12.17 / 13.12): remove or trap Object.prototype.__proto__
node --disable-proto=throw server.js     # access throws ERR_PROTO_ACCESS; 'delete' removes the accessor
```
- **zod.** Zod 4 provides `z.strictObject()`, which rejects unrecognized keys, and `z.looseObject()`. Plain `z.object()` strips unknown keys by default, which also removes `__proto__` from the output. **Conflict:** one changelog extract says `.strict()` was removed in v4, while my prior knowledge is that it is deprecated but still present. Use `z.strictObject()` on v4 and `z.object({...}).strict()` on v3. — [Zod v4 changelog](https://zod.dev/v4/changelog) [V via extract]; [v4.zod.dev changelog](https://v4.zod.dev/v4/changelog) [V via extract]
- **valibot** offers `v.strictObject()` for the same purpose. — [valibot docs](https://valibot.dev/api/strictObject/) [K]
- **`--disable-proto=mode`.** `delete` removes `Object.prototype.__proto__`; `throw` keeps it but throws `ERR_PROTO_ACCESS` on access. Added in v13.12.0 and v12.17.0. — [Node CLI docs](https://nodejs.org/api/cli.html#--disable-protomode) [K]; [Node v16.14 CLI docs](https://r2.nodejs.org/docs/v16.14.0/api/cli.html) [V via extract]
- **qs options.** `allowPrototypes` defaults to `false`, and `plainObjects: true` returns null-prototype objects. — [qs README](https://github.com/ljharb/qs) [K]
- **secure-json-parse.** `protoAction` and `constructorAction` take `'error' | 'remove' | 'ignore'` and default to `'error'`. — [fastify/secure-json-parse](https://github.com/fastify/secure-json-parse) [K]
- **Python.** Pydantic/FastAPI models are typed, and Python has no shared mutable prototype. The analogous Python bug, "class pollution" through recursive `setattr` merges reaching `__class__`/`__globals__`, applies to hand-written `merge(obj, dict)` helpers. Fix it the same way: typed models with `model_config = ConfigDict(extra="forbid")`, and never `setattr` from request keys. — [Pydantic config `extra`](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra) [K]. The Python class-pollution framing is my inference; I did not search for a primary source on it.
- **Dependencies.** lodash ≥4.17.23, or ≥4.18.x for CVE-2026-2950 (uncertain, see above); ejs ≥3.1.10; elysia ≥1.4.17; canvg ≥4.0.3 / 3.0.11. Install `xlsx` from cdn.sheetjs.com, not npm. Sources are in (b).

**(f) Incorrect or incomplete fixes**
- *Blocking only `__proto__`.* The `constructor` → `prototype` path still reaches `Object.prototype`. lodash CVE-2019-10744 used `constructor`. — [NVD CVE-2019-10744](https://nvd.nist.gov/vuln/detail/CVE-2019-10744) [K]
- *String-only guards.* Code that checks `key === "__proto__"` but also accepts array paths: lodash's 4.17.23 guard was bypassed by array-wrapped path members (CVE-2026-2950). — [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-13465) [V]
- *Checking only top-level keys* of a recursive merge. My inference: pollution keys can sit at any depth.
- *`--disable-proto` alone.* It removes only the `__proto__` accessor, so `constructor.prototype` traversal still works. This is my inference from the documented semantics, which say the flag affects `Object.prototype.__proto__`. — [Node CLI docs](https://nodejs.org/api/cli.html#--disable-protomode) [K]
- *`Object.freeze(Object.prototype)` as the main fix.* It blocks new properties, but writes are silently ignored outside strict mode. It also triggers the "override mistake": assigning `obj.toString = …` fails when the inherited property is frozen, which breaks some libraries and polyfills. And it leaves `Array.prototype`, `Function.prototype` and others unfrozen unless each is frozen too. — [OWASP PP Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html) [K]. The override-mistake detail is my inference from language semantics.
- *`Object.assign({}, parsed)` instead of merge.* `Object.assign` invokes the `__proto__` setter on the target. It does not pollute globally, but the new object gets an attacker-chosen prototype, so injected "inherited" fields still appear. Spread (`{...parsed}`) defines an own data property instead. This is my inference from ECMAScript `[[Set]]` vs `CreateDataProperty` semantics.
- *`obj.hasOwnProperty(k)` on null-prototype objects* throws; use `Object.hasOwn(obj, k)`. This is my inference.

**(g) Verify the fix**
```ts
import { deepMerge, setPath } from "../src/util";
afterEach(() => { delete (Object.prototype as any).ppCanary; });
test.each([
  ['{"__proto__":{"ppCanary":1}}'],
  ['{"constructor":{"prototype":{"ppCanary":1}}}'],
])("merge does not pollute Object.prototype: %s", (body) => {
  try { deepMerge({}, JSON.parse(body)); } catch {}
  expect(({} as any).ppCanary).toBeUndefined();     // fails on naive deepMerge
});
test("array-wrapped path is blocked", () => {
  expect(() => setPath({}, [["__proto__"] as any, "ppCanary"], 1)).toThrow();
  expect(({} as any).ppCanary).toBeUndefined();
});
test("HTTP: unknown keys rejected", async () => {
  const r = await request(app).patch("/settings").send('{"__proto__":{"isAdmin":true}}').set("content-type","application/json");
  expect(r.status).toBe(400);
});
```

### Inferences
- In 2026 the most likely source of prototype pollution in a vibe-coded app is a generated utility function, not lodash. Library CVEs get patched through Dependabot; a hand-rolled `deepMerge` never receives an advisory.
- Schema validation with strict objects closes the request-body route and also blocks mass-assignment (`role`, `isAdmin` in the body), which is a distinct but co-occurring vibe-code bug.
- Express 5 adoption shrinks the query-string route, but not the `urlencoded({ extended: true })` body route, which still uses qs nesting.

### Gaps
- I found no measurement of how often AI assistants emit unsafe `deepMerge`/`setByPath` helpers.
- The exact lodash release that closes CVE-2026-2950 and CVE-2026-4800 is not confirmed from a primary lodash advisory.
- The PortSwigger whitepaper date (2022 vs 2023) is not verified.
- Whether Zod 4 still ships `.strict()` as a deprecated alias is unresolved (the sources conflict).

---

## (17) Server-side and client-side template injection (SSTI / CSTI)

### Takeaway
Template injection happens when user input becomes part of a template's *source* rather than its *data*. The template engine then evaluates attacker expressions. In Jinja2, Twig, Freemarker, EJS, Pug and Handlebars that often means server-side code execution; in AngularJS or Vue in-DOM templates it means XSS. There is one rule: templates are code; user input is context.

Sandboxes reduce blast radius but are not a boundary. Jinja2's sandbox had escapes fixed in 3.1.5 (CVE-2024-56326) and 3.1.6 (CVE-2025-27516), and sandboxes do not stop resource exhaustion. Since 2024 the fastest-growing SSTI surface is LLM tooling: chat templates shipped inside model files (llama-cpp-python CVE-2024-34359, SGLang CVE-2026-5760), prompt templates (LangChain CVE-2025-65106) and evaluator/prompt-builder features (Agenta, RAGFlow, Giskard).

### Cited Findings

**(a) Mechanism**
- Template engines compile template text into code, either generated JS/Python functions or an AST interpreter. With user input concatenated into the template text, expression syntax like `{{ … }}`, `<%= … %>`, `${ … }` or `#{ … }` is executed. In Jinja2, expressions can walk the Python object graph (dunder attributes, globals) toward the interpreter. In EJS, Pug and lodash `_.template`, compile *options* are spliced into generated JS source, so option injection is code injection. — [PortSwigger SSTI research (Kettle, 2015)](https://portswigger.net/research/server-side-template-injection) [K]; [PortSwigger Academy SSTI](https://portswigger.net/web-security/server-side-template-injection) [K]
- The second variant is passing the whole request object as render *data/options*. Example: EJS CVE-2022-29078, where Express's `res.render(view, req.query)` let `settings[view options][outputFunctionName]` reach EJS's code generator. Fixed in ejs 3.1.7. — [NVD CVE-2022-29078](https://nvd.nist.gov/vuln/detail/CVE-2022-29078) [K]
- Python's `str.format` variant: `user_supplied_format.format(obj=some_object)` allows `{obj.attr.attr[key]}` traversal. That reaches globals and secrets with no template engine at all. — [Armin Ronacher, "Be Careful with Python's New-Style String Format"](https://lucumr.pocoo.org/2016/12/29/careful-with-str-format/) [K]. LangChain CVE-2025-65106 is the 2025 instance of this exact bug class (below).
- Client-side template injection: AngularJS (1.x) evaluates `{{ }}` expressions in any DOM it compiles. When a server reflects user input into a page that AngularJS then compiles, the input runs as an Angular expression, which leads to XSS. The expression sandbox was removed in 1.6, and AngularJS reached end of life on 31 Dec 2021. Vue's guidance is "never use non-trusted templates", which matters especially for in-DOM templates mounted onto server-rendered HTML. — [AngularJS version support status](https://docs.angularjs.org/misc/version-support-status) [K]; [Vue security guide](https://vuejs.org/guide/best-practices/security) [K]

**(b) Incidents and CVEs**
- *Classic engine CVEs (historical, still in lockfiles):*
  - **EJS** CVE-2022-29078 (≤3.1.6, fixed in 3.1.7) [K, NVD above]. EJS CVE-2024-33883 added pollution protection in 3.1.10 — [OSV](https://osv.dev/vulnerability/CVE-2024-33883) [V].
  - **Handlebars** CVE-2019-19919 (<4.3.0, prototype access → RCE) [K: [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-19919)]. 4.6.0 made prototype-property access off by default, with opt-in `allowProtoPropertiesByDefault` / `allowProtoMethodsByDefault` [K]. CVE-2021-23369 and CVE-2021-23383 allowed RCE "when selecting certain compiling options to compile templates coming from an untrusted source"; fixed in 4.7.7 — [NVD CVE-2021-23369](https://nvd.nist.gov/vuln/detail/CVE-2021-23369) [V]; [Snyk](https://security.snyk.io/vuln/SNYK-JS-HANDLEBARS-1056767) [V].
  - **Pug** CVE-2021-21353 (`pretty` option injection, fixed in 3.0.1) [K: [NVD](https://nvd.nist.gov/vuln/detail/CVE-2021-21353)]. Pug CVE-2024-36361 covers untrusted input to the `name` option of `compileClient`/`compileFileClient`/`compileClientWithDependenciesTracked` through 3.0.2. Sources disagree on fix status (one lists <3.0.3 as affected), and NVD marks it **Disputed** — [NVD CVE-2024-36361](https://nvd.nist.gov/vuln/detail/CVE-2024-36361) [V].
  - **lodash `_.template`** CVE-2021-23337: command injection via the `variable` option, fixed in 4.17.21 — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2021-23337) [K].
- *Jinja2 sandbox escapes:*
  - CVE-2024-56326: indirect calls to `str.format` were not caught by the sandbox; fixed in 3.1.5.
  - CVE-2025-27516: the `|attr` filter could fetch a string's `format` method and bypass the sandbox's attribute checks; fixed in 3.1.6.
  - Both require attacker-controlled *template content*.
  
  — [NVD CVE-2025-27516](https://nvd.nist.gov/vuln/detail/cve-2025-27516) [V]; [Ubuntu USN-7343-1](https://ubuntu.com/security/notices/USN-7343-1) [V]; [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-27516) [V]. CVE-2024-56201 (a compiler bug with attacker-controlled filename *and* template content, fixed in 3.1.5) is [K].
- *LLM-app template injection, 2024–2026:*
  - **llama-cpp-python CVE-2024-34359 ("Llama Drama"), published 10 May 2024.** `Llama.__init__` read `tokenizer.chat_template` from GGUF model metadata and rendered it with a plain `jinja2.Environment`, not a sandboxed one. A malicious model file therefore yielded RCE on load or chat. Affected 0.2.30–0.2.71, fixed in 0.2.72. — [GHSA-56xg-wfcc-g829](https://github.com/abetlen/llama-cpp-python/security/advisories/GHSA-56xg-wfcc-g829) [V]. The advisory text does not itself name the patch mechanism; it is commonly reported as switching to `ImmutableSandboxedEnvironment` [uncertain].
  - **SGLang CVE-2026-5760.** The same bug class: a GGUF `chat_template` was rendered by an unsandboxed Jinja2 environment, giving RCE from a malicious model file. A secondary table lists CVSS 9.8. — [infosec.ge write-up](https://infosec.ge/blog/sglang-gguf-rce-cve-2026-5760/) [V, secondary]; [chs.us table](https://chs.us/guides/ssti/) [V, secondary]. Not confirmed against NVD.
  - **vLLM CVE-2025-61620.** DoS rather than RCE: a crafted chat template sent to the OpenAI-compatible server consumed CPU and memory. The fix rejects user-supplied templates unless a feature flag is enabled. This shows that even sandboxed rendering can be exhausted. — [Miggo](https://www.miggo.io/vulnerability-database/cve/CVE-2025-61620) [V, aggregator]
  - **LangChain CVE-2025-65106 (NVD 21 Nov 2025).** In `langchain-core`, f-string prompt templates did not validate variable names, so `.` attribute access and `[]` indexing passed through. That is the `str.format` traversal bug. The Mustache renderer also fell back to `getattr`, and Jinja2 received hardening. Fixed in langchain-core 1.0.7 and 0.3.80. Severity ratings conflict between vendors (8.2–8.3 vs "low"). — [OSV GHSA-6qv9-48xg-fc7f](https://osv.dev/vulnerability/GHSA-6qv9-48xg-fc7f) [V]; [Endor Labs](https://www.endorlabs.com/vulnerability/cve-2025-65106) [V]; [Red Hat](https://access.redhat.com/security/cve/CVE-2025-65106) [V]
  - **Agenta** (CVE-2026-27961, authenticated Jinja2 RCE in custom-evaluator templates) — [GHSA-cfr2-mp74-3763](https://github.com/Agenta-AI/agenta/security/advisories/GHSA-cfr2-mp74-3763) [V]. **RAGFlow**: SSTI in its Prompt Generator leads to RCE — [GHSA-wpg4-h5g2-jxm6](https://github.com/infiniflow/ragflow/security/advisories/GHSA-wpg4-h5g2-jxm6) [V]. **Giskard**: non-sandboxed Jinja2 `Environment` in `ChatWorkflow.chat()` — [GHSA-frv4-x25r-588m](https://github.com/Giskard-AI/giskard-oss/security/advisories/GHSA-frv4-x25r-588m) [V].

**(c) Why vibe-coded apps are prone**
- *Express + EJS:* generated code like `res.render('profile', req.query)` or `res.render('page', { ...req.body })` passes request objects as render options, the CVE-2022-29078 shape. The fix is to pick explicit fields. — [NVD CVE-2022-29078](https://nvd.nist.gov/vuln/detail/CVE-2022-29078) [K]
- *Flask:* assistants often produce `render_template_string(f"<h1>Hello {name}</h1>")` for a quick page. The f-string places user input into template *source*. Flask autoescapes `render_template_string`, but autoescaping is an XSS control and does not stop SSTI. — Flask autoescape behaviour [K: [Flask templating docs](https://flask.palletsprojects.com/en/stable/templating/)].
- *"Let users customize their email, invoice or notification template"* features get built with `Handlebars.compile(userTemplate)`, `nunjucks.renderString(userTemplate)`, `jinja2.Template(user_template)` or `_.template(userTemplate)`. Those engines are not designed for untrusted authors. — Handlebars untrusted-template CVEs [V above]; [Jinja2 sandbox docs](https://jinja.palletsprojects.com/en/stable/sandbox/) [K]
- *AI/LLM features in AI-built apps:* user-editable system prompts rendered with Jinja2/f-strings, and loading third-party GGUF/HF models whose chat templates are code. — llama-cpp-python, SGLang, LangChain advisories [V above]
- *Django:* `Template(user_string).render(Context({...}))` cannot reach underscore attributes or call methods with arguments. It can still disclose anything in the context, and Django does not support untrusted template authors. — [Django template docs](https://docs.djangoproject.com/en/stable/ref/templates/language/) [K]
- *Next.js/React:* JSX escapes by default, so SSTI is rare unless code uses `eval`/`new Function`, server-side template engines for emails, or `dangerouslySetInnerHTML` (XSS, not SSTI). This is my inference.

**(d) Safe self-testing**
- *Arithmetic probes* in every reflected field, including headers, filenames, profile names and "template" settings: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`, `#{7*7}`. If `49` appears in output, emails, PDFs or logs, input is being evaluated. `{{7*'7'}}` distinguishes Jinja2 (`7777777`) from Twig (`49`). Stop at detection and do not escalate. — [PortSwigger SSTI methodology](https://portswigger.net/research/server-side-template-injection) [K]
- *Error probes.* An unbalanced `{{` or `<%` that produces a template-engine stack trace also indicates injection (same source, [K]).
- *Static analysis:*
  - Semgrep rules for `render_template_string` with non-literal arguments and for `jinja2.Environment` without autoescape/sandbox [K];
  - Bandit B701 (`jinja2_autoescape_false`) and B702 (`use_of_mako_templates`) [K: [Bandit plugins](https://bandit.readthedocs.io/en/latest/plugins/index.html)];
  - CodeQL `py/template-injection` and `js/template-object-injection` (the EJS/Pug options-object pattern) [K: [CodeQL js/template-object-injection](https://codeql.github.com/codeql-query-help/javascript/js-template-object-injection/)].
- *LLM apps.* Grep for `jinja2.Environment(` / `Template(` on any string that came from model metadata, a DB row or a request. Check that llama-cpp-python ≥0.2.72, langchain-core ≥1.0.7 (or ≥0.3.80 on 0.3.x) and Jinja2 ≥3.1.6 are installed. Version sources are in (b).

**(e) Fix — TypeScript/Node first**
```ts
// EJS / Pug / Handlebars with Express: data only, explicit fields, never the request object.
app.get("/profile", (req, res) => {
  const name = String(req.query.name ?? "").slice(0, 100);
  res.render("profile", { name });            // NOT res.render("profile", req.query)
});

// User-customizable text (emails, notifications): no template engine; allow-listed placeholders.
const ALLOWED = new Set(["firstName", "orderId"]);
export function fill(tpl: string, vars: Record<string, string>) {
  if (tpl.length > 5000) throw new Error("too long");
  return tpl.replace(/\{\{\s*([A-Za-z]{1,32})\s*\}\}/g, (_, k) =>
    ALLOWED.has(k) ? escapeHtml(vars[k] ?? "") : "");
}

// If you must run Handlebars on developer-owned templates, keep current defaults:
import Handlebars from "handlebars";            // >= 4.7.7
const tpl = Handlebars.compile(DEV_OWNED_SOURCE, { strict: true, knownHelpersOnly: true });
tpl(data /* runtime options: do NOT set allowProtoPropertiesByDefault / allowProtoMethodsByDefault */);
```
- Pin versions: ejs ≥3.1.10, handlebars ≥4.7.7, pug ≥3.0.3 (uncertain, given the disputed CVE), lodash ≥4.17.21 for `_.template`. Sources are in (b).
- *Engines designed for untrusted authors:* LiquidJS, the Shopify Liquid model, exposes resource limits (`parseLimit`, `renderLimit`, `memoryLimit`) [K, verify against [LiquidJS docs](https://liquidjs.com/tutorials/options.html)]. Mustache-style logic-less templates limit, but do not remove, risk (LangChain's Mustache `getattr` fallback shows the limit; [V above]).

```python
# Flask: template source is a constant; user input is context.
from flask import render_template_string
@app.get("/hello")
def hello():
    return render_template_string("<h1>Hello {{ name }}</h1>", name=request.args.get("name", "")[:100])

# Truly user-authored templates: sandbox + autoescape + current Jinja2 + process limits.
from jinja2.sandbox import ImmutableSandboxedEnvironment   # Jinja2 >= 3.1.6
env = ImmutableSandboxedEnvironment(autoescape=True)
out = env.from_string(user_template[:5000]).render(first_name=user.first_name)  # only primitives in context
# Run in a worker with CPU/memory/time limits: the sandbox does not stop loops or huge output.

# Never str.format a user-supplied format string with objects in scope:
#   user_fmt.format(user=user)  -> attribute traversal
# Use string.Template (only $name substitution, no attribute access) with plain strings:
from string import Template
Template(user_fmt).safe_substitute(first_name=user.first_name)
```
- `ImmutableSandboxedEnvironment` also blocks mutation of lists and dicts. Jinja2's docs state the sandbox alone is not a full solution, and that template size, time and resource use must be limited separately. — [Jinja2 sandbox docs](https://jinja.palletsprojects.com/en/stable/sandbox/) [K]; the need for separate limits is corroborated by [vLLM CVE-2025-61620](https://www.miggo.io/vulnerability-database/cve/CVE-2025-61620) [V]
- `string.Template` supports only `$identifier` substitution, with no attribute or index access. — [Python string docs](https://docs.python.org/3/library/string.html#template-strings) [K]
- *LLM apps.* Render model chat templates only in a sandboxed environment, and upgrade llama-cpp-python, SGLang, vLLM and langchain-core. Do not accept per-request chat templates from clients (vLLM now gates this behind an opt-in flag). Treat model files from hubs as code: pin revisions and prefer trusted publishers. — advisories in (b) [V]
- *Client-side.* Migrate off AngularJS (EOL). If you cannot, mark user-content regions `ng-non-bindable` and never server-render user input inside an `ng-app` root. With Vue, do not mount on server-rendered DOM containing user content; use precompiled SFCs (runtime-only build). CSP helps against the XSS impact but does not stop CSTI, since AngularJS expressions execute even in CSP mode. — [Vue security](https://vuejs.org/guide/best-practices/security) [K]; [AngularJS ngNonBindable](https://docs.angularjs.org/api/ng/directive/ngNonBindable) [K]
- *Java/PHP (brief).* Freemarker: set `new_builtin_class_resolver` to `TemplateClassResolver.ALLOWS_NOTHING_RESOLVER` and disable `?api`. Twig: use the `SandboxExtension` with an allow-list policy. Neither replaces "don't build templates from input". — [K: [FreeMarker Configuration API](https://freemarker.apache.org/docs/api/freemarker/template/Configuration.html); [Twig sandbox](https://twig.symfony.com/doc/3.x/api.html#sandbox-extension)]

**(f) Incorrect or incomplete fixes**
- *Escaping or stripping `{{` with a regex.* Other delimiters (`{%`, `{#`, line statements), whitespace-control variants and engine-specific syntax remain. This is my inference; PortSwigger's methodology probes multiple syntaxes for this reason [K].
- *Blocklisting `__class__`, `__globals__`, etc.* The 2024–2025 Jinja2 sandbox escapes went through `str.format` and the `|attr` filter, not through obviously blocked names. — [NVD CVE-2025-27516](https://nvd.nist.gov/vuln/detail/cve-2025-27516) [V]
- *Treating `SandboxedEnvironment` as complete.* Escapes exist (CVE-2024-56326, CVE-2025-27516), and resource exhaustion is out of scope for the sandbox (vLLM CVE-2025-61620). — sources in (b) [V]
- *Relying on autoescaping.* It prevents HTML injection in output, not expression evaluation in the template source. This is my inference from engine semantics.
- *"Only admins can edit templates."* In multi-tenant SaaS a tenant admin is still untrusted relative to the server; Agenta's and RAGFlow's RCEs were authenticated. — [Agenta GHSA](https://github.com/Agenta-AI/agenta/security/advisories/GHSA-cfr2-mp74-3763) [V]; [RAGFlow GHSA](https://github.com/infiniflow/ragflow/security/advisories/GHSA-wpg4-h5g2-jxm6) [V]
- *Patching only the f-string path in LangChain-style code.* The 2025 fix also hardened Mustache and Jinja2, because each renderer had its own traversal route. — [Endor Labs](https://www.endorlabs.com/vulnerability/cve-2025-65106) [V]
- *Pinning `ejs@3.1.7`.* The options-injection fix was followed by further hardening in 3.1.10 [V], and EJS's position is that passing untrusted objects as options is outside its security model [K].

**(g) Verify the fix**
```ts
test("name is rendered as data, not evaluated", async () => {
  const r = await request(app).get("/profile").query({ name: "{{7*7}}<%= 7*7 %>${7*7}" });
  expect(r.text).not.toContain("49");
  expect(r.text).toContain("{{7*7}}");   // or its HTML-escaped form
});
test("render options cannot be set from the query", async () => {
  const r = await request(app).get("/profile").query({ "settings[view options][debug]": "true" });
  expect(r.status).toBe(200);            // and snapshot unchanged
});
```
```python
def test_hello_does_not_evaluate(client):
    r = client.get("/hello", query_string={"name": "{{7*7}}"})
    assert b"49" not in r.data and b"{{7*7}}" in r.data

def test_sandbox_blocks_attribute_traversal():
    from jinja2.sandbox import ImmutableSandboxedEnvironment, SecurityError
    env = ImmutableSandboxedEnvironment()
    import pytest
    with pytest.raises(SecurityError):
        env.from_string("{{ x.__class__ }}").render(x="")   # detection-level probe, not an escape
```
`SecurityError` raised on unsafe attribute access is [K]: some sandbox configurations return `Undefined` instead of raising. Adjust the assertion to "output does not contain `<class`".

### Inferences
- In vibe-coded apps the 2026 SSTI hot spot is AI features: prompt templates, evaluator templates, chat templates. That surface is new, AI assistants scaffold it with Jinja2 by default, and the 2024–2026 advisories cluster there (llama-cpp-python, LangChain, SGLang, vLLM, Agenta, RAGFlow, Giskard).
- "Model files are code" belongs in the remediation report. GGUF chat templates are executable template source, and loading an untrusted model is equivalent to running untrusted Jinja2.

### Gaps
- SGLang CVE-2026-5760's CVSS and fixed version are not confirmed from NVD or the vendor advisory; only secondary write-ups were seen.
- The llama-cpp-python patch mechanism (which sandbox class was used) is not stated in the advisory text I retrieved.
- Pug CVE-2024-36361's fix status is disputed and unresolved.
- I found no 2025–2026 EJS or Handlebars SSTI CVE beyond those listed; absence is not confirmed exhaustively.

---

## (18) XXE — XML external entity file read (plus XInclude and entity-expansion DoS)

### Takeaway
XXE happens when an XML parser honours a document's DTD. That lets the document define entities whose values are loaded from `file://` or `http://` URIs (file read, SSRF, out-of-band exfiltration through parameter entities). It also lets the document define recursively nested entities ("billion laughs" DoS), or pull files through XInclude.

Vibe-coded apps parse XML without noticing it: SAML SSO, SVG avatars (sharp → libvips → librsvg), DOCX/XLSX/PPTX uploads, RSS/Atom import, sitemaps, SOAP/XML-RPC integrations, GPX/KML, and RAG document ingestion. Most modern defaults are safe. The known holes are specific, and some are recent:
- lxml's `iterparse()`/`ETCompatXMLParser` resolved external entities by default until **6.1.0** (CVE-2026-41066, April 2026);
- libxmljs with `noent: true`;
- fast-xml-parser entity-expansion DoS (CVE-2026-26278, then the bypass CVE-2026-33036);
- librsvg XInclude file read (CVE-2023-38633).

The fix: reject DTDs entirely where possible (`forbid_dtd=True`, `disallow-doctype-decl`, `DtdProcessing.Prohibit`, `processEntities: false`), upgrade the parsers, and keep untrusted SVG/Office files away from full-featured converters.

### Cited Findings

**(a) Mechanism**
- A DTD in `<!DOCTYPE …>` may declare internal entities (inline text), external general entities (`SYSTEM "URI"`, whose content is substituted into the document) and parameter entities (`%name;`, used inside DTDs). Each gives a different outcome:
  - If the parser resolves external entities and the app echoes parsed content, the result is local file read.
  - If the URI is `http://`, the result is SSRF.
  - In a blind case, parameter entities in an attacker-hosted external DTD can build a URL containing file contents (out-of-band exfiltration).
  - XInclude (`xi:include href=…`) is a separate inclusion mechanism, processed by some parsers and renderers even without entities.
  - Nested internal entities expand exponentially ("billion laughs"); quadratic blowup uses one large entity referenced many times.
  
  — [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) [K]; [PortSwigger XXE](https://portswigger.net/web-security/xxe) [K]
- Precondition: attacker-controlled XML bytes reach a parser with DTD or entity processing enabled. File read additionally requires the parsed value to be reflected, logged or exfiltrable. Impact: secrets (`.env`, cloud credentials files, SSH keys), SSRF to metadata endpoints, and DoS.

**(b) Incidents and CVEs**
- *lxml CVE-2026-41066 / GHSA-vfmq-68hx-4jfw* (maintainer advisory 18 Apr 2026; NVD 24 Apr 2026; CVSS 3.1 7.5, CWE-611). lxml 5.0 changed the default of the standard XML/HTML parsers to `resolve_entities='internal'`, but `etree.iterparse()` and `ETCompatXMLParser()` kept `resolve_entities=True`. Every lxml before 6.1.0 using those entry points with defaults could read local files. 6.1.0 makes `'internal'` the default everywhere. The workaround is to pass `resolve_entities='internal'` or `False` explicitly. — [GHSA-vfmq-68hx-4jfw](https://github.com/advisories/GHSA-vfmq-68hx-4jfw) [V]; [lxml 5.0.0 changelog](https://lxml.de/changes-5.0.0.html) [V via extract]
- *fast-xml-parser* (npm, pure JS):
  - CVE-2026-26278: unbounded DOCTYPE entity expansion, where a tiny input costs seconds to minutes of CPU. Fixed in 5.3.6, and in 4.5.4 per one database.
  - CVE-2026-33036 (GHSA-8gc5-j5rx-235r) is an incomplete fix. The new limits (e.g. `maxTotalExpansions`) applied only to DOCTYPE-defined entities, and numeric entity references bypassed them. Fixed in 4.5.5 and 5.5.6.
  - A further truthiness bug in `maxEntityCount`/`maxEntitySize` checks is reported fixed in 5.5.7 (aggregator).
  - Earlier issues: CVE-2023-34104 (entity-name regex injection, fixed in 4.2.4) and prototype pollution before 4.1.2 (Snyk).
  
  — [NVD CVE-2026-26278](https://nvd.nist.gov/vuln/detail/CVE-2026-26278) [V]; [OSV GHSA-8gc5-j5rx-235r](https://osv.dev/GHSA-8gc5-j5rx-235r) [V]; [releasealert fast-xml-parser](https://releasealert.dev/npmjs/_/fast-xml-parser/cves) [V, aggregator]; [GHSA-6w63-h3fj-q4vw](https://github.com/advisories/GHSA-6w63-h3fj-q4vw) [V]. Separately, CVE-2026-25128 appears in GitLab's advisory index for fast-xml-parser, but I could not retrieve its details (host blocked) — [GitLab index entry](https://advisories.gitlab.com/pkg/npm/fast-xml-parser/CVE-2026-25128/) [unverified].
- *librsvg CVE-2023-38633* (July 2023; historical but still present in old images). A crafted `xi:include` `href` with special characters and traversal segments allowed arbitrary file read when rendering an SVG, classified CWE-22. Fixed in 2.56.3 and the stable backports 2.55.3, 2.54.7, 2.52.11, 2.50.9 and 2.48.12. librsvg also added an XInclude nesting-depth limit. — [Red Hat Bugzilla 2224945](https://bugzilla.redhat.com/show_bug.cgi?id=2224945) [V]; [oss-security 2023-07-27](https://openwall.com/lists/oss-security/2023/07/27/1) [V]; [librsvg security page (GNOME GitLab pages build)](https://librsvg-b807a6.pages.gitlab.gnome.org/devel-docs/security.html) [V via extract]
- *Python stdlib.* ElementTree does not expand external entities and raises `ParseError` on them. Billion-laughs resistance depends on the linked Expat: older docs said ≥2.4.1, and the revised text says Expat below 2.6.0 "may be vulnerable", related to CVE-2023-52425 (large tokens). In July 2025 CPython replaced the "XML vulnerabilities" table and red warning with an "XML security" note, backported to 3.13. — [CPython 3.11 xml.rst](https://git.joshthomas.dev/mirrors/cpython/src/branch/3.11/Doc/library/xml.rst) [V via extract]; [python-checkins msg (2025)](https://www.mail-archive.com/python-checkins@python.org/msg13130.html) [V]; [cpython PR #135294](https://github.com/python/cpython/pull/135294) [V]; [3.12 docs](https://docs.python.org/3.12/library/xml.html) [V via extract]
- *defusedxml* is still at 0.7.1 (March 2021) upstream. Distribution packages are being rebuilt (e.g. Arch 0.7.1-8, Dec 2025), but there is no new release. — [defusedxml changelog](https://doc.duckcorp.org/cgi-bin/dwww/usr/share/doc/python3-defusedxml/changelog.gz) [V]; [Arch package](https://www.archlinux.org/packages/extra/any/python-defusedxml) [V]
- *Other 2024–2026 XXE in the wild (not re-verified this session):*
  - Ivanti Connect Secure CVE-2024-22024: XXE in the SAML component, Feb 2024 — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-22024) [K].
  - Apache Tika CVE-2025-54988, and CVE-2025-66516 extending it to tika-core: XXE through crafted XFA content in PDFs, fixed in 3.2.2 — [NVD CVE-2025-66516](https://nvd.nist.gov/vuln/detail/CVE-2025-66516) [K, uncertain on exact versions]. This matters for RAG and document-ingestion apps that use Tika.
  - ImageTragick CVE-2016-3714 (historical) is why ImageMagick ships a `policy.xml` to disable risky coders (MVG, MSL, URL and, optionally, SVG) — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2016-3714) [K].
  - libxmljs CVE-2024-34391/34392 (type confusion, no upstream fix; package unmaintained) — [NVD CVE-2024-34391](https://nvd.nist.gov/vuln/detail/CVE-2024-34391) [K, uncertain].

**(c) Why vibe-coded apps are prone**
- *Hidden XML surfaces* in features assistants add on request:
  - "Sign in with Okta/Azure AD (SAML)";
  - "upload an avatar (SVG allowed)";
  - "import from Excel/Word";
  - "import RSS/podcast feed";
  - "upload GPX/KML";
  - "parse sitemap";
  - "connect to legacy SOAP API";
  - "chat with your documents" (RAG ingestion through Tika, unstructured, docx/xlsx libraries).
  
  DOCX/XLSX/PPTX are ZIP containers of XML parts. This is my inference, consistent with OWASP's list of XML entry points [K].
- *Node libxmljs/libxmljs2:* assistants copy `libxmljs.parseXml(str, { noent: true })` from older answers. `noent: true` means "substitute entities", which enables external entity expansion; the default is `false`. — [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) [K]
- *Python lxml:* `etree.iterparse(upload)` is the idiomatic streaming call for large XML feeds and Office parts, and was XXE-by-default until lxml 6.1.0. — [GHSA-vfmq-68hx-4jfw](https://github.com/advisories/GHSA-vfmq-68hx-4jfw) [V]
- *openpyxl* does not guard against billion-laughs/quadratic blowup by default and recommends installing defusedxml. — [openpyxl docs](https://openpyxl.readthedocs.io/en/stable/) [K]
- *Image pipelines:* `sharp(upload).resize().toBuffer()` will rasterize SVG through libvips/librsvg if the bytes are SVG, whatever the file extension. sharp ships prebuilt libvips binaries, so the librsvg version tracks the sharp version. — [sharp installation docs](https://sharp.pixelplumbing.com/install) [K]; librsvg CVE above [V]
- *fast-xml-parser* is pure JS and does not fetch external entities (my understanding of its design [K]). Its risk is entity-expansion DoS, with `processEntities` on by default. — [NVD CVE-2026-26278](https://nvd.nist.gov/vuln/detail/CVE-2026-26278) [V]

**(d) Safe self-testing**
- *Canary-file probe (own environment only).* Create a temp file containing a unique string such as `CANARY-7f3a`. Submit an XML/SVG/DOCX part whose DOCTYPE declares one external entity pointing at that file's `file://` path, and reference it in a field the app echoes or stores. If the canary appears anywhere (response, DB row, rendered PNG, logs), the parser resolves external entities. Use only internal canary files and no network URLs. — technique per [PortSwigger XXE](https://portswigger.net/web-security/xxe) [K]
- *DOCTYPE-acceptance probe.* Submit a minimal document with an empty `<!DOCTYPE x []>`. A hardened parser should reject it (`forbid_dtd`, `disallow-doctype-decl`, `DtdProcessing.Prohibit`). This tests the control without exercising expansion.
- *Dependency audit.* Check lxml ≥6.1.0, fast-xml-parser ≥4.5.5 / ≥5.5.7, librsvg ≥2.56.3 (via sharp/libvips or OS packages), and no `libxmljs` with `noent: true`. Also `grep -R "noent\|resolve_entities=True\|XMLParser(\|iterparse(\|LIBXML_NOENT\|DtdProcessing.Parse"` across the code.
- *Static analysis.* CodeQL `js/xxe`, `py/xxe`, `java/xxe` [K: [CodeQL js/xxe](https://codeql.github.com/codeql-query-help/javascript/js-xxe/)]; Bandit B313–B320 flag stdlib/lxml XML parsing and recommend defusedxml [K: [Bandit blacklist calls](https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html)].

**(e) Fix — TypeScript/Node first**
```ts
// Prefer JSON. If XML is required, use fast-xml-parser >= 5.5.7 (or 4.5.5+) with entities off.
import { XMLParser } from "fast-xml-parser";
const parser = new XMLParser({
  processEntities: false,      // no DOCTYPE entity expansion (DoS + regex issues)
  htmlEntities: false,
  allowBooleanAttributes: false,
});
if (buf.length > 1_000_000) throw new Error("too large");
const doc = parser.parse(buf.toString("utf8"));

// libxmljs / libxmljs2: avoid (unmaintained); if unavoidable, never noent:true, and block network:
// libxmljs.parseXml(str, { noent: false, nonet: true, dtdload: false, dtdvalid: false })

// SVG uploads: do not accept SVG for avatars; sniff magic bytes, not extensions.
import { fileTypeFromBuffer } from "file-type";
const ft = await fileTypeFromBuffer(buf);
if (!ft || !["image/png", "image/jpeg", "image/webp"].includes(ft.mime)) throw new Error("unsupported");
await sharp(buf, { limitInputPixels: 40_000_000 }).rotate().resize(512).webp().toBuffer();
```
- The `processEntities` option and its DOCTYPE role are documented in the fast-xml-parser advisory workaround. — [GHSA-6w63-h3fj-q4vw](https://github.com/advisories/GHSA-6w63-h3fj-q4vw) [V]. Version floors: [OSV GHSA-8gc5-j5rx-235r](https://osv.dev/GHSA-8gc5-j5rx-235r) [V]; [releasealert](https://releasealert.dev/npmjs/_/fast-xml-parser/cves) [V, aggregator]. `htmlEntities`/`allowBooleanAttributes` names are [K].
- libxmljs option names `noent`, `nonet`, `dtdload`, `dtdvalid` are [K]. `file-type` and the sharp `limitInputPixels` option are [K: [sharp constructor](https://sharp.pixelplumbing.com/api-constructor)].
- *SAML:* use a maintained library (`@node-saml/node-saml`, `python3-saml`, `pysaml2`) at current versions, and never hand-parse assertions. Recent SAML CVEs are mostly parser-differential and signature-wrapping bugs, not XXE: xml-crypto CVE-2025-29775 and ruby-saml CVE-2025-25291/25292. Library currency matters more than parser flags here. — [NVD CVE-2025-29775](https://nvd.nist.gov/vuln/detail/CVE-2025-29775) [K, uncertain]

```python
# Python: defusedxml for stdlib-style parsing, with DTDs forbidden outright.
from defusedxml.ElementTree import fromstring        # pip install defusedxml (0.7.1)
root = fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)

# lxml: be explicit even on 6.1+, because defaults have changed twice.
from lxml import etree                                # lxml >= 6.1.0
parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                         dtd_validation=False, huge_tree=False)
root = etree.fromstring(data, parser)
for _ev, el in etree.iterparse(fp, resolve_entities=False, no_network=True, load_dtd=False):
    ...
# openpyxl: pip install defusedxml so openpyxl uses it automatically.
```
- `resolve_entities='internal'` is the default since lxml 5.0 for XMLParser and since 6.1.0 for iterparse/ETCompatXMLParser; passing it explicitly is the advisory's workaround. — [GHSA-vfmq-68hx-4jfw](https://github.com/advisories/GHSA-vfmq-68hx-4jfw) [V]
- `no_network=True`, `load_dtd=False` and `huge_tree=False` as lxml defaults [K: [lxml parser docs](https://lxml.de/parsing.html)]. The defusedxml `forbid_dtd` / `forbid_entities` / `forbid_external` keywords [K: [defusedxml README](https://github.com/tiran/defusedxml)].
- *Java.* `DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance(); dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true); dbf.setXIncludeAware(false); dbf.setExpandEntityReferences(false);`. Where DTDs must be allowed, set the `external-general-entities` and `external-parameter-entities` features to false and `load-external-dtd` to false. — [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) [K]
- *.NET.* `new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }`. .NET Framework ≥4.5.2 and .NET Core default `XmlDocument`'s resolver to null. — same OWASP source [K]
- *PHP.* libxml2 ≥2.9.0 disables external entity loading by default; `libxml_disable_entity_loader()` was deprecated in PHP 8.0. Never pass `LIBXML_NOENT` or `LIBXML_DTDLOAD` for untrusted input. — same OWASP source [K]; [PHP manual](https://www.php.net/manual/en/function.libxml-disable-entity-loader.php) [K]
- *Image pipelines:*
  - keep sharp current, or OS librsvg ≥2.56.3;
  - in ImageMagick's `policy.xml`, disable `MSL`, `MVG`, `URL`, `TEXT`, `EPHEMERAL` and, unless needed, `SVG` coders (`<policy domain="coder" rights="none" pattern="{MSL,MVG,SVG,URL,TEXT,EPHEMERAL}" />`), or use ImageMagick's shipped `policy-websafe.xml`;
  - run converters in a sandbox (container without secrets, no network egress).
  
  — [ImageMagick security policy](https://imagemagick.org/script/security-policy.php) [K]; librsvg CVE [V]
- *Defense in depth.* Run parsers in processes with no secrets on disk and no network egress, so XXE that slips through yields nothing. Add body-size limits and timeouts for expansion DoS. Use separate upload workers.

**(f) Incorrect or incomplete fixes**
- *Assuming "lxml ≥5 is safe by default".* `iterparse()` and `ETCompatXMLParser` stayed XXE-by-default until 6.1.0. — [GHSA-vfmq-68hx-4jfw](https://github.com/advisories/GHSA-vfmq-68hx-4jfw) [V]
- *Upgrading fast-xml-parser to 5.3.6 and stopping.* The CVE-2026-26278 fix was bypassed with numeric entity references (CVE-2026-33036), so explicit limits alone did not help until 4.5.5/5.5.6. — [OSV GHSA-8gc5-j5rx-235r](https://osv.dev/GHSA-8gc5-j5rx-235r) [V]
- *Regex-stripping `<!DOCTYPE`* before parsing. Encodings (UTF-16/UTF-7 declarations), comments and whitespace variants can evade a byte-level filter. Parser configuration is the control. This is my inference, consistent with OWASP's guidance to configure parsers [K].
- *Disabling only external general entities* (Java). Parameter entities and external DTD loading remain, which enables out-of-band exfiltration; prefer `disallow-doctype-decl`. — [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) [K]
- *Blocking entities but not XInclude.* librsvg's file read went through `xi:include`. — [Red Hat Bugzilla 2224945](https://bugzilla.redhat.com/show_bug.cgi?id=2224945) [V]
- *Validating the file extension or `Content-Type`.* An "avatar.png" that is SVG bytes still reaches librsvg via libvips content sniffing (my inference). Use magic-byte allow-lists of raster types.
- *Running DOMPurify on SVG and calling it done.* DOMPurify addresses script/XSS in the browser. It does not stop a server-side parser or renderer that already processed the DTD or XInclude (my inference).
- *Using `defusedxml.lxml`.* It is deprecated; defusedxml's README recommends configuring lxml directly. — [defusedxml README](https://github.com/tiran/defusedxml) [K]

**(g) Verify the fix**
```python
# pytest: fails on lxml < 6.1 iterparse defaults or on a permissive parser; passes after hardening.
import io, pathlib, pytest
from app.xml_ingest import parse_feed            # your function under test

def test_dtd_rejected_or_entity_not_resolved(tmp_path: pathlib.Path):
    canary = tmp_path / "canary.txt"; canary.write_text("CANARY-7f3a")
    doc = (f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY c SYSTEM "{canary.as_uri()}">]>'
           f'<r><title>&c;</title></r>').encode()
    try:
        out = parse_feed(io.BytesIO(doc))
    except Exception:
        return                                     # rejecting the DTD is the preferred outcome
    assert "CANARY-7f3a" not in repr(out)
```
```ts
// vitest: same canary idea for a Node endpoint; plus an empty-DOCTYPE rejection test.
test("XML import rejects DOCTYPE", async () => {
  const r = await request(app).post("/import").set("content-type", "application/xml")
    .send('<?xml version="1.0"?><!DOCTYPE r []><r/>');
  expect([400, 415, 422]).toContain(r.status);
});
test("avatar upload rejects SVG bytes even with .png name", async () => {
  const r = await request(app).post("/avatar").attach("file", Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"/>'), "a.png");
  expect(r.status).toBe(415);
});
```
For entity-expansion DoS, assert that DTD-bearing input is *rejected* rather than timing an expansion. That keeps DoS inputs out of the test suite.

### Inferences
- In 2026, "XXE in a vibe-coded app" most likely means one of three things. First, Python lxml `iterparse` on an unpatched lxml (<6.1.0) in a feed or Office importer. Second, an SVG or document converter (librsvg, ImageMagick, Tika) in an upload pipeline. Third, entity-expansion DoS in a JS parser. Classic Java/PHP XXE is less likely, because those runtimes' defaults improved and vibe-coded stacks skew to Node and Python.
- lxml's defaults changed twice, at 5.0 and at 6.1.0, so explicit parser options are more robust than relying on version-specific defaults.
- RAG and "chat with your documents" features greatly widen the XML surface (PDF XFA, DOCX/PPTX/XLSX parts, EPUB, SVG). Those features are among the most common AI-built additions.

### Gaps
- I could not retrieve the GitLab entry for fast-xml-parser CVE-2026-25128 (host blocked), nor confirm whether fast-xml-parser's 5.5.7 fix is distinct from 5.5.6.
- The Apache Tika, Ivanti, xml-crypto and libxmljs CVE details are from prior knowledge and were not re-verified this session.
- I found no ImageMagick-specific SVG XXE CVE in 2024–2026 searches; the policy.xml guidance is from the canonical ImageMagick page [K].
- The current wording of the CPython "XML security" docs (after the July 2025 rewrite), including whether they still name defusedxml, was not read directly.
- Hosts blocked in this session: `advisories.gitlab.com`, `blog.cloudflare.com` and `stackstatus.tumblr.com`. Allowing them would let the [K] and "via extract" items be confirmed against primary text.
