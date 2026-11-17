# Credential-handling attacks on vibe-coded apps: (2) the 52-character username / bcrypt truncation, (6) 2FA/OTP replay and brute force, (20) Unicode username canonicalization ("Unicode = Spotify")

Research date: 2026-11-17. Method note: in this session WebFetch could not resolve several hosts (trust.okta.com, engineering.atspotify.com, oasis.security, rfc-editor.org). For those I used web-search summaries and say so where it matters. Library behaviour, OWASP text, NIST SP 800-63B-4 text, Django code, Supabase Auth code and the next-auth fix were all checked against primary sources. I cloned the public repositories (pyca/bcrypt, golang/crypto, dcodeIO/bcrypt.js, kelektiv/node.bcrypt.js, pyauth/pyotp, yeojz/otplib, supabase/auth, OWASP/CheatSheetSeries, usnistgov/800-63-4, django/django, nextauthjs/next-auth, twisted/twisted, fastapi/fastapi) on 2026-11-17. I also ran the library behaviours locally: bcrypt 5.0.0, passlib 1.7.4, argon2-cffi 25.1.0, pyotp 2.12.0, bcryptjs 3.0.3, bcrypt (npm) 6.0.0, argon2 (npm) 0.45.2, otplib 13.6.0, Node 22. Anything marked "from prior knowledge" or "unverified" was not checked against a primary source in this session.

## Attack 2 — the "52-character username" bcrypt truncation bypass (and bcrypt input-limit bugs in general)

### Takeaway
On 30 Oct 2024 Okta found a flaw in how it built the AD/LDAP delegated-authentication cache key. It ran bcrypt over userId + username + password. Bcrypt reads only the first 72 bytes, so when the username was 52 characters or longer the password fell outside the hashed input. From 23 Jul to 30 Oct 2024, an affected user could therefore log in from cache with any password. Okta fixed it by switching the key derivation to PBKDF2. The general lesson for app developers: bcrypt silently ignores input beyond 72 bytes in the two most common Node libraries, which AI assistants emit by default. pyca/bcrypt 5.0.0 now raises instead, and Go's `GenerateFromPassword` returns `ErrPasswordTooLong`. A slow password hash must never serve as a lookup or cache key. Use Argon2id for storage, and use a length-prefixed HMAC for keys.

### Cited Findings

**(a) Mechanism — the Okta incident**
- Okta's advisory is titled "Okta AD/LDAP Delegated Authentication - Username Above 52 Characters Security Advisory" and dated Nov 1, 2024. Okta says it "internally identified" a vulnerability in generating the cache key for AD/LDAP DelAuth on October 30, 2024, and that "Bcrypt was used to hash a combined string of userId + username + password." I read this through a search summary of the advisory; the page itself could not be fetched here — [Okta Trust advisory](https://trust.okta.com/security-advisories/okta-ad-ldap-delegated-authentication-username/)
- Exposure window: introduced in the 23 Jul 2024 release, fixed in production on 30 Oct 2024. Required conditions: AD/LDAP DelAuth in use, no MFA, username of 52 or more characters, and the user had authenticated before, so a cache entry existed. The cache was used instead of a fresh authentication when the AD/LDAP agent was unreachable, for example under high load or during connectivity problems — [Okta Trust advisory (via search summary)](https://trust.okta.com/security-advisories/okta-ad-ldap-delegated-authentication-username/); [Nudge Security summary](https://www.nudgesecurity.com/post/ad-ldap-delegated-authentication-bypass-username-above-52-characters); [Cyber Kendra](https://www.cyberkendra.com/2024/11/okta-patches-critical-authentication.html)
- Fix: Okta "switched from Bcrypt to PBKDF2" for cache-key generation on 30 Oct 2024. It told customers to search the System Log for unexpected authentications by usernames longer than 52 characters between 23 Jul and 30 Oct 2024 — [Okta Trust advisory (via search summary)](https://trust.okta.com/security-advisories/okta-ad-ldap-delegated-authentication-username/)
- Third-party analyses attribute the 52-character figure to bcrypt's 72-byte input limit: a long enough userId + username consumes all 72 bytes, so the password contributes nothing. Okta's own text does not walk through the arithmetic — [Joseph Scott, "Okta, bcrypt, and 52+ Character Usernames"](https://josephscott.org/blog/2024/okta-bcrypt-and-52-character-usernames/); [Invicti explanation](https://www.invicti.com/blog/web-security/okta-vulnerability-bcrypt-auth)

**(a) Mechanism — bcrypt's input limit, generalised**
- The OWASP Password Storage Cheat Sheet says: "bcrypt has a maximum length input length of 72 bytes for most implementations, so you should enforce a maximum password length of 72 bytes." Its legacy guidance reads: "use a work factor of 10 or more and with a password limit of 72 bytes" — [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- Bytes, not characters. node.bcrypt.js: "only the first 72 bytes of a string are used. Any extra bytes are ignored when matching passwords. Note that this is not the first 72 *characters*… (e.g. a UTF-8 encoded string containing emojis)." — [node.bcrypt.js README](https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md). I confirmed locally that 18 × "🔒" (4 bytes each in UTF-8) already fills 72 bytes.
- NUL bytes when pre-hashing. OWASP: "The original bcrypt expects a null terminated password string, this means that the hash value will only be used to the first null byte in the hash value. (`bcrypt(H($password)), $salt, $cost) == bcrypt("", $salt, $cost)` if `H($password)[0] == 0`)". It also warns about "password shucking": `bcrypt(base64(sha512($password)))` "is as secure as just using pure SHA-512" against an attacker who holds leaked unsalted hashes — [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- OWASP's prescribed pre-hash if bcrypt must stay: `bcrypt(base64(hmac-sha384(data:$password, key:$pepper)), $salt, $cost)`, with the pepper stored outside the database — [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- NIST SP 800-63B-4 (final) says verifiers "SHALL verify the entire submitted password (e.g., not truncate it)". If Unicode is accepted, they "SHOULD apply… Normalization Form Canonical Composition (NFC)… before hashing". They "SHOULD permit a maximum password length of at least 64 characters", and each "Unicode code point SHALL be counted as a single character". Single-factor passwords must be at least 15 characters — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) (text extracted from the [usnistgov/800-63-4 repo](https://github.com/usnistgov/800-63-4), whose README states the four volumes are "finalized")
- Implication: a 64-character passphrase made of 2–4-byte code points can exceed 72 bytes. Under NIST's "not truncate" rule, plain bcrypt with silent truncation is non-conformant for such inputs (my inference from the two citations above).

**(b) Incidents, CVEs, library history**
- Okta (above): 23 Jul to 30 Oct 2024, fixed in Okta's SaaS by moving to PBKDF2. There is no customer-installed version to patch — [Okta Trust advisory](https://trust.okta.com/security-advisories/okta-ad-ldap-delegated-authentication-username/)
- node.bcrypt.js (`bcrypt` on npm), historical: "Versions `< 5.0.0` suffer from bcrypt wrap-around bug and will truncate passwords >= 255 characters" and "do not handle NUL characters inside passwords properly leading to all subsequent characters being dropped." The 5.0.0 changelog (2020-06-02) says "Fix the bcrypt 'wrap-around' bug" and "Fix a bug related to NUL in password input" — [node.bcrypt.js README](https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md); [CHANGELOG](https://github.com/kelektiv/node.bcrypt.js/blob/master/CHANGELOG.md)
- `bcrypt` (npm) current is 6.0.0. The CHANGELOG header reads "6.0.0 (2025-02-28)", while the npm registry publish time is 2025-05-11. The two dates conflict. 6.0.0 dropped Node ≤16 and switched to prebuildify. It made no change to 72-byte handling — [CHANGELOG](https://github.com/kelektiv/node.bcrypt.js/blob/master/CHANGELOG.md); `npm view bcrypt time` (run 2026-11-17)
- I tested locally that `bcrypt@6.0.0` `compareSync('x'*72+'B', hash('x'*72+'A'))` returns **true**, so silent truncation is still present. Two Buffers that both begin with 0x00 but differ afterwards do **not** match, so the NUL bug is fixed for Buffer input (local test, 2026-11-17).
- `bcryptjs` latest is 3.0.3, published 2025-11-02; 3.0.0 came out 2025-02-13 — `npm view bcryptjs time`. Its README says: "The maximum input length is 72 bytes… Note that maximum input length is not implicitly checked by the library for compatibility with the C++ binding on Node.js, but should be checked with `bcrypt.truncates(password)` where necessary." — [bcrypt.js README](https://github.com/dcodeIO/bcrypt.js/blob/main/README.md). I confirmed locally that bcryptjs 3.0.3 silently truncates (the same 73-byte test returns true) and that `truncates()` returns true for 73 bytes.
- pyca/bcrypt 5.0.0 (Python): "Passing `hashpw` a password longer than 72 bytes now raises a `ValueError`. Previously the password was silently truncated" — [pyca/bcrypt CHANGELOG](https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst). In the source, `checkpw` calls `hashpw`, so verification raises too; I confirmed this locally. The error text is "password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])" — [pyca/bcrypt src/_bcrypt/src/lib.rs](https://github.com/pyca/bcrypt/blob/main/src/_bcrypt/src/lib.rs)
- pyca's README recommends pre-hashing as `bcrypt.hashpw(base64.b64encode(hashlib.sha256(password).digest()), …)` "to prevent NULL byte problems" — [pyca/bcrypt README](https://github.com/pyca/bcrypt/blob/main/README.rst). This **unpeppered** recipe is exactly the construction OWASP warns is exposed to password shucking. The two sources are in tension — [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- passlib 1.7.4 (last release on PyPI; a maintained fork is published as `libpass`, latest 1.9.4 per `pip index versions`, 2026-11-17). Local test: `CryptContext(schemes=["bcrypt"]).hash("short")` under passlib 1.7.4 with bcrypt 5.0.0 raises `ValueError: password cannot be longer than 72 bytes…`, after an `AttributeError: module 'bcrypt' has no attribute '__about__'` trace. In other words, hashing even a short password fails with this combination (my local test; the cause is passlib's backend self-test, which I inferred from the trace and did not read in the source).
- Go `golang.org/x/crypto/bcrypt`: `ErrPasswordTooLong = errors.New("bcrypt: password length exceeds 72 bytes")`, and `GenerateFromPassword` returns it when `len(password) > 72`. In the source I read (HEAD 2026-11-15), `CompareHashAndPassword` has no explicit length check — [golang/crypto bcrypt.go](https://github.com/golang/crypto/blob/master/bcrypt/bcrypt.go)
- FastAPI's official OAuth2/JWT tutorial now recommends `pwdlib[argon2]` with `PasswordHash.recommended()` (Argon2) and says "for working with outdated hashes, it is recommended to use the passlib library" — [FastAPI docs, oauth2-jwt.md](https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/security/oauth2-jwt.md)

**(c) Library defaults relevant to AI-generated code**
- OWASP's primary recommendation is "Argon2id with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism". Equivalent settings: m=47104 (46 MiB), t=1, p=1; m=19456 (19 MiB), t=2, p=1; m=12288, t=3; m=9216, t=4; m=7168, t=5. If FIPS-140 is required, "PBKDF2 with a work factor of 600,000 or more… HMAC-SHA-256". A pepper is optional defense in depth — [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- `argon2` (npm, node-argon2) 0.45.2 defaults: `memoryCost: 1 << 16` (64 MiB), `timeCost: 3`, `parallelism: 4` (read from `node_modules/argon2/argon2.cjs`, 2026-11-17), which is above the OWASP minimum. argon2-cffi 25.1.0 `PasswordHasher()` defaults: time_cost 3, memory_cost 65536, parallelism 4, type ID (local inspection) — [argon2-cffi on PyPI](https://pypi.org/project/argon2-cffi/)
- OWASP on PBKDF2: when the password is longer than the HMAC block size (64 bytes for SHA-256) it is pre-hashed automatically, and naive implementations can create a long-password DoS (the 2013 Django case) — [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

### Inferences

**Why vibe-coded apps are prone (c).**
1. The default Node pairing that assistants emit is `bcryptjs`/`bcrypt` + `hash(password, 10)` + `compare()`. Both libraries silently ignore bytes past 72, and neither warns (cited above). Nothing in the generated code shows the limit.
2. The Okta anti-pattern recurs in generated code whenever someone wants a deterministic key that "includes the password": cache keys, idempotency keys, API-key fingerprints, "remember-me" tokens, or `bcrypt(userId + email + password)`. Bcrypt is reached for because it is "the secure hash". Bcrypt is salted, though, so to get a stable key code either reuses a fixed salt or compares on every entry, and the 72-byte cap makes long prefixes swallow the secret.
3. Python assistants trained on pre-2025 FastAPI tutorials still emit `passlib.context.CryptContext(schemes=["bcrypt"])`. With bcrypt 5.0.0 this throws even on short passwords (local test). The common "fix" is to pin `bcrypt==4.0.1`, which restores silent truncation rather than fixing anything.
4. Upgrading to pyca/bcrypt 5.0.0 turns long passwords into `ValueError` at **login** (`checkpw` raises). Code that is not wrapped in try/except returns a 500 error instead of "wrong password".

**Managed providers vs. app owner.** If Supabase Auth, Clerk, Firebase Auth or Auth.js credentials-free flows (OAuth/magic link) store the passwords, the provider owns the hash choice and its length handling, and I did not verify each provider's limits in this session. The app developer still owns:
- any custom credentials provider. Auth.js's `Credentials` provider leaves hashing and verification entirely to app code (from prior knowledge of Auth.js docs, not re-fetched here).
- every derived key or cache key built from secrets.
- secondary secrets: API keys, PINs, recovery codes.
- the migration path when a library's behaviour changes.

**(d) Safe self-tests (non-destructive, on your own app, against a test account).**
- Register a test user with password `P = "x"*72 + "A"`. Try to log in with `"x"*72 + "B"`. Success means you truncate.
- Repeat with 18 emoji followed by a differing tail, to catch byte/char confusion.
- Grep the codebase for `bcrypt` used anywhere other than password storage, and for hashes or keys built from string concatenation of identifiers plus secrets.
- With pyca/bcrypt ≥5, log in with a 100-byte password. A 500 response means the `ValueError` is not handled.

**(e) Fix — TypeScript/Node (preferred: Argon2id, no 72-byte cap).**
```ts
// npm i argon2@0.45.2  (node-argon2; type argon2id is the default)
import argon2 from "argon2";

const MAX_CODEPOINTS = 256; // DoS bound; NIST asks for >= 64 characters to be allowed
const PARAMS = { type: argon2.argon2id, memoryCost: 19456, timeCost: 2, parallelism: 1 }; // OWASP minimum; library default (64 MiB, t=3, p=4) is also fine

function prep(pw: string): string {
  const n = pw.normalize("NFC");               // NIST 800-63B-4: SHOULD normalize to NFC before hashing
  if ([...n].length > MAX_CODEPOINTS) throw new RangeError("password too long");
  return n;
}
export const hashPassword = (pw: string) => argon2.hash(prep(pw), PARAMS);
export async function verifyPassword(stored: string, pw: string): Promise<boolean> {
  let ok = false;
  try { ok = await argon2.verify(stored, prep(pw)); } catch { ok = false; }
  // optional: if (ok && argon2.needsRehash(stored, PARAMS)) await saveNewHash(...)
  return ok;
}
```
If bcrypt must remain (legacy hashes), pick one of two options. Option A: reject anything over 72 UTF-8 bytes at **registration and password change**, with the check `Buffer.byteLength(pw, "utf8") > 72` or `bcryptjs.truncates(pw)`. Option B: the OWASP peppered pre-hash:
```ts
import bcrypt from "bcryptjs";                 // 3.0.3
import { createHmac } from "node:crypto";
const PEPPER = Buffer.from(process.env.PASSWORD_PEPPER_B64!, "base64"); // 32 random bytes, kept outside the DB
const preHash = (pw: string) =>
  createHmac("sha384", PEPPER).update(pw.normalize("NFC"), "utf8").digest("base64"); // 64 ASCII chars: no NUL, under 72 bytes
export const hashLegacy = (pw: string) => bcrypt.hash(preHash(pw), 12);
export const verifyLegacy = (pw: string, h: string) => bcrypt.compare(preHash(pw), h);
```
Option B changes every hash's input, so version the stored hashes (for example a `hash_scheme` column), verify old-scheme hashes once, and rehash on successful login. Prefer migrating to Argon2id with rehash-on-login.

**Fix for the Okta pattern (derived keys).** Never use a password hash as a key. Key by identity only, and verify the secret against a slow hash stored in the value:
```ts
import { createHmac } from "node:crypto";
const KEY_SECRET = Buffer.from(process.env.CACHE_KEY_SECRET_B64!, "base64");
export function derivedKey(domain: string, ...parts: string[]): string {
  const h = createHmac("sha256", KEY_SECRET).update(domain);
  for (const p of parts) {                     // length-prefix each field: "ab"+"c" != "a"+"bc"
    const b = Buffer.from(p, "utf8"); const len = Buffer.alloc(4); len.writeUInt32BE(b.length);
    h.update(len).update(b);
  }
  return h.digest("hex");
}
// cache.set(derivedKey("delauth-v1", userId, username), { pwHash: await hashPassword(pw), exp })
// on cache hit: return await verifyPassword(entry.pwHash, submittedPw)
```

**Fix — Python.**
```python
# pip install argon2-cffi==25.1.0   (or: pwdlib[argon2], as the FastAPI docs now use)
import unicodedata
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)  # OWASP minimum; defaults (3, 65536, 4) also OK

def _prep(pw: str) -> str:
    n = unicodedata.normalize("NFC", pw)
    if len(n) > 256:
        raise ValueError("password too long")
    return n

def hash_password(pw: str) -> str:
    return ph.hash(_prep(pw))

def verify_password(stored: str, pw: str) -> bool:
    try:
        return ph.verify(stored, _prep(pw))
    except (VerificationError, InvalidHashError):
        return False
# after a successful verify: if ph.check_needs_rehash(stored): store ph.hash(...)
```
Legacy pyca/bcrypt ≥5 with the OWASP pre-hash: `bcrypt.hashpw(base64.b64encode(hmac.new(PEPPER, pw.encode(), hashlib.sha384).digest()), bcrypt.gensalt(12))`. The input is 64 bytes, so it is under the limit and contains no NUL. Do **not** "fix" the `ValueError` by slicing `pw[:72]`, which reintroduces truncation. Remove `passlib` or switch to `pwdlib`/`libpass`; do not pin `bcrypt<5`.

**(f) Incorrect or incomplete fixes.**
- Capping at 72 **characters**: multi-byte characters still overflow 72 bytes.
- Capping only in the front-end: the API is still callable directly.
- Unpeppered `bcrypt(base64(sha256(pw)))`: exposed to shucking (per OWASP), although pyca's README suggests it.
- `bcrypt(sha256(pw).digest())` with raw bytes: the NUL truncation risk applies wherever the implementation treats input as a C string.
- Hex-encoding SHA-512 before bcrypt: 128 chars, which truncates to 72 hex chars (288 bits). That is safe-ish in entropy terms but still shuckable.
- Moving the password first in a concatenated key: it only moves the problem to long passwords.
- "Fixing" the Okta pattern by switching bcrypt to SHA-256: removes truncation but makes the key a fast, offline-crackable password hash.
- Pinning `bcrypt==4.0.1` to quiet passlib: restores silent truncation.

**(g) Verify the fix (fails before, passes after).**
```ts
// vitest
import { test, expect } from "vitest";
import { hashPassword, verifyPassword } from "./password";
test.each([
  ["ascii", "x".repeat(72)],
  ["emoji", "🔒".repeat(18)],                 // 72 UTF-8 bytes
])("bytes after the 72nd are significant (%s)", async (_, prefix) => {
  const h = await hashPassword(prefix + "A");
  expect(await verifyPassword(h, prefix + "A")).toBe(true);
  expect(await verifyPassword(h, prefix + "B")).toBe(false); // passes with bcryptjs/bcrypt only if you pre-hash or reject
});
test("derived keys depend on every field", () => {
  const u = "u".repeat(52);
  expect(derivedKey("t", "00u1234567890abcdefg", u, "pw1")).not.toBe(derivedKey("t", "00u1234567890abcdefg", u, "pw2"));
});
```
Python equivalent: `assert not verify_password(hash_password("x"*72+"A"), "x"*72+"B")`, plus `assert verify_password(h, "y"*100) is False` (no exception) for pyca/bcrypt ≥5 setups.

**Okta arithmetic (inference, uncertain).** Okta user IDs look like 20-character strings beginning with "00u", and 20 + 52 = 72. That would explain the exact threshold, but Okta's advisory does not state it.

### Gaps
- I could not fetch Okta's advisory page directly; all Okta quotes come from search-result summaries that consistently attribute the text to it.
- I did not verify how Supabase Auth, Clerk or Firebase handle passwords longer than 72 bytes. Supabase Auth is Go-based and may use x/crypto/bcrypt, but I did not inspect its password path.
- I did not test `CompareHashAndPassword` in Go with inputs over 72 bytes; I only read that it lacks an explicit check.
- I did not confirm the exact date x/crypto added `ErrPasswordTooLong`.

## Attack 6 — 2FA/OTP code replay and brute force

### Takeaway
A 6-digit code has 10^6 values. A verifier that accepts ±1 time step makes 3 of them valid at once, so every unthrottled guess has a 3-in-a-million chance. Microsoft's "AuthQuake" (reported June 2024, disclosed December 2024) showed what a long acceptance window plus unbounded parallel sessions does: about an hour to bypass MFA. RFC 6238 §5.2, NIST SP 800-63B-4 and OWASP all require a code to be accepted only once. Every popular OTP library (otplib, pyotp, speakeasy) is stateless, so replay protection, attempt budgets per **account** (not per session or IP), binding to the pending login, expiry and single-use for email/SMS codes are the app developer's job. Managed providers cover only parts of this.

### Cited Findings

**(a) Mechanism and requirements**
- NIST SP 800-63B-4 on OTP verifiers: "Verifiers SHALL accept a given OTP only once while it is valid to provide replay resistance". "Time-based OTPs [TOTP] SHALL have a defined lifetime that is determined by the expected clock drift… plus an allowance for network delay and claimant entry". The rate limiter is "SHOULD", or "SHALL" "if the authenticator output is less than 64 bits in length" for single-factor OTP, and "SHALL" for multi-factor OTP — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- NIST SP 800-63B-4 general throttling: "the verifier SHALL limit consecutive failed authentication attempts using a specific authenticator on a single subscriber account to no more than 100 by disabling that authenticator" — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- NIST SP 800-63B-4 on out-of-band codes (email/SMS-style): "the authentication SHALL be considered invalid unless completed within 10 minutes. Verifiers SHALL accept a given authentication secret as valid only once during the validity period"; secrets must be "at least six decimal digits"; and "Generating a new authentication secret SHALL NOT reset the failed authentication count" — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- NIST SP 800-63B-4 on look-up secrets (backup/recovery codes): "A secret from a look-up secret authenticator SHALL be used successfully only once", and look-up secrets "SHALL be at least six decimal digits (or equivalent)" — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- RFC 6238 §5.2 (TOTP), as summarised by OWASP. Accept "the current time step and at most one previous step for network delay". "Reject a code that has already been accepted for that user, even if it is still inside the window… store the last accepted time step per token, reject that step and any earlier one, and update the record atomically so parallel verifier instances can't both accept the same code." OWASP notes this "does not stop a real-time phishing proxy" — [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html); [RFC 6238 §5.2](https://www.rfc-editor.org/rfc/rfc6238.html#section-5.2). From prior knowledge, not re-fetched here: RFC 6238 §5.2 says "The verifier MUST NOT accept the second attempt of the OTP after the successful validation has been issued for the first OTP" and recommends at most one time step of network delay.
- OWASP on server-generated OTPs: generate with a CSPRNG; "Consider 8-digit or longer codes"; "On 'resend', generate a new OTP and overwrite the old record"; hash stored OTPs. Hashing is for log/DB-exposure hygiene, not offline resistance, because a "6-digit code" has "~1 million possibilities". TOTP seeds should be stored encrypted (ideally with an HSM/KMS key), the seed never returned after enrollment, and a new seed enrolled after suspected exposure, because "Changing the password… does not invalidate the old seed" — [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- OWASP on SMS: NIST SP 800-63B-4 designates SMS/PSTN codes as *restricted*. Where SMS is used, "enforce per-account rate limits, monitor for SIM-swap signals" — [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)

**(b) Incidents**
- AuthQuake (Oasis Security). Microsoft's MFA accepted a TOTP code for about 3 minutes rather than roughly 30 seconds plus one step. There was no effective rate limiting, and attackers could open many new sessions in parallel and guess in each. Oasis put the odds at about 3% per extended window and the average time at about one hour. The attack needed the victim's username and password, required no user interaction and generated no alert. Oasis found it on 24 Jun 2024. Reported fix timing differs: one source says a temporary fix on 4 Jul 2024 and a permanent one on 9 Oct 2024, while others say only "October". Coverage cites 400M+ Office 365 seats as the exposed population, which is a ceiling rather than a count of affected accounts. The permanent fix reportedly added stricter rate limits, with details undisclosed — [SecurityWeek](https://www.securityweek.com/microsoft-mfa-bypassed-via-authquake-attack/); [WorkOS summary](https://workos.com/blog/authquake-microsofts-mfa-system-vulnerable-to-totp-brute-force-attack); [SC World](https://www.scworld.com/news/critical-authquake-bug-lets-attackers-bypass-microsoft-mfa); the original Oasis post could not be fetched in this session.
- Library-level developments, 2026:
  - pyotp 2.11.2 (2026-11-14): "Harden OTP verification APIs and document replay prevention".
  - pyotp 2.12.0 (2026-11-15): "Require 112-bit OTP secrets" and "Limit TOTP intervals to 120 seconds" — [pyotp Changes.rst](https://github.com/pyauth/pyotp/blob/HEAD/Changes.rst)
  - otplib 13.x (13.0.0 published 2026-01-10; 13.6.0 published 2026-10-31 per npm) documents `afterTimeStep` replay protection and "guardrails" (MAX_WINDOW 99 checks, MAX_PERIOD 3600 s) — [otplib advanced-usage](https://github.com/yeojz/otplib/blob/HEAD/apps/docs/guide/advanced-usage.md); [otplib danger-zone](https://github.com/yeojz/otplib/blob/HEAD/apps/docs/guide/danger-zone.md)

**(c) Library defaults and what they leave to you**
- otplib: "otplib is a **stateless** library. It does not track which tokens have already been verified." For TOTP: "Without this [stateful tracking], a valid token can be reused multiple times within its validity window." It also says "Do implement rate limiting in your application". Its UNSAFE example is `epochTolerance: 300` and its SAFER example `epochTolerance: 30` — [otplib security guide](https://github.com/yeojz/otplib/blob/HEAD/apps/docs/guide/security.md)
- otplib 13.6.0 TOTP `verify` defaults to `epochTolerance = 0` (source `packages/totp/src/index.ts`). `afterTimeStep` is an "exclusive lower bound… Time steps less than or equal to this value are rejected", and successful verifications return `timeStep` — [otplib advanced-usage](https://github.com/yeojz/otplib/blob/HEAD/apps/docs/guide/advanced-usage.md)
- pyotp: "`TOTP.verify()` and `TOTP.verify_and_get_timecode()` are stateless: they can accept the same OTP repeatedly while it remains valid." The fix is to persist the returned timecode and "Reject a timecode that is less than or equal to the last accepted timecode", with "check and update… atomic". pyotp also warns not to use the raw OTP string or its hash as a replay key: "PyOTP applies Unicode NFKC normalization when comparing OTPs: for example, `123456` and `１２３４５６` are treated as the same code… An attacker could submit another spelling of an already-used code to bypass such a check. Track the accepted counter instead." `valid_window` defaults to 0 — [pyotp README](https://github.com/pyauth/pyotp/blob/HEAD/README.rst); [pyotp totp.py](https://github.com/pyauth/pyotp/blob/HEAD/src/pyotp/totp.py)
- speakeasy (npm): latest 2.0.0, registry last modified 2022-06-26, so it is effectively unmaintained (`npm view speakeasy`, 2026-11-17). I did not inspect its replay behaviour.
- Supabase Auth (Go server, HEAD 387e91f, 2026-11-16), verified in [internal/api/mfa.go](https://github.com/supabase/auth/blob/HEAD/internal/api/mfa.go):
  - TOTP is verified with `totp.ValidateCustom(… Period: 30, Skew: 1 …)`.
  - A challenge is rejected if `challenge.VerifiedAt != nil || challenge.IPAddress != currentIP`, so challenges are single-use and IP-bound.
  - Challenges expire by `ChallengeExpiryDuration`, default 300 s per [internal/conf/configuration.go](https://github.com/supabase/auth/blob/HEAD/internal/conf/configuration.go).
  - The factor-verify route sits behind `limitHandler(api.limiterOpts.FactorVerify)` in [internal/api/api.go](https://github.com/supabase/auth/blob/HEAD/internal/api/api.go).
  - Email/SMS OTP length defaults to 6 (allowed range 6–10), and `MaxFrequency` defaults to 1 minute between sends — [configuration.go](https://github.com/supabase/auth/blob/HEAD/internal/conf/configuration.go)
- Clerk: backup codes are enabled in the Dashboard MFA settings and generated at the end of authenticator-app setup. Regenerating replaces the previous set, and removing the last second factor deletes backup codes and disables MFA. The search found no Clerk documentation of a specific MFA attempt limit — [Clerk MFA recovery docs](https://clerk.com/docs/guides/secure/mfa-recovery.md); [Clerk manage-MFA custom flow](https://clerk.com/docs/guides/development/custom-flows/account-updates/manage-mfa.md)

### Inferences

**Brute-force math (computed; formula P = 1 − (1 − k/10^d)^n).**
- 6 digits, ±1 step (k = 3): per guess 3×10⁻⁶.
- Capped at NIST's 100 consecutive failures, success ≈ 3.0×10⁻⁴; with a 10-failure lockout, ≈ 3.0×10⁻⁵.
- With no cap, about 231,000 guesses give a 50% chance: ≈ 38 minutes at 100 req/s, which matches the shape of AuthQuake.
- Email OTP with a 5-attempt cap per code (k = 1): 5×10⁻⁶ per issued code. If resends reset the counter, 10,000 resends (50,000 guesses) reach ≈ 4.9%. NIST therefore forbids resetting the failure count on a new secret.
- 8 digits with 100 attempts: ≈ 1×10⁻⁶.
- The budget must be **per account and factor, across sessions, IPs and code reissues**. Per-session or per-IP budgets are what AuthQuake defeated with parallel sessions.

**Vibe-coded failure patterns (c).** These come from the failure modes the cited sources warn against. I did not run an empirical survey of assistant output.
- `authenticator.verify({ token, secret })` (otplib) or `totp.verify(code, valid_window=…)` (pyotp) called with no persisted time step, so replay works.
- Widening the window for "clock skew" UX: `epochTolerance: 300`, `valid_window=10`, `window: 20` in speakeasy.
- In-memory `Map` attempt counters. They reset on deploy and are not shared across serverless instances, so the effective limit is unbounded.
- A rate limit on `/login` but not on `/verify-otp`.
- Email/SMS codes from `Math.random()`.
- A code stored in plaintext with no expiry and not deleted after use.
- Code compared with `===`. Timing leaks are minor next to the other problems.
- An OTP verify endpoint that takes `{ email, code }` instead of a server-held pending-login id, so a code issued to one account can complete another account's login, or the step can be skipped by calling the post-MFA endpoint directly.
- The OTP echoed in the JSON response "for debugging", or in logs or analytics events. OWASP's hashing rationale cites "accidental disclosure via logs, metrics, or debugging tools".
- Backup codes stored in plaintext and never invalidated after use.
- "MFA enabled" in Supabase but never enforced. Supabase marks MFA-completed sessions as `aal2` in the JWT, and the app must check `aal2` in RLS policies or server routes. This comes from prior knowledge of Supabase's MFA docs and was not re-fetched here; the enforcement point is app-owned either way.

**Managed provider vs. app owner.** Supabase covers single-use, IP-bound, 5-minute challenges, a 30 s/±1 TOTP window and a rate limiter on factor verify (verified in code). I found no persisted "last accepted time step" check in `mfa.go`, so a code might be reusable on a *new* challenge within its ~90 s window. That is an inference from reading one file, so confirm before stating it publicly. The app owns AAL enforcement on data and routes, any custom OTP flows (for example email codes for "sensitive action" re-auth), backup-code UX if self-built, and not leaking codes. With Clerk and Firebase the provider owns the verifier; the app owns step-up enforcement and anything self-built. For otplib, pyotp and speakeasy, the app owns everything stateful.

**(d) Safe self-tests on your own app (test account, your own environment).**
1. Replay: log in, submit a valid TOTP, log out. Within the same 30 s step, log in again and submit the same code. It must fail.
2. Concurrency: send the same valid code in two simultaneous requests. Exactly one may succeed.
3. Budget: send wrong codes. After N (≤100, and lower is better) failures the factor or account must lock, across new sessions and different IPs. Confirm with two browsers, not just one session.
4. Binding: start logins for test accounts A and B, then submit A's valid code to B's pending login. It must fail.
5. Leakage: inspect the network responses of "send code" and "verify". The code must not appear, and it must not appear in server logs.
6. Email OTP: confirm expiry (≤10 min), single use, that a resend invalidates the old code, and that the failure count does not reset on resend.
7. Backup codes: each code works once, and backup-code failures count toward the same budget.
Do not run high-volume guessing against production. Test the counter logic, not the keyspace.

**(e) Fix — TypeScript (otplib 13.6.0 + Postgres).**
```ts
import { verify } from "otplib";             // 13.6.0; stateless, so the state lives in your DB
import { randomInt, createHmac, timingSafeEqual } from "node:crypto";
const MAX_FAILS = 10;                          // per user+factor, across sessions/IPs; NIST ceiling is 100

// Tables: totp_factor(user_id PK, secret_enc, last_time_step BIGINT NULL, failures INT DEFAULT 0, locked_until TIMESTAMPTZ)
//         pending_login(id UUID PK, user_id, expires_at, completed_at NULL)  -- created after password check
export async function verifyTotp(db: Db, pendingLoginId: string, token: string): Promise<boolean> {
  return db.tx(async (tx) => {
    const pl = await tx.oneOrNone(
      "SELECT user_id FROM pending_login WHERE id=$1 AND completed_at IS NULL AND expires_at > now() FOR UPDATE", [pendingLoginId]);
    if (!pl) return false;                                      // OTP bound to THIS pending login (and thus user)
    const f = await tx.one(
      "SELECT secret_enc, last_time_step, failures, locked_until FROM totp_factor WHERE user_id=$1 FOR UPDATE", [pl.user_id]);
    if (f.locked_until && f.locked_until > new Date()) return false;
    const r = await verify({
      secret: decrypt(f.secret_enc), token,
      epochTolerance: 30,                                       // ±1 step (RFC 6238 §5.2 / OWASP)
      afterTimeStep: f.last_time_step ?? undefined,             // replay: reject step <= last accepted
    });
    if (!r.valid) {
      await tx.none(`UPDATE totp_factor SET failures = failures + 1,
                       locked_until = CASE WHEN failures + 1 >= $2 THEN now() + interval '15 minutes' END
                     WHERE user_id=$1`, [pl.user_id, MAX_FAILS]);
      return false;
    }
    const upd = await tx.result(                                // atomic compare-and-set (row is also locked)
      "UPDATE totp_factor SET last_time_step=$2, failures=0 WHERE user_id=$1 AND (last_time_step IS NULL OR last_time_step < $2)",
      [pl.user_id, r.timeStep]);
    if (upd.rowCount !== 1) return false;
    await tx.none("UPDATE pending_login SET completed_at=now() WHERE id=$1", [pendingLoginId]);
    return true;                                                // only now issue the full session
  });
}

// Server-generated email/SMS code: CSPRNG, keyed hash at rest, 10-min expiry, single use, never returned in the response
const OTP_KEY = Buffer.from(process.env.OTP_HMAC_KEY_B64!, "base64");
export const newEmailCode = () => randomInt(0, 1_000_000).toString().padStart(6, "0");   // consider 8 digits
export const codeMac = (pendingId: string, code: string) =>
  createHmac("sha256", OTP_KEY).update(`${pendingId}:${code}`).digest();                  // bind code to the pending login
export const macEqual = (a: Buffer, b: Buffer) => a.length === b.length && timingSafeEqual(a, b);
// Verify inside a txn: row FOR UPDATE; reject if consumed_at/expired; count failures on the USER (not on the code row),
// so a resend does not reset them (NIST); on success set consumed_at in the same txn.
```
Backup codes: generate about 10 high-entropy codes (for example 10 base32 characters, roughly 50 bits each) and store only their hashes. Consume one with `DELETE … WHERE user_id=$1 AND code_hash=$2 RETURNING 1`, which is atomic and single-use. Count failures against the same per-user budget.

**Fix — Python (pyotp 2.12.0).** Use pyotp's documented pattern verbatim:
```python
import pyotp
def verify_totp_once(db, credential_id, totp, otp):
    try:
        matched_timecode = totp.verify_and_get_timecode(otp, valid_window=1)  # ±1 step
    except pyotp.OTPVerificationError:
        return False  # also increment a per-credential failure counter here, with lockout
    with db:
        updated = db.execute(
            "UPDATE totp_credentials SET last_timecode = ? "
            "WHERE id = ? AND (last_timecode IS NULL OR last_timecode < ?)",
            (matched_timecode, credential_id, matched_timecode),
        )
    return updated.rowcount == 1
```
(Pattern from the [pyotp README](https://github.com/pyauth/pyotp/blob/HEAD/README.rst); `valid_window=1` and the failure-counter comment are my additions.) For email codes in Python, use `secrets.randbelow(10**6)`, `hmac.new(key, f"{pending_id}:{code}".encode(), hashlib.sha256).digest()` and `hmac.compare_digest`, with the same transaction rules as the TypeScript version.

**(f) Incorrect or incomplete fixes.**
- Storing "used codes" as raw strings or hashes: bypassed by full-width digit spellings under NFKC-normalizing verifiers (pyotp's warning), and it grows without bound.
- Read-then-write without an atomic condition: two parallel requests both pass.
- Per-IP or per-session rate limits only: AuthQuake used parallel sessions.
- Resetting the failure counter on resend: NIST forbids this, and resends become a fresh-guess faucet.
- An in-process counter: lost on restart and not shared across instances.
- Lockout without notifying the user or offering a recovery path: becomes an account-lockout DoS. Prefer backoff plus notification, and lock the *factor*, not the whole account.
- Lengthening the TOTP window to fix clock drift: per OWASP, record per-token drift instead.
- Replay tracking that does not survive a challenge change, as in my Supabase inference above.
- Checking the OTP on the client: there is nothing to verify server-side.
- Returning `{"sent": true, "code": "123456"}`: it leaks the code.

**(g) Verify the fix.**
```ts
// vitest — freeze time so both submissions fall in the same 30 s step
test("TOTP code cannot be replayed", async () => {
  vi.setSystemTime(new Date("2026-11-17T12:00:05Z"));
  const code = await generate({ secret });                     // otplib
  expect(await verifyTotp(db, await newPendingLogin(user), code)).toBe(true);
  expect(await verifyTotp(db, await newPendingLogin(user), code)).toBe(false); // fails before the fix
});
test("concurrent submissions: exactly one wins", async () => {
  const code = await generate({ secret });
  const [a, b] = await Promise.all([verifyTotp(db, p1, code), verifyTotp(db, p2, code)]);
  expect([a, b].filter(Boolean)).toHaveLength(1);
});
test("failure budget is per user, not per session", async () => {
  for (let i = 0; i < MAX_FAILS; i++) await verifyTotp(db, await newPendingLogin(user), "000000");
  expect(await verifyTotp(db, await newPendingLogin(user), await generate({ secret }))).toBe(false); // locked
});
test("code for user A does not complete user B's login", async () => { /* ... */ });
test("send-code response never contains the code", async () => { /* assert body/log lines exclude it */ });
```
Python: the same tests with `totp.at(fixed_ts)` / `for_time` and `freezegun`.

### Gaps
- I could not fetch the original Oasis Security write-up. The 3% per window, ~1 hour and timeline figures come from secondary coverage, which disagrees on the fix dates.
- RFC 6238 and RFC 4226 text could not be fetched directly; I relied on OWASP's citations plus prior knowledge. RFC 4226 §7.3 throttling and the look-ahead window are from prior knowledge.
- Firebase Auth / Identity Platform TOTP replay and attempt-limit behaviour: no reliable source found.
- Clerk's MFA attempt limits: not documented in the sources found.
- I found no verified 2025–2026 production incident of this class (OTP replay or brute force) comparable to AuthQuake.
- I did not find a citable public CVE for "OTP returned in API response". The pattern is widely reported in bug-bounty write-ups, but none was verified here.
- Supabase's exact default for the `FactorVerify` limiter and its units were not extracted. `RateLimitVerify` defaults to 30, units unverified.

## Attack 20 — Unicode username canonicalization account takeover ("Unicode = Spotify")

### Takeaway
Spotify (June 2013) derived a "canonical username" with XMPP nodeprep (via Twisted). The function was not idempotent: `ᴮᴵᴳᴮᴵᴿᴰ` canonicalized to `BIGBIRD` on the first pass and to `bigbird` on the second. An attacker could register the look-alike, request a password reset, and end up resetting the victim `bigbird`'s password. The same class recurred in GitHub's 2019 dotless-ı reset bug, in Django CVE-2019-19844, and in 2026 in next-auth/Auth.js's email normalizer (validate-before-canonicalize with a full-width `＠`). The defence:
- canonicalize once, with an idempotent function (NFKC + case fold, then an allowlist);
- store the canonical form in its own column with a UNIQUE index;
- compare only canonical forms;
- send reset mail only to the stored address;
- keep database collation semantics consistent with the app's.

### Cited Findings

**(a)/(b) Spotify, 2013 (historical)**
- Spotify's engineering post "Creative usernames and Spotify account hijacking" (June 2013) describes this sequence:
  - registering the username `ᴮᴵᴳᴮᴵᴿᴰ` (Unicode modifier capital letters);
  - requesting a password reset, which is mailed to the attacker's own email;
  - the reset logging the attacker in as `bigbird`.
  The cause was that Spotify used XMPP nodeprep to compute a canonical username and relied on it being idempotent, which it was not. Spotify temporarily disabled account creation. The chosen fix was to reject usernames for which canonicalization is not idempotent, rather than change the canonicalization function, because canonical usernames were stored in many databases — [Spotify Engineering (via search summary)](https://engineering.atspotify.com/2013/06/creative-usernames); [Hacker News discussion](https://news.ycombinator.com/item?id=5902286); [Jeff Kaufman, "Is Unicode safe?"](https://jefftkaufman.substack.com/p/is-unicode-safe)
- The StringPrep framework under nodeprep is pinned to Unicode 3.2 — [search summary of HN commentary](https://news.ycombinator.com/item?id=5902286). Local reproduction (Python 3, stdlib `stringprep`): U+1D2E etc. are *unassigned* in Unicode 3.2 (`in_table_a1` returns True). Applying the 3.2 B.2 case map (which leaves them unchanged) and then **current-version** NFKC yields `BIGBIRD`; a second pass yields `bigbird`. Using `unicodedata.ucd_3_2_0` NFKC leaves the string unchanged.
- Current Twisted `xmpp_stringprep.py` imports `ucd_3_2_0 as unicodedata`, normalizes with it, and has `check_unassigneds=True`, raising `UnicodeError("Unassigned code point …")`. That combination rejects Spotify's input — [twisted xmpp_stringprep.py](https://github.com/twisted/twisted/blob/trunk/src/twisted/words/protocols/jabber/xmpp_stringprep.py). The exact Twisted version and diff in use at Spotify in 2013 were not verified.

**(b) GitHub, 2019 (historical)**
- John Gracey's write-up, "Hacking GitHub's Auth with Unicode's Turkish Dotless 'I'" (late Nov/Dec 2019): GitHub's forgot-password flow compared a case-transformed submitted email with stored addresses, and **mailed the reset link to the address the attacker supplied**. An address containing `ı` (U+0131, which uppercases to ASCII `I`) could therefore match a victim's address. The post also lists `ß` → "ss". GitHub fixed it by making sure the address in the database matches the address that initiated the reset. Commenters noted that exploitation needs a mail provider that accepts the Unicode local part — [dev.to/jagracey](https://dev.to/jagracey/hacking-github-s-auth-with-unicode-s-turkish-dotless-i-460n); [CNCF TAG-Security catalog entry](https://tag-security.cncf.io/community/catalog/compromises/2016/gh-unicode/) (its 2016 date conflicts with the 2019 publication). I found no GitHub-authored disclosure.

**(b) Django CVE-2019-19844 (historical, fixed 18 Dec 2019)**
- Django's password-reset form matched emails case-insensitively in the DB. An attacker who knows the victim's address could craft one that becomes equal under Unicode case transformation and receive the reset token. Simon Charette found it after reading the GitHub disclosure. Affected versions were before 1.11.27, 2.x before 2.2.9 and 3.x before 3.0.1. The fix re-checks matches in Python using the Unicode TR36 identifier comparison and **sends the email to the stored address** rather than the submitted one — [Django security releases 2019-12-18](https://www.djangoproject.com/weblog/2019/dec/18/security-releases/); [Django 1.11.27 release notes](https://docs.djangoproject.com/en/6.0/releases/1.11.27/); [oss-sec](https://seclists.org/oss-sec/2019/q4/163)
- Django's current `PasswordResetForm.get_users` (main, 2026-11-17) filters `email__iexact` and then keeps only users where `_unicode_ci_compare(email, stored)`, defined as `unicodedata.normalize("NFKC", s1).casefold() == unicodedata.normalize("NFKC", s2).casefold()`, citing "Unicode Technical Report 36, section 2.11.2(B)(2)" — [django/contrib/auth/forms.py](https://github.com/django/django/blob/main/django/contrib/auth/forms.py)
- Adjacent, not Unicode: Django CVE-2024-45231 (3 Sep 2024), "Potential user email enumeration via response status on password reset" — [Django security archive](https://docs.djangoproject.com/en/dev/releases/security/); [weblog](https://www.djangoproject.com/weblog/2024/sep/03/security-releases/)

**(b) 2024–2026: Auth.js / next-auth email normalizer (GHSA-7rqj-j65f-68wh)**
- GitHub advisory "Email normalizer validates the address before Unicode normalization, allowing a homoglyph @ bypass" — [next-auth advisory GHSA-7rqj-j65f-68wh](https://github.com/nextauthjs/next-auth/security/advisories/GHSA-7rqj-j65f-68wh)
- The v4 fix commit (merged 2026-06-11, 19d2feb) says: "The inline email normalizer validated the address on the ASCII `@` before any Unicode normalization. A character that is a homoglyph of `@` — e.g. U+FF20 FULLWIDTH COMMERCIAL AT — passed the single-`@` (atCount) check, but can be canonicalized to an ASCII `@` by a downstream address parser (NFKC), splitting the address into multiple recipients (CWE-180: validate before canonicalize)." The change is `identifier.trim()` → `identifier.normalize("NFKC").trim()` in `packages/next-auth/src/core/routes/signin.ts` — [nextauthjs/next-auth commit 19d2feb](https://github.com/nextauthjs/next-auth/commit/19d2feb)
- Versions from the npm registry: next-auth 4.24.14 was published 2026-04-14, before the fix merge, and 4.24.15 on 2026-07-20, the release commit after the merge. `@auth/core` 0.41.3 was published 2026-07-20. A search summary says the advisory lists 4.24.14 / 0.41.3 as fixed, but the git history places the v4 fix in **4.24.15**. Treat ≥4.24.15 and `@auth/core` ≥0.41.3 as the safe floor — [npm next-auth](https://www.npmjs.com/package/next-auth); [SecureLayer7 write-up](https://securelayer7.net/lab/authjs-email-homoglyph-unicode-at-bypass-account-takeover)
- A third-party blog labels this "CVE-2026-73420". I did not find that ID in the advisory or commit, so it is unverified — [orbisappsec blog](https://orbisappsec.com/blog/how-unicode-homoglyph-email-bypass-happens-in-next-js-auth-js)
- Other 2025–2026 reports of the class are application-level, not CVEs. One is a login lookup that lowercases and then queries an accent- and case-insensitive collation ("folds diacritics"), enabling takeover — [tomyka/el2025 issue #41](https://github.com/tomyka/el2025/issues/41). Another is an "accent-insensitive collation" email collision where the reset goes to the submitted address — [Securifyai write-up](https://securifyai.co/learnings/zero-click-account-takeover-via-unicode-email-collision/). Both are low-authority sources.

**(a) Unicode mechanics (verified locally with Python 3 / Node 22)**
- NFKC maps `ᴮᴵᴳᴮᴵᴿᴰ` → `BIGBIRD`, `＠` (U+FF20) → `@` and `ﬁ` → `fi`. `.lower()`/`.casefold()` leave `ᴮᴵᴳᴮᴵᴿᴰ` unchanged, so case mapping without NFKC misses it.
- `ß`: lower → `ß`, upper → `SS`, casefold → `ss`. JS has no casefold, and `'ß'.toUpperCase()` is `SS`.
- `ı` (U+0131): upper → `I`, casefold → `ı`, so it is not equal to `i` under casefold.
- `İ` (U+0130): lower → `i̇`, which is 2 code points (i + U+0307).
- Kelvin sign U+212A: lower → `k`, NFKC → `K`.
- So `upper()`-based comparison (GitHub's case) collides `ı` with `i`, and `lower()` vs `casefold()` disagree on `ß`. Any pair of *different* functions used at write time and at lookup time is a collision source (local run, 2026-11-17).
- NIST SP 800-63B-4 recommends NFC for *passwords*. That is a different goal from identifier comparison, where NFKC + casefold, per Django/TR36, is the comparison form — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html); [Django forms.py](https://github.com/django/django/blob/main/django/contrib/auth/forms.py)
- OWASP Forgot Password Cheat Sheet: reset tokens should be "Stored securely" and be "Single use and expire after an appropriate period" — [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

### Inferences

**PRECIS / UTS #39 / collation.** From prior knowledge; RFC and Unicode pages could not be fetched here, so verify the wording before quoting.
- RFC 8264 (PRECIS framework, 2017) replaced stringprep's Unicode-3.2 pinning with version-agile derived properties. As I recall, it tells implementations to re-apply rules until the output is stable and reject otherwise, which is a direct answer to the Spotify bug.
- RFC 8265 `UsernameCaseMapped`: width mapping (full-width/half-width → decomposition), case mapping with Unicode `toLowerCase`, NFC normalization, the bidi rule, and IdentifierClass, which disallows symbols and spaces.
- Implementations exist as Go `golang.org/x/text/secure/precis` (`precis.UsernameCaseMapped`) and Python `precis-i18n` (`precis_i18n.get_profile("UsernameCaseMapped").enforce(s)`, API unverified).
- UTS #39 defines `skeleton()` for confusable detection (for example Cyrillic `а` vs Latin `a`). NFKC does *not* merge cross-script confusables, so use skeletons to *block registration* of look-alikes of existing names, never as the identity key.
- MySQL 8's default `utf8mb4_0900_ai_ci` is accent- and case-insensitive. Postgres `citext` uses `lower()`. Postgres ICU nondeterministic collations (`deterministic = false`, e.g. `und-u-ks-level2`) can make unique indexes treat case variants as equal. All of these are a *second* canonicalizer that can disagree with application code, which is the tomyka issue pattern. Prefer an explicit `*_canonical` column under a plain deterministic UNIQUE index.

**Why vibe-coded apps are prone (c).**
- Generated code typically does `email.toLowerCase()` (or nothing) at signup, `.toLowerCase().trim()` at login, and an ORM `findFirst({ where: { email: { equals: input, mode: "insensitive" } } })` (Prisma on Postgres uses ILIKE/`lower`) at reset time. Those are three different canonicalizers.
- It typically mails the reset to `req.body.email` rather than `user.email`.
- Usernames are accepted as free Unicode and used directly in URLs and lookups.
- AI-generated MySQL schemas inherit `_ai_ci` collations.
- Managed auth (Supabase, Clerk, Firebase, Auth.js) owns the email identity and the reset-mail destination for *its* flows, and Auth.js's own normalizer needed the 2026 fix. App developers still own:
  - usernames, handles and slugs stored in their own tables;
  - any custom "invite", "magic link" or "transfer ownership" flow that matches by email;
  - DB collations;
  - mapping from provider user IDs to app rows. Key on the provider's immutable user ID, never on email.

**(d) Safe self-tests (own app, test accounts).**
1. Create a test user `bigbird`, then try to register `ᴮᴵᴳᴮᴵᴿᴰ`, `ＢＩＧＢＩＲＤ` (full-width), `BigBird` and `bıgbird`. All must be rejected as taken or invalid, and none may create a second account that later resolves to the first.
2. Request a password reset for `victim@yourtestdomain` spelled with `ı`, `ß`/`ss`, full-width letters, a trailing space, or `＠`. The response must not send mail to the submitted spelling. Inspect your mail sink: the only recipient may be the stored address, or nobody.
3. Run `SELECT username_canonical, count(*) … GROUP BY 1 HAVING count(*) > 1` after backfilling the canonical function over existing rows to find existing collisions.
4. Property-test idempotence over all code points.

**(e) Fix — TypeScript.**
```ts
// Identity = canonical form, computed ONCE, stored in its own UNIQUE column, never recomputed with a different function.
const USERNAME_RE = /^[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?$/;   // ASCII allowlist after canonicalization

export function canonicalUsername(raw: string): string {
  const c = raw.normalize("NFKC").toLowerCase().normalize("NFKC"); // ᴮᴵᴳᴮᴵᴿᴰ -> bigbird, ＢＩＧ -> big, K(U+212A) -> k
  if (!USERNAME_RE.test(c)) throw new Error("invalid username");    // rejects ı, ß, İ, cross-script letters, etc.
  if (c.normalize("NFKC").toLowerCase().normalize("NFKC") !== c)    // Spotify's fix: refuse non-idempotent inputs
    throw new Error("invalid username");
  return c;
}
// Display name may stay free Unicode, but is never used for identity, lookup, URLs or mail routing.

export function canonicalEmail(raw: string): string {
  const s = raw.normalize("NFKC").trim();                           // canonicalize BEFORE validating (CWE-180; next-auth fix)
  const at = s.lastIndexOf("@");
  if (at < 1 || s.indexOf("@") !== at) throw new Error("invalid email");
  const local = s.slice(0, at);
  const domain = domainToASCII(s.slice(at + 1));                   // import { domainToASCII } from "node:url"; IDNA -> punycode, lowercased; "" if invalid
  if (!domain || !/^[a-z0-9.-]+$/.test(domain)) throw new Error("invalid email");
  if (!/^[\x21-\x7e]+$/.test(local)) throw new Error("unsupported email"); // most apps: reject non-ASCII local parts
  return `${local.toLowerCase()}@${domain}`;                        // lowercasing the local part is a policy choice; apply it everywhere
}

// Password reset: look up by canonical, send ONLY to the stored address.
export async function requestReset(db: Db, mailer: Mailer, submitted: string) {
  let key: string; try { key = canonicalEmail(submitted); } catch { return; }   // same response either way (no enumeration)
  const user = await db.oneOrNone("SELECT id, email FROM users WHERE email_canonical = $1", [key]);
  if (user) await mailer.sendReset(user.email /* stored */, await issueSingleUseToken(user.id));
}
```
```sql
ALTER TABLE users ADD COLUMN username_canonical text NOT NULL, ADD COLUMN email_canonical text NOT NULL;
CREATE UNIQUE INDEX users_username_canonical_uq ON users (username_canonical);   -- deterministic collation
CREATE UNIQUE INDEX users_email_canonical_uq    ON users (email_canonical);
```

**Fix — Python.**
```python
import re, unicodedata
USERNAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?")

def _canon(s: str) -> str:
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", s).casefold())  # TR36-style, as in Django

def canonical_username(raw: str) -> str:
    c = _canon(raw)
    if not USERNAME_RE.fullmatch(c) or _canon(c) != c:
        raise ValueError("invalid username")
    return c
# Reset: user = User.objects.filter(email_canonical=canonical_email(submitted)).first(); send to user.email.
# Django users: keep Django >= 3.0.1 / 2.2.9 / 1.11.27 behaviour; do not override PasswordResetForm.get_users() to match differently.
```
Defense in depth:
- Block registration of a name whose UTS #39 skeleton equals an existing name's skeleton (via ICU SpoofChecker or a confusables table).
- Key OAuth/IdP-linked accounts on the provider's immutable `sub`/user ID, not email.
- Require re-verification when the canonical email changes.
- Audit-log resets with both the submitted and the stored address.

**(f) Incorrect or incomplete fixes.**
- `toLowerCase()` alone misses NFKC look-alikes (`ᴮᴵᴳ`, full-width letters) and `ß`.
- `toUpperCase()` merges `ı` with `I`, which is GitHub's case.
- `toLocaleLowerCase()` or locale-sensitive case mapping varies by server locale (Turkish).
- NFC instead of NFKC for identifiers misses compatibility forms.
- Canonicalizing at signup but comparing raw at reset, or the reverse, misses collisions.
- Relying on DB collation and app code at the same time, when they differ.
- Validating and then normalizing (next-auth bug, CWE-180).
- Mailing the reset to the submitted address (GitHub/Django).
- Applying NFKC once without an idempotence check, especially with a different Unicode version in another service (Spotify).
- Using the UTS #39 skeleton *as* the stored key: it is lossy and version-dependent. Use it only to deny look-alike registrations.
- Retroactively changing the canonical function without backfilling and checking for collisions.

**(g) Verify the fix.**
```ts
test("look-alikes canonicalize to the same key", () => {
  for (const v of ["ᴮᴵᴳᴮᴵᴿᴰ", "ＢＩＧＢＩＲＤ", "BigBird", "bigbird"]) expect(canonicalUsername(v)).toBe("bigbird");
});
test("non-ASCII residue is rejected", () => {
  for (const v of ["bıgbird", "straße", "bİgbird"]) expect(() => canonicalUsername(v)).toThrow();
});
test("idempotent over the BMP", () => {
  for (let cp = 0; cp <= 0xffff; cp++) {
    let c: string; try { c = canonicalUsername("ab" + String.fromCodePoint(cp) + "cd"); } catch { continue; }
    expect(canonicalUsername(c)).toBe(c);
  }
});
test("reset mail goes only to the stored address", async () => {
  await createUser({ email: "mike@example.test" });
  await requestReset(db, mailer, "mıke@example.test");            // fails before the fix if the submitted address is mailed
  expect(mailer.sent.map(m => m.to)).toEqual(expect.not.arrayContaining(["mıke@example.test"]));
});
test("second registration of a look-alike violates the unique index", async () => {
  await register("bigbird"); await expect(register("ᴮᴵᴳᴮᴵᴿᴰ")).rejects.toThrow(/taken/);
});
```
In Python, use `hypothesis` `st.text()` for the idempotence property and Django's `mail.outbox` for the reset assertion.

### Gaps
- I could not fetch Spotify's 2013 post itself. Its details (the `ᴮᴵᴳᴮᴵᴿᴰ` example, nodeprep, the idempotence check as the fix, disabled sign-ups) come from search summaries that consistently cite it, and the mechanism was reproduced locally. The exact Twisted/Python versions involved in 2013 are unverified.
- RFC 8264/8265 and UTS #39/UAX #15 text could not be fetched; the PRECIS details above are from prior knowledge.
- I found no GitHub-authored advisory for the 2019 dotless-ı issue, and could not pin the exact disclosure date (late Nov–Dec 2019 per secondary sources).
- The patched-version wording of GHSA-7rqj-j65f-68wh could not be read directly, so git history and the search summary conflict (4.24.14 vs 4.24.15). The "CVE-2026-73420" ID is unverified.
- I did not verify whether Supabase Auth, Clerk or Firebase normalize email Unicode before uniqueness and reset routing.
- I did not verify Postgres ICU nondeterministic-collation equivalences (for example whether `ß` = `ss` at level 2) in this session.
