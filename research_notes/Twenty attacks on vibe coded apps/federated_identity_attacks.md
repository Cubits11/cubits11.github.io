# Federated identity attacks on vibe-coded apps: (3) SAML authentication bypass and (4) nOAuth email-claim account takeover

## S1. SAML authentication bypass: what is the mechanism, what does an attacker need, and what is the impact?

### Takeaway
All the major SAML bypass classes share one root cause. The bytes the service provider (SP) verified cryptographically are not the bytes it later reads identity from. Wrapping, comment truncation, parser differentials, canonicalization bugs, embedded-key trust, and skipped verification are different ways of opening that gap. In most library CVEs from 2024–2026, the attacker needs only one validly signed document from the IdP, for example their own login. The result is a login as any user, including admins.

### Cited Findings
**XML Signature Wrapping (XSW): the canonical class**
- XSW against SAML was described in 2012 in "On Breaking SAML: Be Whoever You Want to Be." OWASP's countermeasures come from a follow-up paper: always schema-validate against local, hardened schemas; ignore `KeyInfo` and use a statically configured key; "Never use `getElementsByTagName` to select security related elements"; "Always use absolute XPath expressions to select elements, unless a hardened schema is used." — [OWASP SAML Security Cheat Sheet (source)](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/SAML_Security_Cheat_Sheet.md)
- OWASP's SP requirement: verify that the signature's `<ds:Reference URI>` resolves to the signed Assertion or Response, "and that the exact assertion used for authentication is protected by that validated signature… Reject assertions outside the validated signed content." — [OWASP SAML Security Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/SAML_Security_Cheat_Sheet.md)
- node-saml's README (current master, v5.2.0, Oct 2026) states the core rule: "**Only signed bytes are trusted.** Verification returns the content the signature actually covers, and that is the content the library goes on to process. The original document is never re-read after verification, because an attacker controls the difference between the two — that is the whole of an XML signature wrapping attack." — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- node-saml rejects ambiguity rather than resolving it. It refuses a response with more than one assertion, more than one `Issuer`, more than one signature on an element, an `ID` that resolves to more than one element, a reference pointing anywhere other than its own parent, or more than two transforms. "The library does not pick a reading, and it does not pick the reading that happens to verify." — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- xml-crypto's README marks the dangerous pattern explicitly: "DO NOT attempt to parse whatever data object you have here in `doc` and then use it to verify the signature… BAD: parseAssertion(doc)". After `checkSignature`, use `sig.getSignedReferences()` and parse only that ("Be sure to only use authenticated data"). — [xml-crypto README](https://github.com/node-saml/xml-crypto/blob/master/README.md)

**Comment injection / text-node truncation (2018 class, historical)**
- Duo Labs disclosed on 2018-02-27, with CERT/CC VU#475445. Some SAML libraries read only part of a node's inner text: text after an XML comment was dropped. Canonicalization ignores comments, so the signature still validates. A NameID such as `user@victim.com<!---->.evil.com` could therefore be read as `user@victim.com`. — [Duo PSA-2017-003](https://duo.com/labs/psa/duo-psa-2017-003), [CERT/CC VU#475445](https://kb.cert.org/vuls/id/475445)
- Current xml-crypto (6.x) documents the underlying fact: for a `Reference` whose URI is empty or `#id`, "Comments in that content are not signed, even with a `#WithComments` transform: adding, removing or changing one does not invalidate the signature. Read signed content from `getSignedReferences()`, which does not contain them." — [xml-crypto README](https://github.com/node-saml/xml-crypto/blob/master/README.md)

**Parser differentials (2025 class)**
- ruby-saml CVE-2025-25291 ("DOCTYPE handling") and CVE-2025-25292 ("namespace handling"): "ReXML and Nokogiri parse XML differently, the parsers can generate entirely different document structures from the same XML input. That allows an attacker to be able to execute a Signature Wrapping attack." — [GitLab advisory record CVE-2025-25291](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-25291.yml), [CVE-2025-25292](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-25292.yml)
- Secondary reporting describes the mechanism as "a disconnect between verification of the hash and verification of the signature": one parser's view is digest-checked and the other parser's view is signature-checked or consumed. An attacker holding any valid signed document can log in as another user. — [The Hacker News](https://thehackernews.com/2025/03/github-uncovers-new-ruby-saml.html); primary write-up: [GitHub Security Lab, "Sign in as anyone"](https://github.blog/security/sign-in-as-anyone-bypassing-saml-sso-authentication-with-parser-differentials/) (not retrievable from this session)
- node-saml CVE-2025-54419 combines an xml-crypto C14N deviation for processing instructions with a parser differential. The securing.pl example: xml-crypto "will compute the same digest for `SecuRing` and `<?x Secu?>Ring`." — [securing.pl](https://www.securing.pl/en/cve-2025-54419-how-two-bugs-combine-to-break-saml-authentication-in-node-saml-5-0-1/) (via search excerpt)

**Canonicalization / libxml2 (late-2025 class)**
- ruby-saml CVE-2025-66568: "an issue at libxml2 canonicalization process used by Nokogiri for document transformation" enables signature wrapping. — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-66568.yml)

**Trusting the attacker's key**
- xml-crypto CVE-2024-32962 (4.0.0 to <6.0.0): the default configuration "does not check authorization of the signer, it only checks the validity of the signature… allows a malicious actor to re-sign an XML document, place the certificate in a `<KeyInfo />` element, and pass `xml-crypto` default validation checks." Fixed in 6.0.0, where `getCertFromKeyInfo` defaults to a no-op. — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2024-32962.yml), [xml-crypto CHANGELOG 6.0.0](https://github.com/node-saml/xml-crypto/blob/master/CHANGELOG.md)

**Verification never called (integration failure)**
- GPUStack CVE-2026-102894 (published 2026-11-10): the SAML callback "Base64-decodes the posted XML, reads NameID and attributes, resolves or provisions the user, and mints a gpustack_session JWT — but never calls `OneLogin_Saml2_Auth.process_response()`, the step that verifies the signature, issuer, audience, destination, and time conditions." No credentials are required, and it affects deployments without SAML configured. Affected >=0.7.1,<2.2.2; fixed in 2.2.2. — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/pypi/gpustack/CVE-2026-102894.yml) (GHSA-62m9-f875-rqw6)

**Preconditions and impact (from advisories)**
- ruby-saml CVE-2024-45409: "An unauthenticated attacker with access to any signed saml document (by the IdP) can thus forge a SAML Response/Assertion with arbitrary contents… log in as arbitrary user." — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2024-45409.yml)
- samlify CVE-2025-47949: forge a SAML Response "to authenticate as any user. An attacker would need a signed XML document by the identity provider." — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/samlify/CVE-2025-47949.yml)
- node-saml CVE-2025-54369: "loads the assertion from the (unsigned) original response document… in one attack it is possible to remove any character from the SAML assertion username… attacker would need a validly signed document from the identity provider." — [GitLab advisory record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/@node-saml/node-saml/CVE-2025-54369.yml)
- Protocol-level gaps beyond signatures: missing `InResponseTo` binding was "one of the missing attributes that left Google's SSO vulnerable" (malicious-SP MITM). Missing `Destination` checks allow cross-SP assertion replay. — [OWASP SAML Security Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/SAML_Security_Cheat_Sheet.md)

### Inferences
- A useful single sentence for developers: a SAML library is only as safe as the guarantee that the identity the app reads (NameID and attributes) comes from the exact signed bytes. Every bug class above breaks that guarantee in a different way: element selection, text extraction, parser, canonicalizer, key choice, or skipping the check.
- The common precondition, "any validly signed document from the IdP," is cheap in multi-user SaaS. Any self-registered or low-privilege user of the same IdP can produce one. Many advisories therefore describe the attack as escalation from a low-privilege account to any account.

### Gaps
- I could not retrieve the GitHub Security Lab, PortSwigger "Fragile Lock," ProjectDiscovery, or WorkOS SAMLStorm write-ups directly. The session network blocks those hosts. Their technical details come from search excerpts and advisory records.
- I found no source that publishes current XSW variant numbering authoritatively. Search results note that numbering differs between HackTricks pages and tools, so no numbered XSW1–XSW8 taxonomy is given here.

## S2. SAML authentication bypass: which incidents and CVEs matter, with dates and fixed versions, through November 2026?

### Takeaway
The class has not been retired. Major SP libraries in every ecosystem issued auth-bypass fixes in 2024, 2025 and 2026: ruby-saml four times, xml-crypto and node-saml twice each, plus samlify, SimpleSAMLphp and goxmldsig. Backport branches have repeatedly shipped incomplete fixes. The newest entries (2026) are integration failures and protocol-path confusions rather than new XSW tricks.

### Cited Findings
**Historical (pre-2024)**
- **2012** XSW research, "On Breaking SAML" (USENIX Security 2012). — cited in [OWASP SAML Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/SAML_Security_Cheat_Sheet.md)
- **2018-02-27** Duo comment-injection disclosure. CVE-2017-11427 (OneLogin python-saml), CVE-2017-11428 (ruby-saml), CVE-2017-11429 (Clever saml2-js), CVE-2017-11430 (OmniAuth-SAML), CVE-2018-0489 (Shibboleth: one source says XMLTooling, CERT/CC says OpenSAML-C), CVE-2018-5387 (Wizkunde SAMLBase <1.2.7), CVE-2018-7340 (Duo Network Gateway). — [Duo PSA-2017-003](https://duo.com/labs/psa/duo-psa-2017-003), [CERT/CC VU#475445](https://kb.cert.org/vuls/id/475445), [SecurityWeek](https://www.securityweek.com/widespread-vulnerability-found-single-sign-products)
  - Fixed versions per primary changelogs: ruby-saml **1.7.0** (2018-02-27, "Fix vulnerability CVE-2017-11428. Process text of nodes properly, ignoring comments") — [ruby-saml CHANGELOG](https://github.com/SAML-Toolkits/ruby-saml/blob/master/CHANGELOG.md). python3-saml **1.4.0** "includes a fix for the CVE-2017-11427 vulnerability" — [python3-saml README](https://github.com/SAML-Toolkits/python3-saml/blob/master/README.md). One secondary source says python-saml 2.4.0 / ruby-saml 1.7.2, which conflicts with the ruby-saml changelog's 1.7.0.
- **2022** node-saml 4.0.0 made document signatures required by default ("Setting wantAuthenResponseSigned=false… restores the prior, less secure behavior"). — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)

**2024**
- **2024-05-01** xml-crypto **CVE-2024-32962** (GHSA-2xp3-57p7-qf4v), CVSS 10.0. KeyInfo certificate trusted by default. Affected >=4.0.0 <6.0.0; fixed **6.0.0**. Workaround: `getCertFromKeyInfo: () => undefined`/`null`. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2024-32962.yml), [search summary of NVD/Feedly](https://nvd.nist.gov/vuln/detail/CVE-2024-32962)
- **2024-05 / 2024-10** GitHub Enterprise Server **CVE-2024-4985** (encrypted-assertions feature, CVSS 10.0/9.8; fixed 3.9.15, 3.10.12, 3.11.10, 3.12.4) and **CVE-2024-9487** (CVSS 9.5). The second was introduced by the incomplete May 2024 fix and affected versions before 3.15. — [The Hacker News](https://thehackernews.com/2024/10/github-patches-critical-flaw-in.html), [SecurityWeek](https://www.securityweek.com/github-patches-critical-vulnerability-in-enterprise-server/), [Start with Identity](https://startwithidentity.com/cves/cve-2024-4985/) (secondary)
- **2024-09-10** ruby-saml **CVE-2024-45409** (GHSA-jw9c-mfg7-9rx2), "SAML authentication bypass via Incorrect XPath selector". Affected <1.12.3 and >=1.13.0 <1.17.0; fixed **1.12.3 / 1.17.0**. Reported by ahacker1 (SecureSAML). omniauth-saml fixed in 1.10.5 / 2.1.2 / 2.2.1 (GHSA-cvp8-5r8g-fhvq). — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2024-45409.yml), [omniauth-saml record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/omniauth-saml/GHSA-cvp8-5r8g-fhvq.yml). GitLab was affected through ruby-saml and omniauth-saml; ProjectDiscovery published a walkthrough and a Nuclei template. — [ProjectDiscovery](https://projectdiscovery.io/blog/ruby-saml-gitlab-auth-bypass) (search excerpt)

**2025**
- **2025-01** GHES **CVE-2025-23369**: SAML bypass involving libxml2 parsing, CVSS 7.6 per iThome. — [iThome](https://www.ithome.com.tw/news/167374), [Start with Identity](https://startwithidentity.com/cves/cve-2025-23369/) (secondary; fixed versions not verified)
- **2025-03-11** SimpleSAMLphp saml2 **CVE-2025-27773**, an HTTP-Redirect binding signature confusion: "An attacker with any signed SAMLResponse via the HTTP-Redirect binding can cause the application to accept an unsigned message". Fixed 4.17.0 / 5.0.0-alpha.20. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/packagist/simplesamlphp/saml2/CVE-2025-27773.yml)
- **2025-03-12** ruby-saml **CVE-2025-25291 / CVE-2025-25292** (parser differential, GHSA-4vc4-m8qh-g8jm / GHSA-754f-8gm6-c4r2) plus CVE-2025-25293 (DoS). Affected <1.12.4 and >=1.13.0 <1.18.0; fixed **1.12.4 / 1.18.0**. omniauth-saml fixed 1.10.6 / 2.1.3 / 2.2.3. — [ruby-saml CHANGELOG](https://github.com/SAML-Toolkits/ruby-saml/blob/master/CHANGELOG.md), [GitLab record 25291](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-25291.yml), [omniauth-saml record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/omniauth-saml/GHSA-hw46-3hmr-x9xv.yml). Found independently by GitHub Security Lab and bug-bounty researcher "ahacker1". CVSS is 8.8 per The Hacker News and 9.8 per other aggregators. — [The Hacker News](https://thehackernews.com/2025/03/github-uncovers-new-ruby-saml.html)
- **2025-03-14** xml-crypto **CVE-2025-29774** (multiple SignedInfo references, GHSA-9p8x-f768-wp2g) and **CVE-2025-29775** (comment inside DigestValue, GHSA-x3m8-899r-f7c3), branded "SAMLStorm" by WorkOS. Affected >=4.0.0 <6.0.1, >=3.0.0 <3.2.1, <2.1.6; fixed **6.0.1 / 3.2.1 / 2.1.6**. node-saml 5.0.1 and passport-saml 5.0.1 (2025-03-14) updated xml-crypto. — [GitLab record 29774](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2025-29774.yml), [GitLab record 29775](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2025-29775.yml), [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md), [passport-saml CHANGELOG](https://github.com/node-saml/passport-saml/blob/master/CHANGELOG.md). **Conflict:** WorkOS says the first is exploitable via node-saml and the second is not; other aggregators list both as affecting node-saml. — [WorkOS SAMLStorm](https://workos.com/blog/samlstorm) (search excerpt)
- **2025-05-19** samlify **CVE-2025-47949** (GHSA-r683-v43c-6xqv), signature wrapping. Affected <2.10.0; fixed **2.10.0** (commit 115679a). CVSS is 9.9 (v4) per vuln.today and the Belgian CCB, 7.5 per other databases. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/samlify/CVE-2025-47949.yml), [CCB advisory](https://ccb.belgium.be/advisories/warning-critical-signature-wrapping-vulnerability-samlify-library-saml-single-sign-patch)
- **2025-06-05** signxml (Python) **CVE-2025-48994/48995**: HMAC algorithm confusion and timing, only when `verify(require_x509=False, hmac_key=...)` is used without `expect_config`; fixed 4.0.4. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/pypi/signxml/CVE-2025-48994.yml)
- **2025-07-25 / 07-28** node-saml **CVE-2025-54369** (GHSA-m837-g268-mmv7) and **CVE-2025-54419** (GHSA-4mxg-3p6v-xgq3). The assertion was loaded from the unsigned original document. Affected <5.1.0; fixed **@node-saml/node-saml 5.1.0** (released 2025-07-21; "Use new .signedReferences interface in xml-crypto to 'see what is signed'"), which upgrades xml-crypto to 6.1.2. The advisory says this "is distinct from the previous xml-crypto CVEs." — [GitLab record 54369](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/@node-saml/node-saml/CVE-2025-54369.yml), [GitLab record 54419](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/@node-saml/node-saml/CVE-2025-54419.yml), [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)
  - **The unscoped `passport-saml` package (last release 3.2.4, 2022-10-22) is listed as affected by CVE-2025-54419 at "<=3.2.4" with "no solution available".** — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/passport-saml/CVE-2025-54419.yml), [npm registry](https://registry.npmjs.org/passport-saml)
- **2025-07-29** ruby-saml 1.18.1 fixes CVE-2025-54572 (DoS from a large SAML message). — [ruby-saml CHANGELOG](https://github.com/SAML-Toolkits/ruby-saml/blob/master/CHANGELOG.md)
- **2025-12-08** ruby-saml **CVE-2025-66567** (GHSA-9v8j-x534-2fx3: "incomplete fix for CVE-2025-25292") and **CVE-2025-66568** (GHSA-x4h9-gwv3-r4m4: libxml2 canonicalization). Affected "up to and including 1.12.4"; "does not affect the version 1.18.0". The ruby-saml README says "affects version ruby-saml < 1.18.0 (including 1.12.4), upgrade to 1.18.1". — [GitLab record 66567](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-66567.yml), [GitLab record 66568](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-66568.yml), [ruby-saml README](https://github.com/SAML-Toolkits/ruby-saml/blob/master/README.md). These come from PortSwigger's "The Fragile Lock: Novel Bypasses For SAML Authentication" (Black Hat Europe, 10 Dec 2025), which uses the 1.12.4 patches to argue that incremental fixes do not solve the underlying XML parsing problems. — [PortSwigger Research](https://portswigger.net/research/the-fragile-lock) (search excerpt only). SimpleSAMLphp published a security advisory 202512-01 in the same period; its content was not retrieved. — [simplesamlphp.org](https://simplesamlphp.org/security/202512-01)
  - RubyGems shows the newest ruby-saml is **1.18.1 (2025-07-29)**. There is no 1.12.5, so the 1.12.x backport line remains vulnerable. — [RubyGems API](https://rubygems.org/api/v1/versions/ruby-saml.json)

**2026 (through mid-November)**
- **2026-03-18** goxmldsig (Go) **CVE-2026-33487** (GHSA-479m-364c-43vc), a loop-variable capture in `validateSignature`: "lets an attacker get around integrity checks for certain signed elements by replacing their content with the content from another element that is also referenced in the same signature." Fixed 1.6.0. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/go/github.com/russellhaering/goxmldsig/CVE-2026-33487.yml)
- **2026-04 to 2026-09** @xmldom/xmldom, the DOM parser used by xml-crypto, node-saml and samlify, published about 20 CVEs. They include XML injection through CDATA, comment, DocumentType and processing-instruction serialization, attribute-name injection, and ReDoS. Current fixed lines are 0.8.15 / 0.9.12. These are serialization/injection and DoS issues, not direct SAML bypasses. — [GitLab advisory directory for @xmldom/xmldom](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/tree/master/npm/@xmldom/xmldom), [npm registry](https://registry.npmjs.org/@xmldom%2fxmldom)
- **2026-05-21** samlify **CVE-2026-46490** (GHSA-34r5-q4jw-r36m). When samlify acts as IdP, its templates do not escape element text. A user can inject `<saml:Attribute>` elements into an attribute value such as email or name, which "the IdP then signs… and the SP accepts the injected attributes as trusted", leading to privilege escalation when roles or groups come from attributes. Fixed **2.13.0**. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/samlify/CVE-2026-46490.yml)
- **2026-07-02** SimpleSAMLphp saml2 **CVE-2026-49283** (GHSA-6929-8p9f-26jx), HTTP-Artifact TLS validator confusion: an "unsigned embedded SAML `Response`" is treated "as cryptographically valid for the wrong IdP" (cross-IdP bypass). Fixed 4.19.3 / 4.20.2 / 5.0.6 / 6.2.1. **CVE-2026-49289** (XPath-transform DoS) has the mitigation "restrict transforms to only the transform-algorithms mentioned in the SAML 2.0 Core Specifications". Packagist shows saml2 v6.3.2 / v6.2.6 released 2026-11-10 and v7.0.0-rc5 in progress. — [GitLab record 49283](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/packagist/simplesamlphp/saml2/CVE-2026-49283.yml), [GitLab record 49289](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/packagist/simplesamlphp/saml2/CVE-2026-49289.yml), [Packagist](https://repo.packagist.org/p2/simplesamlphp/saml2.json)
- **2026-10-26** @node-saml/node-saml **5.2.0** shipped hardening without a CVE identifier. Its changes: "Reject replayed assertions by remembering their IDs when asked to"; "Check `idpIssuer` on a login Response and its assertion, and reject a message with more than one `Issuer`"; "Read the status of a signed response from the bytes its signature covers"; "Stop trusting an unsigned Response's InResponseTo"; "Read the verified bytes in `validatePostRequestAsync`, not the raw ones"; "Enforce SubjectConfirmationData NotOnOrAfter in every validateInResponseTo mode"; warnings before v6 enforces Recipient/Destination; xml-crypto updated to 6.3.3. — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md). @node-saml/passport-saml 5.1.1 was released 2026-09-28. — [npm registry](https://registry.npmjs.org/@node-saml%2fpassport-saml)
- **2026-11-10** GPUStack **CVE-2026-102894**: SAML callback never verified (see S1). Fixed 2.2.2. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/pypi/gpustack/CVE-2026-102894.yml)
- **Reported by aggregators only (not verified at a primary source in this session):** Keycloak CVE-2026-18217 (duplicate parameters in HTTP-Redirect binding inject a chosen SAMLResponse); Perl Net::SAML2 CVE-2026-18089/18092/18108 (<0.86: self-signed certs accepted, XSW, unsigned encrypted assertions accepted); SAP AS ABAP CVE-2026-120017 (CVSS 10.0, SAP Note 3849308); Elixir Samly CVE-2026-53424 (assertion replay, no patch listed); WordPress miniOrange "SAML Single Sign On" CVE-2026-15981 (≤5.4.4, OpenSSL error return treated as success). — [SentinelOne Keycloak](https://www.sentinelone.com/vulnerability-database/cve-2026-18217/), [SentinelOne Net::SAML2](https://www.sentinelone.com/vulnerability-database/cve-2026-18089/), [RedRays SAP](https://redrays.io/blog/sap-note-3849308-saml2-authentication-bypass-cve-2026-120017/), [Ionix Samly](https://www.ionix.io/threat-center/cve-2026-53424/), [GHSA-wgjx-q85h-87v2](https://github.com/advisories/GHSA-wgjx-q85h-87v2)

**Current versions (registries queried 2026-11-17)**
- @node-saml/node-saml **5.2.0** (2026-10-26); @node-saml/passport-saml **5.1.1** (2026-09-28); xml-crypto **6.4.0** (2026-10-14; maintenance tags 3x=3.2.1, 2x=2.1.6); samlify **2.15.1** (2026-10-21); @xmldom/xmldom 0.9.12 / lts 0.8.15; ruby-saml **1.18.1**; omniauth-saml 2.2.5 (2026-02-21); python3-saml **1.16.0** (2023-10-09, still the latest); xmlsec (Python) 1.3.18 (2026-10-29); signxml 5.3.0 (2026-11-12); pysaml2 7.5.5 (2026-09-17). — [npm registry](https://registry.npmjs.org/@node-saml%2fnode-saml), [RubyGems](https://rubygems.org/api/v1/versions/ruby-saml.json), [PyPI python3-saml](https://pypi.org/pypi/python3-saml/json)

### Inferences
- Three distinct failure modes appear repeatedly. (1) Incomplete fixes on backport lines: ruby-saml 1.12.4 → CVE-2025-66567/66568, and GHES CVE-2024-4985 → CVE-2024-9487. Developers should move to the actively fixed major (ruby-saml 1.18.x) rather than trust a backport. (2) Two components that each look correct but disagree: parser vs parser (ruby-saml), canonicalizer vs parser (node-saml CVE-2025-54419), library vs app (node-saml CVE-2025-54369, GPUStack). (3) Mutable defaults in older majors, such as xml-crypto <6 KeyInfo trust and node-saml <4 unsigned documents.
- For vibe-coded Node apps the highest-value check is `npm ls passport-saml`. The unscoped package is frozen at 3.2.4 with a known unpatched bypass. Older tutorials and model training data predate the 2022 move to `@node-saml/passport-saml`.

### Gaps
- No primary source was retrieved for GHES fixed versions of CVE-2025-23369, for the Keycloak, Net::SAML2, SAP, Samly and miniOrange 2026 CVEs, or for the PortSwigger research text. Treat those rows as secondary.
- I could not determine whether xml-crypto 6.2.0–6.4.0 (Sep–Oct 2026) included unannounced security fixes. The README "Upgrading" section documents canonicalization corrections, enveloped-signature handling and DOCTYPE deprecation, but the master CHANGELOG stops at 6.0.0 and the GitHub releases page was unreachable.
- python3-saml has had no release since October 2023. I found no advisory directory for it in the GitLab DB. Whether that means "no new vulns" or "not maintained" was not determined.

## S3. SAML: why are vibe-coded apps prone, what do the common stacks default to, and what does a managed broker cover versus what the developer still owns?

### Takeaway
AI-generated SAML code tends to go wrong in three ways. It hand-parses the `SAMLResponse` and never verifies it, re-reads the original XML after the library verified it, or turns off a check that produced an error ("make it work"). Several library defaults still leave replay, `InResponseTo`, Recipient/Destination, algorithm and schema enforcement to the developer. A managed broker (Supabase SSO, Auth0, WorkOS, Clerk) removes the XML-signature layer. The developer still owns token verification, identity keying, tenant binding and attribute-based authorization.

### Cited Findings
**Library defaults that leave work to the developer (current versions)**
- **node-saml 5.2.0**: `validateInResponseTo` defaults to `"never"`, where "any captured response can be replayed until its timestamps expire"; `"always"` "on more than one server or process… needs a shared cache provider". `rejectReplayedAssertions` defaults to `false`. `acceptedClockSkewMs: -1` "disables those checks entirely". `audience: false` skips the audience check. `signatureAlgorithm`/`digestAlgorithm` default to `"sha1"` (outgoing). Recipient/Destination are enforced only in the next major: "Until then a response that fails either check is accepted." — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- **node-saml**: `getSamlResponseXml()` is deprecated because it "returns the response document as it arrived… Never treat what you read from it as authenticated"; use `getAssertionXml()` ("The assertion XML **that the signature covers**"). — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- **node-saml v5.0.0** renamed `cert` → `idpCert` and `signingCert` → `publicCert`. — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)
- **samlify 2.15.1**: a schema validator must be registered, and the README shows how to skip it: "always resolve to skip validation… `return Promise.resolve('skipped')`… Skipping validation means accepting messages that may be malicious." — [samlify README](https://github.com/tngan/samlify/blob/master/README.md). In the package types, `allowUnsolicitedResponse` "Defaults to `true`"; `replayCache` is "Not set by default: samlify keeps no state, so replay protection is only active when the application supplies a store"; `allowedSignatureAlgorithms` "Unset (the default) accepts every supported algorithm"; `wantAudienceCheck` defaults to `true`; a bearer SubjectConfirmationData with no `Recipient` only produces `console.warn`. — [samlify 2.15.1 package (types/src/types.d.ts, build/src/flow.js)](https://registry.npmjs.org/samlify/-/samlify-2.15.1.tgz)
- **ruby-saml**: the README's sample settings use `settings.idp_cert_fingerprint` with `idp_cert_fingerprint_algorithm = "http://www.w3.org/2000/09/xmldsig#sha1"`. The same README later warns that "The fingerprint, is a hash, so at the end is open to a collision attack". `Response.new` accepts `skip_audience`, `skip_recipient_check`, `skip_conditions`, `skip_subject_confirmation`. `settings.security[:soft] = true` stops raising on failed signature validation. Replay prevention "is your responsibility". — [ruby-saml README](https://github.com/SAML-Toolkits/ruby-saml/blob/master/README.md)
- **python3-saml**: "In production, the **strict** parameter MUST be set as **'true'**. Otherwise your environment is not secure". Prefer registering the IdP certificate over the fingerprint. The sample advanced settings show `"wantMessagesSigned": false` and `"wantAssertionsSigned": false`. Replay protection is left to the app (`get_last_message_id`/`get_last_assertion_id`). RelayState on HTTP-POST "can't [be] trust[ed]". — [python3-saml README](https://github.com/SAML-Toolkits/python3-saml/blob/master/README.md)
- **xml-crypto**: since 6.0.0, `getCertFromKeyInfo` defaults to `noop`. Before 6.0.0 the KeyInfo certificate was trusted (CVE-2024-32962). — [xml-crypto CHANGELOG](https://github.com/node-saml/xml-crypto/blob/master/CHANGELOG.md), [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2024-32962.yml)

**Managed brokers: what they do, and what they leave**
- **Supabase SAML SSO**: Supabase Auth verifies the assertion signature against the certificate in the IdP metadata. SSO users "are not eligible for identity linking to existing user accounts for security reasons". "Emails are not necessarily unique… Always use the user's UUID to correctly reference user accounts." For tenancy it recommends RLS on the SSO provider UUID (`auth.jwt()#>>'{amr,0,provider}'`) with a `RESTRICTIVE` policy, and warns that with MFA "the `amr` array may have a different method at index `0`". NameID must be `emailAddress` or `persistent`. — [Supabase SAML SSO docs](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/enterprise-sso/auth-sso-saml.mdx)
- **Auth.js (`@auth/core` 0.41.3)**: no SAML provider ships in the package. Its built-in providers are OAuth/OIDC types (`type: "oidc"` / OAuth2). — [@auth/core 0.41.3 package](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz)
- **Base44 (Wix), July 2025**: Wiz found that a vibe-coding platform's registration and OTP-verification APIs needed only the non-secret `app_id`. That let outsiders register on "private" apps "bypassing authentication systems including Single Sign-On (SSO)". Patched within 24 hours of disclosure (found 2025-07-09); not exploited in the wild. — [Wiz](https://www.wiz.io/blog/critical-vulnerability-base44), [The Hacker News](https://thehackernews.com/2025/07/wiz-uncovers-critical-access-bypass.html)

**AI-agent-facing documentation (evidence that ecosystems expect AI-written integrations)**
- node-saml 5.2.0 added "AGENTS.md and CLAUDE.md" (#416). — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)
- Clerk's account-linking doc contains an `<If is="llm">` block telling AI agents to inspect `verify_at_sign_up` with `npx clerk@latest config pull --keys auth_email`. — [Clerk docs source](https://github.com/clerk/clerk-docs/blob/main/docs/guides/configure/auth-strategies/social-connections/account-linking.mdx)

### Inferences
**Code patterns AI assistants are likely to emit** (inferred from the library docs' own warnings and from the CVE root causes above; not measured):
1. **Decode-and-read with no verification.** `Buffer.from(req.body.SAMLResponse, "base64")` → `xml2js`/`fast-xml-parser`/`DOMParser` → read `NameID` → create a session. This is the GPUStack CVE-2026-102894 shape. It "works" against every IdP on the first try, so it survives a prompt-and-test loop.
2. **Verify, then re-parse the original.** The model calls `checkSignature()` (or a library), then extracts the user from the original `doc` or from `getSamlResponseXml()`. This is xml-crypto's "BAD" example and the node-saml CVE-2025-54369/54419 root cause.
3. **Non-anchored element selection.** `getElementsByTagName("saml:Assertion")[0]`, `//*[local-name()='NameID']`, or `.textContent` of the first child. OWASP forbids this, and it recreates XSW and comment-truncation bugs.
4. **Error-driven disabling.** Clock skew errors lead to `acceptedClockSkewMs: -1`. Audience mismatch (entityID typo) leads to `audience: false` / `skip_audience: true`. "InResponseTo not found" on serverless or multi-instance hosts (in-memory cache) leads to `validateInResponseTo: "never"`. samlify's schema validator requirement leads to the `Promise.resolve('skipped')` stub the README itself prints. ruby-saml exceptions lead to `security[:soft] = true`. Python errors lead to `"strict": false`.
5. **Stale package names and options.** `require("passport-saml")` (unscoped, 3.2.4, unpatched CVE-2025-54419), `cert:` instead of `idpCert:`, ruby-saml `~> 1.12` pins, `idp_cert_fingerprint` with SHA-1.
6. **Trusting the email attribute for account mapping and tenant routing.** The assertion's `email` attribute is used as the primary key or matched against an existing password account, which carries the nOAuth problem into SAML. samlify CVE-2026-46490 shows attributes can be attacker-shaped even inside a valid IdP signature.
7. **Serverless deployment (Vercel/Netlify functions)**, typical of vibe-coded apps, makes the stateful parts (request-ID cache, replay cache) the hardest to get right. Each needs a shared atomic store such as Redis `SET NX PX`.

**Responsibility split: broker vs app**
| Concern | Managed broker (Supabase SSO, Auth0, WorkOS, Clerk enterprise SSO) | Self-hosted library (node-saml, samlify, ruby-saml, python3-saml) |
|---|---|---|
| XML parsing, C14N, XSW defenses, cert pinning, Audience/Recipient/time checks | Broker | App developer (via library config + upgrades) |
| InResponseTo / replay cache | Broker (for its own ACS) | App developer (shared store) |
| Verifying the broker's own token/session (JWT signature, `aud`, `iss`, `exp`) on every server request | **App developer** | n/a |
| Keying users on the broker's immutable user ID, not email | **App developer** (Supabase says so explicitly) | **App developer** (issuer + persistent NameID) |
| Binding user → tenant/org by SSO connection ID, not email domain | **App developer** (Supabase RLS on provider UUID) | **App developer** |
| Turning IdP-asserted attributes (roles/groups) into authorization; JIT provisioning rules | **App developer** | **App developer** |
| Deciding whether IdP-initiated SSO is allowed; RelayState allowlist | Shared (broker setting + app redirect handling) | App developer |
| Keeping SDKs current | App developer | App developer (higher stakes) |

### Gaps
- I found no empirical study that measures how often AI coding assistants or app builders (Lovable, Bolt, v0, Cursor, Base44) emit insecure SAML handlers. The pattern list above is inferred from documented root causes, not measured.
- I did not verify Firebase/Google Cloud Identity Platform SAML support details or Auth0/WorkOS/Clerk SAML internals; their docs were unreachable from this session. The broker column describes the generic broker model, plus Supabase specifics that were verified.

## S4. SAML: how can a developer safely test their own app?

### Takeaway
Test only your own SP, against an IdP you control, in a non-production environment. Start with static and config checks (dependency versions, options, code grep). Then run negative tests with messages you generate and sign yourself. Use SAML Raider in Burp Suite for interactive XSW and signature-removal checks against staging.

### Cited Findings
- SAML Raider is a Burp Suite extension that can display, edit, re-sign and strip signatures from SAML messages, and it includes eight common XSW attacks. It was developed by students at the University of Applied Sciences Rapperswil with Compass Security. The documented workflow starts with a legitimate login to capture a valid signed response at the ACS, then applies each XSW variant or "Remove Signatures". — [CompassSecurity/SAMLRaider project listing](https://awesome.ecosyste.ms/projects/github.com%2FCompassSecurity%2FSAMLRaider), [RedFox Security](https://www.redfoxsec.com/blog/saml-raider-exploiting-and-securing-saml-authentication) (secondary)
- XSW variant numbering differs between sources (HackTricks English vs Korean pages), so record results by the transformation applied, not by number. — [HackTricks SAML Attacks](https://book.hacktricks.xyz/pentesting-web/saml-attacks) (search summary)
- node-saml logs security warnings under `NODE_DEBUG=node-saml`, including unset security-relevant defaults, missing Recipient/Destination, multi-reference signatures, and use of deprecated `getSamlResponseXml()`. — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md), [node-saml CHANGELOG 5.2.0](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)
- ProjectDiscovery published a Nuclei template for CVE-2024-45409. — [ProjectDiscovery](https://projectdiscovery.io/blog/ruby-saml-gitlab-auth-bypass) (search excerpt)
- Supabase serves SP metadata (append `?download=true` for XML), which is useful for checking the configured ACS and entityID. — [Supabase SAML SSO docs](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/enterprise-sso/auth-sso-saml.mdx)

### Inferences
**A safe, non-destructive test sequence for your own app:**
1. **Inventory (no traffic):** `npm ls passport-saml @node-saml/node-saml @node-saml/passport-saml samlify xml-crypto @xmldom/xmldom`; `bundle list | grep -E "ruby-saml|omniauth-saml"`; `pip show python3-saml xmlsec lxml signxml`. Flag: unscoped `passport-saml` (any version); node-saml < 5.1.0 (prefer 5.2.0); xml-crypto < 6.0.1 (or < 3.2.1 / < 2.1.6 on old lines); samlify < 2.10.0 (< 2.13.0 if used as IdP); ruby-saml < 1.18.0 (including 1.12.4); omniauth-saml < 2.2.3. Run `npm audit` / `osv-scanner` too.
2. **Config grep:** `audience: false`, `acceptedClockSkewMs: -1`, `validateInResponseTo: "never"` or unset, `wantAuthnResponseSigned: false`, `getSamlResponseXml`, `getCertFromKeyInfo` returning a value, `Promise.resolve('skipped')`, `skip_audience`, `skip_recipient_check`, `security[:soft]`, `idp_cert_fingerprint`, `"strict": false`, `certFingerprint`. Also look for any route that base64-decodes `SAMLResponse` without calling the library's validate/process function.
3. **Test IdP you control:** a local Keycloak or SimpleSAMLphp instance in Docker, or a dev tenant of your real IdP (Okta/Entra developer tenant) with test users only. Never test against a customer's production IdP or other users' accounts.
4. **Negative-message tests in CI:** generate fixtures with a test-only signing key (see S7). These are standard conformance checks: they prove your SP rejects malformed or tampered input. They are not exploits against third parties.
5. **Interactive pass in staging with SAML Raider:** capture your own test user's response at your own ACS, then try "Remove Signatures", re-sign with SAML Raider's self-signed cert (tests KeyInfo trust), each XSW template (cloning your own assertion), changing NameID to another test user you own, and replaying the same response twice. Every one must be rejected, and the server log should show a specific validation error.
6. **Replay and freshness:** post the same captured response twice; post one older than `NotOnOrAfter` + skew; post one with an unknown `InResponseTo`; if IdP-initiated SSO is disabled, post an unsolicited response.

### Gaps
- `samltest.id`, a once-common public test IdP, was not checked for availability; I did not find a current authoritative list of public SAML test IdPs.
- I did not verify that SAML Raider's current release still ships exactly eight XSW templates; this comes from secondary sources.

## S5. SAML: what is the correct fix (TypeScript/Node first, then Python), the full validation checklist, and the defense in depth?

### Takeaway
Use a current, maintained SP library with every security check on, and consume only the identity the library returns from verified bytes. Pin the IdP signing certificate. Bind each response to a request you issued and to your ACS URL. Reject replays with a shared atomic store. Map users by (IdP entityID or connection ID, persistent NameID), never by email. Prefer a managed broker if you do not need to own SAML.

### Cited Findings
- node-saml's minimal secure example sets `callbackUrl`, `issuer`, `idpCert`, `entryPoint`, `validateInResponseTo: "always"`, `privateKey`, `publicCert`, `signatureAlgorithm: "sha256"`, `digestAlgorithm: "sha256"`. Validation: `await saml.validatePostResponseAsync(req.body)`, which "rejects with an `Error` on anything it cannot vouch for". — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- node-saml response-validation options (names verbatim): `wantAssertionsSigned` (default `true`), `wantAuthnResponseSigned` (default `true`), `acceptedClockSkewMs` (default `0`), `maxAssertionAgeMs` (default `0`), `rejectReplayedAssertions` (default `false`), `idpIssuer`, `audience` (default = `issuer`), `requestIdExpirationPeriodMs` (8h), `cacheProvider` (in-memory). `idpCert` can be an array for rollover or a callback. "Decrypted content is not trusted content: an `EncryptedAssertion` is decrypted and then still has to have its signature verified." — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- xml-crypto direct use: `new SignedXml({ publicCert, getCertFromKeyInfo: () => null })`, then `checkSignature(xml)`, then `getSignedReferences()` ("returns the canonical XML of each reference, only after `checkSignature` succeeds"). Use one `SignedXml` instance per signature. `checkSignature()` throws when the document contains more than one `Signature` with the same value. Signing or verifying a document with a DOCTYPE "is deprecated and will throw in 7.0". — [xml-crypto README](https://github.com/node-saml/xml-crypto/blob/master/README.md)
- samlify 2.15.1 SP settings (verbatim names): `wantAssertionsSigned`, `wantMessageSigned`, `wantLogoutResponseSigned`, `clockDrifts: [number, number]`, `wantAudienceCheck`, `allowUnsolicitedResponse`, `allowInsecureDecryptionAlgorithms` (default `false`), `allowedSignatureAlgorithms`, `replayCache` (`saveIfAbsent(key, expiresAt)`, "as one atomic operation", e.g. Redis `SET key 1 NX PXAT expiresAt`). `parseLoginResponse(idp, binding, request, options?)` accepts the expected `inResponseTo`. samlify reads InResponseTo from the signed SubjectConfirmationData and trusts the outer `Response@InResponseTo` only when the whole message is signed. — [samlify 2.15.1 package](https://registry.npmjs.org/samlify/-/samlify-2.15.1.tgz)
- python3-saml settings (verbatim): `"strict": true`; `security.wantMessagesSigned`, `wantAssertionsSigned`, `wantNameId`, `wantAttributeStatement`, `rejectDeprecatedAlgorithm: true`, `allowRepeatAttributeName: false`, `signatureAlgorithm` rsa-sha256, `digestAlgorithm` sha256. Replay: `get_last_message_id` / `get_last_assertion_id`. Uses defusedxml (since 1.2.6, CVE-2017-9672). Install lxml from source so that xmlsec and lxml share a libxml2 version. — [python3-saml README](https://github.com/SAML-Toolkits/python3-saml/blob/master/README.md)
- ruby-saml: `settings.security[:want_assertions_signed] = true`, `settings.security[:strict_audience_validation] = true`, `allowed_clock_drift`, `response.assertion_id` stored in "a persistent cache (like Redis or Memcached) that is shared across your servers… Do not store it in the user's session". Nokogiri is used "by always disabling its DTDLOAD option and enabling its NONET option". — [ruby-saml README](https://github.com/SAML-Toolkits/ruby-saml/blob/master/README.md)
- OWASP SP checklist: signed by an authorized IdP; `Destination` "exactly matches the SP's expected… ACS URL… Reject responses that are missing `Destination`"; Audience equals SP EntityID; NotBefore/NotOnOrAfter; Recipient, InResponseTo, SubjectConfirmationData; "at least RSA-SHA-256… Reject SHA-1-based algorithms"; reference URI resolves to the consumed assertion; RelayState allowlist; replay detection for IdP-initiated SSO. — [OWASP SAML Security Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/SAML_Security_Cheat_Sheet.md)
- SimpleSAMLphp's 2026 mitigation restricts transforms "to only the transform-algorithms mentioned in the SAML 2.0 Core Specifications (and specifically refuse XPath transforms)". node-saml rejects "more than two transforms". — [GitLab record CVE-2026-49289](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/packagist/simplesamlphp/saml2/CVE-2026-49289.yml), [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)

### Inferences
**Synthesized secure configuration: Node/TypeScript with `@node-saml/node-saml` 5.2.0** (option names from the README above; the Redis cache adapter is left as an interface implementation because I did not verify its method signatures):
```ts
// package.json: "@node-saml/node-saml": "^5.2.0"   (NOT "passport-saml")
import { readFileSync } from "node:fs";
import { SAML, type Profile } from "@node-saml/node-saml";

const ACS_URL = "https://app.example.com/api/auth/saml/acs";       // exact URL the IdP posts to
const SP_ENTITY_ID = "https://app.example.com/saml/metadata";

export const saml = new SAML({
  callbackUrl: ACS_URL,
  issuer: SP_ENTITY_ID,
  audience: SP_ENTITY_ID,                                   // explicit; never `false`
  idpCert: [readFileSync("idp-signing-current.pem", "utf8")], // pinned out-of-band from IdP metadata; add next cert during rollover
  idpIssuer: "https://idp.example.com/entity-id",           // reject any other Issuer
  entryPoint: "https://idp.example.com/sso",
  wantAssertionsSigned: true,                               // defaults, stated so nobody "fixes" them away
  wantAuthnResponseSigned: true,
  validateInResponseTo: "always",                           // SP-initiated only
  cacheProvider: sharedRedisCacheProvider,                  // implements node-saml CacheProvider; atomic consume; NOT in-memory on serverless
  rejectReplayedAssertions: true,                           // 5.2.0+
  acceptedClockSkewMs: 30_000,                              // small, never -1
  maxAssertionAgeMs: 5 * 60_000,
  signatureAlgorithm: "sha256",
  digestAlgorithm: "sha256",
});

// ACS route (Express shown; same in a Next.js route handler)
app.post("/api/auth/saml/acs", express.urlencoded({ extended: false }), async (req, res) => {
  let profile: Profile | null;
  try {
    ({ profile } = await saml.validatePostResponseAsync(req.body));
  } catch (e) {
    log.warn({ err: String(e) }, "saml_reject");            // do not echo details to the browser
    return res.status(401).send("SSO failed");
  }
  if (!profile?.nameID) return res.status(401).send("SSO failed");
  // Identity key: (connection/IdP entityID, NameID). Prefer NameID format persistent.
  const user = await db.federatedIdentity.findUnique({
    where: { connectionId_nameId: { connectionId: CONNECTION_ID, nameId: profile.nameID } },
  });
  // profile.email is an attribute, not a key. Never link to an existing password account by email.
  // If you need the raw assertion: profile.getAssertionXml() (signed bytes) — never getSamlResponseXml().
  ...
});
```
- **Defense in depth until node-saml v6 enforces Recipient/Destination:** after `validatePostResponseAsync` succeeds, parse `profile.getAssertionXml()` (signed bytes only) with `@xmldom/xmldom` and require that a bearer `SubjectConfirmationData/@Recipient` exactly equals `ACS_URL`. Use namespace-qualified, anchored XPath. Alternatively, watch for the `NODE_DEBUG=node-saml` warning in staging and fix IdP config so the warning never fires.

**Synthesized secure configuration: samlify 2.15.1** (names from the package types):
```ts
import * as samlify from "samlify";
import * as validator from "@authenio/samlify-node-xmllint";  // a real schema validator; never the 'skipped' stub
samlify.setSchemaValidator(validator);

const sp = samlify.ServiceProvider({
  entityID: SP_ENTITY_ID,
  assertionConsumerService: [{ Binding: "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST", Location: ACS_URL }],
  wantAssertionsSigned: true,
  wantMessageSigned: true,                 // if the IdP signs the Response
  wantAudienceCheck: true,
  allowUnsolicitedResponse: false,         // default is true
  clockDrifts: [-30_000, 30_000],
  allowedSignatureAlgorithms: [
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512",
  ],
  replayCache: redisReplayCache,           // { saveIfAbsent(key, expiresAt) } atomic
});
const idp = samlify.IdentityProvider({ metadata: pinnedIdpMetadataXml }); // file shipped with the app, not fetched per request
const { extract } = await sp.parseLoginResponse(idp, "post", { body: req.body },
  { inResponseTo: pendingRequestIdsForThisBrowserSession });
```

**Synthesized secure configuration: Python with `python3-saml` 1.16.0** (`xmlsec` 1.3.18, `lxml` built against the same libxml2):
```python
from onelogin.saml2.auth import OneLogin_Saml2_Auth

SAML_SETTINGS = {
    "strict": True, "debug": False,
    "sp": {"entityId": SP_ENTITY_ID,
           "assertionConsumerService": {"url": ACS_URL,
               "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"},
           "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"},
    "idp": {"entityId": IDP_ENTITY_ID,
            "singleSignOnService": {"url": IDP_SSO_URL,
               "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"},
            "x509cert": PINNED_IDP_CERT},          # not certFingerprint
    "security": {"wantMessagesSigned": True, "wantAssertionsSigned": True,
                 "wantNameId": True, "rejectDeprecatedAlgorithm": True,
                 "allowRepeatAttributeName": False,
                 "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                 "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"},
}

def acs(request_data, session, replay_store):
    auth = OneLogin_Saml2_Auth(request_data, SAML_SETTINGS)
    auth.process_response(request_id=session.pop("saml_request_id", None))  # binds InResponseTo
    if auth.get_errors() or not auth.is_authenticated():
        raise PermissionError(auth.get_last_error_reason())
    # replay: atomic set-if-absent with TTL >= NotOnOrAfter + skew
    if not replay_store.set(f"saml:{IDP_ENTITY_ID}:{auth.get_last_assertion_id()}", 1, nx=True, ex=600):
        raise PermissionError("replayed assertion")
    return (IDP_ENTITY_ID, auth.get_nameid())     # identity key; email is an attribute only
```
- **Ruby/Rails:** `gem "ruby-saml", "~> 1.18", ">= 1.18.1"` (leave the 1.12.x line); `omniauth-saml >= 2.2.3`. Use `settings.idp_cert` (not fingerprint), `security[:want_assertions_signed] = true`, `security[:strict_audience_validation] = true`, `matches_request_id:` on the Response, no `skip_*`, no `soft`; store `response.assertion_id` in Redis.

**Full SP validation checklist** (each item maps to a CVE class above):
1. Signature verified with a **pinned** IdP key; `KeyInfo` ignored; no fingerprint or SHA-1 thumbprint (CVE-2024-32962 class).
2. Signature **required**: Assertion signed, and Response signed where the IdP supports it. Algorithms limited to RSA-SHA256 or stronger, digests SHA-256 or stronger.
3. **Exactly one** Assertion; reject mixed `Assertion` + `EncryptedAssertion`, multiple `Signature`/`Issuer`, duplicate IDs, multi-reference signatures (XSW, CVE-2025-29774 class).
4. Reference URI resolves to the element you consume. Transforms limited to enveloped-signature + exclusive C14N, max 2, no XPath/XSLT (CVE-2026-49289 class).
5. Identity read **only from verified bytes** (`getSignedReferences()` / `getAssertionXml()` / library profile). Never re-parse the raw POST (CVE-2025-54369/54419, parser differentials).
6. **One XML parser** for verification and consumption; DTD/DOCTYPE rejected; no external entities or network fetches (CVE-2025-25291 class; XXE).
7. Text extraction concatenates all text nodes, or reads from C14N output without comments (2018 comment class).
8. `Issuer` equals the configured IdP entityID on Response and Assertion.
9. `Audience` equals the SP entityID; `AudienceRestriction` required.
10. `Response@Destination` and bearer `SubjectConfirmationData@Recipient` equal the ACS URL exactly.
11. `NotBefore`/`NotOnOrAfter` (Conditions and SubjectConfirmationData) with small skew; `SessionNotOnOrAfter` respected; optional max assertion age.
12. `InResponseTo` equals an outstanding request ID, consumed once, stored in a shared atomic store. IdP-initiated SSO disabled unless required; if enabled, compensate with replay cache and RelayState allowlist.
13. Assertion-ID **replay cache**, shared and atomic, TTL until expiry plus skew.
14. `StatusCode` Success read from signed content.
15. Encrypted assertions: decrypt, then verify; reject RSA1.5/3DES key transport.
16. Schema validation against local schemas, where the library supports it (samlify requires it).
17. Account mapping: key on (connection or IdP entityID, persistent NameID). Bind connection to tenant server-side. No email-based auto-linking to non-SSO accounts (Supabase's rule). Attributes used for roles are validated against an allowlist (CVE-2026-46490 class).
18. Dependencies current: subscribe to GHSAs for xml-crypto, @xmldom/xmldom, node-saml, samlify, ruby-saml, nokogiri/libxml2, xmlsec.

**Defense in depth:** prefer a managed broker; run SSO sessions short with IdP re-auth for admin actions; alert on SAML validation-error spikes and on the first login of privileged accounts via SSO; log assertion ID, issuer, NameID and source IP; require step-up for role changes that arrive via SAML attributes.

### Gaps
- I did not verify node-saml's `CacheProvider` method names (`saveAsync`/`getAsync`/`removeAsync` plus a `consumeAsync` mentioned in the README), so the snippet references an adapter rather than implementing one.
- I did not verify `@authenio/samlify-node-xmllint`'s current version or maintenance status; the samlify README lists it as one of three validator options.
- `process_response(request_id=...)` and `get_last_error_reason()` in python3-saml are from my knowledge of the library API, not re-verified against the 1.16.0 source in this session.

## S6. SAML: which fixes are commonly incorrect or incomplete, and why do they fail?

### Takeaway
Fixes fail when they patch a symptom (one wrapping layout, one comment position, one backport) or verify one thing and use another. They also fail when they turn an error into a pass by disabling a check. Each failure below has a documented real-world counterpart.

### Cited Findings
- **Backport patches that leave the root cause:** ruby-saml 1.12.4's fix for CVE-2025-25292 was incomplete (CVE-2025-66567); only the 1.18.0 redesign is unaffected. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/gem/ruby-saml/CVE-2025-66567.yml). GHES's May 2024 fix for CVE-2024-4985 introduced CVE-2024-9487. — [SecurityWeek](https://www.securityweek.com/github-patches-critical-vulnerability-in-enterprise-server/). PortSwigger argues that "incremental fixes don't solve the underlying XML parsing problems." — [PortSwigger](https://portswigger.net/research/the-fragile-lock) (search excerpt)
- **Upgrading the crypto library but not the consumer:** node-saml CVE-2025-54419/54369 is "distinct from the previous xml-crypto CVEs". Upgrading xml-crypto to 6.0.1 for SAMLStorm did not fix node-saml's habit of reading the unsigned original document. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/@node-saml/node-saml/CVE-2025-54419.yml)
- **Staying on the deprecated package:** unscoped `passport-saml` ≤3.2.4 has "no solution available" for CVE-2025-54419. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/passport-saml/CVE-2025-54419.yml)
- **"Signature check" that only checks presence or validity, not signer:** xml-crypto <6 validated against whatever cert was in `KeyInfo`. — [GitLab record CVE-2024-32962](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/xml-crypto/CVE-2024-32962.yml)
- **Fingerprint pinning:** "a hash, so at the end is open to a collision attack that can end on a signature validation bypass." — [python3-saml README](https://github.com/SAML-Toolkits/python3-saml/blob/master/README.md), [ruby-saml README](https://github.com/SAML-Toolkits/ruby-saml/blob/master/README.md)
- **Trusting decryption as authentication:** node-saml: "Decrypted content is not trusted content". GHES 2024 bugs were in the encrypted-assertions path. — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md), [The Hacker News](https://thehackernews.com/2024/10/github-patches-critical-flaw-in.html)
- **Unsigned outer fields:** node-saml 5.2.0 had to "Stop trusting an unsigned Response's InResponseTo" and "Read the status of a signed response from the bytes its signature covers". When only the assertion is signed, "the response's `Issuer`, `Status`, and timestamps — is covered by any signature". — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md), [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- **Verifying the Redirect-binding query differently from what is consumed:** SimpleSAMLphp CVE-2025-27773 (v4). "V5 is well designed and instead builds the signed query from the same message that will be consumed." node-saml 5.2.0: "Process the Redirect-binding parameters that were verified". — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/packagist/simplesamlphp/saml2/CVE-2025-27773.yml), [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)

### Inferences
- **Regex or string-level sanitizing** (stripping `<!--`, rejecting the string `Signature` in unexpected places, counting `<Assertion` substrings) fails because canonicalization, namespaces, entities and parser differentials mean the string view is not the parsed view.
- **Adding a second, "stricter" parser** for a pre-check recreates the ruby-saml parser-differential precondition (two parsers, two views).
- **Disabling `InResponseTo` because serverless instances lose the in-memory cache** trades a login bug for a replay bug. The right fix is a shared store.
- **"We use a broker, so we're done"** fails if the app then trusts an unverified client-side token, keys users on email, or maps tenant by email domain (see N-sections).
- **Pinning the IdP cert by fetching metadata at runtime from a URL the request can influence**, or without TLS pinning, moves trust to whoever controls that fetch. ruby-saml notes it does not validate the metadata URL ("SSRF"). — [ruby-saml README](https://github.com/SAML-Toolkits/ruby-saml/blob/master/README.md)

### Gaps
- No source quantified how often teams pin by fingerprint versus full certificate in production.

## S7. SAML: how does a developer verify the fix, with a test that fails before and passes after?

### Takeaway
Build a regression suite of locally signed SAML responses from a test-only IdP key. The valid fixture must be accepted. Every tampered, unsigned, foreign-key, mis-targeted, stale or replayed variant must be rejected. Run it in CI against the real ACS handler, not against a mocked library.

### Cited Findings
- node-saml added tests "for the signature ambiguity rejections, the SHA-1 fallback, and error statuses" (#460), a model for app-level tests. — [node-saml CHANGELOG](https://github.com/node-saml/node-saml/blob/master/CHANGELOG.md)
- node-saml's errors are distinguishable ("an invalid signature, a mismatched audience, an expired assertion, and a missing decryption key"), so tests can assert the specific rejection reason. — [node-saml README](https://github.com/node-saml/node-saml/blob/master/README.md)
- xml-crypto can sign as well as verify (`computeSignature`, `getSignedXml`), so a test can mint fixtures with a throwaway key. — [xml-crypto README](https://github.com/node-saml/xml-crypto/blob/master/README.md)

### Inferences
**Test matrix (same fixtures for Node or Python; Python can sign with `signxml`/`xmlsec`):**
| # | Fixture (all built from your own test IdP template) | Before (vulnerable) | After |
|---|---|---|---|
| 1 | Valid signed response for test user A, correct audience/recipient/InResponseTo | accept | accept → identity key = (idp, nameID_A) |
| 2 | Same, signature element removed | often accept (hand-rolled) | reject |
| 3 | Signed with a different, self-generated key whose cert is embedded in `KeyInfo` | accept (xml-crypto <6, KeyInfo trust) | reject |
| 4 | Fixture #1 with NameID changed after signing | accept if re-parsing raw doc | reject (digest) |
| 5 | Fixture #1 plus a second, unsigned Assertion for user B (document structure only; no attack-specific layout needed) | may return B | reject ("more than one assertion") |
| 6 | Comment inserted inside NameID text of a re-signed fixture | identity truncated | identity equals full signed text, or reject |
| 7 | Valid signature but Audience = another SP | accept if `audience:false` | reject |
| 8 | Valid signature but Recipient/Destination = other URL | accept | reject (custom check until node-saml v6) |
| 9 | `NotOnOrAfter` in the past (beyond skew) | accept if skew -1 | reject |
| 10 | Unknown `InResponseTo`, or none when SP-initiated only | accept if "never" | reject |
| 11 | Post fixture #1 twice | accept twice | second rejected (replay cache) |
| 12 | Document with a DOCTYPE | parsed | reject |
| 13 | RSA-SHA1 signature | accept | reject (policy) |
| 14 | Attribute value containing XML markup (IdP role tests, samlify <2.13) | extra attributes appear | escaped / rejected |
- Assert both the HTTP status and that **no session cookie was issued** and **no user row was created** (catches GPUStack-style JIT provisioning before verification).
- Add a CI dependency gate: fail the build if `passport-saml` (unscoped) is present, or if node-saml < 5.2.0, xml-crypto < 6.0.1, samlify < 2.13.0, or ruby-saml < 1.18.1 resolves in the lockfile.
- For managed brokers: test that the app rejects a broker JWT with a wrong `aud`/`iss`, an expired token, and a token signed by a different key, and that two SSO users with the same email in different connections stay separate.

### Gaps
- I did not find a maintained public corpus of SAML negative-test fixtures licensed for reuse. Teams have to generate their own.

## N1. nOAuth: what is the mechanism, what are the preconditions, and what is the impact?

### Takeaway
nOAuth is an application flaw, not an IdP bug. A multi-tenant app that accepts Microsoft Entra ID sign-ins uses the `email` claim as the account key or merge key. Entra lets a tenant admin set a user's mail attribute to any address without proving ownership. An attacker who controls any Entra tenant can therefore mint a genuine, correctly signed token carrying the victim's email and be logged into the victim's account. The same failure applies to any IdP and any automatic link-by-email logic. That broader form is the "pre-account takeover" class.

### Cited Findings
- Descope describes nOAuth as "an authentication implementation flaw that can affect Microsoft Azure AD multi-tenant OAuth applications"; "the email claim is both mutable and unverified so it should never be trusted or used as an identifier." The attacker changes the email attribute of an account in their own Azure AD tenant to the victim's address. "Vulnerable applications will use the attacker's account's email claim and incorrectly associate it with the victim's leading to a full account takeover." — [Descope](https://descope.com/blog/post/noauth) (search excerpt)
- Okta's analysis notes "two unique conditions that must be met": the app trusts the email claim, and the attack works across tenants. — [Okta Security](https://sec.okta.com/articles/2023/08/saying-no-thanks-noauth/) (search excerpt)
- Semperis (June 2025): abuse requires "an Entra ID tenant that can hold an unverified email address, and an app registration that accepts that email claim as a user identifier"; "attackers require only their own Entra tenant and the email address of a target user." — [Semperis blog](https://www.semperis.com/blog/noauth-abuse-alert-full-account-takeover/) (search excerpt)
- Microsoft's current claim docs: `email` "isn't guaranteed to be correct, and is mutable over time - never use it for authorization or to save data for a user". `upn` is "Not a durable identifier… shouldn't be used for authorization… Instead, use the user object ID (`oid`) as a database key." — [Entra optional claims reference, ms.date 2026-07-22](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/optional-claims-reference.md) (Learn: [optional-claims-reference](https://learn.microsoft.com/entra/identity-platform/optional-claims-reference))
- "Never use claims like `email`, `preferred_username` or `unique_name`… These claims aren't unique and can be controllable by tenant administrators or sometimes users… use the immutable claim values `tid` and `oid` as a combined key." — [Entra claims validation, ms.date 2025-03-21](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/claims-validation.md)
- `oid`: "The immutable identifier for an object… can't be reused"; differs per tenant for the same person. `sub`: "immutable and can't be reassigned or reused… a pairwise identifier and is unique to an application ID". `tid`: tenant GUID; the MSA consumer tenant is `9188040d-6c67-4c5b-b112-36a304b66dad`. "To correctly store information per-user, use `sub` or `oid` alone… with `tid` used for routing or sharding." Don't use `idp` to correlate users across tenants. — [Entra ID token claims reference](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/id-token-claims-reference.md)
- OpenID Connect Core 1.0 §5.7 (Claim Stability and Uniqueness): "The sub (subject) and iss (issuer) Claims, used together, are the only Claims that an RP can rely upon as a stable identifier for the End-User". Other claims such as email, phone_number, preferred_username and name "MUST NOT be used as unique identifiers". — quoted in [Authelia, "OpenID Connect 1.0 Nuances"](https://www.authelia.com/blog/technical-openid-connect-1.0-nuances/); spec at [openid.net](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability) (not fetched directly)
- **Generalization, pre-account takeover:** Sudhodanan & Paverd (MSRC), "Pre-hijacked accounts: An Empirical Study of Security Failures in User Account Creation on the Web," USENIX Security 2022. The attacker knows only the victim's email. There are five attack types, and at least 35 of 75 popular services were vulnerable. In the **classic-federated merge** attack, the attacker registers via password with the victim's email; the victim later signs in via a federated IdP; the service merges insecurely and the attacker keeps access. Recommendations: verify email before any feature use, and rely on IdP verification. — [USENIX](https://www.usenix.org/conference/usenixsecurity22/presentation/sudhodanan), [arXiv:2205.10174](https://arxiv.org/abs/2205.10174v1), [Malwarebytes summary](https://www.malwarebytes.com/blog/news/2022/06/hackers-can-take-over-accounts-you-havent-even-created-yet)
- Google: the domain of the `email` claim "is insufficient to ensure that the account is managed by a domain or organization"; use `hd`. "If email_verified is true and hd is set, this is a Google Workspace account." — [Google, Authenticate with a backend server](https://developers.google.com/identity/sign-in/web/backend-auth) (search excerpt)

### Inferences
- **Preconditions, consolidated:** (1) the app accepts identities from issuers the attacker can control or join: Entra multi-tenant (`common`/`organizations`), "any Google account", or any OIDC IdP that lets users set unverified emails; (2) the app looks up or merges accounts by an email (or UPN or username) claim rather than (iss, sub); (3) the victim has, or will create, an account under that email.
- **Impact:** full account takeover with no interaction from the victim. Because authentication happens in the attacker's tenant, the victim's own MFA and Conditional Access are never evaluated. This follows from the mechanism; I did not retrieve a primary statement of it.
- The same failure appears in SAML: if a SaaS app maps SAML logins to users by the `email` attribute across IdP connections, the admin of any connected IdP can assert any email.

### Gaps
- I could not fetch the Descope, Semperis and MSRC pages directly (network policy), so verbatim technical detail is limited to search excerpts.

## N2. nOAuth: which incidents, research and vendor changes matter, from 2023 to November 2026?

### Takeaway
Descope reported nOAuth to Microsoft in April 2023, and it was jointly disclosed on 2023-06-20. Microsoft changed defaults for new app registrations and added the `xms_edov` claim and the `removeUnverifiedEmailClaim` behavior, but legacy registrations and app code remained exposed. In June 2025 Semperis found 9 of 104 tested Entra-gallery SaaS apps still vulnerable. In 2026 the same class surfaced as a CVE in a popular TypeScript auth library (better-auth CVE-2026-53516). Microsoft's dedicated "migrate off email claim" page has since been retired from Learn.

### Cited Findings
- **2023-04-11** Descope reported to Microsoft; $75,000 bug bounty; **2023-06-20** joint public disclosure. Descope's PoC compromised no unauthorized accounts or data. — [Descope](https://descope.com/blog/post/noauth), [The Hacker News](https://thehackernews.com/2023/06/critical-noauth-flaw-in-microsoft-azure.html) (search excerpts)
- **June 2023** MSRC, "Potential Risk of Privilege Escalation in Azure AD Applications": an attacker can falsify the email claim in tokens; the risk is mainly to multi-tenant apps; Microsoft called it "an insecure anti-pattern". Microsoft "deployed mitigations to omit token claims from unverified domain owners for most applications." — [MSRC blog](https://msrc.microsoft.com/blog/2023/06/potential-risk-of-privilege-escalation-in-azure-ad-applications), [Redmondmag](https://redmondmag.com/Articles/2023/06/21/Azure-Active-Directory-nOAuth-Attack-Route.aspx) (search excerpts)
- **`xms_edov` optional claim**: "Boolean value indicating whether the user's email domain owner has been verified… if it belongs to the tenant where the user account resides and the tenant admin has done verification of the domain. Also, the email must be from a Microsoft account (MSA), a Google account, or used for authentication using the one-time passcode (OTP) flow. Facebook and SAML/WS-Fed accounts **do not** have verified domains. For this claim to be returned in the token, the presence of the `email` claim is required." JWT only. — [Entra optional claims reference](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/optional-claims-reference.md)
- **`authenticationBehaviors.removeUnverifiedEmailClaim`** (Microsoft Graph `application` resource, v1.0 and beta): "If `true`, removes the `email` claim from tokens sent to an application when the email address's domain can't be verified." — [Graph authenticationBehaviors resource (v1.0)](https://github.com/microsoftgraph/microsoft-graph-docs-contrib/blob/main/api-reference/v1.0/resources/authenticationbehaviors.md); how-to: [Manage application authenticationBehaviors](https://learn.microsoft.com/graph/applications-authenticationbehaviors)
- **Default for new registrations:** secondary sources state that app registrations created after June 2023 do not emit an unverified `email` claim by default. — [Semperis](https://www.semperis.com/blog/noauth-abuse-alert-full-account-takeover/), [Cayosoft](https://www.cayosoft.com/blog/noauth/) (search excerpts). The Graph resource page I read does not state the default.
- **2024-12 → 2025-04** Semperis opened an MSRC case in December 2024; MSRC closed it without details in April 2025. — [Semperis](https://www.semperis.com/blog/noauth-abuse-alert-full-account-takeover/) (search excerpt)
- **2025-06-27** Semperis research: of 104 SaaS apps from the Entra Gallery tested, nine were vulnerable to cross-tenant nOAuth (~9%). Wider claims of ">10,000"/"15,000+" apps are extrapolations. Semperis says customers have little ability to fix this themselves. — [Semperis press release](https://www.semperis.com/press-release/research-risk-noauth-vulnerability-microsoft-entra-id-enterprise-saas-applications/), [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/microsoft-noauth-flaw-2025/), [The Hacker News](https://thehackernews.com/2025/06/noauth-vulnerability-still-affects-9-of.html) (search excerpts)
- **Microsoft's migration guide retired:** in the current `MicrosoftDocs/entra-docs` repo, `/docs/identity-platform/migrate-off-email-claim-authorization.md` is redirected to `/entra/identity-platform/` (fetched 2026-11-17). The guidance now lives in the claim-reference and claims-validation pages cited in N1. — [entra-docs .openpublishing.redirection.json](https://github.com/MicrosoftDocs/entra-docs/blob/main/.openpublishing.redirection.json)
- **2026-07-07 better-auth CVE-2026-53516** (GHSA-g38m-r43w-p2q7): the OAuth auto-link gate accepted a link "whenever the provider asserts `email_verified: true`, without requiring the local user row's `emailVerified` to also be `true`. An attacker who pre-registers a victim's email through `/sign-up/email`… can have the victim's later OAuth identity bound to the attacker's user row… This is the pre-account-hijacking class — the same shape as Microsoft 'nOAuth' (2023) and the Sign in with Apple JWT flaw (2020)." Fixed **1.6.11**. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/better-auth/CVE-2026-53516.yml)
- **2026-07-07 better-auth CVE-2026-53514** (GHSA-fmh4-wcc4-5jm3): organization `acceptInvitation` "trusts an email-string equality check as proof that the session user owns the invited address"; with stock `emailAndPassword: { enabled: true }`, "`requireEmailVerification` defaults to `false`". Fixed 1.6.11. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/better-auth/CVE-2026-53514.yml)
- **Email-as-identity adjacent bugs in Auth.js:** GHSA-5jpx-9hw9-2fx4 (2025-10-29): a nodemailer address-parser bug let magic-link emails for `"e@attacker.com"@victim.com` go to the attacker; fixed next-auth 4.24.12 / 5.0.0-beta.30. GHSA-7rqj-j65f-68wh (2026-07-23): the email normalizer validated "**before** applying Unicode normalization", so a homoglyph `@` can redirect sign-in links; fixed next-auth 4.24.15 / 5.0.0-beta.32 and @auth/core 0.41.3. — [GitLab record 5jpx](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/next-auth/GHSA-5jpx-9hw9-2fx4.yml), [GitLab record 7rqj](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/next-auth/GHSA-7rqj-j65f-68wh.yml)
- **2026 open-source issue traffic:** October 2026 GitHub issues in several projects (e.g., "OIDC: support Microsoft Entra ID, which sends no email_verified claim"; "Microsoft sign-in can't take over an existing account (nOAuth)" in an AI-SaaS cookiecutter template) show the pattern still being found and fixed. — [peterrichards-lr/mcp_agent_mail#18](https://github.com/peterrichards-lr/mcp_agent_mail/issues/18), [CrimsonCowLabs/cookiecutter-ai-saas#101](https://github.com/CrimsonCowLabs/cookiecutter-ai-saas/issues/101) (search results; not opened)

### Inferences
- What changed since 2023: Microsoft added tools (`xms_edov`, `removeUnverifiedEmailClaim`, quieter defaults for new registrations) but did not remove the root cause. An `email` claim, even a domain-verified one, is still not an identifier, and app code that keys on it stays exposed. The retirement of the migration page means developers now get the rule only from the claim-reference tables.
- better-auth CVE-2026-53516 shows the class is not specific to Entra. Any library that auto-links on "provider says verified" without also requiring local verification reproduces it.

### Gaps
- I found no Microsoft statement after 2023 changing Entra's emission behavior for pre-June-2023 multi-tenant registrations. I found no CVE assigned to nOAuth itself; it is an app-side anti-pattern.
- I found no prevalence data for nOAuth in AI-generated or vibe-coded apps specifically.

## N3. nOAuth: why are vibe-coded apps prone, and what do the common auth stacks do by default?

### Takeaway
The default "Sign in with Microsoft" path that assistants generate is multi-tenant (Auth.js defaults its Entra issuer to `common`). Vibe-coded apps also tend to treat `session.user.email` as the user's identity in database queries and RLS. When an "account already exists with a different provider" error appears, the fastest fix an assistant can suggest is to turn on email-based linking, which is exactly the vulnerable configuration. Managed brokers mostly link by email but gate on verification, and each has different edge cases.

### Cited Findings
**Auth.js / NextAuth (`@auth/core` 0.41.3, next-auth 4.24.15 / 5.0.0-beta.32)**
- Accounts are keyed by provider + `providerAccountId` (`userFromProfile.id`). The Entra provider maps `id: profile.sub`. — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz) (`lib/actions/callback/oauth/callback.js`, `providers/microsoft-entra-id.js`)
- Linking by email is **off by default**. If an existing user has the same email, Auth.js throws `OAuthAccountNotLinked("Another account already exists with the same e-mail address")`. The opt-in is `allowDangerousEmailAccountLinking: true`: "Automatic account linking on sign in is not secure between arbitrary providers and is disabled by default… it may be desirable… if you trust that the provider involved has securely verified the email address." The source comments explain the default: it "makes it harder to hijack a user account using a 3rd party OAuth account… by creating an oauth account then changing the email address associated with it." — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz) (`providers/oauth.d.ts`, `lib/actions/callback/handle-login.js`)
- Entra provider default: "When the `issuer` parameter is omitted it will default to `https://login.microsoftonline.com/common/v2.0/`. This allows any Microsoft account (Personal, School or Work) to log in." Restrict with `AUTH_MICROSOFT_ENTRA_ID_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0/`. — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz)
- The Google provider's documented tip restricts sign-in with `profile.email_verified && profile.email.endsWith("@example.com")`, an email-suffix check rather than the `hd` claim. — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz) (`providers/google.js`); contrast [Google backend-auth guidance](https://developers.google.com/identity/sign-in/web/backend-auth)

**Supabase Auth**
- "Supabase Auth automatically links identities with the same email address to a single user." To prevent pre-account takeover, "when a new identity can be linked to an existing user, Supabase Auth will remove any other unconfirmed identities linked to an existing user." Manual linking (beta) is `linkIdentity()` while signed in, enabled in the dashboard or with `GOTRUE_SECURITY_MANUAL_LINKING_ENABLED: true`. SAML SSO users are never linking targets. — [Supabase identity linking docs](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/auth-identity-linking.mdx)
- For Azure, Supabase "recommend[s] configuring the optional `xms_edov` claim" so it can tell whether Entra's email is verified, and supports an "Azure Tenant URL" (`https://login.microsoftonline.com/<tenant-id>`) to restrict tenants. — [Supabase Azure docs](https://supabase.com/docs/guides/auth/social-login/auth-azure) (search excerpt; what Supabase does when `xms_edov` is absent was not confirmed)
- With SSO, "Emails are not necessarily unique… Always use the user's UUID." — [Supabase SAML SSO docs](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/enterprise-sso/auth-sso-saml.mdx)

**Firebase Authentication** (secondary sources only)
- In "One account per email address" mode, Firebase links by email. A "trusted provider" (an IdP that is also the email provider, e.g. Google for gmail.com) signs straight into the existing account. "If there is an existing account with the same email address but created with non-trusted credentials (e.g. non-trusted provider or password), the previous credentials are removed for security reason." A newer project setting allows multiple accounts per email, in which case the "sign-in flow cannot rely on an email address to identify a user account." — [firebase-talk Google Group](https://groups.google.com/g/firebase-talk/c/ms_NVQem_Cw/m/8g7BFk1IAAAJ), [Stack Overflow mirror](https://kaweah.freedombox.rocks/kiwix/stackoverflow.com_en_all_2023-11/questions/65565874/firebase-authentication-provider-silently-changes-from-password-to-google-com)

**Clerk**
- "By using the email address as the common identifier, Clerk automatically attempts to link accounts." With a **verified** OAuth email it links and signs in, which "even applies to password-protected accounts, as the OAuth sign-in process automatically bypasses password verification". An unverified OAuth email triggers verification first. If "Verify at sign-up" was disabled and a user signed up unverified, Clerk "will prompt the user to change their password before linking". — [Clerk account-linking docs (source)](https://github.com/clerk/clerk-docs/blob/main/docs/guides/configure/auth-strategies/social-connections/account-linking.mdx)

**Auth0**
- Auth0 sets `email_verified` from the IdP, which "transfers the responsibility to the identity provider to do it properly, which Auth0 can't ensure"; it defaults to false if absent. Account linking should "request authentication for both accounts before linking occurs." — [Auth0 verified email usage](https://auth0.com/docs/manage-users/user-accounts/user-profiles/verified-email-usage), [Auth0 user account linking](https://auth0.com/docs/manage-users/user-accounts/user-account-linking) (search excerpts)

**better-auth (1.7.25)**
- Implicit OAuth linking is refused when `(!isTrustedProvider && !userInfo.emailVerified) || (requireLocalEmailVerified && !dbUser.user.emailVerified) || accountLinking.enabled === false || accountLinking.disableImplicitLinking === true`; `requireLocalEmailVerified` defaults to `true` (post-CVE-2026-53516). Providers in `trustedProviders` skip the provider-side `emailVerified` check. `allowDifferentEmails` permits manual links across differing emails. — [better-auth 1.7.25 source](https://registry.npmjs.org/better-auth/-/better-auth-1.7.25.tgz) (`dist/oauth2/link-account.mjs`)

### Inferences
**Patterns likely in AI-generated code** (inferred from the defaults above and the CVE descriptions; not measured):
1. `MicrosoftEntraID({ clientId, clientSecret })` with no issuer, which means multi-tenant plus personal accounts.
2. Hitting `OAuthAccountNotLinked` and "fixing" it with `allowDangerousEmailAccountLinking: true` on every provider, including Entra or a generic OIDC provider.
3. Custom `signIn`/`jwt` callbacks or API routes doing `prisma.user.findUnique({ where: { email: profile.email } })` or `upsert` by email. This bypasses Auth.js's safe default even with the flag off.
4. JWT-session apps reading `session.user.email` as the user's key in queries. Supabase RLS policies of the form `auth.jwt() ->> 'email' = owner_email` instead of `auth.uid() = owner_id`.
5. "Org" features (invitations, domain-based auto-join) matching `user.email` strings or `email.endsWith("@corp.com")`. This is the better-auth CVE-2026-53514 shape and the Google `hd` mistake.
6. Adding Entra or generic OIDC to a "trusted providers" list (better-auth `trustedProviders`, or similar in other libraries) to silence linking errors.
7. Email sign-up without mandatory verification, plus automatic linking: the classic-federated-merge precondition.

**Broker vs developer:**
- The broker owns token verification, provider-side `email_verified` normalization, and its own link policy (Supabase removes unconfirmed identities; Clerk forces verification or password change; Firebase drops untrusted credentials).
- The developer owns: (a) which tenants/issuers are accepted (Entra single-tenant vs `common`; Supabase "Azure Tenant URL"); (b) Entra app-registration settings (`xms_edov`, `removeUnverifiedEmailClaim`); (c) never keying app data or RLS on email; (d) invitation and domain-join logic; (e) not enabling dangerous linking flags; (f) requiring email verification at sign-up; (g) any custom linking code outside the broker.

### Gaps
- WorkOS docs were unreachable. I could not confirm WorkOS AuthKit's linking behavior or its SSO domain-verification semantics. The WorkOS blog post "Stop using email as a primary key" surfaced in search but was not read.
- Official Firebase documentation for "trusted providers" and the multiple-accounts setting could not be fetched; the Firebase findings rest on a Google Group reply and a Stack Overflow answer.
- I did not verify what Supabase does when `xms_edov` is absent or false.

## N4. nOAuth: how can a developer safely test their own app?

### Takeaway
Use only identities you own. Create a test Entra tenant (or a second test Google or OIDC account) and a test user whose email matches another test account in your app. Check whether signing in links, merges or switches accounts. Pair this with a code and schema audit for email-keyed lookups and an ID-token inspection for `iss`, `tid`, `oid`, `sub`, `email`, `xms_edov` and `email_verified`.

### Cited Findings
- The attack needs only an attacker-controlled tenant and a target email. The same setup with your own tenant and your own second test account reproduces the precondition without touching third parties. — [Semperis](https://www.semperis.com/blog/noauth-abuse-alert-full-account-takeover/) (search excerpt)
- `xms_edov` is returned only when `email` is present, and SAML/WS-Fed and Facebook accounts never have verified domains, so its absence is meaningful. — [Entra optional claims reference](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/optional-claims-reference.md)
- Pre-account tests follow the paper's attacker model: classic sign-up with an email, followed by federated sign-up with the same email. — [USENIX 2022](https://www.usenix.org/conference/usenixsecurity22/presentation/sudhodanan)

### Inferences
**Test plan (staging; your accounts only):**
1. **Static audit.** Grep auth callbacks, API routes and SQL/RLS for `where: { email`, `findBy(email`, `getUserByEmail`, `->> 'email'`, `.email ==`, `endsWith("@`, `allowDangerousEmailAccountLinking`, `trustedProviders`, `upn`, `preferred_username`. Check the users/identities schema: there should be a unique index on `(provider, provider_account_id)` or `(iss, sub)`, and email should be non-unique or merely informational.
2. **Token inspection.** Sign in with your own Entra user, decode the ID token (locally, not on a third-party site), and record `iss`, `tid`, `oid`, `sub`, `email`, `xms_edov`, `preferred_username`. Confirm your stored key is `tid+oid` or `iss+sub`.
3. **Cross-tenant nOAuth test.** In your app, create account A with an address you control (e.g., `qa-a@yourdomain.test`). In a separate test Entra tenant you own, where `yourdomain.test` is **not** a verified domain, create a user and set its mail attribute to `qa-a@yourdomain.test`. Sign into your app with that user. **Pass:** a new, separate account is created, or the login is rejected. **Fail:** you land in account A.
4. **Pre-account test.** Register via email and password as `qa-b@…` without completing verification. Then sign in via Google or Entra with a real `qa-b@…` identity you own. **Pass:** linking is refused or requires verification of the existing account, and the old password no longer grants access (Clerk-style) or is removed (Firebase-style). **Fail:** both the password and the OAuth identity open the same account.
5. **Email-change test.** Change the email on your IdP test user. **Pass:** the same app account is reached (keyed on `oid`/`sub`), and no other account becomes reachable.
6. **Invitation test.** Invite `qa-c@…` to an org; sign up unverified as `qa-c@…` from another browser; try to accept. **Pass:** acceptance requires a verified email.

### Gaps
- I did not verify the current availability and terms of free Microsoft 365 developer tenants versus a plain free Entra tenant for this kind of testing.

## N5. nOAuth: what is the correct fix (TypeScript/Node first, then Python), the checklist, and the defense in depth?

### Takeaway
Key every federated identity on the issuer plus the immutable subject: `(iss, sub)` generally, `(tid, oid)` for Entra. Validate the token's issuer against the tenant you expect. Restrict which tenants can sign in. Treat email as a display or contact attribute. Never auto-link by email. If you must link, do it only when the user is already signed in, or when both the IdP and your local record prove verification. In Entra, also request `xms_edov` and set `removeUnverifiedEmailClaim`.

### Cited Findings
- Entra multi-tenant issuer validation: "Instead of expecting the issuer claim in the token to exactly match the issuer value from metadata, the application should replace the `{tenantid}` value in the issuer metadata with the tenant ID that is the target of the current request, and then check the exact match (`tid` claim of the token)." — [Entra access tokens doc](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/access-tokens.md)
- "Always check that the `tid` in a token matches the tenant ID used to store data… Never allow data in one tenant to be accessed from another tenant… by only checking the tenant ID and the presence of an `oid` claim, your API could inadvertently authorize all service principals in that tenant." — [Entra claims validation](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/claims-validation.md)
- Use `sub` or `oid` (+`tid`) as keys; never `email`, `upn`, `preferred_username`. — [Entra ID token claims reference](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/id-token-claims-reference.md)
- `removeUnverifiedEmailClaim` on the application's `authenticationBehaviors` (Graph). — [Graph resource doc](https://github.com/microsoftgraph/microsoft-graph-docs-contrib/blob/main/api-reference/v1.0/resources/authenticationbehaviors.md)
- Google: use `hd` for Workspace-domain restriction; verify `aud`, `exp`, `iss` and signature with the client library, then check `hd`. — [Google backend-auth](https://developers.google.com/identity/sign-in/web/backend-auth) (search excerpt)
- Auth.js: keep linking off; "require the user to sign in *then* link accounts". — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz). Supabase: manual `linkIdentity()` while signed in. — [Supabase docs](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/auth/auth-identity-linking.mdx)
- better-auth: upgrade to ≥1.6.11 (CVE-2026-53516/53514); keep `requireLocalEmailVerified` (default `true`); options `disableImplicitLinking`, `trustedProviders`. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/better-auth/CVE-2026-53516.yml), [better-auth 1.7.25 source](https://registry.npmjs.org/better-auth/-/better-auth-1.7.25.tgz)
- Current library versions (registries, 2026-11-17): `jose` 6.2.17, `openid-client` 6.9.0, `next-auth` 4.24.15 (v5 beta 5.0.0-beta.32), `@auth/core` 0.41.3, `better-auth` 1.7.25; PyPI `PyJWT` 2.15.1, `Authlib` 1.9.8, `msal` 1.39.0. — [npm registry](https://registry.npmjs.org/jose), [PyPI](https://pypi.org/pypi/PyJWT/json)

### Inferences
**Synthesized fix: Auth.js (next-auth v5 / @auth/core ≥0.41.3)**
```ts
// auth.ts
import NextAuth from "next-auth";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import Google from "next-auth/providers/google";

const ALLOWED_TENANTS = new Set([process.env.ENTRA_TENANT_ID!]); // or a DB-backed allowlist of onboarded customer tenants

export const { handlers, auth } = NextAuth({
  adapter,                                   // DB adapter: Account rows keyed (provider, providerAccountId=sub)
  providers: [
    MicrosoftEntraID({
      clientId: process.env.AUTH_MICROSOFT_ENTRA_ID_ID!,
      clientSecret: process.env.AUTH_MICROSOFT_ENTRA_ID_SECRET!,
      issuer: `https://login.microsoftonline.com/${process.env.ENTRA_TENANT_ID}/v2.0/`, // single-tenant: not "common"
      // NO allowDangerousEmailAccountLinking
    }),
    Google({ /* NO allowDangerousEmailAccountLinking */ }),
  ],
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider === "microsoft-entra-id") {
        const tid = (profile as any)?.tid;
        if (!tid || !ALLOWED_TENANTS.has(tid)) return false;     // tenant allowlist (multi-tenant apps)
      }
      if (account?.provider === "google" && process.env.GOOGLE_WORKSPACE_DOMAIN) {
        if ((profile as any)?.hd !== process.env.GOOGLE_WORKSPACE_DOMAIN) return false; // hd, not email suffix
      }
      return true;
    },
    async jwt({ token, account, profile }) {
      if (account) {                                // first sign-in of this session
        token.iss = (profile as any)?.iss;
        token.tid = (profile as any)?.tid;
        token.oid = (profile as any)?.oid;
      }
      return token;                                 // token.sub = app user id; never look users up by token.email
    },
    async session({ session, token }) {
      session.user.id = token.sub!;                 // expose the stable id; app code keys on session.user.id
      return session;
    },
  },
});
```
- Database rule: `UNIQUE(provider, provider_account_id)` on accounts (the Auth.js adapter default); app tables reference `user_id`; any `email` column is non-unique and informational. Supabase RLS: `using (auth.uid() = owner_id)`, never `auth.jwt() ->> 'email'`.

**Synthesized fix: hand-rolled OIDC verification in Node with `jose` 6.x** (for apps not using a framework):
```ts
import { createRemoteJWKSet, jwtVerify } from "jose";
const JWKS = createRemoteJWKSet(new URL("https://login.microsoftonline.com/common/discovery/v2.0/keys"));

export async function verifyEntraIdToken(idToken: string, expectedNonce: string) {
  const { payload } = await jwtVerify(idToken, JWKS, {
    audience: process.env.ENTRA_CLIENT_ID,
    algorithms: ["RS256"],
  });
  const tid = String(payload.tid ?? "");
  if (!ALLOWED_TENANTS.has(tid)) throw new Error("tenant not allowed");
  if (payload.iss !== `https://login.microsoftonline.com/${tid}/v2.0`) throw new Error("bad issuer"); // {tenantid} substitution rule
  if (payload.nonce !== expectedNonce) throw new Error("bad nonce");
  return { key: `${tid}:${payload.oid}`, email: payload.email ?? null, emailDomainVerified: payload.xms_edov === true };
}
```

**Synthesized fix: Python with `PyJWT` 2.x**
```python
import jwt  # PyJWT
jwks = jwt.PyJWKClient("https://login.microsoftonline.com/common/discovery/v2.0/keys")

def verify_entra_id_token(id_token: str, client_id: str, allowed_tenants: set[str], nonce: str):
    key = jwks.get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=client_id,
                        options={"require": ["exp", "iat", "iss", "aud", "sub", "tid", "oid"]})
    tid = claims["tid"]
    if tid not in allowed_tenants:
        raise PermissionError("tenant not allowed")
    if claims["iss"] != f"https://login.microsoftonline.com/{tid}/v2.0":
        raise PermissionError("bad issuer")
    if claims.get("nonce") != nonce:
        raise PermissionError("bad nonce")
    return (tid, claims["oid"])          # identity key; claims.get("email") is display-only

# Generic OIDC (Google, Okta, ...): key = (claims["iss"], claims["sub"]).
# Google Workspace restriction: claims.get("hd") == "corp.example" (not email.endswith).
```
- Authlib's `OAuth.register(..., server_metadata_url=...)` and `msal`'s `ConfidentialClientApplication` handle the protocol flow. The identity-keying rule is the same.

**Entra app-registration settings (owner-side config):**
- Single-tenant unless the product is truly multi-tenant. If multi-tenant, keep a `tid` allowlist populated at customer onboarding.
- Add optional claim `xms_edov` (ID token) if email is used for anything beyond display.
- Set `authenticationBehaviors.removeUnverifiedEmailClaim = true` (Graph `PATCH /applications/{id}`, per [Microsoft Graph authenticationBehaviors how-to](https://learn.microsoft.com/graph/applications-authenticationbehaviors)).

**Checklist:**
1. Identity key = `(iss, sub)`; for Entra `(tid, oid)` (or `sub` per-app). Unique index; email not unique and not a key.
2. Validate signature (JWKS), `aud`, `exp`/`iat`, exact `iss` (with Entra `{tenantid}` substitution), `nonce`, `state`, PKCE.
3. Tenant restriction: single-tenant issuer or `tid` allowlist. Reject the MSA consumer tenant `9188040d-…` unless consumer accounts are intended.
4. No automatic link-by-email. Linking only (a) while the user is signed in to the existing account, or (b) after an emailed verification challenge to the existing account's address. Never because the incoming token "says verified."
5. If any email trust is required: Google `email_verified === true` (plus `hd` for Workspace); Entra `xms_edov === true` (absent means unverified); local record `emailVerified === true` too (better-auth CVE-2026-53516).
6. Email verification mandatory at sign-up before features or invitations (pre-account class; better-auth CVE-2026-53514).
7. Authorization (RLS, ownership checks, invitations, domain auto-join) keyed on user ID, tenant ID and SSO connection ID, never on email strings or suffixes.
8. Library flags: Auth.js `allowDangerousEmailAccountLinking` absent; better-auth ≥1.6.11 with `requireLocalEmailVerified` left `true`, no Entra/generic OIDC in `trustedProviders` (consider `disableImplicitLinking: true`); next-auth ≥4.24.15 / @auth/core ≥0.41.3 for the 2025–2026 email-handling advisories.
9. Canonicalize emails (Unicode normalization, lowercase) before validation and comparison (GHSA-7rqj class), and still treat them only as contact data.
10. Migration for already email-keyed users: on next login, attach `(iss, sub)`/`(tid, oid)` to the existing row only if the email is verified (`xms_edov`/`email_verified`) and the account's prior identity source matches. Otherwise force re-verification. After migration, look up only by the immutable key.

**Defense in depth:** notify users by email when a new sign-in method is linked; require re-authentication with an existing factor before linking; alert on logins where `tid` differs from the tenant that created the account; log `iss/tid/oid/sub` for every federated login; put admin roles behind step-up auth.

### Gaps
- I did not verify that the Auth.js v5 Entra profile object exposes `tid`/`oid` unchanged in the `signIn`/`jwt` callbacks. It is the raw ID-token claims in Auth.js's design, but this was not tested here.
- The exact Graph HTTP request body for `removeUnverifiedEmailClaim` comes from the how-to page title and snippets; the full page was not retrieved.

## N6. nOAuth: which fixes are commonly incorrect or incomplete, and why?

### Takeaway
Most broken fixes replace one mutable or forgeable attribute with another, or check verification on only one side. Some depend on Microsoft-side defaults that do not cover legacy registrations or all account types.

### Cited Findings
- **Switching from `email` to `upn`/`preferred_username`:** Microsoft says `upn` "often changes over the lifetime of a user principal", and `preferred_username` is mutable and "can't be used to make authorization decisions." — [Entra claims validation](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/claims-validation.md), [Entra ID token claims](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/id-token-claims-reference.md)
- **Checking `email_verified` on Entra:** Entra does not send `email_verified`. Projects in October 2026 were still adding `xms_edov` or `tid/oid` handling because of this. — [GitHub issue (search result)](https://github.com/peterrichards-lr/mcp_agent_mail/issues/18)
- **Checking only the provider's verification flag:** better-auth's pre-1.6.11 gate trusted `email_verified: true` from the provider without requiring the local row to be verified, which is CVE-2026-53516. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/better-auth/CVE-2026-53516.yml)
- **Email-suffix domain checks:** Google says the email domain is insufficient; use `hd`. — [Google backend-auth](https://developers.google.com/identity/sign-in/web/backend-auth) (search excerpt)
- **Relying on `xms_edov` alone:** it only says the domain owner verified the domain in the user's home tenant. It is absent for Facebook and SAML/WS-Fed accounts. The `email` claim stays "mutable over time" and can be reassigned within the legitimate domain. — [Entra optional claims reference](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/optional-claims-reference.md)
- **Relying on Microsoft's post-June-2023 default:** Semperis found vulnerable gallery apps two years later and says vendors, not customers, must fix them. — [Semperis](https://www.semperis.com/blog/noauth-abuse-alert-full-account-takeover/) (search excerpt)
- **Checking only `tid` plus presence of `oid`:** this "could inadvertently authorize all service principals in that tenant." — [Entra claims validation](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/claims-validation.md)
- **Relying on `idp` to correlate users across tenants:** "It doesn't work." — [Entra ID token claims](https://github.com/MicrosoftDocs/entra-docs/blob/main/docs/identity-platform/id-token-claims-reference.md)

### Inferences
- **Switching Entra from `common` to `organizations`** removes personal Microsoft accounts but not attacker-controlled work tenants, so nOAuth is unaffected.
- **Leaving Auth.js's linking flag off but doing an email lookup in a custom callback** reintroduces the bug behind the framework's back.
- **Lowercasing or trimming emails before keying** fixes duplicate-account bugs, not takeover. An attacker-asserted email normalizes the same way.
- **Restricting to "verified" providers via a static `trustedProviders` list** encodes a trust assumption about the IdP (e.g., "Microsoft verifies emails") that Microsoft's own docs reject.
- **Fixing nOAuth for new sign-ups only:** existing rows keyed by email remain reachable until migrated (checklist item 10 in N5).

### Gaps
- I found no public, reproducible case where `xms_edov === true` was spoofed. The limitation above is from the claim's documented semantics, not from an observed bypass.

## N7. nOAuth: how does a developer verify the fix, with a test that fails before and passes after?

### Takeaway
Write integration tests against a local OIDC issuer (test keys you generate) that mints tokens with chosen `iss`/`tid`/`oid`/`sub`/`email` claims. Assert that identity resolution depends only on the immutable key. The cross-tenant-same-email test is the canonical one: it fails on an email-keyed implementation and passes once keying is fixed. Add the cross-tenant test from N4 as a manual staging check.

### Cited Findings
- The vulnerable behavior is defined precisely by better-auth's advisory: "the victim's later OAuth identity bound to the attacker's user row, granting both a password login and the victim's OAuth identity on the same account." That gives an exact assertion target. — [GitLab record](https://gitlab.com/gitlab-org/security-products/gemnasium-db/-/blob/master/npm/better-auth/CVE-2026-53516.yml)
- Auth.js's safe default throws `OAuthAccountNotLinked` when an email-matching user exists, which gives a deterministic error to assert. — [@auth/core 0.41.3 source](https://registry.npmjs.org/@auth/core/-/core-0.41.3.tgz)

### Inferences
**Integration tests (local issuer with JWKS you control; `jose` `SignJWT` in Node or PyJWT in Python):**
| # | Setup | Token presented | Before (email-keyed) | After |
|---|---|---|---|---|
| 1 | none | iss=T1, oid=U1, email=a@x.test | creates account A | creates account A, key (T1,U1) |
| 2 | account A exists | **iss=T2**, oid=U9, email=a@x.test, xms_edov absent | **logs into A** | separate account or rejected (tenant not allowed); never A |
| 3 | account A exists | iss=T1, oid=U2, email=a@x.test | logs into A | separate account (same tenant, different object) |
| 4 | account A exists | iss=T1, oid=U1, email=changed@x.test | new account | logs into A (email change does not split identity) |
| 5 | password sign-up a2@x.test, unverified | Google-like token email=a2@x.test, email_verified=true | linked; password still works | link refused, or requires verifying the existing account and invalidates the old password |
| 6 | org invite to c@x.test; attacker signed up c@x.test unverified | attacker session | invite accepted | rejected until email verified |
| 7 | any | token with iss=`.../common/v2.0` or tid not in allowlist | accepted | rejected |
| 8 | any | email with homoglyph `@` (magic-link flow) | link sent elsewhere | rejected/normalized (next-auth ≥4.24.15) |
- Static regression guards: a lint or CI grep that fails on `allowDangerousEmailAccountLinking`, on `where: { email` inside auth code paths, and on RLS policies containing `->> 'email'`. A schema test asserts there is no unique constraint used as an identity key on `users.email`, and that one exists on `(provider, provider_account_id)`.
- Dependency gate: fail if better-auth < 1.6.11, next-auth < 4.24.15 (v4) / < 5.0.0-beta.32 (v5), or @auth/core < 0.41.3 resolves.

### Gaps
- No vendor-provided conformance test exists for "nOAuth-safe" identity keying. The OpenID Foundation RP certification suite tests protocol conformance, but I found no evidence it tests account-linking policy (not verified).
