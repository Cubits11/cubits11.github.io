# Token and cryptography attacks on vibe-coded apps: (8) JWT algorithm confusion, (13) Math.random tokens, (14) timing attacks, (15) padding oracles

*Research date: 2026-11-17.*

*How sources were read. This session's network blocked direct fetches of supabase.com, portswigger.net, rfc-editor.org and docs.python.org. For those I read the same documentation from its source repository on GitHub (Supabase docs MDX, CPython `Doc/`, Node `doc/api`, pyca `docs/`, panva/jose `docs/`), and I cite the GitHub file. GitHub Advisory Database pages, npm/PyPI registry metadata, and the V8 and supabase-js source code were read directly. When a fact comes only from search-result summaries, I say so. When it comes from my prior knowledge and I did not re-read it this session, it is marked **[not re-verified]**.*

*Code tested this session. I ran every Node and Python fix snippet below in a scratch environment: Node v22.23.4, jose 6.2.17, jsonwebtoken 9.0.3, Python 3.13.18, PyJWT 2.15.1, cryptography 50.0.2. Each one produced the expected accept/reject result. Results are given under each section's Inferences.*

---

## (8) JWT algorithm confusion: mechanism, CVEs (incl. 2025–2026), AI-prone patterns, testing, fix

### Takeaway
JWT algorithm confusion happens when the verifier lets the token (its `alg`, `kid`, `jku`, `x5u` or `jwk` header) choose the algorithm or the key. The fix is to pin both outside the token: an explicit one-algorithm allow-list, a typed key or JWKS bound to that algorithm, and checks on `iss`, `aud`, `exp` and `typ`. The 2025–2026 advisory stream shows the problem is not historical. PyJWT, fast-jwt, Authlib, Hono, Parse Server, MinIO and Keycloak all shipped algorithm-confusion or key-confusion fixes in 2026, and several of them were incomplete patches of earlier CVEs. In every case the trigger was a library guessing the key type from the key's bytes while the caller allowed mixed algorithm families.

### Cited Findings

#### (a) Mechanism
- RFC 7515 lets the JWS protected header carry `alg`, `jku` (JWK Set URL), `jwk` (embedded key), `kid` (key ID hint), `x5u` and `x5c`. RFC 7518 §3.6 defines `alg: "none"` (an unsecured JWS). A verifier that reads these fields from an unverified token and acts on them hands the choice of algorithm or key to the attacker. — [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515), [RFC 7518 §3.6](https://www.rfc-editor.org/rfc/rfc7518#section-3.6) **[not re-verified]**
- RFC 8725 (JWT BCP, Feb 2020) requires libraries to let callers specify the allowed algorithms and to use no others. It also says to validate all cryptographic operations, validate `iss`/`sub`, use and validate `aud`, use explicit typing (`typ`), and to stop trusting received claims to pick keys. — [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) **[not re-verified; rfc-editor.org blocked this session]**
- How RS256 turns into HS256: the classic API `verify(token, secretOrPublicKey)` takes one untyped string. If the header says `HS256`, a vulnerable library computes an HMAC using the RSA public key's PEM bytes as the secret. The public key is public (for example in a JWKS), so anyone can mint a token that passes. The fast-jwt advisory states the same root cause in present-day terms: the library "uses the key's content to decide whether it's a PEM public key or an HMAC secret". If detection fails, an attacker "can sign an HS256 token using the RSA public key as the HMAC secret… the forged token is accepted." — [GHSA-ww5h-9m49-7xx4 (fast-jwt)](https://github.com/advisories/GHSA-ww5h-9m49-7xx4)
- Preconditions in the current libraries, from the 2026 PyJWT advisory. The allow-list for `jwt.decode` includes both an HMAC algorithm and an asymmetric one. The key is passed as raw PEM text or bytes, not through `PyJWK`. The attacker has the public key. A single-algorithm list such as `["ES256"]` rejected the forged token. — [GHSA-ffc3-869f-jxw9 (PyJWT CVE-2026-102268)](https://github.com/advisories/GHSA-ffc3-869f-jxw9)
- Header-trust variant (2026): Hono's JWK/JWKS middleware took the algorithm from the JWK's `alg` if present and "fell back to the `alg` in the unverified JWT header" otherwise. JWK `alg` is optional and often omitted, so the attacker chose the algorithm. — [GHSA-f67f-6cw9-8mq4 (Hono CVE-2026-22817)](https://github.com/advisories/GHSA-f67f-6cw9-8mq4)
- `kid` injection: if the app uses `kid` in a file path or SQL query to load the key, path traversal can select a known file (for example an empty one) and SQL injection can return an attacker-chosen key. `jku`/`x5u` injection makes the server fetch a JWKS the attacker hosts, which also works as SSRF. An embedded `jwk` lets the token supply its own verification key. — summarized from [jsmon blog (secondary)](https://blogs.jsmon.sh/jwt-algorithm-confusion-to-account-takeover-rs256-hs256-jku-injection-kid-sqli/) and PortSwigger Web Security Academy JWT labs **[PortSwigger not fetched; host blocked]**
- Impact: any claim can be forged (`sub`, `role`, `app_metadata`), which means authentication bypass, account takeover and privilege escalation. Hono's advisory: "forge tokens with arbitrary claims, enabling authentication or authorization bypass". — [GHSA-f67f-6cw9-8mq4](https://github.com/advisories/GHSA-f67f-6cw9-8mq4)

#### (b) Historical and recent incidents/CVEs
**Historical (label as such):**
- CVE-2015-9235, jsonwebtoken (npm), "Verification Bypass", Critical, added to the GitHub Advisory DB on 2018-10-09. Disclosed March 2015 alongside Tim McLean's Auth0 write-up on `none` and RS/HS confusion across many libraries; fixed in jsonwebtoken 4.2.2. — [GHSA-c7hr-j4mj-j2w6](https://github.com/advisories/GHSA-c7hr-j4mj-j2w6) (date and severity verified); fix version and McLean attribution **[not re-verified]**
- CVE-2018-0114, node-jose (Cisco): the verifier trusted a public key embedded in the JWS header (`jwk`), so a self-signed token was accepted. — **[not re-verified; search returned nothing usable]**
- CVE-2022-21449 "Psychic Signatures", Java 15–18 ECDSA: signatures with `r = s = 0` verified against any key, so any ES256 JWT could be forged on affected JREs. Fixed in the April 2022 Oracle CPU. This is a verifier bug in the primitive, not an algorithm-confusion bug. — **[not re-verified; search returned nothing usable]**
- jsonwebtoken v9.0.0 (2022-12-21) security fixes. CVE-2022-23540: "Insecure default algorithm in jwt.verify() could lead to signature validation bypass". CVE-2022-23541: "Insecure implementation of key retrieval function could lead to Forgeable Public/Private Tokens from RSA to HMAC". CVE-2022-23539: "Unrestricted key type could lead to legacy keys usage". CVE-2022-23529 was later withdrawn. Breaking changes in v9: `verify()` "no longer accepts unsigned tokens by default"; "RSA key size must be 2048 bits or greater"; "Key types must be valid for the signing / verification algorithm". — [jsonwebtoken CHANGELOG](https://github.com/auth0/node-jsonwebtoken/blob/master/CHANGELOG.md); [GHSA-qwph-4952-7xr6](https://github.com/advisories/GHSA-qwph-4952-7xr6), [GHSA-hjrf-2m68-5959](https://github.com/advisories/GHSA-hjrf-2m68-5959), [GHSA-8cf7-32gw-wr33](https://github.com/advisories/GHSA-8cf7-32gw-wr33)
- PyJWT CVE-2022-29217: algorithm confusion when callers passed `algorithms=jwt.algorithms.get_default_algorithms()` together with an SSH or other public key. Affected 1.5.0–2.3.0, fixed in 2.4.0 (May 2022). — **[not re-verified]**. The 2026 PyJWT advisories name it as "the CVE-2022-29217 guard" that their bypasses defeat: [GHSA-p4g4-x82p-q773](https://github.com/advisories/GHSA-p4g4-x82p-q773)
- python-jose CVE-2024-33663: "algorithm confusion with OpenSSH ECDSA keys and other key formats", python-jose ≤3.3.0, patched 3.4.0, CVSS v4 9.3, published 2024-04-26. — [GHSA-6c5p-j8vq-pqhj](https://github.com/advisories/GHSA-6c5p-j8vq-pqhj). Companion CVE-2024-33664 (JWE decompression bomb) was also fixed in 3.4.0 **[not re-verified]**. The latest python-jose is 3.5.0, released 2025-05-28. — [PyPI python-jose](https://pypi.org/project/python-jose/)

**2025:**
- fast-jwt CVE-2025-30144, "Improperly Validates iss Claims", published 2025-03-19. — [GHSA-gm45-q3v2-6cf8](https://github.com/advisories/GHSA-gm45-q3v2-6cf8)
- get-jwks CVE-2025-59936, "poisoned JWKS cache allows post-fetch issuer validation bypass", Critical, 2025-09-26. — [GHSA-qc2q-qhf3-235m](https://github.com/advisories/GHSA-qc2q-qhf3-235m)
- jws (auth0/node-jws) CVE-2025-65945, 2025-12-04, CVSS 7.5. HMAC verification is improper when an app uses `jws.createVerify()` and feeds header or payload data into its HMAC secret lookup. Affected <3.2.3 and 4.0.0; patched 3.2.3 and 4.0.1. The advisory says jsonwebtoken users (who go through `jws.verify()`) are not affected. jsonwebtoken 9.0.3 (2025-12-04) "updates jws version to 4.0.1". — [GHSA-869p-cjfg-cm3x](https://github.com/advisories/GHSA-869p-cjfg-cm3x); [jsonwebtoken CHANGELOG](https://github.com/auth0/node-jsonwebtoken/blob/master/CHANGELOG.md)
- Jervis CVE-2025-68925 (Maven): does not validate that the header specifies RS256. All versions before 2.2. Published 2026-01-13. — [GHSA-5pq9-5mpr-jj85](https://github.com/advisories/GHSA-5pq9-5mpr-jj85)

**2026** (GitHub Advisory DB listings; titles as shown):
- Hono CVE-2026-22817 (JWT middleware) and CVE-2026-22818 ("JWK Auth Middleware has JWT algorithm confusion when JWK lacks 'alg' (untrusted header.alg fallback)"), both 2026-01-13, High. Affected <4.11.4, patched 4.11.4. "The fix makes the `alg` option mandatory", which is a breaking change. — [GHSA-f67f-6cw9-8mq4](https://github.com/advisories/GHSA-f67f-6cw9-8mq4), [GHSA-3vhc-576x-3qv4](https://github.com/advisories/GHSA-3vhc-576x-3qv4). Current hono is 4.13.19 (2026-11-16). — [npm registry](https://registry.npmjs.org/hono)
- Parse Server CVE-2026-27804, "Account takeover via JWT algorithm confusion in Google auth adapter", Critical, 2026-02-25. — [GHSA-4q3h-vp4r-prv2](https://github.com/advisories/GHSA-4q3h-vp4r-prv2)
- MinIO CVE-2026-33322, "JWT Algorithm Confusion in OIDC Authentication", Critical, 2026-03-19. — [GHSA-5cx5-wh4m-82fh](https://github.com/advisories/GHSA-5cx5-wh4m-82fh)
- fast-jwt chain of incomplete fixes:
  - CVE-2023-48223 (original RSA→HS confusion via PEM detection).
  - CVE-2026-34950, "Incomplete fix for CVE-2023-48223… via Whitespace-Prefixed RSA Public Key", Critical, 2026-04-02. Fixed by adding `key.trim()` in 6.2.0.
  - CVE-2026-107722, "Non-whitespace key-prefix re-enables RSA→HS256", Critical (CVSS 9.8), 2026-10-08. Affected ≥6.2.0 ≤6.2.4, patched 6.3.0. "`trim()` only removes whitespace… Any non-whitespace leading content, such as a `#` comment, control characters, zero-width Unicode… prevents a match." Vulnerable configurations: no `algorithms` allow-list, a callback key, or `HS256` allowed alongside an RSA key. "Allowing only `RS256` is protected."
  - Current fast-jwt is 6.3.7 (2026-11-16).
  — [GHSA-mvf2-f6gm-w987](https://github.com/advisories/GHSA-mvf2-f6gm-w987), [GHSA-ww5h-9m49-7xx4](https://github.com/advisories/GHSA-ww5h-9m49-7xx4), [npm registry](https://registry.npmjs.org/fast-jwt)
- lightrag-hku CVE-2026-39413 (2026-04-08), Lemur CVE-2026-55165 "JWT verifier honors attacker-supplied alg" (2026-06-25), web-token/jwt-bundle "JWSVerifier uses algorithm from unprotected header" (2026-06-18), Strapi users-permissions CVE-2026-57997 "fails to restrict JWT algorithms" (2026-06-30, unreviewed), Keycloak CVE-2026-11800 "authentication bypass via jwt algorithm confusion" (2026-11-03, High). — [GitHub Advisory DB search "jwt algorithm confusion"](https://github.com/advisories?query=jwt+algorithm+confusion)
- PyJWT 2026 cluster:
  - CVE-2026-48526 (2026-06-15): "Public-key JWK accepted as HMAC secret enables forged HS256 tokens when mixed families are allowed". Fixed in 2.13.0, which also binds the header `alg` to `PyJWK.algorithm_name`.
  - 2026-09-29 batch: CVE-2026-102268 ("Asymmetric-PEM detection bypass… whitespace/line-ending-mutated public keys", Critical 9.1), CVE-2026-102271 (DER public keys as HMAC secrets), CVE-2026-102272 (BOM bypass), CVE-2026-102273 (public JWK containers as HMAC secrets), CVE-2026-102266 (PyJWK accepts empty HMAC keys), CVE-2026-102267 ("PyJWKClient follows redirects when fetching JWKS"), and others. All fixed in 2.14.0 (released 2026-09-11 per the advisory). The changelog says 2.14.0 "Harden[s] HMAC key validation against public-key material supplied as JWK, JWKS, array, encoded, BOM-prefixed, DER, or PEM input" and "Reject[s] automatic redirects when `PyJWKClient` fetches a JWKS".
  - GHSA-pxh4-856f-4h89 (2026-10-22): "HS256/384/512 verify accepts empty HMAC key via oct JWK".
  - Current PyJWT is 2.15.1 (2026-09-28).
  — [GHSA-xgmm-8j9v-c9wx](https://github.com/advisories/GHSA-xgmm-8j9v-c9wx), [GHSA-ffc3-869f-jxw9](https://github.com/advisories/GHSA-ffc3-869f-jxw9), [PyJWT CHANGELOG](https://github.com/jpadilla/pyjwt/blob/master/CHANGELOG.rst), [GitHub Advisory DB "pyjwt"](https://github.com/advisories?query=pyjwt), [PyPI](https://pypi.org/project/PyJWT/)
- Empty-HMAC-key acceptance (a related forgery class, since an empty secret is guessable): joserfc CVE-2026-49852 (2026-07-02), Authlib CVE-2026-114616 (2026-10-27), PyJWT GHSA-9j54-fg26-wv3r / GHSA-pxh4-856f-4h89. Authlib also has CVE-2026-114615, "incomplete algorithm-confusion fix permits HMAC forgery with prefixed public keys" (2026-10-27). — [GitHub Advisory DB "pyjwt"](https://github.com/advisories?query=pyjwt), [GitHub Advisory DB "jsonwebtoken"](https://github.com/advisories?query=jsonwebtoken)
- Hard-coded default secret: praisonai-platform CVE-2026-57147, "default JWT signing secret enables token forgery", Critical, 2026-06-18. — [GitHub Advisory DB "pyjwt"](https://github.com/advisories?query=pyjwt)
- Disputed or unclear: one blog lists "CVE-2025-4692 (python-jose)" as RS256→HS256 confusion, but another source calls it an audience-validation bypass. It does not appear in the python-jose advisory shown above. Treat it as unverified. — [search summary of redsentry / intelligencex blogs](https://redsentry.com/resources/blog/jwt-vulnerabilities-list-2026-security-risks-mitigation-guide)

#### (c) Why vibe-coded apps are prone, and stack defaults
- The jsonwebtoken README warns that `jwt.decode()` "will __not__ verify whether the signature is valid… You most likely want to use `jwt.verify` instead." Semgrep ships dedicated rules for decode-without-verify: `jwt-decode-without-verify` (JS) and `unverified-jwt-decode` (Python, flags `verify=False`). It also ships `jwt-none-alg` and `jwt-hardcode`, and a React rule `react-jwt-decoded-property`. — [jsonwebtoken README](https://github.com/auth0/node-jsonwebtoken/blob/master/README.md), [semgrep-rules (develop)](https://github.com/semgrep/semgrep-rules/tree/develop/javascript/jsonwebtoken/security)
- jsonwebtoken 9.0.3 default when `algorithms` is omitted: "If not specified a defaults will be used based on the type of key provided: secret → HS256/384/512; rsa → RS256/384/512; ec → ES256/384/512; default → RS256/384/512." — [jsonwebtoken README](https://github.com/auth0/node-jsonwebtoken/blob/master/README.md)
- jose (panva) 6.x: `algorithms` "Defaults to all algorithms applicable to the key or secret. Unsecured JWTs (`alg: "none"`) are never accepted." Keys are typed (`CryptoKey`/`KeyObject` via `importSPKI`/`importJWK`) and bound to an algorithm. — [jose JWTVerifyOptions](https://github.com/panva/jose/blob/main/docs/jwt/verify/interfaces/JWTVerifyOptions.md), [jose jwtVerify](https://github.com/panva/jose/blob/main/docs/jwt/verify/functions/jwtVerify.md)
- PyJWT 2.x requires `algorithms` in `decode()`. I observed this error in testing: "It is required that you pass in a value for the "algorithms" argument when calling decode()". PyJWT also documents `options={"verify_signature": False}` for reading tokens without verification. — [PyJWT usage docs](https://github.com/jpadilla/pyjwt/blob/master/docs/usage.rst)
- Supabase, legacy and current:
  - The legacy system uses one shared HS256 "JWT secret" that signs all user tokens and the `anon` and `service_role` keys, which are themselves JWTs. Supabase: "**No longer recommended.** Available for backward compatibility."
  - The new "JWT signing keys" support ES256 (recommended), RS256, EdDSA ("Coming soon") and HS256 ("**Not recommended for production applications**").
  - Public keys are served at `GET https://<project-id>.supabase.co/auth/v1/.well-known/jwks.json`.
  - Migration path: "Migrate JWT secret" imports the legacy secret, creates a standby asymmetric key, "Rotate keys", then revoke the legacy secret after the access-token lifetime plus 15 minutes.
  - Revoking the legacy secret requires disabling `anon`/`service_role` in favour of `sb_publishable_…`/`sb_secret_…` keys.
  - Supabase specifically warns about leaking the shared secret through env vars "prefixed with `NEXT_PUBLIC_`, `VITE_`, `PUBLIC_`".
  — [Supabase docs: signing-keys.mdx (source)](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/signing-keys.mdx) (canonical: supabase.com/docs/guides/auth/signing-keys)
- Supabase verification guidance. "Avoid implementing the algorithms yourself and instead rely on `supabase.auth.getClaims()`." The JWKS is edge-cached for 10 minutes; "We recommend waiting at least 20 minutes when creating a standby signing key, or revoking a previously used key". For HS256 projects, Supabase recommends verifying via `GET /auth/v1/user` and "strongly recommend[s] against" verifying locally with the shared secret. — [Supabase docs: jwts.mdx (source)](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/jwts.mdx)
- How `supabase.auth.getClaims()` works in supabase-js source:
  - It decodes the JWT and checks `exp` unless `allowExpired`.
  - If `alg` is missing or starts with `HS`, if there is no `kid`, or if WebCrypto is unavailable, it falls back to `getUser(token)`, a round trip to the Auth server.
  - Otherwise it fetches the JWK by `kid` from the project JWKS and verifies with `crypto.subtle.verify`.
  - The `getUser()` doc comment says it "Should always be used when checking for user authorization on the server… `getSession` is insecure on the server."
  — [supabase-js GoTrueClient.ts](https://github.com/supabase/supabase-js/blob/master/packages/core/auth-js/src/GoTrueClient.ts). Current `@supabase/supabase-js` is 2.119.0 (2026-11-04) and `@supabase/ssr` is 0.12.7. — [npm registry](https://registry.npmjs.org/@supabase%2Fsupabase-js)
- Webhook-style JWT handling with untrusted `alg` also shows up outside auth. For example, the Symfony Mailomat webhook parser "Reads the HMAC Algorithm from the Request: Signature Algorithm Downgrade" (CVE-2026-48747). — [GitHub Advisory DB](https://github.com/advisories?query=jwt+algorithm+confusion)

#### (d) Safe self-testing
- Static checks:
  - Semgrep community rules: `jwt-decode-without-verify` and `jwt-none-alg` (javascript/jsonwebtoken), `jwt-none-alg` (javascript/jose), and `unverified-jwt-decode`, `jwt-none-alg` and `jwt-hardcode` (python/jwt).
  - Run `semgrep --config p/jwt` or point at those rule paths. — [semgrep-rules](https://github.com/semgrep/semgrep-rules/tree/develop/python/jwt/security)
- Dependency checks: `npm audit` / `pip-audit` against the advisories above (hono <4.11.4, fast-jwt <6.3.0, PyJWT <2.14.0, python-jose <3.4.0, jws <3.2.3/4.0.1). — advisories cited above
- Unit and integration tests against your own verifier. These are non-destructive:
  - an `alg:"none"` token must be rejected;
  - an HS256 token signed with a random 32-byte secret must be rejected when you expect ES256/RS256;
  - wrong `aud` and wrong `iss` must be rejected;
  - an expired token must be rejected.
  - In jose these surface as `ERR_JOSE_ALG_NOT_ALLOWED` / `ERR_JWT_CLAIM_VALIDATION_FAILED`, and in PyJWT as `InvalidAlgorithmError`. I observed all of these this session; the test code is under Inferences.

#### (e) Fix (versions current as of 2026-11-17)
- Library versions: jose 6.2.17 (2026-11-09), jsonwebtoken 9.0.3, PyJWT 2.15.1, joserfc 1.8.0, Authlib 1.9.8 (2026-11-16), hono 4.13.19, fast-jwt 6.3.7. — [npm registry](https://registry.npmjs.org/jose), [PyPI PyJWT](https://pypi.org/project/PyJWT/), [PyPI joserfc](https://pypi.org/project/joserfc/), [PyPI Authlib](https://pypi.org/project/Authlib/)
- jose `jwtVerify` options: `algorithms`, `issuer`, `audience`, `requiredClaims`, `clockTolerance`, `maxTokenAge`, `subject`, `typ` ("Expected JWT "typ"… Requires the parameter to be present"). — [JWTVerifyOptions](https://github.com/panva/jose/blob/main/docs/jwt/verify/interfaces/JWTVerifyOptions.md)
- jose `createRemoteJWKSet(url, options)`:
  - It selects a key "using the header's "alg" and "kid" and respects the JWK's "use" and "key_ops". Exactly one key must match."
  - It refetches on an unknown `kid` only after `cooldownDuration` (default 30000 ms).
  - `cacheMaxAge` defaults to 600000 ms (10 minutes) and `timeoutDuration` to 5000 ms.
  - The JWKS URL is fixed by the caller, never taken from `jku`.
  — [createRemoteJWKSet](https://github.com/panva/jose/blob/main/docs/jwks/remote/functions/createRemoteJWKSet.md), [RemoteJWKSetOptions](https://github.com/panva/jose/blob/main/docs/jwks/remote/interfaces/RemoteJWKSetOptions.md)
- jsonwebtoken `verify` options: `algorithms`, `audience`, `issuer`, `maxAge`, `allowInvalidAsymmetricKeyTypes` ("intended only for backwards compatability and should be avoided"). — [jsonwebtoken README](https://github.com/auth0/node-jsonwebtoken/blob/master/README.md)
- PyJWT mitigation stated in the advisories: "avoid mixing HMAC and asymmetric algorithms in one allow-list, and verify with a single algorithm. Prefer `PyJWK` objects for key handling over raw PEM strings." — [GHSA-ffc3-869f-jxw9](https://github.com/advisories/GHSA-ffc3-869f-jxw9)
- fast-jwt mitigation: "Pin the expected algorithms explicitly, for example `algorithms: ['RS256']`… Where possible, make sure keys are loaded from clean sources without extra content before the PEM header." — [GHSA-ww5h-9m49-7xx4](https://github.com/advisories/GHSA-ww5h-9m49-7xx4)

#### (f) Common incorrect or incomplete fixes
- Detecting the key type by pattern-matching key bytes. This is how the libraries themselves got it wrong, repeatedly: fast-jwt's `trim()` patch (CVE-2026-34950) was bypassed by non-whitespace prefixes (CVE-2026-107722). PyJWT's PEM regex was bypassed by whitespace, CR line endings, DER, BOM and JWK forms (CVE-2026-102268/102271/102272/102273). Authlib's fix was bypassed by "prefixed public keys" (CVE-2026-114615). The robust control is the caller's single-family allow-list plus typed keys. — advisories cited in (b)
- Allowing `['RS256','HS256']` "for compatibility": this exact mix is the precondition for the PyJWT and fast-jwt bypasses. — [GHSA-ffc3-869f-jxw9](https://github.com/advisories/GHSA-ffc3-869f-jxw9), [GHSA-ww5h-9m49-7xx4](https://github.com/advisories/GHSA-ww5h-9m49-7xx4)
- Trusting JWK `alg`, or falling back to the header `alg` when the JWK omits it (the Hono bug). — [GHSA-3vhc-576x-3qv4](https://github.com/advisories/GHSA-3vhc-576x-3qv4)
- Verifying the signature but not `iss`/`aud`. Validating issuer after the JWKS fetch was itself the get-jwks bug. — [GHSA-qc2q-qhf3-235m](https://github.com/advisories/GHSA-qc2q-qhf3-235m)
- Following redirects or `jku` when fetching JWKS (PyJWT CVE-2026-102267). — [PyJWT CHANGELOG](https://github.com/jpadilla/pyjwt/blob/master/CHANGELOG.rst)
- Caching the JWKS indefinitely. Supabase: "Make sure that you do not cache this data for longer in your application, as it might make revocation difficult." — [jwts.mdx](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/jwts.mdx)
- Using `getSession()` on the server in Supabase/Next.js ("`getSession` is insecure on the server"). — [GoTrueClient.ts](https://github.com/supabase/supabase-js/blob/master/packages/core/auth-js/src/GoTrueClient.ts)

#### (g) Verifying the fix
- A regression test should fail before the fix (with `jwt.decode`, or `verify` without `algorithms`, or a header-trusting verifier) and pass after. jsonwebtoken 9.0.3 with an EC `KeyObject` and `algorithms:['ES256']`:
  - rejected `alg:none` with "jwt signature is required";
  - rejected an HS256 token with "invalid algorithm";
  - also rejected the HS256 token when `algorithms` was omitted, because the EC key type restricts defaults to ES*.
  - `jwt.decode()` returned the attacker's claims unchanged, which is why decode-only code fails the test.
  — observed in this session; default behavior per [jsonwebtoken README](https://github.com/auth0/node-jsonwebtoken/blob/master/README.md)

### Inferences
- **Why AI assistants emit the bad pattern (inference).** Next.js Middleware runs on the Edge runtime, where jsonwebtoken (Node-crypto based) does not work. A model asked to "read the user id in middleware" plausibly reaches for `jwt.decode()` or `jwt-decode` (decode-only) to get past the runtime error. The fix is jose (Web Crypto based) or Supabase `getClaims()`, both of which run on Edge. I have no study that measures how often assistants do this; Semgrep's dedicated rules suggest the pattern is common.
- **Supabase specifics (inference from reading the code).** `getClaims()` checks signature and `exp` but not `aud`/`iss`. It is project-scoped because it uses your project's JWKS. If you verify Supabase tokens yourself with jose, add `issuer: 'https://<ref>.supabase.co/auth/v1'`, `audience: 'authenticated'` and `algorithms: ['ES256']`; the official snippet omits these. Values are from the Supabase JWT payload example and the getClaims example response.
- **Recommended TypeScript (jose 6.x).** Tested pattern:
```ts
import { createRemoteJWKSet, jwtVerify, errors } from 'jose';
const ISSUER = 'https://<project-ref>.supabase.co/auth/v1';            // or your IdP
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks.json`)); // fixed URL, never from jku/x5u
export async function requireUser(bearer: string | undefined) {
  if (!bearer?.startsWith('Bearer ')) throw new Error('unauthenticated');
  const { payload } = await jwtVerify(bearer.slice(7), JWKS, {
    algorithms: ['ES256'],          // exactly one family; never mix HS* with RS*/ES*
    issuer: ISSUER,
    audience: 'authenticated',
    requiredClaims: ['exp', 'sub'],
    clockTolerance: 5,              // seconds
  });
  return payload;                   // treat custom claims as input; authorize on server-side data
}
```
- **Static key (PEM) in jose.** Use `const key = await importSPKI(pem, 'RS256')` and pass `algorithms: ['RS256']`. The key object is then bound to RS256, so a string can never double as an HMAC secret.
- **jsonwebtoken (if you must keep it).** Use `jwt.verify(token, publicKeyObject, { algorithms: ['ES256'], issuer, audience, maxAge: '15m' })` with a `crypto.createPublicKey()` KeyObject, not a raw string. Never call `jwt.decode()` on an auth path.
- **Python (PyJWT ≥2.14).** Tested pattern:
```python
import jwt
jwks = jwt.PyJWKClient(f"{ISSUER}/.well-known/jwks.json")   # PyJWT ≥2.14 refuses redirects
def require_user(token: str) -> dict:
    key = jwks.get_signing_key_from_jwt(token)                # PyJWK binds one algorithm
    return jwt.decode(token, key, algorithms=["ES256"], issuer=ISSUER,
                      audience="authenticated",
                      options={"require": ["exp", "iss", "aud", "sub"]})
```
- **Python library choice.** Prefer PyJWT or joserfc over python-jose for new code. This is an inference from python-jose's 2024 CVEs and its last release (May 2025); I did not verify its maintenance status.
- **Defense in depth.**
  - Short access-token TTL. Supabase's migration guide uses 1 hour as its example expiry.
  - Explicit `typ` (`at+jwt` per RFC 9068 **[not re-verified]**) to stop ID-token/access-token substitution.
  - `kid` used only as a lookup key into a server-side map or JWKS, never a path or SQL value.
  - Prefer asymmetric keys, so a leaked env var cannot mint tokens.
  - Rotate yearly (Supabase: "at least once a year").
  - Authorize from server-side state (RLS / DB), not from mutable custom claims.
- **Tested regression test (Node; shape only).** Build three tokens: (1) a valid ES256 token; (2) `base64url({"alg":"none"})+"."+base64url(claims)+"."`; (3) an HS256 token signed with `crypto.randomBytes(32)`. Assert that (1) verifies and that (2) and (3) are rejected with `ERR_JOSE_ALG_NOT_ALLOWED`. Also assert a wrong `aud` gives `ERR_JWT_CLAIM_VALIDATION_FAILED`. This session's run passed all of these. PyJWT gave `InvalidAlgorithmError` for (2) and (3). The test does not demonstrate the public-key-as-secret trick; it shows that the pin blocks any non-expected `alg`.

### Gaps
- I could not fetch RFC 8725 or RFC 7515/7518 text (rfc-editor.org blocked). The BCP requirements above come from memory and should be checked against the RFC.
- I could not fetch PortSwigger's JWT research or labs. The `kid`/`jku`/`jwk` mechanism descriptions rest on a secondary blog and my own knowledge.
- I did not verify these details against NVD: CVE-2015-9235's fixed version (4.2.2), CVE-2018-0114, CVE-2022-21449, and CVE-2022-29217's version range.
- Many 2026 CVE IDs above (for example CVE-2026-102268, CVE-2026-114615) have unusually high sequence numbers. I report them as listed by the GitHub Advisory Database and did not cross-check NVD.
- I did not verify whether Supabase has set a hard deprecation date for the legacy JWT secret or `anon`/`service_role` keys. The docs I read give no date, only "No longer recommended".

---

## (13) Math.random-generated (predictable) tokens: mechanism, incidents, AI patterns, fix

### Takeaway
`Math.random()` in V8 is xorshift128+ with 128 bits of state, and each output exposes 52–53 bits of it. Published SMT-solver techniques recover the state from a handful of consecutive outputs and then predict every past and future value. Python's `random` (MT19937) has the same problem, and UUIDv1 is time-based. Any reset, invite, magic-link, API or session token built from these is guessable once the attacker sees a few outputs; CVE-2025-7783 (form-data) showed such outputs leak through things as mundane as an `x-request-id` header. The fix is a CSPRNG (`crypto.randomBytes`/`randomUUID`/`getRandomValues`/`randomInt`, nanoid, Python `secrets`) plus lifecycle controls: hash at rest, single use, short TTL, rate limits.

### Cited Findings

#### (a) Mechanism
- V8's current source implements `XorShift128(uint64_t* state0, uint64_t* state1)` ("Generate random numbers using xorshift128+"). `ToDouble` gets "a random [0,2**53) integer value… by dropping 11 bits of the state" and divides by 2^53. — [V8 random-number-generator.h](https://github.com/v8/v8/blob/main/src/base/utils/random-number-generator.h)
- V8 refills a per-context cache of `kCacheSize = 64` values (`math-random.h`/`math-random.cc`). Public write-ups note the cache is consumed in reverse generation order, so observed outputs must be reversed before solving. — [V8 math-random.h](https://github.com/v8/v8/blob/main/src/numbers/math-random.h); reversal per [search summary of JorianWoltjer / haqpl write-ups](https://book.jorianwoltjer.com/cryptography/pseudo-random-number-generators-prng)
- V8 moved to xorshift128+ in 2015 (Chrome 49) after its earlier MWC1616 generator was shown to be weak. The V8 team stated that Math.random is not intended to be cryptographically secure. — [V8 blog "There's Math.random(), and then there's Math.random()"](https://v8.dev/blog/math-random) (via search summary; page not fetched)
- State recovery: because xorshift128+ is linear over GF(2) apart from the final addition, an SMT solver (Z3) recovers the state from a few outputs. Reported sample counts vary: ~3 full doubles (Yurichev, against Firefox's xorshift128+), ~10, or ~15 when only `Math.floor(N*Math.random())` is visible. — [Yurichev, "Predicting Math.random() … using Z3"](https://yurichev.com/blog/xorshift/), [ivanludvig "Hacking Google RNG"](https://ivanludvig.github.io/tech/google-random) (via search summary)
- Python's `random` "uses the Mersenne Twister as the core generator" with "53-bit precision floats and… period of 2**19937-1". The docs warn: "The pseudo-random generators of this module should not be used for security purposes. For security or cryptographic uses, see the `secrets` module." — [CPython Doc/library/random.rst](https://github.com/python/cpython/blob/main/Doc/library/random.rst) (canonical: docs.python.org/3/library/random.html)
- MT19937's state is 624 32-bit words, and 624 consecutive 32-bit outputs are enough to clone it (the tempering function is invertible). This is a standard, widely implemented result (e.g., "randcrack"). **[not re-verified this session]**
- UUIDv1 "sandwich attack" (Lupin & Holmes, 2023-08-11): v1 UUIDs encode a timestamp, clock sequence and MAC. The attacker requests reset tokens for their own account, then the victim's, then their own again. The victim's token falls in a small, enumerable range between the two. The researchers report a "0 Click Account Take Over". — [Lupin & Holmes](https://www.landh.tech/blog/20230811-sandwich-attack/); Semgrep's `insecure-uuid-version` rule cites it: [rule](https://github.com/semgrep/semgrep-rules/blob/develop/python/lang/security/insecure-uuid-version.yaml)
- Modulo bias: "`random % alphabet` is a popular mistake to make when coding an ID generator. The distribution will not be even; there will be a lower chance for some symbols to appear compared to others. So, it will reduce the number of tries when brute-forcing." — [nanoid README](https://github.com/ai/nanoid/blob/main/README.md). Node's `crypto.randomInt` "implementation avoids modulo bias". — [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md)

#### (b) Incidents and CVEs
- **form-data CVE-2025-7783** (Critical, CVSS v4 9.4; NVD 2025-07-18, GHSA 2025-07-21). "form-data uses `Math.random()` to select a boundary value." An attacker who observes several sequential `Math.random()` outputs can predict the boundary and inject extra multipart fields. The advisory names "an `x-request-id` header used for tracing" as a leak channel. Affected <2.5.4, 3.0.0–<3.0.4, 4.0.0–<4.0.4; patched 2.5.4/3.0.4/4.0.4. This is the clearest recent demonstration that Math.random prediction is practical from incidental leaks. — [GHSA-fjxv-7rqg-78g4](https://github.com/advisories/GHSA-fjxv-7rqg-78g4)
- undici CVE-2025-22150, "use of insufficiently random values", 2025-01-21 (title only). My understanding is that it is also a Math.random multipart boundary in `fetch`; **[details not re-verified]**. — [GHSA-c76h-2ccp-4975](https://github.com/advisories/GHSA-c76h-2ccp-4975)
- nodebb CVE-2022-36045, "cryptographically weak PRNG in generateUUID", Critical, 2022-08-30. — [GHSA-p4cc-w597-6cpm](https://github.com/advisories/GHSA-p4cc-w597-6cpm)
- Fastly js-compute CVE-2022-39218: a fixed random seed baked in at compile time, so Math.random was identical across instances. — [GHSA-cmr8-5w4c-44v8](https://github.com/advisories/GHSA-cmr8-5w4c-44v8)
- 2026 listings (GitHub Advisory DB titles):
  - Etherpad "weak token RNG, login timing, plugin path and API handling issues" (2026-08-17);
  - Etherpad CVE-2026-55086, Math.random() temp paths (2026-08-13);
  - Rejetto HFS CVE-2026-61500, "derives session-cookie signing key from a non-cryptographic source" (Critical, 2026-07-13);
  - sm-crypto CVE-2026-73567, "predictable SM2 key generation from weak default RNG" (Critical, 2026-07-24);
  - crypto-js CVE-2026-71851, "insufficient entropy in secret generation via dependency chain" (Critical, 2026-08-07);
  - Zipline CVE-2025-71461, predictable filenames (2026-11-13).
  — [GitHub Advisory DB search "Math.random"](https://github.com/advisories?query=Math.random)

#### (c) Why vibe-coded apps are prone
- Typical generated patterns: `Math.random().toString(36).slice(2)`, `Date.now().toString(36) + Math.random()...`, `Math.floor(100000 + Math.random()*900000)` for OTPs, `uuid.v1()`/`uuid.uuid1()`, and Python `random.choice(string.ascii_letters)` for tokens. These are the patterns the Semgrep `insecure-uuid-version` rule and nanoid's "Unpredictability… Instead of using the unsafe `Math.random()`" note address. — [nanoid README](https://github.com/ai/nanoid/blob/main/README.md), [Semgrep rule](https://github.com/semgrep/semgrep-rules/blob/develop/python/lang/security/insecure-uuid-version.yaml)
- Tooling gap. The Semgrep community repository (develop branch, cloned 2026-11-17) has no Math.random rule in `javascript/lang/security` and no timing-attack rule. eslint-plugin-security 4.2.1 (2026-10-30) has `detect-pseudoRandomBytes` (for `crypto.pseudoRandomBytes`), not a Math.random rule. A default lint setup therefore does not flag `Math.random()` token generation. — [semgrep-rules](https://github.com/semgrep/semgrep-rules/tree/develop/javascript/lang/security), [eslint-plugin-security README via npm](https://registry.npmjs.org/eslint-plugin-security)
- `nanoid/non-secure` exists as a separate, faster, Math.random-based export (the README benchmarks it as "Non-secure"). An assistant can import the wrong entry point. — [nanoid README](https://github.com/ai/nanoid/blob/main/README.md)

#### (d) Safe self-testing
- Grep or Semgrep for `Math.random`, `uuid.v1`/`uuid1`, `random.` (Python), `nanoid/non-secure` and `Date.now()` inside token, OTP, invite, reset or API-key generation.
  - Python: Bandit's B311 flags the `random` module **[not re-verified]**.
  - Semgrep: `python.lang.security.insecure-uuid-version`. — [Semgrep rule](https://github.com/semgrep/semgrep-rules/blob/develop/python/lang/security/insecure-uuid-version.yaml)
- Lifecycle checks against your own DB: tokens stored hashed, `expires_at` present, `used_at` set atomically, and old tokens invalidated on password change.

#### (e) Fix
- Node APIs:
  - `crypto.randomBytes(32).toString('base64url')` yields 43 characters, 256 bits (observed).
  - `crypto.randomUUID()` gives a v4 UUID with 122 random bits.
  - `crypto.randomInt(min, max)` avoids modulo bias (documented).
  - Browser and Edge: `crypto.getRandomValues()`.
  — [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md)
- nanoid 6.0.2 (2026-10-05): "uses the `crypto` module in Node.js and the Web Crypto API in browsers"; uniformity-tested. — [npm registry](https://registry.npmjs.org/nanoid), [README](https://github.com/ai/nanoid/blob/main/README.md)
- Python: `secrets` "should be used in preference to the default pseudo-random number generator in the `random` module". `secrets.token_urlsafe()` defaults to `DEFAULT_ENTROPY` (32 bytes, observed `secrets.DEFAULT_ENTROPY == 32`). The docs' example: `url = 'https://example.com/reset=' + secrets.token_urlsafe()`. The docs say "it is believed that 32 bytes (256 bits) of randomness is sufficient". `secrets.randbelow()` and `secrets.choice()` cover OTPs and alphabets. — [CPython Doc/library/secrets.rst](https://github.com/python/cpython/blob/main/Doc/library/secrets.rst)

#### (f) Common incorrect fixes
- Hashing a Math.random output (for example `sha256(Math.random())`). This keeps the predictability: the hash of a predictable input is predictable. — (inference)
- Making the Math.random string longer by concatenating several calls. Each call comes from the same recoverable 128-bit state, so length adds no unpredictability. — (inference from [V8 source](https://github.com/v8/v8/blob/main/src/base/utils/random-number-generator.h))
- `crypto.randomBytes(n)[i] % alphabet.length`, which introduces modulo bias. Use `randomInt` or nanoid's `customAlphabet`. — [nanoid README](https://github.com/ai/nanoid/blob/main/README.md), [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md)
- Switching UUIDv1 to UUIDv4 but storing it unhashed without expiry. The token is now unpredictable, but DB/log leaks and replay remain.
- Rate-limiting only the "request reset" endpoint and not the "redeem token" endpoint. The sandwich attack works by brute-forcing redemption. — [Lupin & Holmes](https://www.landh.tech/blog/20230811-sandwich-attack/)

#### (g) Verification
- Unit tests:
  - mock or spy that the generator calls `crypto.randomBytes`/`secrets` and never `Math.random`/`random`;
  - assert a length of ≥43 base64url characters (256 bits);
  - assert that the DB column stores `sha256(token)` (64 hex characters) and not the token;
  - assert a second redemption fails and a token older than its TTL fails.
  A static CI rule that fails on `Math.random` under `auth/` is the before/after gate.

### Inferences
- **Recommended TypeScript (tested pieces).**
```ts
import { randomBytes, createHash, randomInt } from 'node:crypto';
export function newResetToken() {
  const token = randomBytes(32).toString('base64url');            // 256-bit, URL-safe; send this to the user
  const tokenHash = createHash('sha256').update(token).digest('hex'); // store only this
  return { token, tokenHash, expiresAt: new Date(Date.now() + 30 * 60_000) };
}
export const sixDigitOtp = () => String(randomInt(0, 1_000_000)).padStart(6, '0'); // unbiased; still rate-limit + expire
// Redeem: UPDATE reset_tokens SET used_at = now()
//         WHERE token_hash = $1 AND used_at IS NULL AND expires_at > now() RETURNING user_id;
```
- **Python equivalent.** `token = secrets.token_urlsafe(32)`, store `hashlib.sha256(token.encode()).hexdigest()`, OTP `f"{secrets.randbelow(10**6):06d}"`.
- **Why a fast hash is acceptable here (inference).** A plain SHA-256 is acceptable for 256-bit random tokens because they cannot be brute-forced. Passwords still need Argon2id/scrypt/bcrypt.
- **Lookup by hash.** Looking up by the hash, not by the raw token, also removes the string-compare timing side channel on the raw secret (see (14)). For API keys use a "selector.verifier" split: a public ID for the lookup, then a constant-time compare of the hashed secret (Paragon IE pattern **[not re-verified]**).
- **Do not store tokens in `localStorage`.** This avoids XSS exfiltration. The React Semgrep rule `react-jwt-in-localstorage` exists. — [semgrep-rules](https://github.com/semgrep/semgrep-rules/tree/develop/typescript/react/security/audit)

### Gaps
- I could not open the V8 blog post directly; its content is from search summaries. I did not confirm whether V8 has any 2025–2026 plan to change Math.random. The current V8 main branch is still xorshift128+, verified in source.
- I did not verify the undici CVE-2025-22150 details beyond its title.
- I did not find a primary-source measurement of how often AI assistants emit `Math.random()` for tokens. The Veracode benchmark reports on CWE-327 (algorithms), not specifically on CWE-330/338 (randomness); see the cross-cutting section.

---

## (14) Timing attacks on secret comparison: mechanism, feasibility evidence, AI patterns, fix

### Takeaway
Early-exit comparison (`===`, `==`, `!=`, `strcmp`) of an attacker-supplied value against a secret (API key, HMAC or webhook signature, session or reset token) leaks how many leading bytes match. Research from 2009 to 2024 has steadily shrunk the noise that makes remote exploitation hard:
- Crosby et al. (2009): about 100 ns on a LAN, tens of µs over the Internet.
- "Timeless" timing (2020): about 100 ns remotely over HTTP/2.
- Kettle's single-packet attack (2024): made web timing measurements "local".

The fix is cheap and deterministic: `crypto.timingSafeEqual` or `hmac.compare_digest` on equal-length digests, vendor SDK verifiers for Stripe and GitHub webhooks, lookup by hashed token, and a dummy password hash so logins take the same time whether or not the user exists.

### Cited Findings

#### (a) Mechanism and feasibility
- GitHub's webhook docs: "Never use a plain `==` operator. Instead consider using a method like `secure_compare` or `crypto.timingSafeEqual`, which performs a "constant time" string comparison to help mitigate certain timing attacks against regular equality operators, or regular loops in JIT-optimized languages." — [GitHub Docs: validating webhook deliveries (source)](https://github.com/github/docs/blob/main/content/webhooks/using-webhooks/validating-webhook-deliveries.md)
- Crosby, Wallach & Riedi, "Opportunities and Limits of Remote Timing Attacks", ACM TISSEC 12(3), 2009. — [bib entry](https://ftp.math.utah.edu/pub/tex/bib/idx/tissec/12/3/17-17.html). My recollection of the abstract is "reliably distinguish remote timing differences as low as 20µs" over the Internet and "as small as 100ns" on a LAN **[not re-verified]**. A 29C3 slide deck citing the paper gives 200 ns (LAN) and 30 µs (Internet) with 1,000 measurements. — [29C3 Schinzel slides](https://fahrplan.events.ccc.de/congress/2012/Fahrplan/attachments/2235_29c3-schinzel.pdf) (secondary; numbers conflict slightly)
- Van Goethem, Pöpper, Joosen & Vanhoef, "Timeless Timing Attacks: Exploiting Concurrency to Leak Secrets over Remote Connections", USENIX Security 2020. They compare the response order of concurrent requests instead of absolute time. They report "a roughly 100-fold improvement over typical Internet timing attacks, with detection of differences as small as 100ns". The HTTP/2 result needed roughly 40,000 request pairs to infer 100 ns. Targets also included Tor onion services and EAP-pwd. A caveat: CDNs that speak HTTP/1.1 to the origin limit exposure. — [USENIX abstract](https://usenix.org/conference/usenixsecurity20/presentation/van-goethem), [The Hacker News coverage](https://thehackernews.com/2020/07/http2-timing-side-channel-attacks.html)
- James Kettle (PortSwigger), "Listen to the whispers: web timing attacks that actually work", Black Hat USA / DEF CON 32 (talk 2024-08-09). The single-packet attack makes timing attacks "'local', universal, and feasible". It is implemented in Param Miner. The defensive guidance is to assume attackers can see the full execution flow and not to rely on noise. — [PortSwigger research](https://portswigger.net/research/listen-to-the-whispers-web-timing-attacks-that-actually-work), [Black Hat slides](https://i.blackhat.com/BH-US-24/Presentations/US-24-Kettle-Listen-to-the-whispers-web-timing-attacks-that-actually-work.pdf) (via search summary; host blocked for direct fetch)
- Login user enumeration: a recent concrete case is Traefik CVE-2026-88010, "BasicAuth singleflight coalescing reintroduces an unauthenticated username-enumeration timing oracle" (Moderate, 2026-09-22). — [GitHub Advisory DB "padding oracle" results page](https://github.com/advisories?query=padding+oracle)

#### (b) Incidents and CVEs (comparison-timing class)
- Historical: cookie-signature (npm, used by Express's cookie signing) CVE-2016-1000236; Symfony UriSigner CVE-2019-18887; Apache Tapestry HMAC compare CVE-2019-10071 (Critical). — [GitHub Advisory DB search](https://github.com/advisories?query=timing+attack+signature+comparison)
- 2025–2026:
  - httpsig-rs CVE-2025-59058, "HMAC verification is vulnerable to timing attack" (2025-09-12);
  - SCRAM CVE-2025-59432 (2025-09-16);
  - mojic (npm) CVE-2026-41244, "Observable Timing Discrepancy in HMAC Verification" (2026-04-16);
  - phpseclib CVE-2026-40194, "variable-time HMAC comparison… using != instead of hash_equals()" (2026-04-10);
  - **pay-rails/pay: "non-constant-time HMAC comparison in Paddle Billing webhook signature verifier"** (High, 2026-07-01). This is the webhook-handler pattern exactly;
  - Mojo::JWT CVE-2026-9537 (2026-07-17);
  - Phalcon CVE-2026-54736 (2026-08-28).
  — [GitHub Advisory DB search](https://github.com/advisories?query=timing+attack+signature+comparison), [phpseclib GHSA-r854-jrxh-36qx](https://github.com/advisories/GHSA-r854-jrxh-36qx)

#### (c) Why vibe-coded apps are prone, and stack defaults
- Typical generated code: `if (signature === expectedSignature)` in hand-rolled Stripe, GitHub, Clerk or Paddle webhook handlers; `if (req.headers['x-api-key'] !== process.env.API_KEY)` in Next.js API routes; `if token == stored_token` in Flask or FastAPI. eslint-plugin-security's `detect-possible-timing-attacks` rule exists precisely to flag "insecure comparisons (`==`, `!=`, `!==` and `===`), which check input sequentially". — [eslint-plugin-security 4.2.1 README](https://registry.npmjs.org/eslint-plugin-security)
- `crypto.timingSafeEqual(a, b)`: "`a` and `b`… must have the same byte length. An error is thrown if `a` and `b` have different byte lengths." Also: "Use of `crypto.timingSafeEqual` does not guarantee that the _surrounding_ code is timing-safe." I observed the thrown code `ERR_CRYPTO_TIMING_SAFE_EQUAL_LENGTH`. A naive wrapper therefore turns a malformed header into an uncaught 500. — [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md) (Node docs v26.13.1)
- Python `hmac.compare_digest(a, b)` "uses an approach designed to prevent timing analysis by avoiding content-based short circuiting behaviour". Inputs must both be `str` (ASCII) or both bytes-like. "If a and b are of different lengths… a timing attack could theoretically reveal information about the types and lengths… but not their values." Since 3.10 it uses OpenSSL `CRYPTO_memcmp()` when available. `secrets.compare_digest` is the same function. — [CPython Doc/library/hmac.rst](https://github.com/python/cpython/blob/main/Doc/library/hmac.rst), [secrets.rst](https://github.com/python/cpython/blob/main/Doc/library/secrets.rst)
- Stripe's Node SDK `webhooks.constructEvent(payload, header, secret, tolerance?)` has `DEFAULT_TOLERANCE: 300, // 5 minutes`, so it rejects stale timestamps (replay) as well as bad signatures. Hand-rolled verifiers usually skip the timestamp. — [stripe-node src/Webhooks.ts](https://github.com/stripe/stripe-node/blob/master/src/Webhooks.ts)
- GitHub's official JS example uses `@octokit/webhooks`' `webhooks.verify(body, signature)` on the raw `await req.text()` body. The header is `X-Hub-Signature-256: sha256=<hex>`. — [GitHub Docs source](https://github.com/github/docs/blob/main/content/webhooks/using-webhooks/validating-webhook-deliveries.md)

#### (d) Safe self-testing
- Lint: eslint-plugin-security `detect-possible-timing-attacks` (JS/TS). Grep for `===`/`==` adjacent to `signature|hmac|token|apiKey|secret|digest`. Python: grep `==` against `hexdigest()`. — [eslint-plugin-security](https://registry.npmjs.org/eslint-plugin-security)
- Unit tests:
  - the verifier returns `false` (not throw) for a missing header, a shorter or longer header, and a wrong-case prefix;
  - it returns `true` for the correct signature;
  - a spy shows `timingSafeEqual`/`compare_digest` is called.
  - Do not try statistical timing measurements against production. Kettle's and Van Goethem's techniques need request volumes that look like an attack.

#### (e) Fix
- Node: compare fixed-length digests with `timingSafeEqual` after an explicit length check, or hash both sides to 32 bytes first. Use vendor SDKs where they exist (`stripe.webhooks.constructEvent`, `@octokit/webhooks`). — [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md), [Stripe](https://github.com/stripe/stripe-node/blob/master/src/Webhooks.ts), [GitHub Docs](https://github.com/github/docs/blob/main/content/webhooks/using-webhooks/validating-webhook-deliveries.md)
- Python: `hmac.compare_digest(expected, received)`, as in GitHub's FastAPI example (`if not hmac.compare_digest(expected_signature, signature_header): raise HTTPException(status_code=403…)`). — [GitHub Docs source](https://github.com/github/docs/blob/main/content/webhooks/using-webhooks/validating-webhook-deliveries.md)

#### (f) Common incorrect fixes
- Adding a random `sleep`/jitter. Noise averages out over repeated requests, and Kettle's guidance is that "security should not rely on noise". — [PortSwigger research (search summary)](https://portswigger.net/research/listen-to-the-whispers)
- `timingSafeEqual(Buffer.from(a), Buffer.from(b))` with no length guard. It throws on mismatch, which gives an unhandled 500 and a distinguishable response. — [Node crypto.md](https://github.com/nodejs/node/blob/main/doc/api/crypto.md)
- Comparing lengths and then looping with `return false` on the first mismatch: still early-exit. Converting both to hex and using `===`: still early-exit. — (inference)
- Constant-time compare of the signature while still parsing JSON first, or verifying the re-serialized parsed body instead of the raw body. Verification then fails on legitimate requests, and developers "fix" it by removing the check. — (inference; GitHub's example reads `await req.text()`)
- Fixing the comparison but not the existence check. Login code that returns early when the user doesn't exist (skipping bcrypt or Argon2) still leaks which accounts exist. The Traefik 2026 CVE is this class. — [GitHub Advisory DB](https://github.com/advisories?query=padding+oracle)

#### (g) Verification
- Before: the handler with `===` passes functional tests but fails the ESLint rule. A test passing a 1-character header crashes with `ERR_CRYPTO_TIMING_SAFE_EQUAL_LENGTH` if the naive wrapper is used.
- After: lint is clean, and the unequal-length test returns 401 without throwing. Observed this session: the `safeEqual` helper below returned false for `'abc'` vs `'abcd'` and `''` vs `'x'`, and the GitHub-style verifier returned false for a truncated header and for `undefined`.

### Inferences
- **Recommended TypeScript (tested).**
```ts
import { createHmac, createHash, timingSafeEqual } from 'node:crypto';
// General secret compare (API keys, tokens): hash both to fixed 32 bytes -> no length throw, no length leak
export function safeEqual(a: string, b: string): boolean {
  const ha = createHash('sha256').update(a).digest();
  const hb = createHash('sha256').update(b).digest();
  return timingSafeEqual(ha, hb);
}
// GitHub-style webhook (Next.js App Router: const raw = await req.text(); never JSON.parse first)
export function verifyGithub(raw: string, header: string | null, secret: string): boolean {
  if (!header) return false;
  const expected = Buffer.from('sha256=' + createHmac('sha256', secret).update(raw).digest('hex'));
  const got = Buffer.from(header);
  return got.length === expected.length && timingSafeEqual(got, expected); // length is public for HMAC-SHA256
}
// Stripe: stripe.webhooks.constructEvent(raw, req.headers.get('stripe-signature')!, process.env.STRIPE_WEBHOOK_SECRET!)
```
- **Python.**
```python
import hmac, hashlib
def verify_github(raw: bytes, header: str | None, secret: bytes) -> bool:
    if not header: return False
    expected = "sha256=" + hmac.new(secret, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```
- **Login equalization (inference; pattern widely recommended, e.g. OWASP Authentication Cheat Sheet [not re-verified]).** If the user is not found, still run the password verifier against a precomputed dummy hash with the same parameters, then return the same generic error. For example, Python argon2-cffi: `ph.verify(DUMMY_HASH, password)` inside `try/except`. Node: `await argon2.verify(DUMMY_HASH, password)`.
- **Token and API-key lookup (inference).** Look up by `sha256(token)` (an indexed equality on a hash the attacker cannot steer prefix-by-prefix), or by a public key-ID followed by `timingSafeEqual` on the hashed secret. Do not run `WHERE token = $raw`.
- **Defense in depth.** Rate-limit per IP and per account on signature and redemption failures. Use webhook timestamp tolerance (Stripe default 300 s) and idempotency keys against replay.

### Gaps
- I could not fetch the Kettle paper or the Timeless Timing paper PDFs directly. The figures come from abstracts and secondary coverage. I did not confirm whether Kettle demonstrated byte-by-byte secret recovery via string comparison; my understanding is that his findings centred on discovering hidden attack surface (parameters, SSRF/reverse-proxy routing, server-side injection) **[uncertain]**.
- The Crosby et al. figures differ between my recollection of the abstract (20 µs Internet / 100 ns LAN) and the 29C3 slides (30 µs / 200 ns). The paper itself was not opened.
- No primary data on how often AI assistants emit `===` for signature checks.

---

## (15) Padding oracle attacks: mechanism, history, 2026 CVEs, AI patterns, AEAD fix

### Takeaway
Any app that decrypts attacker-supplied AES-CBC ciphertext before authenticating it is exposed. Hand-rolled `aes-256-cbc` "encrypt/decrypt" helpers with no MAC, and MAC-then-encrypt designs, both qualify. If the app reveals whether the padding was valid through different errors, status codes or timing, an attacker can decrypt (and often forge) tokens byte by byte. The defect was described in 2002 and was exploited in ASP.NET (2010), SSL 3.0 (POODLE, 2014) and TLS (Lucky Thirteen, 2013). It still produced CVEs in 2026: Tomcat, phpseclib, node-forge, wolfSSL. The fix is an AEAD (AES-256-GCM with unique 96-bit nonces, or XChaCha20-Poly1305) or a high-level library (libsodium secretbox, Tink, Fernet, iron-session) with a random 32-byte key and versioned key rotation.

### Cited Findings

#### (a) Mechanism
- The term "padding oracle" comes from Serge Vaudenay, "Security Flaws Induced by CBC Padding: Applications to SSL, IPSEC, WTLS…", EUROCRYPT 2002. — [Vaudenay 2002 (IACR archive PDF)](https://iacr.org/archive/eurocrypt2002/23320530/cbc02_e02d.pdf), [Wikipedia: Padding oracle attack](https://en.wikipedia.org/wiki/Padding_oracle_attack)
- How it works. In CBC, each plaintext block is the block-cipher decryption of ciphertext block i XORed with ciphertext block i−1. PKCS#7 padding is checked after decryption. An attacker who can submit modified ciphertexts and observe a "bad padding" vs "bad data" distinction can adjust block i−1 to learn the intermediate decryption one byte at a time: at most 256 guesses per byte. The result is full plaintext recovery without the key. The same oracle can be used to encrypt chosen plaintext ("CBC-R"), which forges valid tokens. — [Wikipedia](https://en.wikipedia.org/wiki/Padding_oracle_attack) (general description; CBC-R/forgery detail **[not re-verified]**)
- Preconditions:
  1. Unauthenticated CBC, or authentication checked after unpadding (MAC-then-encrypt).
  2. Attacker-controlled ciphertext reaches decryption: a cookie, a URL token, a "secure" link parameter, an encrypted hidden form field.
  3. A distinguishable outcome: error message, HTTP status, redirect, or timing.
  Lucky Thirteen showed that (3) can be pure timing even when error messages are uniform. — [Wikipedia](https://en.wikipedia.org/wiki/Padding_oracle_attack), [Lucky 13 summary](https://elvis.hcw.ac.at/wiki/index.php/Lucky_Thirteen)
- Tomcat's 2026 advisory classifies its padding oracle as CWE-209 ("Generation of Error Message Containing Sensitive Information"). The oracle was a distinguishable error, under default configuration. — [GHSA-h468-7pvh-8vr8](https://github.com/advisories/GHSA-h468-7pvh-8vr8)

#### (b) Incidents and CVEs
**Historical:**
- ASP.NET MS10-070 / CVE-2010-3332 (Sept 2010): Rizzo & Duong's "Practical Padding Oracle Attacks". It decrypted and forged ASP.NET encrypted ViewState/auth data and could download `web.config`. — **[not re-verified; search returned nothing on MS10-070]**
- Lucky Thirteen, CVE-2013-0169 (AlFardan & Paterson, 2013): a timing side channel in TLS CBC's MAC-then-encrypt record processing, "distinguishing attacks and plaintext-recovery attacks via statistical analysis of timing data". OpenSSL's fix later introduced another padding oracle, CVE-2016-2107 (May 2016). — [Wikipedia](https://en.wikipedia.org/wiki/Padding_oracle_attack), [cve.enginsight CVE-2013-0169](https://cve.enginsight.com/2013/0169/index.html)
- POODLE, CVE-2014-3566 (Oct 2014, Möller/Duong/Kotowicz): a downgrade to SSL 3.0 combined with SSL 3.0's padding oracle (unchecked padding bytes). — [Wikipedia](https://en.wikipedia.org/wiki/Padding_oracle_attack) (author list **[not re-verified]**)

**2026** (GitHub Advisory DB; 99 advisories match "padding oracle"):
- Apache Tomcat CVE-2026-29146, "Padding Oracle vulnerability in Apache Tomcat's EncryptInterceptor with default configuration".
  - High, CVSS v4 8.7, 2026-04-09.
  - Affected ranges per package data: 11.0.0-M1–11.0.18, 10.1.50–10.1.52, 9.0.13–9.0.115, 8.5.38–8.5.100, 7.0.100–7.0.109.
  - Patched: 9.0.116, 10.1.53, 11.0.20. The description says 11.0.19, which conflicts with the package data.
  — [GHSA-h468-7pvh-8vr8](https://github.com/advisories/GHSA-h468-7pvh-8vr8)
- phpseclib CVE-2026-32935, "AES-CBC unpadding susceptible to padding oracle timing attack" (High, 2026-03-19). — [GHSA-94g3-g5v7-q4jg](https://github.com/advisories/GHSA-94g3-g5v7-q4jg)
- node-forge (npm) CVE-2026-118776, "Incomplete PKCS#7 padding validation in AES/DES CBC and ECB decryption" (Low, 2026-11-10). — [GHSA-2vgq-wchc-25w7](https://github.com/advisories/GHSA-2vgq-wchc-25w7)
- wolfSSL CVE-2026-5504 (PKCS7 CBC padding oracle, 2026-04-10). Oberon ocrypto / PSA Crypto CVE-2026-16458/16459 (2026-08-13). A "Secret Server" padding oracle, CVE-2026-15638 (Critical, unreviewed, 2026-09-16; vendor not shown on the listing). Telerik UI for AJAX RadAsyncUpload CVE-2026-13182 (2026-07-22). — [GitHub Advisory DB "padding oracle"](https://github.com/advisories?query=padding+oracle)
- RSA-padding (Bleichenbacher/Marvin) relatives, relevant to JWE `RSA1_5`:
  - Authlib CVE-2026-28490, "JWE RSA1_5 Bleichenbacher Padding Oracle" (High, 2026-03-16);
  - web-token/jwt-library "RSA1_5… lacks implicit rejection, exposing a Bleichenbacher/Marvin padding oracle" (2026-06-18);
  - pyca/cryptography CVE-2026-69247, "PKCS#7 EnvelopedData decryption exposes a Bleichenbacher oracle" (High, 2026-08-03).
  — [GitHub Advisory DB "padding oracle"](https://github.com/advisories?query=padding+oracle)
- Microsoft.AspNetCore.DataProtection CVE-2026-40372 ("ASP.NET Core Elevation of Privilege", Critical, 2026-04-23) appears in the same search results. Its relation to padding oracles is not stated in the listing. **[uncertain]** — [GitHub Advisory DB](https://github.com/advisories?query=padding+oracle)

#### (c) Why vibe-coded apps are prone
- Node removed the old `crypto.createCipher()`/`createDecipher()` APIs in v22.0.0 (End-of-Life, DEP0106) "as they use a weak key derivation function (MD5 with no salt) and static initialization vectors". Training data and older tutorials are full of them. A model that "upgrades" such code to `createCipheriv('aes-256-cbc', key, iv)` without adding a MAC produces an unauthenticated-CBC helper. — [Node deprecations.md DEP0106](https://github.com/nodejs/node/blob/main/doc/api/deprecations.md)
- Typical generated helper: `const key = crypto.createHash('sha256').update(process.env.SECRET).digest()`; `iv = randomBytes(16)`; `createCipheriv('aes-256-cbc', key, iv)`; return `iv.toString('hex') + ':' + encrypted`. Decrypt wraps `decipher.final()` in try/catch and returns a different error, or a 500 vs a 400. That is exactly the precondition set above. — (inference; pattern consistent with the Semgrep rules below)
- Semgrep rule `crypto-mode-without-authentication` (pyca `cryptography` and PyCryptodome): "An encryption mode of operation is being used without proper message authentication… Consider instead use an AEAD mode of operation like GCM." Node rule: `create-de-cipher-no-iv`. — [semgrep-rules python/cryptography](https://github.com/semgrep/semgrep-rules/blob/develop/python/cryptography/security/mode-without-authentication.yaml), [javascript/node-crypto](https://github.com/semgrep/semgrep-rules/tree/develop/javascript/node-crypto/security)
- GCM misuse hazards in Node:
  - "`decipher.setAuthTag()`… must be called… before `decipher.final()` for `GCM`… can only be called once." If the tag is missing or the data was tampered with, `final()` throws.
  - "Even if the underlying cipher implements authentication, the authenticity and integrity of the plaintext returned from [`update()`] may be uncertain at this time… authenticity is generally only established when the application calls `decipher.final()`."
  - Node v26.0.0: "Using GCM tag lengths other than 128 bits without specifying the `authTagLength` option when creating `decipher` is not allowed anymore" (deprecated in v22.0.0/v20.13.0). This closes truncated-tag acceptance.
  — [Node crypto docs v26.13.1](https://nodejs.org/api/crypto.html)

#### (d) Safe self-testing
- Static checks: grep for `aes-256-cbc`, `aes-128-cbc`, `MODE_CBC`, `modes.CBC`, `createCipher(`, `CryptoJS.AES.encrypt(` (passphrase mode), and `ECB`. Run the Semgrep rules above.
- Unit test against your own decrypt function:
  - flip one bit of the ciphertext, IV or tag; decryption must fail;
  - every failure must surface as the same generic error or HTTP status;
  - no plaintext from `update()` may be returned before `final()` succeeds.
- Do not run padding-oracle tooling against production.

#### (e) Fix
- pyca/cryptography: `AESGCM(key)` accepts "A 128, 192, or 256-bit key", supports only 128-bit tags, and takes a 12-byte nonce: "**NEVER REUSE A NONCE** with a key". The example uses `nonce = os.urandom(12)`. `ChaCha20Poly1305` has the same nonce rule. `decrypt` raises `InvalidTag` on tamper (observed). Current version 50.0.2. — [pyca docs aead.rst](https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/aead.rst), [PyPI](https://pypi.org/project/cryptography/)
- Fernet: "AES in CBC mode with a 128-bit key for encryption" plus HMAC-SHA256 (encrypt-then-MAC). `decrypt(token, ttl=None)` enforces token age. `MultiFernet([key1, key2])` encrypts with the first key, decrypts with any, and `.rotate()` re-encrypts. Fernet is therefore a safe CBC construction. For passwords, "it is generally recommended to use `Argon2id`" as the KDF. — [pyca docs fernet.rst](https://github.com/pyca/cryptography/blob/main/docs/fernet.rst)
- iron-session 9.1.0 (2026-11-12): `password` "has to be at least 32 characters long" and can be `{2: "...", 1: "..."}` "to allow for password rotation. iron-session will use the highest numbered key for new cookies." — [iron-session README](https://github.com/vvo/iron-session/blob/main/README.md), [npm](https://registry.npmjs.org/iron-session)
- Other current versions: libsodium-wrappers 0.8.4 (2026-04-19), @noble/ciphers 2.4.0 (2026-08-27), Tink for Python `tink` 1.16.1 (2026-08-13), PyNaCl 1.6.2. The npm `tink-crypto` package's last release was 0.1.1 (2023), so treat Tink as Python/Java/Go-first. — [npm registry](https://registry.npmjs.org/libsodium-wrappers), [PyPI tink](https://pypi.org/project/tink/), [npm tink-crypto](https://registry.npmjs.org/tink-crypto)
- Node's own replacement advice for `createCipher`: "derive a key using `crypto.pbkdf2()` or `crypto.scrypt()` with random salts and… use `crypto.createCipheriv()`". An automated codemod exists: `npx codemod @nodejs/crypto-createcipheriv-migration`. — [Node DEP0106](https://github.com/nodejs/node/blob/main/doc/api/deprecations.md)

#### (f) Common incorrect or incomplete fixes
- Keeping CBC and returning a uniform error message: timing can still distinguish (Lucky Thirteen; phpseclib CVE-2026-32935 is a *timing* padding oracle). — [Wikipedia](https://en.wikipedia.org/wiki/Padding_oracle_attack), [GHSA-94g3-g5v7-q4jg](https://github.com/advisories/GHSA-94g3-g5v7-q4jg)
- Adding an HMAC but verifying it after decrypt and unpad (MAC-then-encrypt), or MACing the ciphertext without the IV or version byte, or comparing the MAC with `===` (see (14)). — (inference from the mechanism; Fernet's design is encrypt-then-MAC)
- Switching to CTR or GCM but generating the IV from a counter that resets on restart, a constant, or `Math.random`. GCM nonce reuse under one key breaks confidentiality for the colliding messages and leaks the GHASH authentication key, enabling forgeries (Joux "forbidden attack"; Böck et al., USENIX WOOT 2016, found real HTTPS servers repeating GCM nonces). — **[not re-verified]**; pyca's "NEVER REUSE A NONCE" warning is verified: [aead.rst](https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/aead.rst)
- Random 96-bit nonces with no key-usage limit. NIST SP 800-38D limits random-IV GCM to 2^32 invocations per key. — **[not re-verified]**
- Using `decipher.update()` output (streaming) before `final()` succeeds. — [Node crypto docs](https://nodejs.org/api/crypto.html)
- Key = `sha256(passphrase)` or MD5 (EVP_BytesToKey-style, as in the removed `createCipher` and CryptoJS passphrase mode). This is fast and unsalted, so it is brute-forceable. Use a random 32-byte key from a secret store; derive subkeys with HKDF; use scrypt or Argon2id only when the input really is a human password. — [Node DEP0106](https://github.com/nodejs/node/blob/main/doc/api/deprecations.md), [Fernet docs](https://github.com/pyca/cryptography/blob/main/docs/fernet.rst)

#### (g) Verification
- Before: a CBC helper decrypts a 1-bit-flipped ciphertext into garbage, or throws `bad decrypt` only when the padding is wrong. Either way, tamper is not reliably detected.
- After (observed this session):
  - the AES-256-GCM helper round-trips;
  - it rejects a 1-bit ciphertext flip;
  - it rejects a wrong AAD (context binding);
  - Python `AESGCM` raised `InvalidTag` on a 1-bit flip.

### Inferences
- **Recommended TypeScript (Node ≥20; tested on 22.23.4).** Versioned envelope = `version(1) | iv(12) | tag(16) | ciphertext`.
```ts
import { randomBytes, createCipheriv, createDecipheriv } from 'node:crypto';
const KEYS: Record<number, Buffer> = { 1: Buffer.from(process.env.ENC_KEY_V1!, 'base64') }; // 32 random bytes each
const CURRENT = 1;
export function seal(plaintext: string, context: string): string {
  const key = KEYS[CURRENT]; if (key?.length !== 32) throw new Error('bad key');
  const iv = randomBytes(12);                                         // unique 96-bit nonce per message
  const c = createCipheriv('aes-256-gcm', key, iv, { authTagLength: 16 });
  c.setAAD(Buffer.from(context));                                     // bind to purpose/user, e.g. `reset:${userId}`
  const ct = Buffer.concat([c.update(plaintext, 'utf8'), c.final()]);
  return Buffer.concat([Buffer.from([CURRENT]), iv, c.getAuthTag(), ct]).toString('base64url');
}
export function open(token: string, context: string): string {
  const b = Buffer.from(token, 'base64url');
  const key = KEYS[b[0]];
  if (!key || b.length < 29) throw new Error('invalid');              // one generic error for every failure
  const d = createDecipheriv('aes-256-gcm', key, b.subarray(1, 13), { authTagLength: 16 });
  d.setAAD(Buffer.from(context));
  d.setAuthTag(b.subarray(13, 29));                                   // before final()
  try { return Buffer.concat([d.update(b.subarray(29)), d.final()]).toString('utf8'); }
  catch { throw new Error('invalid'); }                               // never release update() output on failure
}
```
- **Where GCM's nonce limit matters.** For high-volume or long-lived keys, prefer XChaCha20-Poly1305: a 192-bit random nonce removes the birthday concern. Use libsodium `crypto_aead_xchacha20poly1305_ietf_*` / `crypto_secretbox_easy` or `@noble/ciphers`' `xchacha20poly1305`. Alternatively, rotate the GCM key by version byte well before 2^32 messages.
- **For session cookies in Next.js.** Use iron-session (or `@hapi/iron`, last release 7.0.1 in Feb 2023 per [npm](https://registry.npmjs.org/@hapi%2Firon)) rather than a custom cipher helper.
- **Python.** `Fernet(Fernet.generate_key())` / `MultiFernet` for app-level tokens with a TTL. Use `AESGCM(AESGCM.generate_key(bit_length=256))` with `os.urandom(12)` nonces when you need AAD.
- **Key handling (inference).**
  - Generate with `crypto.randomBytes(32)` / `os.urandom(32)` and store base64 in a secret manager.
  - Derive per-purpose subkeys with HKDF (`crypto.hkdfSync('sha256', master, salt, info, 32)`) so the encryption and MAC keys, or the cookie and reset-link keys, differ.
  - Never derive keys from a passphrase with a bare hash.
- **Do you even need encryption?** If the goal is integrity only (a signed cookie or link), an HMAC (with constant-time verify) or a random opaque token stored server-side is simpler than encryption.

### Gaps
- I did not fetch Microsoft's MS10-070 bulletin or the Rizzo–Duong paper. Those details are from memory.
- Tomcat's advisory does not state the EncryptInterceptor's cipher mode or whether the fix moved to GCM. The Tomcat 11.0.19 vs 11.0.20 patched-version conflict is unresolved.
- I did not open NIST SP 800-38D or Böck et al. 2016 this session. The nonce-limit and nonce-reuse statements are marked accordingly.
- I did not fetch the libsodium or Tink docs directly; only package versions were checked.

---

## Cross-cutting: evidence that AI-generated code exhibits these flaws, and the tooling that catches them

### Takeaway
Benchmark evidence shows AI coding models still produce insecure code in a large share of security-relevant tasks: about 45% overall in Veracode's 2025 benchmark, essentially unchanged in its Spring 2026 update. Cryptographic-algorithm choice is one of the better categories (about 86% pass). I found no primary study that isolates the four specific patterns covered here, namely `jwt.decode`-instead-of-verify, `Math.random` tokens, `===` signature comparison, and unauthenticated CBC. The strongest pattern-level evidence is indirect: dedicated community lint rules exist for each, and 2025–2026 CVEs keep landing in exactly these shapes.

### Cited Findings
- Veracode's 2025 GenAI Code Security Report: AI-generated code "introduced security vulnerabilities in 45% of 80 curated coding tasks across more than 100 LLMs". — [Veracode press release (July 2025)](https://www.veracode.com/press-release/ai-generated-code-poses-major-security-risks-in-nearly-half-of-all-development-tasks-veracode-research-reveals/)
- Cryptographic-algorithm (CWE-327) pass rate was about 85.6% in 2025 (ITPro) and "86% security pass rate" in the Spring 2026 update, which says the numbers "have barely budged since our initial 2025 report". — [ITPro](https://www.itpro.com/technology/artificial-intelligence/researchers-tested-over-100-leading-ai-models-on-coding-tasks-nearly-half-produced-glaring-security-flaws), [Veracode Spring 2026 update](https://veracode.com/blog/spring-2026-genai-code-security)
- Caveat: the Veracode figures are from a benchmark of prompted tasks and should not be read as a universal measure of AI-generated software. The full report text was not accessible; figures come from the press release and coverage. — [search summary](https://www.softwareseni.com/why-45-percent-of-ai-generated-code-contains-security-vulnerabilities/)
- Existing rules a vibe-coding developer can drop into CI (verified rule IDs and files):
  - Semgrep: `jwt-decode-without-verify`, `jwt-none-alg`, `jwt-hardcode` (JS jsonwebtoken and jose); `unverified-jwt-decode`, `jwt-none-alg`, `jwt-hardcode` (Python); `insecure-uuid-version` (Python); `crypto-mode-without-authentication` (Python cryptography and PyCryptodome); `create-de-cipher-no-iv` (Node).
  - ESLint: eslint-plugin-security 4.2.1 `detect-possible-timing-attacks`, `detect-pseudoRandomBytes`.
  - I found no community Semgrep or ESLint rule for `Math.random()` used for tokens, so a custom rule is needed.
  — [semgrep-rules (develop, cloned 2026-11-17)](https://github.com/semgrep/semgrep-rules), [eslint-plugin-security](https://registry.npmjs.org/eslint-plugin-security)

### Inferences
- **Patterns with simple greppable signatures.** For a vibe-coded app, a five-minute audit covers all four attacks: `jwt.decode(`, `verify_signature`, `algorithms` missing or mixed; `Math.random`, `uuid1`/`v1`, `random.`; `===` near `signature|hmac|apiKey`; `aes-*-cbc`, `MODE_CBC`, `createCipher(`. A minimal custom Semgrep rule for Math.random in token contexts would fill the gap I found.
- **The 2026 advisory cluster suggests libraries are still converging on safe defaults.** Hono made `alg` mandatory, PyJWT now rejects public-key material as HMAC secrets, and Node v26 rejects non-128-bit GCM tags without `authTagLength`. App code should not rely on library defaults alone; pin explicitly.

### Gaps
- No primary study measures how often AI assistants generate each of these four patterns. Pearce et al. "Asleep at the Keyboard" (IEEE S&P 2022) reported about 40% vulnerable Copilot completions, including CWE-327/330 scenarios, but I did not re-verify that this session.
- The Veracode report's per-CWE results for CWE-330/338 (weak randomness) and CWE-208 (timing), if they exist, were not accessible.
