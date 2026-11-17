# Edge and transport-layer attacks on vibe-coded apps: HTTP/2 Rapid Reset (1), HTTP request smuggling (9), web cache poisoning and deception (10), spoofed client-IP headers (11)

Research date: 2026-11-17. Scope: defensive notes for developers of AI-generated ("vibe-coded") apps.

**How these notes were sourced (read first).** In this session WebFetch could not reach portswigger.net, access.redhat.com, nextjs.org, vercel.com, blog.cloudflare.com, developers.cloudflare.com, nginx.org, go.dev, kb.cert.org, nvd.nist.gov, rfc-editor.org, osv.dev or expressjs.com (DNS refusal from the session network policy). Three kinds of evidence result, and each finding is tagged:
- **[verified-primary]**: I read the primary text in this session. Sources: nodejs.org security-release pages and API docs (via curl), published package source from the npm and PyPI registries (express-rate-limit 8.7.4, proxy-addr, @vercel/functions 3.11.3, next 16.4.6, uvicorn 0.54.0, gunicorn 27.0.1, werkzeug 3.1.9), and npm/Node release timestamps.
- **[search-summary]**: the claim comes from WebSearch result summaries of the cited URL. I did not read the page itself. Where search results disagreed, I say so.
- **[prior-knowledge, not re-fetched]**: a canonical fact I could not re-fetch this session, cited to its canonical URL. A writer should re-verify these before publishing.

---

## 1. HTTP/2 Rapid Reset (CVE-2023-44487) and its successors (CONTINUATION flood 2024, MadeYouReset 2025, "HTTP/2 Bomb" and the 2026 Node.js/Apache HTTP/2 CVE wave)

### Takeaway
Rapid Reset exploits the fact that a stream the client cancels with RST_STREAM stops counting toward SETTINGS_MAX_CONCURRENT_STREAMS while the server may still be working on it. The fix is a per-connection cap on resets or on work. Its successors (the CONTINUATION flood in 2024, MadeYouReset in 2025 with server-triggered resets, and the HPACK "HTTP/2 Bomb" in 2026) show that this is a class of resource-accounting bugs, not a single bug. Through November 2026, Node.js and Apache httpd were still shipping HTTP/2 DoS and memory-safety fixes. For a vibe-coded app, the rule is: let a patched CDN or reverse proxy terminate HTTP/2. Expose your own Node or Python HTTP/2 listener only if you patch it on every security release and set its reset and memory limits. Keep the origin unreachable except through the edge.

### Cited Findings

#### (a) Mechanism
- RFC 9113 §5.1.2 counts only streams in the "open" or "half-closed" states toward the peer's concurrency limit. A reset stream is "closed", so a client can open a stream with HEADERS and cancel it at once with RST_STREAM, repeatedly, without ever reaching SETTINGS_MAX_CONCURRENT_STREAMS. The server has often already dispatched the request to the application by then. — [RFC 9113 §5.1.2](https://www.rfc-editor.org/rfc/rfc9113.html#section-5.1.2) [prior-knowledge, not re-fetched]
- Node.js's advisory text: "Rapidly creating and cancelling streams (HEADERS frame immediately followed by RST_STREAM) without bound causes denial of service." — [Node.js Oct 2023 security releases](https://nodejs.org/en/blog/vulnerability/october-2023-security-releases) [verified-primary]
- Scale when disclosed (Oct 10, 2023): Cloudflare saw more than 201M requests/s at peak, Google 398M rps, AWS 155M rps (aimed at CloudFront). The attacks ran from August to October 2023. — [TechTarget](https://www.techtarget.com/cybersecurity/news/366554941/Rapid-Reset-DDoS-attacks-exploiting-HTTP-2-vulnerability); [The Record](https://therecord.media/largest-ddos-incidents-amazon-cloudflare-google) [search-summary]
- Impact: denial of service only. The attacker gains no data. It is cheap per request because no response has to be read.
- **CONTINUATION flood (disclosed Apr 3, 2024; Bartek Nowotarski; reported to CERT/CC Jan 25, 2024).** HEADERS can be followed by an unbounded series of CONTINUATION frames without END_HEADERS. Implementations that did not cap the accumulated header block, or that kept decoding HPACK after exceeding limits, used unbounded CPU or memory. A single TCP connection was enough. — [SecurityWeek](https://www.securityweek.com/new-http-2-dos-attack-potentially-more-severe-than-record-breaking-rapid-reset/); [Checkmarx](https://checkmarx.com/blog/what-you-should-know-http-2-continuation-flood-vulnerability/) [search-summary]
- **MadeYouReset (CVE-2025-8671, disclosed Aug 13, 2025; Tel Aviv University and Imperva).** RST_STREAM serves both client cancellation and server error signalling. The attacker sends deliberately malformed frames (invalid WINDOW_UPDATE, a PRIORITY frame of the wrong size, DATA or HEADERS that violate stream state) so that the *server* resets the stream, as RFC 9113 requires on a stream PROTOCOL_ERROR. The backend keeps processing the already-accepted request. Defences that rate-limit *client-sent* RST_STREAM therefore never trigger. — [Imperva](https://www.imperva.com/blog/madeyoureset-turning-http-2-server-against-itself/); [The Hacker News](https://thehackernews.com/2025/08/new-http2-madeyoureset-vulnerability.html); [CERT/CC VU#767506](https://kb.cert.org/vuls/id/767506) [search-summary]
- **"HTTP/2 Bomb" (disclosed June 2–3, 2026).** An HPACK compression bomb (tiny indexed header references that expand into large retained header lists) combined with a Slowloris-style flow-control stall holds memory open. It affected default HTTP/2 configurations of nginx, Apache httpd, Microsoft IIS, Envoy and Cloudflare Pingora. The Cloud Security Alliance describes it as AI-discovered. — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-http2-bomb-ai-discovered-dos-20260604-csa/); [Cybersecurity News](https://cybersecuritynews.com/http-2-bomb-remote-dos-exploit/); [Red Hat RHSB-2026-007](https://access.redhat.com/security/vulnerabilities/RHSB-2026-007) [search-summary]

#### (b) Incidents, CVEs, affected and patched versions
**Rapid Reset (2023):**
- Node.js: fixed in **v20.8.1 and v18.18.2** (Oct 2023). The bug was in the bundled nghttp2. — [Node.js Oct 2023 release](https://nodejs.org/en/blog/vulnerability/october-2023-security-releases) [verified-primary]
- nginx: fixed in **1.25.3**, which limits new streams per event-loop iteration to 2 × `http2_max_concurrent_streams`. — [safeguard.sh](https://safeguard.sh/resources/blog/nginx-cve-2023-44487); [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2023-44487) [search-summary]
- Go: tracked as **CVE-2023-39325**. Fixed in Go **1.21.3** (and 1.20.10) and in golang.org/x/net v0.17.0, which caps concurrently executing handlers at the stream limit. — [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2023-44487) [search-summary for Go 1.21.3 and the CVE alias; the 1.20.10 and x/net 0.17.0 detail is prior-knowledge]
- Apache httpd: **2.4.58** or later. — [Phoenix Security](https://phoenix.security/vulnerability-http2-rapidreset-2/) [search-summary]
- Envoy: **sources conflict.** One says 1.27.1; another says 1.27.2, 1.26.6, 1.25.11 and 1.24.12. Check Envoy's own advisory. — [Phoenix Security](https://phoenix.security/vulnerability-http2-rapidreset-2/); [systemshardening.com](https://www.systemshardening.com/articles/network/http2-flood-mitigation/) [search-summary]
- h2o: Ubuntu notes that upstream merged the fix (taken from dnsdist's vendored fork) without cutting a new h2o release. — [Ubuntu CVE page](https://ubuntu.com/security/CVE-2023-44487) [search-summary]

**CONTINUATION flood (2024):**
- Node.js **CVE-2024-27983** (High): an assertion failure in `~Http2Session()` when CONTINUATION headers are pending and the TCP connection is closed abruptly. It affected 18.x, 20.x and 21.x and was fixed Apr 3, 2024. — [Node.js Apr 2024 release](https://nodejs.org/en/blog/vulnerability/april-2024-security-releases) [verified-primary]. The fixed versions 18.20.1, 20.12.1 and 21.7.2 come from [Checkmarx](https://checkmarx.com/blog/what-you-should-know-http-2-continuation-flood-vulnerability/) [search-summary].
- Go **CVE-2023-45288**: no cap on CONTINUATION frames. Affected ≤1.21.8 and ≤1.22.1, which implies fixes in 1.21.9 and 1.22.2. — [Checkmarx](https://checkmarx.com/blog/what-you-should-know-http-2-continuation-flood-vulnerability/) [search-summary]
- Apache httpd **CVE-2024-27316**: affected 2.4.17–2.4.58. — same source [search-summary]

**MadeYouReset (2025), per-vendor CVEs:**
- Apache Tomcat **CVE-2025-48989**: affected 11.0.0-M1–11.0.9, 10.1.0-M1–10.1.43 and 9.0.0.M1–9.0.107. Fixed in **11.0.10, 10.1.44 and 9.0.108**. — [search summary of CERT/CC and vendor data](https://kb.cert.org/vuls/id/767506) [search-summary]
- Netty **CVE-2025-55163**: fixed in **4.1.124.Final and 4.2.4.Final**. — same [search-summary]
- Jetty has its own advisory. — [Jetty GHSA-mmxm-8w33-wc4h](https://github.com/jetty/jetty.project/security/advisories/GHSA-mmxm-8w33-wc4h) [search-summary]
- Fastly fixed its internal H2O fork (release 25.17) on June 2, 2025, before disclosure. CERT/CC also lists gRPC and SUSE as affected. — [CERT/CC VU#767506](https://kb.cert.org/vuls/id/767506) [search-summary]
- CYFIRMA's list of affected implementations also includes Varnish, F5, AMPHP, lighttpd and the Rust `h2` crate. — [CYFIRMA](https://www.cyfirma.com/research/cve-2025-8671-http-2-madeyoureset-vulnerability-ddos-attack/) [search-summary]

**2026 HTTP/2 developments (new since most training data):**
- **HTTP/2 Bomb CVE mapping is vendor-specific.** CVE-2026-49975 is the Apache httpd mod_http2 identifier (fixed in mod_http2 2.0.41 and Apache httpd **2.4.68**, released June 8, 2026). Envoy's identifier is **CVE-2026-47774** (GHSA-22m2-hvr2-xqc8), fixed in **1.35.11, 1.36.7, 1.37.3 and 1.38.1**. nginx shipped a `max_headers` directive (default 1000; excess returns 400) in **1.29.8** with no nginx CVE. As of disclosure, IIS and Pingora were reported unpatched. — [Cybersecurity News](https://cybersecuritynews.com/http-2-bomb-remote-dos-exploit/); [lilting.ch](https://lilting.ch/en/articles/http2-bomb-hpack-flow-control-dos); [Plesk KB](https://support.plesk.com/hc/en-us/articles/40997670836247-Vulnerability-CVE-2026-49975-HTTP-2-Bomb); [Rocky Linux forum](https://forums.rockylinux.org/t/nginx-and-cve-2026-49975/20567) [search-summary]. **Conflict:** one summary dates nginx 1.29.8 to **Apr 7, 2026**, before the June disclosure. Whether `max_headers` was a pre-disclosure fix is unverified.
- Apache httpd **CVE-2026-23918**: a double-free in mod_http2 (DoS, possibly RCE) in 2.4.66, fixed in **2.4.67** (May 2026). — [The Hacker News](https://thehackernews.com/2026/05/critical-apache-http2-flaw-cve-2026.html) [search-summary]
- Apache httpd **CVE-2026-119618**: mod_http2 heap corruption/RCE, fixed in **2.4.71** (Nov 11, 2026). Sources disagree: one cites a Red Hat CVSS of 9.8, another says the CVE was still reserved. Red Hat's interim workaround is to drop `h2` from `Protocols`. — [IT-Connect](https://www.it-connect.tech/apache-http-server-critical-http-2-flaw-can-let-attackers-run-code-remotely/); [cipherssecurity](https://cipherssecurity.com/apache-cve-2026-119618-http2-rce/) [search-summary, **uncertain**]
- Node.js shipped HTTP/2 server fixes in three 2026 security releases. — [verified-primary]
  - **Jun 18, 2026** (fixed in 22.23.0, 24.17.0 and 26.3.1): CVE-2026-48937, "HTTP/2 sessions never clean up after GOAWAY on invalid protocol errors"; CVE-2026-48619, unbounded memory in `node:http2` *clients* via ORIGIN frames. — [Node.js Jun 2026](https://nodejs.org/en/blog/vulnerability/june-2026-security-releases)
  - **Jul 29, 2026** (fixed in 22.23.2, 24.18.1 and 26.5.1): CVE-2026-56846 (High), "HTTP/2 retained headers can bypass maxSessionMemory limits"; CVE-2026-56848 (High), a heap use-after-free on re-entrant send. — [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases)
  - **Nov 11, 2026** (fixed in **22.23.5, 24.22.3 and 26.13.1**; only the 22.x, 24.x and 26.x lines received patches):
    - CVE-2026-123863 (High): a remote abort through a `CHECK_EQ(current_nghttp2_memory_, 0)` assertion. It "needs only a default http2 server whose handler responds before the request body has ended" and is "a variant of CVE-2024-27983".
    - CVE-2026-123865 (High): an incomplete fix of CVE-2026-48937 that leaks memory and file descriptors at shutdown.
    - CVE-2026-123866 and CVE-2026-123874 (High): use-after-frees.
    - CVE-2026-123868 (Medium): inbound DATA queued on an undrained stream "is charged to no session budget, so maxSessionMemory neither bounds it nor refuses new streams". About 10 wire bytes per frame retain about 114 bytes of server memory.
    - CVE-2026-123875 (Medium): a crash when a client cancels one `respondWithFile()` download.
    - CVE-2026-123828 (Medium): a one-byte overflow in `altsvc()`.
    - Source: [Node.js Nov 2026](https://nodejs.org/en/blog/vulnerability/november-2026-security-releases)
  - Node.js release index: 26.13.1 is marked LTS "Lithium" (2026-11-10), 24.22.3 "Krypton" (2026-11-10) and 22.23.5 "Jod" (2026-11-11). — [nodejs.org/dist/index.json](https://nodejs.org/dist/index.json) [verified-primary]

#### (c) Who already mitigates what, and the vibe-stack defaults
- **Platform side.** Cloudflare, Google and AWS detected and mitigated Rapid Reset at their edges in Aug–Oct 2023, before public disclosure. — [TechTarget](https://www.techtarget.com/cybersecurity/news/366554941/Rapid-Reset-DDoS-attacks-exploiting-HTTP-2-vulnerability) [search-summary]. Fastly fixed MadeYouReset in its edge in June 2025. — [CERT/CC VU#767506](https://kb.cert.org/vuls/id/767506) [search-summary]. Cloudflare said "no action is needed from Cloudflare customers" for the separate Pingora smuggling bug, which illustrates that edge-side protocol bugs are the CDN's to patch. — [Cloudflare blog](https://blog.cloudflare.com/resolving-a-request-smuggling-vulnerability-in-pingora) [search-summary]
- **Developer side.** The CVE lists above show the developer owns patching wherever *their own process* terminates HTTP/2: self-hosted nginx, Apache, Envoy, a Node `http2.createSecureServer`, Go `net/http`, or Java Tomcat/Netty/Jetty.
- **Python servers.** In uvicorn 0.54.0, HTTP/2 is **opt-in**: `--http2` "Requires --http zttp", and zttp is a pre-1.0 library (0.0.35 on PyPI). Its HTTP/2 implementation enforces `limit_concurrency` but I found no RST_STREAM rate limit in it. — [uvicorn 0.54.0 on PyPI](https://pypi.org/project/uvicorn/0.54.0/) (source inspected: `uvicorn/main.py`, `uvicorn/protocols/http/zttp_h2_impl.py`) [verified-primary]. Gunicorn 27.0.1 has optional HTTP/2 (`http_protocols` including `h2`, requires `gunicorn[http2]`). It closes a connection with ENHANCE_YOUR_CALM after more than `RST_STREAM_RATE_LIMIT = 200` client resets in a 10 s window and 1000 control frames per 10 s. The source comment reads "(CVE-2023-44487 style floods)". — [gunicorn 27.0.1 on PyPI](https://pypi.org/project/gunicorn/27.0.1/) (source `gunicorn/http2/connection.py`) [verified-primary]. That counter only sees *client-sent* resets. By the MadeYouReset mechanism above, it would not count server-generated resets. (This is an inference; I did not test gunicorn.)

#### (d) Safe self-testing (no flood tools)
- Do not run reset-flood, CONTINUATION or HPACK-bomb PoCs against production. Public PoC repos exist for HTTP/2 Bomb, which raises the urgency of patching but is not a reason to run them. — [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-http2-bomb-ai-discovered-dos-20260604-csa/) [search-summary]
- Test by inventory:
  1. Find every process that speaks h2 to the internet. `curl -sI --http2 https://origin.example` and check the protocol. Hit the origin IP directly as well as the CDN hostname.
  2. Compare its version against the fixed versions above.
  3. For Node, compare `process.version` against the latest security release of its line. The Node.js org's `is-my-node-vulnerable` CLI (npm, v1.6.1) automates this. — [npm: is-my-node-vulnerable](https://www.npmjs.com/package/is-my-node-vulnerable) [verified: package exists; behaviour prior-knowledge]
- Read the server's advertised SETTINGS (e.g. `nghttp -nv https://staging.example`) to confirm a finite SETTINGS_MAX_CONCURRENT_STREAMS. [prior-knowledge, not re-fetched]

#### (e) The fix
- **Preferred architecture.** Terminate client HTTP/2 at the CDN or a patched reverse proxy and keep the origin unreachable except from it (firewall to CDN ranges, a Cloudflare Tunnel, or mTLS origin pulls; see §4). An Express app built on `http.createServer`/`app.listen()` does not speak HTTP/2 at all, so these Node HTTP/2 CVEs do not reach it. They reach whatever terminates h2 in front of it.
- **Node (if you must expose `node:http2`).** Run a supported line at its latest security patch: ≥22.23.5, ≥24.22.3 or ≥26.13.1 as of Nov 11, 2026. Node 20 received no Nov 2026 fix. — [Node.js Nov 2026](https://nodejs.org/en/blog/vulnerability/november-2026-security-releases) [verified-primary]. Option names and defaults below are from the current Node.js API docs. — [Node.js http2 API](https://nodejs.org/api/http2.html) [verified-primary]

```ts
import http2 from 'node:http2';
import { readFileSync } from 'node:fs';

const server = http2.createSecureServer({
  key: readFileSync('key.pem'),
  cert: readFileSync('cert.pem'),
  // Incoming RST_STREAM rate limit (token bucket). Added v23.0.0 / v22.10.0.
  // "Both settings must be set to have any effect"; defaults 1000 and 33.
  streamResetBurst: 1000,
  streamResetRate: 33,
  maxSessionInvalidFrames: 1000,   // default 1000: close session after N invalid frames
  maxSessionRejectedStreams: 100,  // default 100: ENHANCE_YOUR_CALM rejections tolerated
  maxSessionMemory: 10,            // MB, credit-based; see CVE-2026-123868 for its known gap
  maxHeaderListPairs: 128,         // default 128 header entries
  settings: { maxConcurrentStreams: 100 },
});
```

- **nginx (self-hosted in front of Express or FastAPI).** Upgrade to at least 1.25.3 for Rapid Reset. Review 1.29.8+ for `max_headers`. — [search-summary sources above]. Keep `http2_max_concurrent_streams` (default 128) and `keepalive_requests` (default 1000) finite, and add `limit_conn`/`limit_req` per client. — [nginx ngx_http_v2_module](https://nginx.org/en/docs/http/ngx_http_v2_module.html) [prior-knowledge, not re-fetched; check that these directives still apply on the nginx version you run]
- **Apache httpd.** Upgrade to 2.4.71. Until then, removing `h2` from `Protocols` is Red Hat's workaround for CVE-2026-119618. — [cipherssecurity](https://cipherssecurity.com/apache-cve-2026-119618-http2-rce/) [search-summary, uncertain]
- **Envoy.** Upgrade to 1.35.11/1.36.7/1.37.3/1.38.1 or later (CVE-2026-47774). [search-summary]
- **Go.** Use a currently supported Go toolchain and golang.org/x/net. CVE-2023-39325 and CVE-2023-45288 were fixed in 1.21.3 and 1.21.9/1.22.2 respectively. [search-summary]

#### (f) Incomplete fixes
- Rate-limiting only client RST_STREAM leaves you exposed to MadeYouReset, where the server issues the resets. — [Imperva](https://www.imperva.com/blog/madeyoureset-turning-http-2-server-against-itself/) [search-summary]
- Trusting `maxSessionMemory` as a hard bound failed twice in Node in 2026: CVE-2026-56846 (retained headers) and CVE-2026-123868 (queued DATA) both bypassed it. — [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases); [Node.js Nov 2026](https://nodejs.org/en/blog/vulnerability/november-2026-security-releases) [verified-primary]
- A fix can be partial: CVE-2026-123865 is explicitly "an incomplete-fix case of CVE-2026-48937", and CVE-2026-123863 is "a variant of CVE-2024-27983". — [Node.js Nov 2026](https://nodejs.org/en/blog/vulnerability/november-2026-security-releases) [verified-primary]
- A CDN in front does not help if the origin's IP is reachable directly, because the attacker skips the edge. (Inference from the architecture.)
- Pinning a Docker base image tag such as `node:20` freezes you out of fixes, because Node 20 got no Nov 2026 patch. (Inference from the release page.)

#### (g) Verifying the fix
- CI gate that fails before and passes after: assert `process.versions.node` ≥ the minimum patched version for its major. Or run `npx is-my-node-vulnerable` in CI. Apply the same to `nginx -v`, `httpd -v` and `envoy --version` in the image build.
- Config assertion test: start the server in a test and assert that `server` was created with `streamResetBurst`/`streamResetRate` both set (the docs say one alone has no effect). — [Node.js http2 API](https://nodejs.org/api/http2.html) [verified-primary]
- Exposure check: `curl --http2 -sI https://<origin-ip>` should time out or be refused once the origin is locked to the CDN.

### Inferences
- Most vibe-stack apps (Next.js on Vercel, Netlify sites, apps behind Cloudflare) do not terminate client HTTP/2 themselves, so Rapid Reset-class risk sits with the platform. The developer's share is (1) not leaking a directly reachable origin and (2) patching self-hosted terminators.
- The 2026 wave (HTTP/2 Bomb, a dozen Node `node:http2` CVEs, three Apache mod_http2 releases) suggests HTTP/2 server code is still being actively mined, partly with AI tooling. A self-hosted HTTP/2 listener should be treated as a component that needs monthly patching.
- AI assistants asked to "enable HTTP/2" for an Express app plausibly reach for `http2.createSecureServer` with `allowHTTP1: true` and no limits. The safer suggestion is to enable HTTP/2 on the proxy or CDN. (Pattern reasoning; I found no empirical study of assistant output.)

### Gaps
- I could not confirm Node.js, nginx, Go or Envoy status for MadeYouReset (CVE-2025-8671). The CERT/CC vendor table was not readable via search.
- Envoy's Rapid Reset fixed versions conflict between sources.
- I could not open the official nginx changelog to confirm whether 1.29.8's `max_headers` was released before the HTTP/2 Bomb disclosure, or whether later nginx releases added HTTP/2 Bomb changes.
- I found no Vercel or Netlify statement specific to HTTP/2 Bomb (2026).
- CVE-2026-119618 (Apache) details remain thin and partly contradictory.

---

## 2. HTTP request smuggling (CL.TE, TE.CL, TE.TE, H2.CL/H2.TE, CL.0, client-side desync, 0.CL / Expect-based desync)

### Takeaway
Smuggling happens when two HTTP/1.1 parsers in a chain (CDN or proxy, then origin) disagree about where a request ends. The attacker's extra bytes are then read as the start of the *next* user's request. The 2025 "HTTP/1.1 must die" research found Expect-based and 0.CL desyncs in Akamai, Cloudflare, Netlify, T-Mobile and GitLab infrastructure. Parser leniency bugs kept appearing through 2026: Node CVE-2026-58044, Gunicorn hardening releases, Kestrel CVE-2025-55315, h11 CVE-2025-43859 and Pingora CVE-2025-4366. Developer-owned fixes:
- never enable Node's `--insecure-http-parser` / `insecureHTTPParser`;
- keep the origin's HTTP stack (llhttp, h11/httptools, gunicorn) patched;
- prefer HTTP/2 end to end where the proxy supports it;
- make the front-end reject or normalize ambiguous framing.

### Cited Findings

#### (a) Mechanism
- **Root cause.** HTTP/1.1 offers two body-length mechanisms, `Content-Length` (CL) and `Transfer-Encoding: chunked` (TE). RFC 9112 §6.1 says a sender MUST NOT send both. A server receiving both MAY reject the request or MUST let TE override, and MUST close the connection afterwards. Connection reuse ("keep-alive") between proxy and origin is what lets leftover bytes poison another user's request. — [RFC 9112 §6.1/§6.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.1) [prior-knowledge, not re-fetched]
- **Variants** (canonical taxonomy from PortSwigger) — [PortSwigger 2019 "HTTP Desync Attacks"](https://portswigger.net/research/http-desync-attacks-request-smuggling-reborn); [2021 "HTTP/2: The Sequel is Always Worse"](https://portswigger.net/research/http2); [2022 "Browser-Powered Desync Attacks"](https://portswigger.net/research/browser-powered-desync-attacks) [prior-knowledge, not re-fetched]:
  - **CL.TE / TE.CL.** Front-end honours CL and back-end honours TE, or the reverse.
  - **TE.TE.** Both support TE, but one is induced to ignore an obfuscated `Transfer-Encoding` (odd whitespace, duplicate headers, `xchunked`).
  - **H2.CL / H2.TE.** An HTTP/2 front-end downgrades to HTTP/1.1 upstream and passes through a `content-length` that disagrees with the h2 frame length, or a `transfer-encoding` header, both of which RFC 9113 says make the message malformed.
  - **CL.0.** The back-end ignores CL on some endpoint (e.g. static files, redirects) and treats the body as the next request.
  - **Client-side desync.** The *browser's* connection to a single server is desynchronized, with no proxy needed.
  - **Pause-based desync.** The server times out mid-body but keeps the connection open.
- **0.CL and Expect-based desync (2025).** In a 0.CL desync the front-end ignores CL but the back-end waits for the body, which deadlocks. Kettle's key insight is that escaping the deadlock needs an "early-response gadget", i.e. a way to make the back-end answer before the body arrives. The `Expect: 100-continue` handshake, including obfuscated values such as `Expect: y 100-continue`, turned out to create such framing disagreements. Findings he lists: a "vanilla Expect 0.CL desync against T-Mobile" and "an obfuscated-Expect 0.CL desync against GitLab" (h1.sec.gitlab.net). — [PortSwigger "HTTP/1.1 must die" research page](https://portswigger.net/research/http1-must-die); [whitepaper PDF](https://portswigger.net/kb/papers/dzmxreq/http1-must-die.pdf); [Black Hat USA 2025 white paper](https://i.blackhat.com/BH-USA-25/Presentations/US-25-Kettle-HTTP1-Must-Die-The-Desync-Endgame-wp.pdf) [search-summary]
- Impact classes: bypassing front-end access controls (e.g. reaching `/admin` that the CDN blocks), capturing other users' requests and cookies, response-queue poisoning, and turning a cache into a poisoning amplifier.

#### (b) Incidents and CVEs (historical, then 2024–2026)
- **"HTTP/1.1 must die" (James Kettle, Black Hat USA and DEF CON, Aug 2025).** — [PortSwigger PDF](https://portswigger.net/kb/papers/dzmxreq/http1-must-die.pdf); [Black Hat slides](https://i.blackhat.com/BH-USA-25/Presentations/US-25-Kettle-HTTP1-Must-Die-The-Desync-Endgame-Wednesday.pdf) [search-summary]
  - **Akamai CVE-2025-32094.** A 0.CL/CL.0 desync via an obfuscated `Expect` header. $9,000 bounty. Some customers received a hotfix quickly; full resolution took 65 days.
  - **Netlify CDN.** A CL.0 response-queue issue triggered by a plain `Expect` header could hijack responses for sites on Netlify. Netlify reportedly declared customer sites out of scope and paid no bounty.
  - **Cloudflare.** A desync was reported and patched quickly. The "~24M sites / $7,000" figures appear only in secondary write-ups ([vulnsy cheat sheet](https://www.vulnsy.com/cheat-sheets/http-request-smuggling)) and are **unverified**. The roughly $350k total bounty figure is also unverified.
  - Kettle's thesis: HTTP/1.1 between proxies and origins is the root problem, so "HTTP/1 needs to die".
- **Cloudflare Pingora CVE-2025-4366 (reported Apr 11, mitigated Apr 12, 2025; blog May 22, 2025).** On a cache hit, unread request body bytes left on the HTTP/1.1 connection could act as a smuggled request. Exposure was limited to a subset of Free-plan traffic during a Pingora caching rollout. Cloudflare found no evidence of exploitation and invalidated cached assets. OSS Pingora users should upgrade to ≥0.5.0. — [Cloudflare blog](https://blog.cloudflare.com/resolving-a-request-smuggling-vulnerability-in-pingora) [search-summary]
- **Node.js (llhttp):**
  - **CVE-2024-27982** (Apr 3, 2024; Medium): "if a space is placed before a content-length header, it is not interpreted correctly, enabling attackers to smuggle in a second request". Affected 18.x, 20.x and 21.x. — [Node.js Apr 2024](https://nodejs.org/en/blog/vulnerability/april-2024-security-releases) [verified-primary]
  - **CVE-2025-23167** (May 2025; Medium): Node 20's parser accepted `\r\n\rX` as the end of headers. Fixed by moving Node 20 to llhttp v9 (20.19.2, alongside 22.15.1, 23.11.1 and 24.0.2 in the same release). — [Node.js May 2025](https://nodejs.org/en/blog/vulnerability/may-2025-security-releases) [verified-primary]
  - **CVE-2026-58044** (Jul 29, 2026; Low): Node could omit headers beyond `maxHeadersCount`/`maxHeaderPairs` from `req.headers`/`req.rawHeaders` "while still using those omitted headers internally for HTTP message framing. In particular, Content-Length can be hidden from userland". This desyncs **Node-based forwarding proxies** that rebuild outbound headers from `req.headers` while piping the body to a reused backend connection. Fixed in 22.23.2, 24.18.1 and 26.5.1. — [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases) [verified-primary]
  - **CVE-2026-123864** (Nov 11, 2026; High): a parser re-entrancy bug, not smuggling. A zero-length TLS write from inside the parser's body callback re-enters `llhttp_execute()` and can copy other connections' memory (including TLS keys) into a request body. Fixed in 22.23.5, 24.22.3 and 26.13.1. — [Node.js Nov 2026](https://nodejs.org/en/blog/vulnerability/november-2026-security-releases) [verified-primary]
  - Historical: CVE-2023-30589 (TE header hidden inside another header's value). — [search summary](https://yadhu.in/2024/05/11/Exploiting-HTTP-Request-Smuggling-in-Node.js-and-Gunicorn/) [search-summary]
- **Python:**
  - **h11 CVE-2025-43859** (published Apr 24, 2025; GHSA-vqfr-h8mv-ghfj; CVSS 9.1 in most sources): lenient chunked-body line terminators. Exploitable only together with a proxy that also misparses chunked encoding. Fixed in **h11 0.16.0**, which is still the current release. — [GitLab advisory DB](https://advisories.gitlab.com/pkg/pypi/h11/CVE-2025-43859/) [search-summary]; h11 0.16.0 is latest on [PyPI](https://pypi.org/project/h11/) [verified-primary]
  - **Gunicorn.** OSV lists PYSEC-2026-1434 (published Jul 7, 2026; 8.2): conflicting `Transfer-Encoding` handling allowed endpoint-restriction bypass, fixed in 22.0.0. This looks like a late catalogue entry for the 2024 Gunicorn TE issue, which is my **uncertain** reading. Gunicorn 26.0.0 (May 2026) shipped a "Request Smuggling Hardening" pass, and 26.2.1 (Sept 5, 2026) bounded chunk-size and trailer lines. — [OSV PYSEC-2026-1434](https://osv.dev/vulnerability/PYSEC-2026-1434); [Gunicorn news](https://gunicorn.org/news/) [search-summary]. The current release is 27.0.1. — [PyPI](https://pypi.org/project/gunicorn/) [verified-primary]
- **ASP.NET Core Kestrel CVE-2025-55315** (Oct 14, 2025; Critical): a lone `\n` inside a chunk extension. When a front-end proxy treats lone LF as a line terminator, requests can be smuggled. — [Praetorian advisory](https://www.praetorian.com/advisories/aspnet-core-kestrel-request-smuggling/) [search-summary]

#### (c) Why vibe-coded apps are exposed; platform vs developer
- **Node's insecure parser.** Node documents that `--insecure-http-parser` and `insecureHTTPParser: true` accept, among other things:
  - messages "containing both Transfer-Encoding and Content-Length headers";
  - "extra data after message when Connection: close is present";
  - "\n to be used as token separator instead of \r\n";
  - "\r\n not to be provided after a chunk".

  The docs warn: "All the above will expose your application to request smuggling or poisoning attack. Avoid using this option." Node 26.3.0 adds `httpValidation: 'strict' | 'relaxed' | 'insecure'` (default `'strict'`), where `'insecure'` is "equivalent to insecureHTTPParser: true". — [Node.js CLI docs](https://nodejs.org/api/cli.html#--insecure-http-parser); [Node.js http docs](https://nodejs.org/api/http.html#httpcreateserveroptions-requestlistener) [verified-primary]
- **Platform side.** Vercel, Netlify and Cloudflare own the parsers at their edge and their edge-to-origin hop (e.g. the Netlify and Cloudflare issues above were fixed on the vendor side, and Pingora customers needed no action). — [Cloudflare blog](https://blog.cloudflare.com/resolving-a-request-smuggling-vulnerability-in-pingora) [search-summary]
- **Developer side.** The developer owns the origin's parser and every self-run proxy hop: nginx → Express, nginx → gunicorn/uvicorn, a hand-written Node proxy (`http-proxy`, `express-http-proxy`), or a Python ASGI server behind a load balancer. CVE-2026-58044 specifically targets Node apps that act as forwarding proxies. — [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases) [verified-primary]

#### (d) Safe self-testing
- Kettle's 2025 release came with updated tooling: the Burp extension HTTP Request Smuggler (v3) and the "HTTP Hacker" extension. Turbo Intruder ships 0.CL scripts. — [PortSwigger research page](https://portswigger.net/research/http1-must-die); [Turbo Intruder repo examples](https://github.com/PortSwigger/turbo-intruder/blob/master/resources/examples/0cl-find-offset.py) [search-summary]. Use only the *detection/scan* modes, only against hosts you own, and preferably on staging. Smuggling probes can affect other users' requests on shared connections.
- PortSwigger's guidance is that timing-based detection is safer than differential-response probes, because the latter can hit real users. — [Web Security Academy: request smuggling](https://portswigger.net/web-security/request-smuggling/finding) [prior-knowledge, not re-fetched]
- Config checks:
  - `grep -r "insecure-http-parser\|insecureHTTPParser\|httpValidation" .` plus `NODE_OPTIONS` in the deploy environment;
  - `pip show h11 gunicorn uvicorn` against the fixed versions;
  - nginx `proxy_http_version`/`keepalive` settings;
  - whether the origin is reachable directly (which bypasses the CDN's normalization).

#### (e) The fix
**Node / Express (origin):**

```ts
import http from 'node:http';
import express from 'express';

const app = express();
const server = http.createServer(
  {
    // Defaults are already safe; set them explicitly so a later "fix"
    // (often an AI-suggested one for an HPE_* parse error) shows up in review.
    insecureHTTPParser: false,   // default false; "Using the insecure parser should be avoided"
    requireHostHeader: true,     // 400 on HTTP/1.1 requests lacking Host
    // httpValidation: 'strict', // Node >= 26.3.0 only; cannot be combined with insecureHTTPParser
  },
  app,
);
server.listen(3000);
```

Option names are from [Node.js http docs](https://nodejs.org/api/http.html) [verified-primary]. Runtime: ≥22.23.5, ≥24.22.3 or ≥26.13.1 (Nov 2026 line), which includes the July CVE-2026-58044 fix. If your app is itself a forwarding proxy, forward `req.rawHeaders` faithfully or, better, use a proxy that re-frames requests. Never rebuild the request from a truncated `req.headers` while piping the original body. — [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases) [verified-primary]

**Python:**
- `h11>=0.16.0` — [GitLab advisory](https://advisories.gitlab.com/pkg/pypi/h11/CVE-2025-43859/) [search-summary]
- current gunicorn (27.x) — [PyPI](https://pypi.org/project/gunicorn/) [verified-primary]
- current uvicorn (0.54.0) — [PyPI](https://pypi.org/project/uvicorn/0.54.0/) [verified-primary]

`uvicorn[standard]` installs `httptools`, a second parser in addition to h11, so both need tracking.

**nginx front-end (defence in depth)** [prior-knowledge, not re-fetched; check against the docs for your nginx version]:

```nginx
# Edge proxy in front of Express / gunicorn / uvicorn.
upstream app {
    server 127.0.0.1:3000;
    keepalive 32;                     # upstream reuse: this is what makes origin parser strictness matter
}
server {
    listen 443 ssl;
    http2 on;                         # nginx >= 1.25.1 syntax; clients speak h2 to nginx
    location / {
        proxy_pass http://app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_request_buffering on;   # default: nginx reads the whole body, then re-frames it upstream
    }
}
```

With request buffering on (the default), nginx reads the full client body and sends its own framing upstream rather than relaying the client's. Turning buffering off for streaming uploads gives up some of that normalization. [prior-knowledge, not re-fetched; verify against the ngx_http_proxy_module docs]

**Architecture:**
- Use HTTP/2 (or HTTP/3) from client to edge **and** from edge to origin where the platform supports it. Kettle's conclusion is that upstream HTTP/1.1 is the root cause. — [PortSwigger](https://portswigger.net/research/http1-must-die) [search-summary]
- Avoid running a second HTTP/1.1 proxy layer (e.g. a Node proxy behind nginx behind a CDN) unless it is needed.
- Disable upstream connection reuse only as a last-resort mitigation, because it costs performance.

#### (f) Incomplete or incorrect fixes
- Adding `--insecure-http-parser` to fix "HPE_INVALID_HEADER_TOKEN" or "Parse Error" from a misbehaving client re-enables CL+TE acceptance and bare-LF terminators. — [Node.js CLI docs](https://nodejs.org/api/cli.html) [verified-primary]
- Patching only the edge. h11's CVE needed *both* a lenient proxy *and* a lenient origin. You do not control your CDN's next parser bug, so the origin must be strict too. — [GitLab advisory](https://advisories.gitlab.com/pkg/pypi/h11/CVE-2025-43859/) [search-summary]
- WAF signatures for `Transfer-Encoding: chunked` + `Content-Length` miss Expect-based and 0.CL desyncs, which need neither. — [PortSwigger](https://portswigger.net/research/http1-must-die) [search-summary]
- Upgrading Node on only one line. CVE-2025-23167 affected only Node 20 before llhttp 9, while CVE-2026-58044 affected 22.x, 24.x and 26.x. — [Node.js May 2025](https://nodejs.org/en/blog/vulnerability/may-2025-security-releases); [Node.js Jul 2026](https://nodejs.org/en/blog/vulnerability/july-2026-security-releases) [verified-primary]

#### (g) Verifying the fix (fails before, passes after)
- A conformance unit test against your own origin, run on localhost in CI. It sends one ambiguous request with both `Content-Length` and `Transfer-Encoding: chunked` over a raw socket and asserts a 400 and a closed connection. Node's docs list accepting both headers as a leniency of the *insecure* parser, so a strict server must reject it. Setting `insecureHTTPParser: true` makes the test fail, and removing it makes it pass. — [Node.js CLI docs](https://nodejs.org/api/cli.html) [verified-primary]

```ts
// test/framing.test.ts (node:test). Sends ONE malformed request to a local test server.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import net from 'node:net';
import { once } from 'node:events';
import { createServer } from '../src/server'; // returns the http.Server you ship

test('origin rejects requests with both Content-Length and Transfer-Encoding', async () => {
  const server = createServer();
  server.listen(0);
  await once(server, 'listening');
  const { port } = server.address() as net.AddressInfo;
  const sock = net.connect(port, '127.0.0.1');
  sock.write(
    'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n' +
    'Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n',
  );
  let data = '';
  sock.on('data', (c) => (data += c));
  await once(sock, 'close');
  assert.match(data, /^HTTP\/1\.1 400/);
  server.close();
});
```

- Also add a dependency gate: `npm ls` / `pip-audit` fails on h11 < 0.16.0, gunicorn versions below the current hardening line, or a Node runtime below the latest security patch.

### Inferences
- The most common vibe-coded smuggling exposure is not on Vercel or Netlify, where the platform owns both parsers. It is in "deploy to a VPS" templates: nginx → Node/gunicorn/uvicorn with keep-alive upstreams, often with an AI-suggested `--insecure-http-parser` or an outdated base image.
- AI-built "API gateway" or "proxy" features in Node, which forward requests to another service with `http.request` and `req.headers`, are exactly the shape CVE-2026-58044 describes. Developers should prefer maintained proxies.
- I found no evidence that Vercel or Netlify expose developer-controllable settings that could reintroduce smuggling, so on those platforms the developer's job reduces to keeping framework dependencies patched.

### Gaps
- I could not read Kettle's full 2025 paper. The complete vendor list, exact CVEs beyond Akamai's, and the specific defensive checklist are not captured here.
- I could not verify the 2025 "funky chunks" research on chunk line terminators (attributed in my memory to Jeppe Bonde Weikop) or map it to specific CVEs.
- I found no Next.js-specific smuggling CVE in 2024–2026.
- I could not confirm whether current nginx can proxy HTTP/2 to upstreams for ordinary `proxy_pass`; my prior knowledge is that it cannot (only 1.0/1.1). Envoy and HAProxy can.
- "TE.0" (2024) appears in a secondary cheat sheet. I did not verify it.

---

## 3. Web cache poisoning and web cache deception

### Takeaway
Poisoning means the attacker makes a shared cache store a *harmful* response under a key other users request. The usual inputs are an unkeyed header such as `X-Forwarded-Host`, parameter cloaking, a fat GET, or a framework-internal header. Deception means the attacker tricks the cache into storing a *victim's private* response by making a dynamic URL look static (`/account/x.css`, `/account;.js`, encoded delimiters). In 2024–2026, Next.js accumulated a long run of cache-poisoning advisories, mostly through internal headers like `x-now-route-matches`, `x-nextjs-data` and RSC/prefetch headers. Most of them affect only **self-hosted** deployments behind a generic CDN. The developer-owned fix:
- send `Cache-Control: private, no-store` on anything personalized;
- never let a CDN cache by extension when the origin's content type disagrees (Cloudflare Cache Deception Armor);
- keep Next.js on the latest patch;
- at a self-run CDN, strip framework-internal headers and key the cache on what the app varies on.

### Cited Findings

#### (a) Mechanism
- **Poisoning lineage:**
  - [Kettle 2018 "Practical Web Cache Poisoning"](https://portswigger.net/research/practical-web-cache-poisoning): unkeyed headers such as `X-Forwarded-Host` reflected into absolute URLs or script tags.
  - [Kettle 2020 "Web Cache Entanglement"](https://portswigger.net/research/web-cache-entanglement): parameter cloaking via parser disagreement on `;` versus `&`, fat GET (a body on a GET that the origin reads but the cache does not key), and cache-key normalization.

  [prior-knowledge, not re-fetched]
- **Deception lineage.** Omer Gil (Feb 2017; Black Hat USA 2017) showed PayPal pages like `/myaccount/home/foo.css` returning private HTML that a CDN cached by extension. — [Omer Gil blog](https://omergil.blogspot.com/2017/02/web-cache-deception-attack.html) [prior-knowledge, not re-fetched]. Cloudflare's response posts are [Understanding our cache and the WCD attack](https://blog.cloudflare.com/understanding-our-cache-and-the-web-cache-deception-attack) and [WCD revisited](https://blog.cloudflare.com/web-cache-deception-attack-revisited/) [search-summary: titles and URLs]
- **"Gotta cache 'em all: bending the rules of web cache exploitation"** was published by **Martin Doyhenard** of PortSwigger (not Kettle) on Aug 8, 2024, and presented at Black Hat USA and DEF CON 32 in August 2024. It covers URL-parser discrepancies between CDN and origin: delimiters (`;`, `.`, encoded `%23`, `%3f`, null bytes), path normalization (`..%2f`, encoded slashes) and static-directory or static-file rules, producing "static path deception" and cache-key confusion. — [PortSwigger research](https://portswigger.net/research/gotta-cache-em-all); [whitepaper PDF](https://portswigger.net/kb/papers/kapvrid/gotta-cache-em-all.pdf); [Web Security Academy: web cache deception](https://portswigger.net/web-security/web-cache-deception) [search-summary]
- **Cloudflare defaults.** Cloudflare caches by file extension, not MIME type, and "does not cache HTML or JSON by default". Caching HTML requires an explicit Cache Rule. — [Cloudflare default cache behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/) [search-summary]
- **Cloudflare Cache Deception Armor** is enabled inside a Cache Rule. It "will verify a URL's extension matches the returned Content-Type". On mismatch (e.g. `/newsfeed/foo.jpg` returning `text/html`) the response is not cached. Its limits:
  - `application/octet-stream` bypasses the check;
  - benign pairs such as `.jpg` served as `image/webp` are allowed;
  - "A Cache-Control header from the origin, or an Edge Cache TTL Cache Rule may override the protection";
  - per the Workers docs, any explicit `Cache-Control` directive skips the check.

  — [Cloudflare Cache Deception Armor docs](https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/); [Workers cache config](https://developers.cloudflare.com/workers/cache/configuration/) [search-summary]
- **Vercel defaults:**
  - Responses without caching headers get `public, max-age=0, must-revalidate`.
  - Vercel Function responses need an explicit `s-maxage` (or equivalent) to enter the CDN cache; "max-age alone … does not opt Function responses into CDN caching".
  - `private` prevents CDN storage, and `no-store` prevents CDN and browser storage.
  - Header precedence on Vercel's CDN is `Vercel-CDN-Cache-Control` > `CDN-Cache-Control` > `Cache-Control`. The first is not sent to browsers.
  - The function's header wins over `next.config.js`/`vercel.json`.
  - Vercel's CDN now respects `Cache-Control` from external origins by default (changelog).

  — [Vercel Cache-Control headers](https://vercel.com/docs/caching/cache-control-headers); [Vercel CDN Cache](https://vercel.com/docs/caching/cdn-cache); [Vercel changelog](https://vercel.com/changelog/vercels-cdn-now-respects-cache-control-headers-from-external-origins-by-default) [search-summary]

#### (b) Next.js and related CVEs (2024 → Nov 2026)
npm publish timestamps for the fixed versions below are verified. — [npm: next versions](https://www.npmjs.com/package/next?activeTab=versions) [verified-primary]

- **CVE-2024-46982 (GHSA-gp8f-8m3g-qvj9, High; Sept 2024).** Pages Router: a crafted request could make a non-dynamic SSR route cacheable. Affected ≥13.5.1 <13.5.7 and ≥14.0.0 <14.2.10. Fixed in **13.5.7 and 14.2.10** (14.2.10 published 2024-09-11). App-Router-only and Vercel-hosted deployments were not affected. Found by zhero; his follow-up says the `x-now-route-matches` header let an SSR request be treated like SSG. — [GitHub advisory](https://github.com/advisories/GHSA-gp8f-8m3g-qvj9); [zhero "Eclipse on Next.js"](https://zhero-web-sec.github.io/research-and-things/eclipse-on-nextjs-conditioned-exploitation-of-an-intended-race-condition) [search-summary]
- **CVE-2025-32421 (Low; 2025).** A race condition that caches a data (hydration) response in place of the page via `__nextDataReq` and a forged `x-now-route-matches`. Affected <14.2.24 and 15.0.0–<15.1.6. Fixed in **14.2.24 and 15.1.6**. The fix strips the header. For self-hosting, zhero advises stripping `x-now-route-matches` at the CDN and using `no-store` on at-risk responses. — [Vercel changelog CVE-2025-32421](https://vercel.com/changelog/cve-2025-32421); [zhero "the stale elixir"](https://zhero-web-sec.github.io/research-and-things/nextjs-cache-and-chains-the-stale-elixir) [search-summary]. zhero's earlier paper "Next.js and cache poisoning: a quest for the black hole" is referenced there; I could not retrieve it.
- **CVE-2025-49826 (High; cache poisoning leading to DoS; 2025).** Fixed in **15.1.8** (published 2025-05-22). The affected range is **reported inconsistently**: 15.0.4–15.1.8 (GitLab) versus ≥15.1.0 <15.1.8 (securityonline, which also mentions 15.2.0 and a 15.0.4 backport). — [GitLab advisory](https://advisories.gitlab.com/npm/next/CVE-2025-49826/); [securityonline](https://securityonline.info/next-js-flaw-cve-2025-49826-cvss-7-5-cache-poisoning-leads-to-denial-of-service/) [search-summary]
- **CVE-2025-57752 (Medium; Aug 2025).** Fixed in **14.2.31 and 15.4.5**. One aggregator describes it as Image Optimization content injection. My prior knowledge is that it was "cache key confusion for Image Optimization API routes", where responses varying on request headers were cached and served cross-user. **Description unverified.** — [Hacktron changelog](https://www.hacktron.ai/tools/security-changelog/nextjs) [search-summary]
- **CVE-2025-29927 (Critical; Mar 2025).** See §4. It is a header-trust bug, but it also bypassed middleware-based cache-header logic.
- **May 2026 release (13 advisories; fixed in 15.5.18 and 16.2.6).** It covers DoS, middleware/proxy bypass, SSRF, cache poisoning and XSS. Vercel deployed no new WAF rules for it. **CVE-2026-44572** (GHSA-3g8h-86w9-wvmq, Low): sending `x-nextjs-data` to a middleware/proxy path that redirects replaces the `Location` header, and if a CDN caches that 3xx, the path is down until the cache clears. Patched in 15.5.16 and 16.2.5. Interim workaround: vary the CDN cache key on `x-nextjs-data`. — [Vercel changelog May 2026](https://vercel.com/changelog/next-js-may-2026-security-release); [GitHub advisory](https://github.com/advisories/GHSA-3g8h-86w9-wvmq) [search-summary]
- **Sept 30, 2026 — CVE-2026-94543 (GHSA-4jqv-mc3x-m676, Medium 6.3).** In **self-hosted** Pages Router apps with SSG/ISR, a page's cache entry could be replaced by another route's content until revalidation. Fixed in **15.5.27 and 16.3.8**. Vercel deployments are not affected. A separate advisory, wording seen only in a Renovate PR, describes root-level catch-all plus SSG/ISR cross-user content substitution from "a single unauthenticated crafted request"; its CVE mapping is **unconfirmed**. — [GitHub advisory](https://github.com/advisories/GHSA-4jqv-mc3x-m676); [Next.js Sept 2026 release](https://nextjs.org/blog/september-2026-security-release); [nocodb PR](https://github.com/nocodb/nocodb/pull/14907) [search-summary]
- **Nov 3, 2026 release (7 advisories; fixed in 16.4.5 and 15.5.29; npm-verified 2026-11-03).** — [Netlify changelog](https://www.netlify.com/changelog/2026-11-03-nextjs-security-vulnerabilities/) [search-summary]
  - GHSA-vvgp-ww4w-46vf: in 16.4+ apps using Cache Components, one request can make valid pages return a cached 404.
  - GHSA-rhh4-g77r-r9qj: binary-argument `use cache` poisoning.
  - GHSA-mfr8-8qww-v76h: `unstable_cache`/nested root-param leak. Severity is inconsistent (blog "High" versus GHSA Moderate 6.3).
  - Also: "cross-client response injection in self-hosted apps", HttpOnly cookie exposure on Edge routes, and an SVG image-optimization bypass.
  - Netlify users also need the adapter **@netlify/plugin-nextjs 5.16.6** (5.16.7 is current on npm).
  - `next@latest` is **16.4.6** (2026-11-09) and the `backport` tag is 15.5.29. — [npm](https://www.npmjs.com/package/next) [verified-primary]

#### (c) Why vibe-coded apps are prone; platform vs developer
- **On Vercel**, several of these were not exploitable (CVE-2024-46982, CVE-2026-94543, CVE-2025-29927) because Vercel's routing and cache layer handles Next's internal headers itself. — [GitHub advisories above]; [Help Net Security](https://helpnetsecurity.com/?p=325795) [search-summary]. **Self-hosted Next.js** (Docker or VPS, `next start` behind Cloudflare, nginx or a generic CDN) carries the risk.
- **Platform-owned:** Cloudflare's refusal to cache HTML/JSON by default and Vercel's refusal to CDN-cache function output without `s-maxage` are both safe defaults. — [Cloudflare default cache behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/); [Vercel Cache-Control docs](https://vercel.com/docs/caching/cache-control-headers) [search-summary]
- **Developer-owned:** the developer *overrides* those defaults:
  - a Cloudflare "Cache Everything" rule or an Edge Cache TTL rule (which overrides Cache Deception Armor);
  - `Cache-Control: public, s-maxage=…` on routes that read cookies or headers;
  - an `export const revalidate`/ISR on pages that render per-user data;
  - not adding `Vary` for headers the response depends on.

  — [Cloudflare Cache Deception Armor](https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/) [search-summary]

#### (d) Safe self-testing
- **Never test poisoning on a live cache key that real users hit.** Always add a unique cache-buster query parameter (e.g. `?cb=<random>`) so a successful poison affects only your own key. This is PortSwigger's standard methodology. — [Web Security Academy: cache poisoning](https://portswigger.net/web-security/web-cache-poisoning) [prior-knowledge, not re-fetched]
- **Tools:** Burp's **Param Miner** ("Guess headers"/"Guess params") finds unkeyed inputs. PortSwigger's WCD labs cover delimiter and normalization discrepancies. — [Web Security Academy: web cache deception](https://portswigger.net/web-security/web-cache-deception) [search-summary for the labs; Param Miner is prior-knowledge]
- **Manual deception check** (logged in as a *test* user):
  1. Request `/account/x.css`, `/account;x.css`, `/account%2fx.css` and `/account.json`, each with a cache-buster.
  2. Inspect `cf-cache-status`, `x-vercel-cache` and `age`.
  3. Repeat the same URL without cookies. A `HIT` with the test user's data is a finding.
- **Next.js self-hosted check:** send requests with `x-now-route-matches`, `x-nextjs-data`, `x-middleware-subrequest` and `rsc`/`next-router-prefetch` headers plus a cache-buster. Check that the CDN either strips them or that the response is `private`/`no-store`.

#### (e) The fix
**Express / Node origin.** Mark personalized responses private by default:

```ts
import express from 'express';
const app = express();

// 1) Anything behind auth: never storable by shared caches.
app.use('/api', (req, res, next) => {
  res.set('Cache-Control', 'private, no-store');
  res.vary('Cookie');           // defence in depth for caches that ignore private
  res.vary('Authorization');
  next();
});

// 2) Serve static assets only from a dedicated prefix, by real files, never by extension sniffing.
app.use('/static', express.static('public', { immutable: true, maxAge: '1y', fallthrough: false }));

// 3) Strict routing: /account/x.css must 404, not render /account.
app.set('strict routing', true);
```

`private` and `no-store` semantics are as in [Vercel docs](https://vercel.com/docs/caching/cache-control-headers) [search-summary] and [RFC 9111 §5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2) [prior-knowledge]. `fallthrough: false` and `strict routing` are Express settings [prior-knowledge, not re-fetched]. Express 5's path-to-regexp v8 also no longer matches arbitrary suffixes by default [prior-knowledge, **uncertain**].

**Next.js (App Router) route handler that reads the session:**

```ts
// app/api/me/route.ts
import { cookies } from 'next/headers';
export const dynamic = 'force-dynamic';
export async function GET() {
  const session = (await cookies()).get('session');
  // ...
  return Response.json(data, { headers: { 'Cache-Control': 'private, no-store' } });
}
```

On Vercel, add `s-maxage` (or `Vercel-CDN-Cache-Control`) **only** to responses that are identical for every user. — [Vercel docs](https://vercel.com/docs/caching/cache-control-headers) [search-summary]

**Self-hosted Next.js behind nginx or a CDN:**
- Upgrade to `next@16.4.6` (or 15.5.29 on the backport line). — [npm](https://www.npmjs.com/package/next) [verified-primary]
- Strip framework-internal request headers at the edge:

```nginx
proxy_set_header x-middleware-subrequest "";
proxy_set_header x-now-route-matches "";
proxy_set_header x-nextjs-data "";      # only if you do not rely on client-side data requests
```

  This follows the guidance in [zhero](https://zhero-web-sec.github.io/research-and-things/nextjs-cache-and-chains-the-stale-elixir) and the [CVE-2026-44572 advisory](https://github.com/advisories/GHSA-3g8h-86w9-wvmq) [search-summary]. Note that stripping `x-nextjs-data` can break Pages Router client navigation. The advisory's alternative is to **vary the cache key** on it.
- Only cache what Next marks as cacheable (`s-maxage`) and never override with a blanket TTL.

**Cloudflare in front of any origin:**
- Leave HTML and JSON uncached unless a rule targets anonymous-only paths.
- Enable **Cache Deception Armor** on any rule that caches by extension.
- Do not set an Edge Cache TTL on rules that cover authenticated paths, because it overrides the Armor.
- Add "bypass cache when cookie present" logic for session cookies.

— [Cloudflare docs](https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/) [search-summary]

**Python (FastAPI):** set `response.headers["Cache-Control"] = "private, no-store"` on authenticated routes, or in middleware for an `/api` prefix. Do not mount catch-all routes that ignore trailing path segments.

#### (f) Incomplete fixes
- `Cache-Control: no-cache` alone *permits storage* (it requires revalidation, not non-storage). Use `no-store` and/or `private`. — [RFC 9111 §5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2) [prior-knowledge]
- Relying on Cloudflare Cache Deception Armor while also sending explicit `Cache-Control` or an Edge TTL: either one disables the check. — [Cloudflare docs](https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/); [Workers docs](https://developers.cloudflare.com/workers/cache/configuration/) [search-summary]
- Blocking `.css`/`.js` suffixes on dynamic routes but not delimiter or encoding variants (`;`, `%2f`, `%23`, `..%2f`), which Doyhenard showed CDNs and origins parse differently. — [PortSwigger](https://portswigger.net/research/gotta-cache-em-all) [search-summary]
- Upgrading Next.js but leaving a generic CDN that forwards and caches on framework-internal headers. Several advisories are triggered *only* through a caching layer the developer configured (CVE-2026-44572's impact "depends on a caching CDN or reverse proxy storing that 3xx response"). — [GitHub advisory](https://github.com/advisories/GHSA-3g8h-86w9-wvmq) [search-summary]
- Netlify users upgrading `next` without updating the OpenNext adapter (`@netlify/plugin-nextjs` ≥5.16.6) for the Nov 2026 batch. — [Netlify changelog](https://www.netlify.com/changelog/2026-11-03-nextjs-security-vulnerabilities/) [search-summary]

#### (g) Verifying the fix
- **Integration test against staging:**
  1. Log in as a test user and `GET /account/test.css?cb=<uuid>`.
  2. Assert that the response is not a 200 HTML page *or* carries `Cache-Control` containing `no-store`/`private`.
  3. `GET` the same URL without cookies and assert no `HIT` and no test-user data.

  This fails when a "Cache Everything" rule plus extension routing is present and passes once Armor, `private` and strict routing are in place.
- **Header-injection regression test** (self-hosted Next): for each internal header (`x-now-route-matches`, `x-nextjs-data`, `x-middleware-subrequest`), send it with a cache-buster. Then send a clean request with the same cache-buster and assert identical status and body to a baseline.
- **Dependency gate:** fail CI if `next` < 16.4.5 (or < 15.5.29 on 15.x).

### Inferences
- For vibe-coded Next.js apps, the hosting choice dominates. On Vercel most Next cache-poisoning CVEs were not exploitable. A "Dockerize my Next app and put Cloudflare in front" setup, which AI assistants commonly produce, inherits them all and adds CDN-rule mistakes.
- The highest-frequency deception bug in AI-generated Express or FastAPI apps is likely a catch-all or lenient route (e.g. `/account*`, `/{path:path}`, SPA fallbacks) combined with a CDN rule that caches by extension. (Pattern reasoning; I found no prevalence data.)
- Next.js shipped cache-related advisories in May, Sept and Nov 2026, so a patch cadence of "within days of each Next security release" is a realistic requirement for self-hosters.

### Gaps
- I could not read the official Nov 2026 Next.js blog to confirm per-advisory CVE IDs, ranges and which advisories affect Vercel-hosted apps.
- The CVE-2025-49826 affected range conflicts between sources. The CVE-2025-57752 description is unverified.
- Netlify's own CDN caching defaults for SSR/functions (e.g. `Netlify-CDN-Cache-Control`) were not researched in this pass.
- The July 2026 "CVE-2026-64642" Next.js middleware bypass (Turbopack plus a single i18n locale) appears only in a third-party blog ([checkyourvibe](https://checkyourvibe.dev/blog/vulnerabilities/nextjs-middleware-bypass)), so it is **unverified**.

---

## 4. Spoofed client-IP headers (X-Forwarded-For etc.), plus the Next.js `x-middleware-subrequest` bypass (CVE-2025-29927)

### Takeaway
`X-Forwarded-For` is a client-writable list: every proxy *appends*, so only entries added by proxies you trust are trustworthy. Code that takes the leftmost value, or `trust proxy: true`, `--forwarded-allow-ips='*'` or `x-real-ip` off-platform, lets any client choose its IP, which defeats rate limits, IP allowlists, geo rules and audit logs. The correct algorithm walks XFF right to left, skipping trusted proxies, and takes the first untrusted address, or uses a platform-set header that the platform overwrites. CVE-2025-29927 is the same bug class: Next.js trusted an internal header (`x-middleware-subrequest`) that any client could send, which skipped all middleware including auth.

### Cited Findings

#### (a) Mechanism
- **express-rate-limit's built-in validations** (v8.7.4 source) encode the failure modes directly:
  - `ERR_ERL_PERMISSIVE_TRUST_PROXY`: "The Express 'trust proxy' setting is true, which allows anyone to trivially bypass IP-based rate limiting."
  - `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR`: "The 'X-Forwarded-For' header is set but the Express 'trust proxy' setting is false (default)…" (i.e. you are probably rate-limiting your proxy's IP, so every user shares one bucket).
  - `ERR_ERL_FORWARDED_HEADER`: the RFC 7239 `Forwarded` header is present but ignored.
  - `ERR_ERL_KEY_GEN_IPV6`: "Custom keyGenerator appears to use request IP without calling the ipKeyGenerator helper function for IPv6 addresses. This could allow IPv6 users to bypass limits."

  Other codes include `ERR_ERL_IPV6_SUBNET`, `ERR_ERL_IPV6SUBNET_OR_KEYGENERATOR`, `ERR_ERL_UNDEFINED_IP_ADDRESS` and `ERR_ERL_INVALID_IP_ADDRESS`. — [express-rate-limit 8.7.4 dist/index.cjs](https://unpkg.com/express-rate-limit@8.7.4/dist/index.cjs) [verified-primary]
- **IPv6.** One user controls at least a /64 (often a /56 or /48), so per-address keys are trivially rotated. express-rate-limit v8's default key generator masks IPv6 to **/56** (`ipKeyGenerator(ip, ipv6Subnet = 56)`). The `ipv6Subnet` option accepts an integer 32–64, a function, or `false`. IPv4-mapped IPv6 (`::ffff:a.b.c.d`) is converted to IPv4 first. — [express-rate-limit 8.7.4 source and README](https://www.npmjs.com/package/express-rate-limit) [verified-primary]
- **CVE-2026-30827 (GHSA-46wh-pxpv-q5gq).** In express-rate-limit **8.0.0–8.2.1**, the default key generator applied /56 masking to IPv4-mapped addresses, so **all IPv4 clients shared one bucket**, an asymmetric DoS. Fixed in **8.2.2, 8.1.1 and 8.0.2**. Current is **8.7.4** (registry modified 2026-11-09). — [OSV CVE-2026-30827](https://osv.dev/vulnerability/CVE-2026-30827) [search-summary]; npm version [verified-primary]
- **Correct trust algorithm.** uvicorn's `ProxyHeadersMiddleware` (0.54.0) walks `X-Forwarded-For` **in reverse** and returns the first host not in the trusted set ("each proxy appends to the header list so check it in reverse order"). With `'*'` (`always_trust`) it returns `x_forwarded_for_hosts[0]`, the **leftmost, client-controlled** entry. — [uvicorn 0.54.0 source `uvicorn/middleware/proxy_headers.py`](https://pypi.org/project/uvicorn/0.54.0/) [verified-primary]. Express's `req.ip` comes from `proxy-addr`, which walks addresses "ordered from closest to furthest" and returns the first untrusted one. It accepts the names `loopback`, `linklocal` and `uniquelocal` as well as IPs/CIDRs. — [proxy-addr README](https://www.npmjs.com/package/proxy-addr) [verified-primary]. With `trust proxy` set to `true`, Express treats the leftmost entry as the client. — [Express "behind proxies"](https://expressjs.com/en/guide/behind-proxies.html) [prior-knowledge, not re-fetched]
- **CVE-2025-29927 (Mar 2025, Critical).** Next.js used an internal `x-middleware-subrequest` header to mark recursive middleware calls and skipped middleware when it was present. Any client could send it, bypassing auth, redirects and CSP set in middleware. Fixed in **15.2.3, 14.2.25, 13.5.9 and 12.3.5**. Affected ranges were roughly 11.1.4 to <13.5.9, 14.0 to <14.2.25 and 15.0 to <15.2.3. Researchers: zhero and inzo_. — [Help Net Security](https://helpnetsecurity.com/?p=325795); [Miggo](https://miggo.io/post/next-js-middleware-authorization-bypass-exploit-cve-2025-29927); [Datadog Security Labs](https://securitylabs.datadoghq.com/articles/nextjs-middleware-auth-bypass/) [search-summary]. npm publish dates: 14.2.25 on 2025-03-17 and 15.2.3 on 2025-03-18. [verified-primary]

#### (b) Incidents / CVEs
- **CVE-2025-29927.** Not affected: Vercel-hosted apps, Netlify-hosted apps and static exports. Cloudflare published a managed WAF rule. Sources disagree on whether it was on by default; the better-supported account says it was **opt-in**, because some third-party auth vendors legitimately send the header. — [Help Net Security](https://helpnetsecurity.com/?p=325795); [Miggo](https://miggo.io/post/next-js-middleware-authorization-bypass-exploit-cve-2025-29927); contra [Socket](https://socket.dev/blog/next-js-patches-critical-middleware-vulnerability) [search-summary]
- **express-rate-limit CVE-2026-30827** (above).
- **Later Next.js middleware/proxy bypasses.** The May 2026 batch (fixed in 15.5.18 and 16.2.6) included several "middleware and proxy bypass" advisories, e.g. an auth bypass via an App Router segment-prefetch URL. — [Vercel changelog May 2026](https://vercel.com/changelog/next-js-may-2026-security-release) [search-summary]. (Next.js 16 renamed `middleware` to `proxy`, which the advisory titles "Middleware / Proxy" reflect.)

#### (c) Platform-provided headers; what is mitigated vs developer-owned
- **Vercel:**
  - `x-forwarded-for` is set by Vercel. `x-vercel-forwarded-for` "is identical to the x-forwarded-for header. However, x-forwarded-for could be overwritten if you're using a proxy on top of Vercel."
  - A custom client-supplied `X-Forwarded-For` is honoured only via an Enterprise "trusted proxy".

  — [Vercel request headers](https://vercel.com/docs/headers/request-headers) [search-summary]
  - `@vercel/functions` `ipAddress(request)` returns `x-real-ip` and nothing else (`IP_HEADER_NAME = "x-real-ip"`, "Client IP as calculated by Vercel Proxy"). — [@vercel/functions 3.11.3 headers.js](https://unpkg.com/@vercel/functions@3.11.3/headers.js) [verified-primary]. **Implication:** this is safe only on Vercel. Self-hosted, `x-real-ip` is whatever the client or your proxy sends.
  - Next.js removed `request.ip`/`request.geo` from `NextRequest` (no such members in `next@16.4.6` type definitions). — [next 16.4.6 `dist/server/web/spec-extension/request.d.ts`](https://www.npmjs.com/package/next) [verified-primary]
- **Cloudflare:**
  - Cloudflare adds `CF-Connecting-IP` and recommends that apps read it instead of `X-Forwarded-For`. It is sent only on edge-to-origin traffic.
  - It is trustworthy only if the origin accepts connections **solely** from Cloudflare: firewall to Cloudflare's published IP ranges (refreshed periodically), Cloudflare Tunnel, or **Authenticated Origin Pulls** (mTLS).
  - Using `real_ip_header CF-Connecting-IP` without `set_real_ip_from` scoping "turns your logs into fiction".

  — [Cloudflare: restoring original visitor IPs](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/); [Cloudflare HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/); [stackharbor guide](https://stackharbor.com/en/knowledge-base/cfops-real-client-ip-at-origin/) [search-summary]
- **Netlify:** staff say they "make no guarantees on anything except `X-Nf-Client-Connection-Ip`". Edge Functions expose `context.ip` (weaker sourcing). The header is absent under `netlify dev`. — [Netlify support forum](https://answers.netlify.com/t/is-the-client-ip-header-going-to-be-supported-long-term/11203) [search-summary]
- **Python servers:**
  - **uvicorn 0.54.0:** `--proxy-headers` defaults to **on**. `--forwarded-allow-ips` accepts "IP Addresses, IP Networks, or literals (e.g. UNIX Socket path)" and defaults to `$FORWARDED_ALLOW_IPS` or `'127.0.0.1,::1'`. "The literal '*' means trust everything." — [uvicorn 0.54.0 `main.py`](https://pypi.org/project/uvicorn/0.54.0/) [verified-primary]
  - **gunicorn 27.0.1:** `--forwarded-allow-ips` defaults to `FORWARDED_ALLOW_IPS` or `"127.0.0.1,::1"`. — [gunicorn 27.0.1 `config.py`](https://pypi.org/project/gunicorn/27.0.1/) [verified-primary]. One user reports the uvicorn worker under gunicorn ignoring gunicorn's setting. — [FastAPI "behind a proxy"](https://fastapi.tiangolo.com/advanced/behind-a-proxy/) and search results [search-summary, uncertain]
  - **werkzeug 3.1.9** `ProxyFix(app, x_for=1, x_proto=1, x_host=0, …)` trusts exactly *N* hops. — [werkzeug 3.1.9 `middleware/proxy_fix.py`](https://pypi.org/project/Werkzeug/3.1.9/) [verified-primary]

#### (d) Safe self-testing
- **Rate-limit spoof test.** Send N+1 requests to a rate-limited endpoint, each with a different `X-Forwarded-For: 203.0.113.<i>` (and separately `X-Real-IP`, `CF-Connecting-IP`, `True-Client-IP`, `X-Client-IP`). If the limit never triggers, the key is client-controlled.
- **Allowlist test.** Call an IP-restricted admin route with `X-Forwarded-For: 127.0.0.1` and `X-Forwarded-For: <office IP>`.
- **Direct-origin test.** Hit the origin IP directly with a forged `CF-Connecting-IP`. If it is accepted, the origin is not locked to the CDN.
- **express-rate-limit** prints the validation errors above at startup or first request. Treat any `ERR_ERL_*` log line as a failing check. — [express-rate-limit source](https://unpkg.com/express-rate-limit@8.7.4/dist/index.cjs) [verified-primary]
- **CVE-2025-29927 check** (self-hosted Next): request a middleware-protected path with `x-middleware-subrequest` set. A patched version, or an edge that strips the header, should still redirect to login. Run it only against your own deployment.

#### (e) The fix
**Express (TypeScript) behind exactly one proxy/LB** (e.g. nginx on the same host, or one cloud LB):

```ts
import express from 'express';
import { rateLimit, ipKeyGenerator } from 'express-rate-limit'; // v8.7.x

const app = express();
// Trust exactly what is in front of you. Pick ONE:
app.set('trust proxy', 1);                 // one hop (single LB / nginx)
// app.set('trust proxy', 'loopback');     // nginx on the same host
// app.set('trust proxy', ['10.0.0.0/8']); // your LB subnet
// NEVER: app.set('trust proxy', true)     // -> ERR_ERL_PERMISSIVE_TRUST_PROXY

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 10,
  standardHeaders: 'draft-8',
  legacyHeaders: false,
  ipv6Subnet: 56, // default; 64 is laxer, 48 stricter
});

// Custom key (IP + account): must wrap the IP in ipKeyGenerator, or ERR_ERL_KEY_GEN_IPV6 fires.
const perAccount = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 5,
  keyGenerator: (req) => `${ipKeyGenerator(req.ip ?? '')}:${String(req.body?.email ?? '')}`,
});
app.post('/login', express.json(), loginLimiter, perAccount, handler);
```

Option names and signature are from express-rate-limit 8.7.4: `ipKeyGenerator(ip: string, ipv6Subnet?: number | false)`, `ipv6Subnet`, `limit`, `standardHeaders: 'draft-6'|'draft-7'|'draft-8'`, and `validate`. Note that `ipv6Subnet` combined with a custom `keyGenerator` raises `ERR_ERL_IPV6SUBNET_OR_KEYGENERATOR`. — [npm express-rate-limit](https://www.npmjs.com/package/express-rate-limit) [verified-primary]. Use a shared `store` (Redis etc.) on serverless or multi-instance hosts. In-memory counts are per instance. — [README](https://www.npmjs.com/package/express-rate-limit) [verified-primary]

**Next.js on Vercel (middleware/proxy or route handler):**

```ts
import { ipAddress } from '@vercel/functions';
import type { NextRequest } from 'next/server';
export function getClientIp(req: NextRequest): string {
  // Reads x-real-ip, which Vercel's proxy sets. Do NOT reuse this helper off Vercel.
  return ipAddress(req) ?? 'unknown';
}
```

Per [@vercel/functions 3.11.3](https://unpkg.com/@vercel/functions@3.11.3/headers.js) [verified-primary]. For rate limiting on Vercel, combine this with a shared store, or use the platform's own WAF rate-limit rules (not researched here).

**Netlify Functions:** `req.headers.get('x-nf-client-connection-ip')`, or `context.ip` in Edge Functions. — [Netlify forum](https://answers.netlify.com/t/is-the-client-ip-header-going-to-be-supported-long-term/11203) [search-summary]

**Cloudflare in front of nginx** [prior-knowledge, not re-fetched; directive names are long-standing ngx_http_realip_module]:

```nginx
# Generate this list from https://www.cloudflare.com/ips-v4 and /ips-v6 and refresh it on a schedule.
set_real_ip_from 173.245.48.0/20;   # ...one line per Cloudflare range
real_ip_header   CF-Connecting-IP;
# Lock the origin: only Cloudflare may connect (or use Cloudflare Tunnel / Authenticated Origin Pulls)
# ssl_client_certificate /etc/nginx/certs/cloudflare-origin-pull-ca.pem;
# ssl_verify_client on;
location / {
  proxy_set_header X-Forwarded-For $remote_addr;   # overwrite, do not append client-supplied XFF
  proxy_set_header X-Real-IP       $remote_addr;
  proxy_set_header x-middleware-subrequest "";     # CVE-2025-29927 defence in depth
  proxy_pass http://127.0.0.1:3000;
}
```

The scoping rule and the Authenticated Origin Pulls mTLS option are from [Cloudflare docs](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/) and the [stackharbor guide](https://stackharbor.com/en/knowledge-base/cfops-real-client-ip-at-origin/) [search-summary]. After `real_ip_header`, `$remote_addr` is the Cloudflare-reported client, so the backend then needs `trust proxy` set to `'loopback'`.

**FastAPI / uvicorn behind nginx on the same host:**

```bash
# uvicorn >= 0.54: proxy headers are on by default; trust only the local proxy.
uvicorn app.main:app --host 127.0.0.1 --port 8000 --forwarded-allow-ips="127.0.0.1,::1"
# In Docker with nginx in another container, use that container's subnet, e.g. "172.18.0.0/16", never '*'.
```

Per [uvicorn 0.54.0 source](https://pypi.org/project/uvicorn/0.54.0/) [verified-primary].

**Flask:**

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # x_for = number of proxies you run
```

Per [werkzeug 3.1.9](https://pypi.org/project/Werkzeug/3.1.9/) [verified-primary].

**CVE-2025-29927 fix:**
- Upgrade Next.js. Any current line (16.4.6 / 15.5.29) contains the 2025 fix. — [npm](https://www.npmjs.com/package/next) [verified-primary]
- As defence in depth, strip `x-middleware-subrequest` at the edge. — [Averlon](https://www.averlon.ai/blog/nextjs-cve-2025-29927-header-injection) [search-summary]
- **Do not rely on middleware alone for authorization.** Re-check the session in the route handler, server action or data layer (inference from the bug class).

#### (f) Common incorrect fixes
- `app.set('trust proxy', true)` to silence `ERR_ERL_UNEXPECTED_X_FORWARDED_FOR`. It swaps one validation error for `ERR_ERL_PERMISSIVE_TRUST_PROXY` and makes `req.ip` attacker-chosen. — [express-rate-limit source](https://unpkg.com/express-rate-limit@8.7.4/dist/index.cjs) [verified-primary]
- `req.headers['x-forwarded-for'].split(',')[0]` takes the leftmost, client-controlled entry. uvicorn returns the same value only in its `'*'`/always-trust mode. — [uvicorn source](https://pypi.org/project/uvicorn/0.54.0/) [verified-primary]
- `--forwarded-allow-ips='*'` in a Dockerfile, so that "the real IP shows up". — same source
- Using `x-real-ip` / `ipAddress()` on a self-hosted Next app. — [@vercel/functions](https://unpkg.com/@vercel/functions@3.11.3/headers.js) [verified-primary]
- Trusting `CF-Connecting-IP` on an origin that is reachable directly. — [Cloudflare guidance via stackharbor](https://stackharbor.com/en/knowledge-base/cfops-real-client-ip-at-origin/) [search-summary]
- `trust proxy: 1` when there are actually two hops (CDN → LB → app). `req.ip` becomes the CDN's edge IP, which collapses all users into a few buckets, or, with too *many* hops trusted, a spoofable value.
- Per-IPv6-address keys (pre-v7 custom keyGenerators returning `req.ip`). — [express-rate-limit `ERR_ERL_KEY_GEN_IPV6`](https://unpkg.com/express-rate-limit@8.7.4/dist/index.cjs) [verified-primary]
- Staying on express-rate-limit 8.0.0–8.2.1 (IPv4-mapped bucket collapse). — [OSV](https://osv.dev/vulnerability/CVE-2026-30827) [search-summary]
- For CVE-2025-29927: blocking only the exact header name at a WAF while running an unpatched version, or depending on Cloudflare's rule without confirming it was enabled (it was opt-in per most sources). — [Miggo](https://miggo.io/post/next-js-middleware-authorization-bypass-exploit-cve-2025-29927) [search-summary]

#### (g) Verifying the fix
**Express unit test with supertest.** It models the real topology: nginx on loopback appends the true peer address as the *last* XFF entry, and the attacker controls everything to its left.

```ts
import request from 'supertest';
import { app } from '../src/app'; // app.set('trust proxy', 'loopback'); loginLimiter limit = 10

test('rate limit cannot be bypassed by rotating a spoofed X-Forwarded-For prefix', async () => {
  const send = (spoofed: string) =>
    request(app)
      .post('/login')
      // "<attacker-chosen>, <address our proxy appended>"
      .set('X-Forwarded-For', `${spoofed}, 198.51.100.7`)
      .send({ email: 'a@b.c' });

  for (let i = 0; i < 10; i++) await send(`203.0.113.${i}`);
  const res = await send('203.0.113.99');
  expect(res.status).toBe(429); // key stays 198.51.100.7 regardless of the spoofed prefix
});
```

How it works, per the [proxy-addr README](https://www.npmjs.com/package/proxy-addr) [verified-primary]:
- With `'loopback'`, proxy-addr trusts the supertest socket peer (127.0.0.1), then returns the next untrusted entry walking right to left, which is `198.51.100.7`. The limiter key is stable, so the 11th request gets 429 and the test passes.
- With `trust proxy` set to `true`, Express returns the leftmost (spoofed) entry. Every request then gets a fresh key, no 429 occurs, and the test fails.

**Other checks:**
- **Startup check:** fail CI if logs contain `ERR_ERL_`.
- **Origin lock check:** `curl --resolve app.example:443:<origin-ip> https://app.example/ -H 'CF-Connecting-IP: 1.2.3.4'` must fail to connect or be rejected.
- **CVE-2025-29927 regression:** an e2e test that requests a protected page with `x-middleware-subrequest: middleware` (and the repeated `src/middleware:…` form) and asserts a redirect to login.

### Inferences
- The single most common vibe-coded IP bug is likely `trust proxy: true` or leftmost-XFF parsing added to make a rate limiter or analytics "work" behind a proxy. express-rate-limit's own warning text pushes in the right direction, but an assistant may suppress it with `validate: false`. (Pattern reasoning; I found no prevalence study.)
- On Vercel and Netlify the platform overwrites its own IP headers, so the developer's job is to read the *platform* header (`x-real-ip`/`ipAddress()`, `x-nf-client-connection-ip`) and not generic XFF parsing. The risk returns the moment the same code is self-hosted.
- App builders differ in hosting: v0 deploys to Vercel; Bolt to Netlify or StackBlitz (sources conflict); Lovable to its own hosting, reportedly on Fly.io; Replit to its own deployments. — [toolhalla comparison](https://toolhalla.ai/blog/bolt-new-vs-lovable-vs-replit-vs-v0-2026); [gautamkhorana.com](https://gautamkhorana.com/blog/hosting-for-lovable-v0-jamstack-apps-2026/) [search-summary, low-reliability secondary sources]. Which trusted client-IP header each exposes was not established.

### Gaps
- I did not research official Lovable, Bolt or Replit documentation on client-IP headers, edge caching or HTTP/2 termination. Hosting claims above are from low-reliability secondary sources.
- I did not verify whether Vercel's `x-forwarded-for` can contain more than one entry, or Netlify's exact XFF semantics.
- I did not re-fetch Express's current `trust proxy` documentation (expressjs.com was unreachable). The leftmost-with-`true` behaviour is from prior knowledge and is consistent with express-rate-limit's warning text.
- The interaction between the uvicorn worker and gunicorn's `forwarded_allow_ips` is reported anecdotally only.
- Cloudflare's `True-Client-IP` (Enterprise) and Cloudflare's current published IP list were not re-checked.
