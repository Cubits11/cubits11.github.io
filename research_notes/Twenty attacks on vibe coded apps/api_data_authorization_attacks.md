# API and data-authorization attacks on vibe-coded apps: (5) GraphQL alias abuse, (12) Postgres views bypassing RLS, (19) WebSocket hijacking

Research date: 2026-11-17. Scope: mechanism, incidents and CVEs (2024 to 2026 plus labelled history), why AI-generated apps are prone, safe self-testing, fixes, wrong fixes, and verification.

Method note for the report writer: this session's network allowed GitHub, the npm registry and web search only. supabase.com, postgresql.org, escape.tech, apollographql.com, socket.io, portswigger.net, nvd.nist.gov and rfc-editor.org could not be fetched directly. I read the primary documentation from the projects' own source repositories on GitHub instead:
- PostgreSQL doc SGML from `postgres/postgres` master
- Supabase docs MDX from `supabase/supabase` master
- splinter's `splinter.sql`
- graphql-armor plugin sources and changelogs
- Apollo Server docs from `apollographql/apollo-server`
- Socket.IO docs from `socketio/socket.io-website`
- `ws` docs, the OWASP Cheat Sheet Series, Hasura docs and GraphQL Yoga docs

Advisories come from github.com/advisories pages. Package versions and dates come from registry.npmjs.org on 2026-11-17. Where I could only see search-result summaries of secondary sources, the finding says so. Below, "[docs src]" means the doc's source file in its GitHub repo, and that file is what I actually read.

---

## (5) GraphQL alias abuse: how aliases, batching and related request-shape tricks defeat per-request rate limits and amplify cost, and what fixes it

### Takeaway
A GraphQL alias lets one operation request the same field, including a mutation such as `login` or `verifyOtp`, many times with different arguments. A rate limiter that counts HTTP requests therefore counts one request while the server runs N resolver calls. That gives brute force (login, 2FA/OTP, coupon or reset codes) and cost amplification. The 2024 to 2026 CVE record shows two recurring failures: servers with no cost or alias limits (Directus, 2026), and limiters that are bypassed by fragments or name tricks (strawberry-graphql CVE-2026-47707, graphql-armor GHSA-733v-p3h5-qpq7 and the max-depth fragment-cache fix). A correct fix counts attempts where the business logic runs (per account or code), not per HTTP request. It then adds alias, depth, cost, token and directive limits, keeps HTTP batching off, and uses trusted documents (persisted-operation allowlists) where the client is first-party. Disabling introspection is defense in depth only.

### Cited Findings

#### (a) Mechanism, preconditions, impact
- PortSwigger's Web Security Academy has a dedicated lab, "Bypassing GraphQL brute force protections". The site rate-limits login requests, and the intended solution sends many aliased login mutations in one HTTP request. Community write-ups explain why it works: GraphQL objects cannot contain multiple properties with the same name unless they are aliased, and rate limiting typically counts HTTP requests, not GraphQL operations — [PortSwigger lab](https://portswigger.net/web-security/graphql/lab-graphql-brute-force-protection-bypass); [write-up](https://siunam321.github.io/ctf/portswigger-labs/Testing-GraphQL-APIs/graphql-4) (lab page not fetched directly; summary via search).
- OWASP calls this class "Batching Attacks, a GraphQL-specific method of brute force attack". It covers both batching multiple queries in one network call (array batching) and batching requests for multiple object instances. OWASP lists the mitigations: object-request rate limiting in code, preventing batching for sensitive objects ("usernames, emails, passwords, OTPs, session tokens"), and limiting the number of queries that can run at once — [OWASP GraphQL Cheat Sheet, "Batching Attacks"](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html) ([src](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/GraphQL_Cheat_Sheet.md)).
- OWASP notes that query depth and per-object "amount" (e.g. `first: 99999999`) "can both be unlimited by default which may lead to a DoS". It recommends depth limiting, amount limiting, pagination, timeouts, query cost analysis and rate limiting per IP or user — [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html).
- graphql-cop, the standard misconfiguration scanner, enumerates the related request-shape classes as distinct checks:
  - Alias Overloading (DoS); it flags when "100+ aliases" are allowed
  - Batch Queries (DoS)
  - Directives Overloading (DoS), meaning duplicated directives
  - Circular Query using Introspection (DoS)
  - Field Suggestions (info leak)
  - Introspection (info leak)
  - GET-based queries, mutations over GET, and urlencoded POST (CSRF)
  - Trace Mode

  Source: [dolevf/graphql-cop README](https://github.com/dolevf/graphql-cop).
- Amplification without brute force (2026): Directus's `/graphql` and `/graphql/system` endpoints did not deduplicate resolver calls within a request. Aliases repeated an expensive relational query many times, with load growing "roughly linearly with the alias count". The existing token limit "still allowed enough aliases", the relational depth limit applied per alias without capping total executions, and rate limiting was disabled by default. Any authenticated user could cause CPU, memory and I/O exhaustion — [GHSA-ph52-67fq-75wj / CVE-2026-35441](https://github.com/advisories/GHSA-ph52-67fq-75wj).
- Unauthenticated variant (same release): aliases on Directus's health-check resolver re-ran its database, cache, storage-write and SMTP checks once per alias. This exhausted the DB connection pool and SMTP connections. CVSS 7.5, PR:N — [GHSA-6q22-g298-grjh](https://github.com/advisories/GHSA-6q22-g298-grjh).
- Fragment-based amplification at validation time: Apollo Server documents an opt-in `maxRecursiveSelections` rule. It "computes how many selections would be in the operation if its named fragment definitions were recursively inlined… and errors if the count exceeds 10,000,000". The default is `false` — [Apollo Server API reference](https://www.apollographql.com/docs/apollo-server/api/apollo-server) ([docs src](https://github.com/apollographql/apollo-server/blob/main/docs/source/api/apollo-server.mdx)).

#### (b) Incidents and CVEs (newest first; older items labelled)
- **CVE-2026-47707 / GHSA-fr49-mhgj-crfc (published 2026-06-04), strawberry-graphql (Python):** "Bypass of MaxAliasesLimiter via Fragment Spreads leading to GraphQL Alias Amplification". The built-in alias limiter did not count aliases reached through fragment spreads — [GitHub advisory listing](https://github.com/advisories?query=CVE-2026-47707). Affected 0.172.0 through 0.315.6, fixed in 0.315.7 per secondary summaries ([vuln.today](https://vuln.today/cve/CVE-2026-47707), [OffSeq](https://radar.offseq.com/threat/cve-2026-47707-cwe-400-uncontrolled-resource-consu-99a52225)); I did not see the version range on the GitHub page itself.
- **CVE-2026-35441 / GHSA-ph52-67fq-75wj (published 2026-04-02), Directus < 11.17.0, fixed 11.17.0:** authenticated alias amplification, CVSS 6.5. The fix adds request-scoped resolver deduplication: aliases calling the same resolver with identical arguments run once — [GHSA-ph52-67fq-75wj](https://github.com/advisories/GHSA-ph52-67fq-75wj).
- **GHSA-6q22-g298-grjh (2026-04-02), Directus < 11.17.0:** unauthenticated alias DoS of the health-check resolver, CVSS 7.5 — [GHSA-6q22-g298-grjh](https://github.com/advisories/GHSA-6q22-g298-grjh).
- **CVE-2026-1174, "birkir prime":** described as resource exhaustion in an alias handler, versions up to 0.4.0.beta.0 — search summary only, unverified ([SentinelOne listing](https://www.sentinelone.com/vulnerability-database/cve-2026-1174/)).
- **CVE-2025-12562, GitLab CE/EE:** unauthenticated bypass of GraphQL query-complexity limits, fixed in 18.4.6, 18.5.4 and 18.6.2. Not shown to be alias-specific — secondary summary ([SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2025-12562/)).
- **graphql-armor max-depth 2.4.2 (npm, 2025-08-22):** the changelog lists "fix: max-depth bypass using fragment cache" and "fix: max-depth ignore only Field Node named `__schema`". I found no GHSA for these — [max-depth CHANGELOG](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-depth/CHANGELOG.md); release date from [npm registry](https://registry.npmjs.org/@escape.tech/graphql-armor-max-depth).
- **GHSA-733v-p3h5-qpq7 (2025-04-25), `@escape.tech/graphql-armor-cost-limit` < 2.4.2, fixed 2.4.2, no CVE, CVSS 5.3:** with `ignoreIntrospection` enabled (the default), any node named `__schema` was costed at 0 without checking the node kind. Naming the operation or a fragment `__schema` therefore zeroed the cost of the real fields. The fix restricts this to `Kind.FIELD`. The interim mitigation was `ignoreIntrospection: false` — [GHSA-733v-p3h5-qpq7](https://github.com/advisories/GHSA-733v-p3h5-qpq7).
- **CVE-2025-31496, apollo-compiler (Rust) < 1.27.0:** exponential resource use validating deeply nested named fragments. This is fragment-based, not alias-based — search summary ([SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2025-31496/)).
- **Historical:** the PortSwigger alias brute-force lab and OWASP's "batching attack" guidance (citing Wallarm's write-up) predate 2024 and remain the canonical teaching examples — [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html).

#### (c) Why AI-generated / vibe-coded apps are prone, and platform defaults vs developer duties

**Apollo Server.** `@apollo/server` 5.5.2 was latest on 2026-11-11, and 5.0.0 shipped 2025-07-17 ([npm](https://registry.npmjs.org/@apollo/server)). Defaults ([API reference docs src](https://github.com/apollographql/apollo-server/blob/main/docs/source/api/apollo-server.mdx); [requests doc](https://github.com/apollographql/apollo-server/blob/main/docs/source/workflow/requests.md)):
- `allowBatchedHttpRequests` defaults to `false`. An array body errors with "Operation batching disabled".
- `introspection` defaults to `true` unless `NODE_ENV` is `production`.
- `maxRecursiveSelections` defaults to `false`.
- There is no built-in alias, depth or cost limit.
- CSRF prevention is on by default since AS4: GET or multipart requests need a non-empty `Apollo-Require-Preflight` or `X-Apollo-Operation-Name` header, or a non-simple content type. Apollo warns not to disable it ([CORS/CSRF doc src](https://github.com/apollographql/apollo-server/blob/main/docs/source/security/cors.mdx)).

**GraphQL Yoga.** Batching is disabled by default. When `batching: true` is set, "by default up to 10 GraphQL requests are allowed within a single HTTP request", configurable with `batching: { limit: n }`. Persisted operations are an opt-in plugin, and arbitrary operations are allowed alongside only via `allowArbitraryOperations` ([Yoga request-batching doc src](https://github.com/dotansimha/graphql-yoga/blob/main/website/content/docs/features/request-batching.mdx); [persisted-operations doc src](https://github.com/dotansimha/graphql-yoga/blob/main/website/content/docs/features/persisted-operations.mdx)). graphql-yoga 6.0.0 shipped 2026-10-22 and 6.1.0 on 2026-11-12 ([npm](https://registry.npmjs.org/graphql-yoga)).

**Hasura.**
- The allow list (`HASURA_GRAPHQL_ENABLE_ALLOWLIST` / `--enable-allowlist`) defaults to `false`, and allow-list validation "will not be enforced for the `admin` role" ([Hasura allow-list doc src](https://github.com/hasura/graphql-engine/blob/master/docs/docs/security/allow-list.mdx)).
- Per-role API limits (rate, depth, and others) are labelled "Cloud & Enterprise Edition". Enterprise rate limiting requires `HASURA_GRAPHQL_RATE_LIMIT_REDIS_URL` ([api-limits doc src](https://github.com/hasura/graphql-engine/blob/master/docs/docs/security/api-limits.mdx)).
- Per-role introspection disabling is "Cloud Professional & Enterprise Edition" ([introspection doc src](https://github.com/hasura/graphql-engine/blob/master/docs/docs/security/disable-graphql-introspection.mdx)).

**Supabase pg_graphql.**
- pg_graphql "fully respects builtin PostgreSQL role and row security". Revoking `SELECT` removes types and fields from the schema ([pg_graphql security doc](https://github.com/supabase/pg_graphql/blob/master/docs/security.md)).
- Since pg_graphql 1.6.0 (breaking change), "GraphQL introspection is now disabled by default", with opt-in per schema via `comment on schema … '@graphql({"introspection": true})'`. The docs stress that "Disabling introspection does not restrict actual queries or mutations" ([changelog](https://github.com/supabase/pg_graphql/blob/master/docs/changelog.md); [security.md](https://github.com/supabase/pg_graphql/blob/master/docs/security.md)).
- The default page size is 30 rows (`max_rows`) ([configuration.md](https://github.com/supabase/pg_graphql/blob/master/docs/configuration.md)).
- Supabase announced that pg_graphql stops being enabled by default for new projects from 2026-05-18 ([Supabase discussion #45329](https://github.com/orgs/supabase/discussions/45329)).
- splinter has lints for GraphQL exposure: `pg_graphql_anon_table_exposed` (0026) and `pg_graphql_authenticated_table_exposed` (0027) ([splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql)).

**Limiter libraries.**
- `graphql-depth-limit`'s latest npm release is 1.1.0 from 2017-08-09 ([npm](https://registry.npmjs.org/graphql-depth-limit)).
- `graphql-query-complexity` 2.0.0 shipped 2026-07-23 and exposes `createComplexityRule({ maximumComplexity, variables, operationName, maxQueryNodes /* default 10_000 */, estimators, onComplete, createError })` ([npm readme](https://registry.npmjs.org/graphql-query-complexity)).

**Platform vs developer.** The server frameworks enforce only what they default on: Apollo's no-batching and CSRF prevention, Yoga's no-batching, and pg_graphql's RLS, privileges and introspection-off. The application developer owns:
- alias, depth, cost, token and directive limits
- per-account and per-operation attempt limits on sensitive mutations
- the trusted-document allowlist
- `NODE_ENV=production`, so that Apollo actually turns introspection off

On Hasura Community Edition, the developer must also supply limits outside Hasura or adopt the allow list, because API limits are Cloud/EE features (docs above).

#### (d) Safely testing your own app (non-destructive)
- Run graphql-cop against your own staging endpoint. It reports alias overloading at 100+ aliases, array batching, introspection, field suggestions, directive overloading, the circular introspection query, and GET/urlencoded CSRF exposures — [graphql-cop README](https://github.com/dolevf/graphql-cop).
- InQL (Doyensec, Burp extension) is the common tool for schema analysis and for building batched or aliased requests in Burp Repeater. Community write-ups of the PortSwigger lab use it for exactly that — [InQL repo](https://github.com/doyensec/inql); [write-up](https://siunam321.github.io/ctf/portswigger-labs/Testing-GraphQL-APIs/graphql-4).
- Expected server responses to look for when a limit is in place:
  - Apollo array batching off: an error containing "Operation batching disabled" ([Apollo API ref src](https://github.com/apollographql/apollo-server/blob/main/docs/source/api/apollo-server.mdx)).
  - Yoga batching limit exceeded: "Batching is limited to N operations per request." ([Yoga doc src](https://github.com/dotansimha/graphql-yoga/blob/main/website/content/docs/features/request-batching.mdx)).
  - graphql-armor alias limit with `exposeLimits: true` (the default): "Aliases limit of N exceeded, found M." ([max-aliases source](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-aliases/src/index.ts)).
- graphql-armor's alias counter skips aliases of fields on its `allowList`, which defaults to `['__typename']`. A probe that aliases `__typename` will not trip the limit. Probe with a cheap real field you own, e.g. your own `me { id }` — [max-aliases source](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-aliases/src/index.ts).

#### (e) The fix (verified option names; code is illustrative and assembled from the cited docs)

**Version compatibility, checked on npm 2026-11-17:**
- `@escape.tech/graphql-armor` 3.2.0 (2025-12-29) declares peers `@apollo/server ^4.0.0 || ^5.0.0` and `@envelop/core ^5.0.0`, and a hard dependency on `graphql ^16.10.0`.
- `@apollo/server` 5.5.2 peers `graphql ^16.11.0`.
- graphql-yoga 6.1.0 depends on `@envelop/core ^6.0.1` and peers `graphql ^16 || ^17`.
- Armor therefore fits Apollo 4/5 on graphql 16. On Yoga 6 or graphql 17 it is outside its declared peer ranges.

Sources: [armor npm](https://registry.npmjs.org/@escape.tech/graphql-armor), [Apollo npm](https://registry.npmjs.org/@apollo/server), [Yoga npm](https://registry.npmjs.org/graphql-yoga).

**graphql-armor defaults, read from plugin sources:**

| Plugin | Package | Defaults |
|---|---|---|
| max-aliases | `@escape.tech/graphql-armor-max-aliases` 2.6.2 | `n: 15`, `allowList: ['__typename']`, `exposeLimits: true`, `propagateOnRejection: true` |
| max-depth | `@escape.tech/graphql-armor-max-depth` 2.4.2 | `n: 6`, `ignoreIntrospection: true`, `flattenFragments: false` |
| cost-limit | `@escape.tech/graphql-armor-cost-limit` 2.4.3 | `maxCost: 5000`, `objectCost: 2`, `scalarCost: 1`, `depthCostFactor: 1.5`, `ignoreIntrospection: true`, `flattenFragments: false` |
| max-directives | `@escape.tech/graphql-armor-max-directives` 2.3.1 | `n: 50` |
| max-tokens | `@escape.tech/graphql-armor-max-tokens` 2.5.1 | `n: 1000` |

The top-level config keys are `maxAliases`, `maxDepth`, `costLimit`, `maxDirectives`, `maxTokens` and `blockFieldSuggestion`. Each also accepts `enabled`, `onAccept`, `onReject` and `propagateOnRejection`. `ApolloArmor.protect()` returns `{ plugins, validationRules }`, and `EnvelopArmorPlugin(config)` is the Envelop/Yoga entry. Sources: [plugin sources](https://github.com/Escape-Technologies/graphql-armor/tree/main/packages/plugins), [types/src/index.ts](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/types/src/index.ts), [apollo/armor.ts](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/graphql-armor/src/apollo/armor.ts), [envelop/armor.ts](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/graphql-armor/src/envelop/armor.ts).

Apollo Server 5 hardening. Option names are from the Apollo API reference and the armor sources above:
```ts
import { ApolloServer } from '@apollo/server';            // 5.x
import { ApolloArmor } from '@escape.tech/graphql-armor';  // 3.2.0 (peer: @apollo/server ^4 || ^5)

const armor = new ApolloArmor({
  maxAliases:    { n: 5 },          // default 15; login-style mutations need far fewer
  maxDepth:      { n: 8 },          // default 6
  costLimit:     { maxCost: 3000 }, // default 5000; tune against real client operations
  maxDirectives: { n: 10 },         // default 50
  maxTokens:     { n: 1000 },       // default 1000
  blockFieldSuggestion: { enabled: true },
});
const { plugins, validationRules } = armor.protect();

const server = new ApolloServer({
  typeDefs,
  resolvers,
  plugins: [...plugins],
  validationRules: [...validationRules, sensitiveFieldsOncePerDocument], // custom rule below
  allowBatchedHttpRequests: false,  // documented default; keep it off
  maxRecursiveSelections: true,     // default false; caps fragment-inlined selections at 10,000,000
  introspection: process.env.NODE_ENV !== 'production', // same as default, but explicit
  // csrfPrevention is on by default since AS4: do not set it to false
});
```

GraphQL Yoga. Option names are from the Yoga docs. The armor plugin is commented out because of the Envelop major-version mismatch noted above:
```ts
import { createYoga } from 'graphql-yoga';
import { usePersistedOperations } from '@graphql-yoga/plugin-persisted-operations';
import { useDisableIntrospection } from '@graphql-yoga/plugin-disable-introspection';

const yoga = createYoga({
  schema,
  batching: false, // documented default
  plugins: [
    usePersistedOperations({
      getPersistedOperation: (hash) => trustedManifest[hash] ?? null, // build-time manifest
      // allowArbitraryOperations defaults to off; leave it off in production
    }),
    useDisableIntrospection(),
    // EnvelopArmorPlugin({ maxAliases: { n: 5 }, ... }) — check @envelop/core v6 compatibility first
  ],
});
```

Sensitive-mutation guard as a graphql-js validation rule. This is illustrative, not a published package. It walks fragment spreads and inline fragments, because that is exactly the path that the strawberry and armor bypasses used:
```ts
import { Kind, GraphQLError, type ASTVisitor, type SelectionSetNode, type ValidationContext } from 'graphql';
const ONCE = new Set(['login', 'verifyTwoFactor', 'redeemCode', 'requestPasswordReset']);

export function sensitiveFieldsOncePerDocument(ctx: ValidationContext): ASTVisitor {
  return {
    Document(doc) {
      let hits = 0;
      const seen = new Set<string>();
      const walk = (set: SelectionSetNode) => {
        for (const s of set.selections) {
          if (s.kind === Kind.FIELD) { if (ONCE.has(s.name.value)) hits++; }
          else if (s.kind === Kind.INLINE_FRAGMENT) walk(s.selectionSet);
          else if (s.kind === Kind.FRAGMENT_SPREAD && !seen.has(s.name.value)) {
            seen.add(s.name.value);
            const f = ctx.getFragment(s.name.value);
            if (f) walk(f.selectionSet);
          }
        }
      };
      for (const d of doc.definitions) if (d.kind === Kind.OPERATION_DEFINITION) walk(d.selectionSet);
      if (hits > 1) ctx.reportError(new GraphQLError('Sensitive operations must be sent one per request.'));
    },
  };
}
```

The per-account attempt counter is the control that actually stops brute force. Apply it inside the `login` and `verifyOtp` resolvers, keyed by target account or OTP challenge, not by IP or HTTP request. OWASP calls this "object request rate limiting in code" and "prevent batching for sensitive objects" — [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html).

Trusted documents:
- Apollo GraphOS Router "Safelisting with Persisted Queries" maintains "an allowlist of trusted operations and optionally require[s] clients to send operation IDs instead of full operation strings" ([router docs src](https://github.com/apollographql/router/blob/dev/docs/source/routing/security/persisted-queries.mdx)).
- Yoga's `usePersistedOperations` provides the same for Yoga ([Yoga doc src](https://github.com/dotansimha/graphql-yoga/blob/main/website/content/docs/features/persisted-operations.mdx)).
- Hasura CE has `HASURA_GRAPHQL_ENABLE_ALLOWLIST=true`, but the admin role is exempt ([Hasura doc src](https://github.com/hasura/graphql-engine/blob/master/docs/docs/security/allow-list.mdx)).

Introspection off in production is defense in depth only:
- Apollo: `introspection: false`, or `NODE_ENV=production`.
- Yoga: `useDisableIntrospection()`.
- pg_graphql: off by default since 1.6.0.
- Hasura: per-role, Cloud Pro/EE.

Sources: docs cited above; the [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html) says to consider disabling introspection for unauthenticated users but that security by obscurity is not recommended.

#### (f) Incorrect or incomplete fixes
- **Alias limiter that does not follow fragment spreads.** Strawberry's `MaxAliasesLimiter` was bypassed this way in 2026 (CVE-2026-47707) — [advisory listing](https://github.com/advisories?query=CVE-2026-47707). graphql-armor's changelogs show the same class fixed over time: "count field alias in fragment spreads" and "graceful handler for recursive fragments" in max-aliases, and "max-depth bypass using fragment cache" — [max-aliases CHANGELOG](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-aliases/CHANGELOG.md), [max-depth CHANGELOG](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-depth/CHANGELOG.md).
- **Exempting introspection by name.** The cost-limit plugin's `__schema` exemption let any operation or fragment named `__schema` cost 0 (GHSA-733v-p3h5-qpq7) — [advisory](https://github.com/advisories/GHSA-733v-p3h5-qpq7).
- **Token limit plus per-alias depth limit, without a cap on total resolver executions.** Directus had both and was still exploitable — [GHSA-ph52-67fq-75wj](https://github.com/advisories/GHSA-ph52-67fq-75wj).
- **Resolver deduplication as a brute-force fix.** Directus's fix deduplicates aliases only when arguments are *identical* ([GHSA-ph52-67fq-75wj](https://github.com/advisories/GHSA-ph52-67fq-75wj)). Brute force varies the argument (each password or OTP guess), so deduplication does not limit it. This is an inference from the advisory's stated fix scope.
- **Disabling introspection and calling it fixed.** pg_graphql states that disabling introspection "does not restrict actual queries or mutations" — [pg_graphql security.md](https://github.com/supabase/pg_graphql/blob/master/docs/security.md).
- **A depth limit alone.** Aliases add width, not depth. OWASP lists depth and amount limiting as separate controls — [OWASP GraphQL Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html). Also, `graphql-depth-limit` has not been released since 2017 — [npm](https://registry.npmjs.org/graphql-depth-limit).
- **Treating the default alias limit as safe for auth.** max-aliases defaults to `n: 15` ([source](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-aliases/src/index.ts)), so the default still allows 15 guesses per request. My inference: multiplied by any per-request rate limit, that is still an amplifier.

#### (g) Verifying the fix
- Unit or integration test with Apollo's `server.executeOperation`:
  1. Send a document with `maxAliases.n + 1` aliases of a cheap real field. Assert the response errors include "Aliases limit of".
  2. POST a JSON array of two operations. Assert "Operation batching disabled".
  3. With `NODE_ENV=production`, send `{ __schema { queryType { name } } }` and assert an error.

  Before the change, (1) succeeds. After it, (1) fails. Error strings are from the [armor source](https://github.com/Escape-Technologies/graphql-armor/blob/main/packages/plugins/max-aliases/src/index.ts) and the [Apollo docs](https://github.com/apollographql/apollo-server/blob/main/docs/source/api/apollo-server.mdx).
- Regression tests for the known bypass shapes:
  - the same aliases placed inside a named fragment and spread (CVE-2026-47707 shape)
  - the same expensive query with the operation named `__schema` (GHSA-733v shape)

  Both must be rejected — [CVE-2026-47707 listing](https://github.com/advisories?query=CVE-2026-47707); [GHSA-733v-p3h5-qpq7](https://github.com/advisories/GHSA-733v-p3h5-qpq7).
- Brute-force control test against a staging test account: send one request containing two `login` selections with wrong passwords. Assert either a validation rejection from the sensitive-field rule, or that the per-account failure counter increased by 2. Then confirm the account locks after the policy threshold regardless of how attempts are packed into requests. This test design is my inference from the OWASP guidance cited above.
- Re-run graphql-cop. "Alias Overloading with 100+ aliases" and "Batch Queries" should no longer be reported — [graphql-cop](https://github.com/dolevf/graphql-cop).

### Inferences
- Rough frequency of each layer:
  - Per-request rate limiting (express-rate-limit or a CDN rule on `/graphql`) is the limiter vibe-coded stacks most often already have.
  - Alias and cost limits are the layer they most often lack. Apollo ships none by default, and Hasura's limits are paid-tier.
  - Brute-force exposure is therefore likely whenever an app exposes `login`, `verifyOtp` or code-redemption mutations through GraphQL. The tests in (g) are cheap.
- Apollo turns introspection off only when `NODE_ENV=production`. A deploy that forgets that variable (common on hand-rolled containers) leaves introspection on, which makes alias targets easy to find. This is low severity alone, but it compounds the alias problem.
- On Supabase pg_graphql, the alias question reduces to cost: authorization is RLS. Aliases cannot read rows RLS hides, but they can multiply collection queries (30 rows each by default). Supabase's own rate limiting of `/graphql/v1` is not documented in what I read (see Gaps).
- The trusted-document approach removes the whole alias, batching and depth class for first-party clients, because unknown documents never execute. For public APIs it is not available, and cost analysis plus per-object limits are the fallback.

### Gaps
- I found no 2024 to 2026 public incident report of a production login or 2FA brute force via GraphQL aliases with a named victim. The evidence is labs, advisories for DoS, and the OWASP and PortSwigger guidance.
- The exact affected range for CVE-2026-47707 came from secondary pages, not the GitHub advisory body. CVE-2025-12562 and CVE-2026-1174 details are secondary.
- I could not confirm whether graphql-armor 3.2.0 works with graphql-yoga 6 (Envelop v6) or graphql 17. Its declared ranges suggest not without testing.
- Supabase's platform-level rate limits for the pg_graphql endpoint were not in the documents I could read.
- I did not verify `@envelop/rate-limiter`'s current API (v11.0.1, 2026-11-12 on npm). Its README was not retrievable, so I did not include code for it.
- Behaviour of Bolt, Replit and v0 GraphQL scaffolds was not researched; no primary data was found.

---

## (12) Postgres views bypassing RLS in Supabase/PostgREST apps, related RLS failure modes, and the incidents

### Takeaway
In PostgreSQL a view checks base-table permissions, and applies RLS, as the view owner unless `security_invoker = true` (PG15+). On Supabase, views are usually created by `postgres`, which has `BYPASSRLS`. A view over an RLS-protected table in an exposed schema therefore returns every row to `anon` or `authenticated` through the auto-generated REST and GraphQL APIs. Fix: `security_invoker = true`, or revoke the view from the client roles, or move it to an unexposed schema. Then run Supabase's splinter lints and pgTAP tests. The same "the API is the database" model produced the largest vibe-coding exposures of 2025 to 2026:
- Lovable CVE-2025-48757 (170 apps)
- Moltbook (Jan to Feb 2026)
- UpGuard's 16,326 readable Supabase databases (Sept 2026)

Supabase answered in 2026 by stopping automatic grants on new tables (new projects from 2026-05-30, all projects from 2026-10-30, new tables only).

### Cited Findings

#### (a) Mechanism (PostgreSQL semantics), preconditions, impact
- PostgreSQL CREATE VIEW: "By default, access to the underlying base relations referenced in the view is determined by the permissions of the view owner." With `security_invoker` set to true, access "is determined by the permissions of the user executing the query".
- On RLS, the same page says: "If any of the underlying base relations has row-level security enabled, then by default, the row-level security policies of the view owner are applied… However, if the view has security_invoker set to true, then the policies and permissions of the invoking user are used instead."
- The page also warns that a view with `security_invoker=false` "is not equivalent to a SECURITY DEFINER function and those concepts should not be confused". The option "can be changed on existing views using ALTER VIEW".

Source for these three bullets: [PostgreSQL CREATE VIEW](https://www.postgresql.org/docs/current/sql-createview.html) ([doc src](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_view.sgml)).
- PostgreSQL RLS: "Superusers and roles with the BYPASSRLS attribute always bypass the row security system… Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with ALTER TABLE … FORCE ROW LEVEL SECURITY." With RLS enabled and no policy, "a default-deny policy is used". TRUNCATE and REFERENCES are not subject to row security — [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) ([doc src](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ddl.sgml)).
- Supabase: "Views bypass RLS by default because they are usually created with the `postgres` user… A view over a protected table hands out every row its policies were meant to withhold." Its safe form is `create view … with(security_invoker = true)` on "Postgres 15 and above". On older versions, revoke from `anon`/`authenticated` or put the view in an unexposed schema — [Supabase RLS guide](https://supabase.com/docs/guides/database/postgres/row-level-security) ([docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx)).
  - Wording conflict: the same Supabase page says Postgres "automatically creates views with `security definer`". The PostgreSQL docs explicitly say owner-privilege views are not SECURITY DEFINER objects. The effect described is the same; the terminology is loose. Splinter's lint name `security_definer_view` uses the same loose term.
- Supabase also states that its `postgres` role has `bypassrls`: "On Supabase the owner is `postgres`, which has `bypassrls`" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx). Combined with the PG rule that BYPASSRLS roles "always bypass" RLS ([PG docs](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ddl.sgml)), `FORCE ROW LEVEL SECURITY` on the base table does not stop a postgres-owned, non-invoker view from leaking.
- Preconditions:
  - the view is in a schema exposed by PostgREST (`pgrst.db_schemas`, default `public`)
  - `anon` or `authenticated` holds `SELECT` on it

  This is exactly what splinter's `security_definer_view` lint checks (`has_table_privilege('anon'|'authenticated', …,'SELECT')` within `pgrst.db_schemas`) — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).
- Default grants make the precondition the norm on older projects. "On existing projects, a new table in `public` starts with every privilege already granted to all three roles… Adding policies doesn't take those grants back" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx); [Securing your API, Default privileges](https://supabase.com/docs/guides/api/securing-your-api) ([docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/api/securing-your-api.mdx)).
- Impact: unauthenticated or cross-tenant read of every row the view projects, through `/rest/v1/<view>` and pg_graphql. pg_graphql exposes views the role can `SELECT` ([pg_graphql security.md](https://github.com/supabase/pg_graphql/blob/master/docs/security.md)); see also splinter lint 0026, which covers "tables, views, materialized views, and foreign tables" ([splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql)).

Related RLS failure modes in the same family. Each has a lint or doc statement.

**Materialized views and foreign tables.** Neither is covered by RLS:
- `materialized_view_in_api` (0016, WARN)
- `foreign_table_in_api` (0017, WARN): "Foreign tables do not respect row level security policies"

Source: [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).

**Views over `auth.users`.** `auth_users_exposed` (0002, ERROR) "Detects if auth.users is exposed to anon or authenticated roles via a view or materialized view" — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).

**SECURITY DEFINER functions.**
- They run as the creator. Created by `postgres`, they have `bypassrls`.
- "Set `search_path = ''` on every `security definer` function and schema-qualify the names inside it. Without a pinned `search_path`, a caller can point an unqualified name at their own object and run it with the function owner's privileges."
- "A `security definer` function in an exposed schema is callable over the Data API with the creator's privileges. Never create one in a schema listed under 'Exposed schemas'."

Source: [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).

Matching lints:
- `function_search_path_mutable` (0011)
- `anon_security_definer_function_executable` (0028)
- `authenticated_security_definer_function_executable` (0029)
- `anon_dynamic_sql_function_executable` (0031) and `authenticated_dynamic_sql_function_executable` (0032), which are ERROR when SECURITY DEFINER with direct use

Source: [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql). New functions get `EXECUTE` through `PUBLIC` by default — [Securing your API](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/api/securing-your-api.mdx).

**`user_metadata` in policies.**
- `raw_user_meta_data` "can be updated by the authenticated user using the `supabase.auth.update()` function. It is not a good place to store authorization data". `raw_app_meta_data` "cannot be updated by the user" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- Lint `rls_references_user_metadata` (0015, ERROR): "`user_metadata` is editable by end users and should never be used in a security context" — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).
- JWT claims, including `app_metadata`, are stale until refresh — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).

**UPDATE without WITH CHECK (correction to a common claim).**
- PostgreSQL: "If only a USING clause is specified, then that clause will be used for both USING and WITH CHECK cases" — [CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html) ([doc src](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_policy.sgml)). Supabase says the same: "If no `with check` expression is defined, the `using` expression decides both" ([Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx)).
- So `for update using (auth.uid() = user_id)` alone does not let a user reassign `user_id` to someone else. The reassignment risk comes from:
  - an explicit permissive `with check (true)`, which lint `rls_policy_always_true` (remediation id `0024_permissive_rls_policy`, WARN) flags for UPDATE, DELETE and INSERT
  - an `INSERT … with check (true)`
  - a USING expression that does not constrain ownership

  Lint source: [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).
- Supabase recommends explicit `using` plus `with check` for clarity: the `with check` "stops a user from reassigning `user_id`" ([Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx)).
- UPDATE also needs a matching SELECT/ALL policy when the statement reads columns — [CREATE POLICY doc src](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_policy.sgml).

**Column-level escalation.** RLS is row-level. A user allowed to update their own `profiles` row can update every column the role has `UPDATE` on (e.g. `role`, `is_admin`, `plan`) unless column privileges restrict it. PostgreSQL supports `GRANT { SELECT | INSERT | UPDATE | REFERENCES } ( column_name [, ...] )` — [GRANT doc src](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/grant.sgml). This is my inference from the RLS and GRANT semantics.

**Other lints in the same family:**
- `rls_disabled_in_public` (0013, ERROR)
- `policy_exists_rls_disabled` (0007, ERROR)
- `rls_enabled_no_policy` (0008, INFO)
- `sensitive_columns_exposed` (0023, ERROR): PII, credential or financial columns exposed without RLS
- `public_bucket_allows_listing` (0025)
- `insecure_queue_exposed_in_api` (0019, ERROR)

Source: [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).

**Performance pattern.** Wrap helpers as `(select auth.uid())` so Postgres runs an `initPlan` and caches the result per statement instead of per row — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx). Lint `auth_rls_initplan` (0003, WARN) detects the unwrapped form — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).

#### Full current splinter lint list (read from splinter.sql, 2026-11-17)
Name (remediation id, level, category):
- unindexed_foreign_keys (0001, INFO, PERF)
- auth_users_exposed (0002, ERROR, SEC)
- auth_rls_initplan (0003, WARN, PERF)
- no_primary_key (0004, INFO, PERF)
- unused_index (0005, INFO, PERF)
- multiple_permissive_policies (0006, WARN, PERF)
- policy_exists_rls_disabled (0007, ERROR, SEC)
- rls_enabled_no_policy (0008, INFO, SEC)
- duplicate_index (0009, WARN, PERF)
- security_definer_view (0010, ERROR, SEC)
- function_search_path_mutable (0011, WARN, SEC)
- rls_disabled_in_public (0013, ERROR, SEC)
- extension_in_public (0014, WARN, SEC)
- rls_references_user_metadata (0015, ERROR, SEC)
- materialized_view_in_api (0016, WARN, SEC)
- foreign_table_in_api (0017, WARN, SEC)
- unsupported_reg_types (WARN, SEC)
- insecure_queue_exposed_in_api (0019, ERROR, SEC)
- table_bloat (0020, WARN, PERF)
- fkey_to_auth_unique (0021, ERROR, SEC)
- extension_versions_outdated (0022, WARN, SEC)
- sensitive_columns_exposed (0023, ERROR, SEC)
- rls_policy_always_true (0024_permissive_rls_policy, WARN, SEC)
- public_bucket_allows_listing (0025, WARN, SEC)
- pg_graphql_anon_table_exposed (0026, WARN, SEC)
- pg_graphql_authenticated_table_exposed (0027, WARN, SEC)
- anon_security_definer_function_executable (0028, WARN, SEC)
- authenticated_security_definer_function_executable (0029, WARN, SEC)
- autovacuum_disabled (0030, INFO, PERF)
- anon_dynamic_sql_function_executable (0031, WARN or ERROR, SEC)
- authenticated_dynamic_sql_function_executable (0032, WARN or ERROR, SEC)

Remediation pages follow `https://supabase.com/docs/guides/database/database-linter?lint=<id>`. Source: [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql). Splinter's README states that `splinter.sql` at the repo root runs all lints in one query, that API-exposure lints read `pgrst.db_schemas` (defaulting to `public` in plain psql), and that Supabase production consumes the query via `lint-query.ts` in `supabase/supabase` — [splinter README](https://github.com/supabase/splinter).

#### (b) Incidents (2025 to 2026) and the platform response
- **Lovable, CVE-2025-48757.**
  - NVD text: "An insufficient database Row-Level Security (RLS) policy in Lovable through 2025-04-15 allows remote unauthenticated attackers to read or write to arbitrary database tables of generated sites". CWE-863; CVSS 3.1 9.3 per mirrors — [NVD](https://nvd.nist.gov/vuln/detail/CVE-2025-48757) (via search summaries; NVD not directly reachable); [Tenable](https://www.tenable.com/cve/CVE-2025-48757).
  - Timeline: Matt Palmer's statement says the flaw was found 2025-03-20, starting from "Linkable", a Lovable-built site. A scan completed 2025-03-21 of 1,645 "Lovable Launched" projects found 303 endpoints in 170 projects (~10.3%) with inadequate RLS. The statement was published 2025-05-29 after the disclosure window; NVD published 2025-05-30 — [Palmer statement (mirror)](https://welcome-b52.pages.dev/posts/2025/05/statement-on-CVE-2025-48757) (original listed as mattpalmer.io/posts/statement-on-CVE-2025-48757/, not reachable here); [Superblocks summary](https://www.superblocks.com/blog/lovable-rls-breach); [Semafor 2025-05-29](https://www.semafor.com/article/05/29/2025/the-hottest-new-vibe-coding-startup-lovable-is-a-sitting-duck-for-hackers).
  - Lovable shipped a "security scan" in Lovable 2.0 (reported 2025-04-24). Secondary sources say it checked for the presence of RLS policies rather than whether they restrict access, and that Palmer's 2025-05-24 reassessment still bypassed Linkable's controls by removing the Authorization header — [Superblocks](https://www.superblocks.com/blog/lovable-rls-breach); search summaries of [rapidevelopers](https://rapidevelopers.com/lovable-issues/lovable-security-guide). This is secondary; the wording varies.
  - Lovable disputes the CVE and holds that customers own their app's data security — search summaries; no primary Lovable statement retrieved.
  - Palmer was a Replit employee, i.e. a competitor — [Analytics India Magazine](https://analyticsindiamag.com/ai-features/when-replit-employees-found-a-critical-security-vulnerability-in-lovable).
- **Moltbook (disclosed late Jan to early Feb 2026, Wiz).**
  - A Supabase API key in client-side JavaScript plus no RLS gave unauthenticated read *and write* to the production database. About 4.75M records were mapped, including ~1.5M API authentication tokens and ~35,000 emails.
  - Wiz notes the key "is normally secure when RLS is properly configured". The team fixed it within hours. The founder said he "didn't write one line of code".

  Sources: [Wiz, "Hacking Moltbook"](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys) (via search summary); [Business Today, 2026-02-04](https://www.businesstoday.in/technology/news/story/moltbook-left-its-production-database-open-exposing-millions-of-ai-agent-records-514548-2026-02-04).
- **Supabase changed its default grants (2026).** Announcement in [GitHub discussion #45329](https://github.com/orgs/supabase/discussions/45329); changelog 45329 on supabase.com:
  - New tables in `public` are no longer granted `select, insert, update, delete` (sequences: `usage, select`) for `anon`, `authenticated` and `service_role` automatically.
  - Timeline:
    - 2026-04-28: opt-in "Automatically expose new tables" checkbox
    - 2026-05-18: pg_graphql no longer enabled by default
    - 2026-05-30: default for new projects
    - 2026-10-30: all existing projects
  - Existing tables keep their grants.
  - CLI v2.102.0 added `[api] auto_expose_new_tables = false`, itself scheduled for removal on 2026-10-30.
  - Supabase's rationale: "agents, CLI scripts, and AI platforms" now create tables without human review. "RLS behavior remains unchanged."
- **UpGuard (2026-09-25).**
  - 16,326 Supabase databases with publicly readable tables, out of ~300,000 domains showing Supabase use. More than half showed signs of PII; some held credentials and payment data.
  - Method: table structure plus a sampled confirmation.
  - UpGuard says tables created programmatically through the API (as coding agents do) do not enable RLS by default, and that AI coding agents account for >60% of newly created Supabase databases.
  - Supabase's CISO called projects "secure by default" and security a shared responsibility.

  Sources: [UpGuard](https://www.upguard.com/blog/everything-everywhere-systemic-data-exposure-in-supabase-apps); [BleepingComputer](https://bleepingcomputer.com/news/security/misconfigured-supabase-apps-expose-data-in-over-16-000-databases) (via search summary; UpGuard page not directly fetched).
- **Escape.tech (Oct 2025):** scanned 5,600+ public apps built on vibe-coding platforms and reported 2,000+ high-impact vulnerabilities, 400+ exposed secrets and 175 PII instances (medical records, IBANs, phones, emails) — [Escape methodology post](https://escape.tech/blog/methodology-how-we-discovered-vulnerabilities-apps-built-with-vibe-coding/) (via search summary).
- **Lovable platform BOLA (April 2026, platform-level rather than RLS).**
  - Sequential project IDs let any free account read other users' projects: source, AI chat history, and hard-coded Supabase credentials including service-role keys, which bypass RLS entirely. Reported via HackerOne 2026-03-03 (closed as duplicate) and demonstrated publicly 2026-04-20.
  - Secondary sources only; scope and cutoff dates conflict (pre-Nov vs pre-Dec 2025 projects): [vibegraveyard](https://vibegraveyard.ai/story/lovable-bola-api-48-days-exposed/), [Halborn](https://www.halborn.com/blog/post/lovable-data-leak-bola-vulnerability-and-app-security-risks).
  - Supabase: a secret key or `service_role` "bypasses RLS… Never use a secret key in the browser" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- **Firebase analog.**
  - Tea app (July 2025): a misconfigured Firebase Storage bucket exposed ~72,000 images, including ~13,000 verification selfies and IDs, per Tea's own statement and 404 Media's verification — [Simon Willison quoting Tea's statement](https://simonwillison.net/2025/Jul/26/official-statement-from-tea/); [The Record](https://therecord.media/tea-app-data-breach-stolen-ids-leaked). Tea was not reported as vibe-coded; it is the same authorization-in-the-backend-config failure class.
  - Firebase Security Rules, like RLS, are developer-owned. Vendor sources claim Lovable, Bolt and other builders do not write them and that "test mode" rules are frequently left in place — [vibeappscanner](https://vibeappscanner.com/vulnerability/firebase-rules-misconfiguration). Vendor content; prevalence figures are unsourced.

#### (c) Why AI-generated / vibe-coded apps are prone, and platform vs developer
- Supabase's own explanation of its 2026 default change is the cleanest primary statement of the cause. The original model assumed a human reviewed each schema change; "agents, CLI scripts, and AI platforms now create tables" without review — [discussion #45329](https://github.com/orgs/supabase/discussions/45329).
- UpGuard attributes exposure to agent-created tables that lack RLS by default — [UpGuard](https://www.upguard.com/blog/everything-everywhere-systemic-data-exposure-in-supabase-apps).
- **What Supabase (the platform) enforces:**
  - the RLS mechanism itself
  - default-deny once RLS is enabled with no policy
  - Security Advisor lints (splinter)
  - since 2026, no automatic grants on new tables
  - pg_graphql introspection off and not enabled by default

  Sources: [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx), [splinter](https://github.com/supabase/splinter), [#45329](https://github.com/orgs/supabase/discussions/45329).
- **What the developer owns:**
  - enabling RLS on every exposed table
  - policies per operation
  - grants, including column grants
  - views (`security_invoker`), materialized views, foreign tables
  - SECURITY DEFINER functions: schema, `search_path` and EXECUTE grants
  - never shipping the secret or `service_role` key
  - Realtime and Storage policies

  Supabase: "Until the suite passes, you don't know whether the policies do what you intended" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- Supabase's API key in the browser is designed to be public. It becomes a "master credential" only without RLS ([Wiz via search summary](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)). AI-generated frontends call PostgREST directly with that key, so every missing or wrong policy is directly reachable.

#### (d) Safely testing your own project
- Supabase Security Advisor runs the splinter lints (above). For a local or CI run, execute `splinter.sql` against the database. Set `pgrst.db_schemas` if you expose schemas other than `public` — [splinter README](https://github.com/supabase/splinter).
- Write pgTAP tests under `supabase/tests/` that assert allow and deny for `select`, `insert`, `update` and `delete`, for both `anon` and `authenticated`. Run them with `supabase test db`. A `with check` violation raises `42501` (use `throws_ok`) — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- Check what your project grants by default with the query in "Check your default privileges". "Default privileges differ between projects, depending on when the project was created and its Data API settings" — [Securing your API](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/api/securing-your-api.mdx).
- Inspect a specific view: `select relname, reloptions from pg_class where oid = 'public.my_view'::regclass;` should show `security_invoker=true` (option name per [CREATE VIEW](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_view.sgml)).
- Black-box check from outside, against your own project only: request `GET /rest/v1/<view>?select=id&limit=1` three ways:
  1. with only the publishable/anon key
  2. with test user A's JWT, for a row owned by test user B
  3. after creating data as B

  Expected results: an empty array or a 401/42501 error for (1) when the view should be private, and no B rows for (2). This is my inference from the role model documented in the [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).

#### (e) The fix (SQL; statements use documented syntax; adapt names)
```sql
-- 1) Views over RLS tables (PG15+): run as the caller
alter view public.order_summaries set (security_invoker = true);
--    or at creation:
create view public.order_summaries with (security_invoker = true) as
  select o.id, o.user_id, o.total from public.orders o;

-- 2) Views that must aggregate across users (admin dashboards, materialized views,
--    PG<15 projects): take them out of the API instead
revoke all on public.admin_stats from anon, authenticated;
create schema if not exists private;          -- not listed in exposed schemas
alter materialized view public.admin_stats set schema private;

-- 3) Per-operation policies with explicit WITH CHECK and initPlan-friendly calls
alter table public.profiles enable row level security;
create policy "own row: select" on public.profiles for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "own row: update" on public.profiles for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- 4) Column-level: users may edit display fields, not role/plan flags
revoke update on public.profiles from authenticated;
grant update (display_name, avatar_url) on public.profiles to authenticated;

-- 5) Roles from app_metadata (server-writable), never user_metadata
create policy "admins read all" on public.reports for select to authenticated
  using ((select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- 6) SECURITY DEFINER helpers: unexposed schema, pinned search_path, minimal EXECUTE
create or replace function private.is_member(_list_id bigint)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.list_members m
                 where m.list_id = _list_id and m.user_id = (select auth.uid()));
$$;
revoke execute on function private.is_member(bigint) from public, anon;
grant usage on schema private to authenticated;
grant execute on function private.is_member(bigint) to authenticated;

-- 7) Stop future implicit grants (projects created before the 2026 change)
alter default privileges for role postgres in schema public
  revoke select, insert, update, delete on tables from anon, authenticated;
```
Sources for each part:
- `security_invoker` and `ALTER VIEW`: [PG CREATE VIEW](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_view.sgml).
- The revoke and unexposed-schema guidance, policy forms, `(select auth.uid())`, `app_metadata` vs `user_metadata`, and SECURITY DEFINER with `search_path = ''`: [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- Column `GRANT` syntax: [PG GRANT](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/grant.sgml).
- `alter default privileges for role postgres in schema public`: [Securing your API](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/api/securing-your-api.mdx).
- Supabase also documents an event trigger that enables RLS automatically on new tables ([RLS guide → Event triggers](https://supabase.com/docs/guides/database/postgres/event-triggers)) and a dedicated API schema as an extra boundary ([Securing your API](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/api/securing-your-api.mdx)).

#### (f) Incorrect or incomplete fixes
- **Enabling RLS on the base table while the app reads a non-invoker view.** The view applies the owner's policies or privileges, so it still leaks — [PG CREATE VIEW](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ref/create_view.sgml).
- **Adding `FORCE ROW LEVEL SECURITY` to "fix" the view.** BYPASSRLS roles always bypass, and Supabase's `postgres` has `bypassrls` — [PG ddl](https://github.com/postgres/postgres/blob/master/doc/src/sgml/ddl.sgml); [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- **`security_invoker` on Postgres 14 or older.** The guide gives the option for PG15+; older projects must revoke or move the view — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- **`security_invoker` on a materialized view.** The splinter lint for materialized views exists because they "are accessible over the Data APIs". The fix is revoking access or moving the schema — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql). That the option does not apply to materialized views is my inference from the CREATE VIEW scope.
- **Silencing access errors with `using (true)` or `with check (true)`.** Lint 0024 flags it for writes. SELECT `using (true)` is "intentionally excluded" because it may be meant to be public data — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql). A scanner that only checks whether a policy exists passes this; that is the critique of Lovable's scan — [Superblocks](https://www.superblocks.com/blog/lovable-rls-breach).
- **Policies without grants hygiene.** "Adding policies doesn't take those grants back" — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- **Relying on the 2026 grant change for old tables.** "Existing tables keep their grants" — [discussion #45329](https://github.com/orgs/supabase/discussions/45329); UpGuard notes it cannot be treated as a fix for every readable table — [UpGuard](https://www.upguard.com/blog/everything-everywhere-systemic-data-exposure-in-supabase-apps).
- **SECURITY DEFINER helper left in `public` without a pinned `search_path`.** It is callable over RPC with owner rights — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- **Roles or tenancy in `user_metadata`.** It is user-editable — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx); [splinter 0015](https://github.com/supabase/splinter/blob/main/splinter.sql).
- **Hiding or rotating the anon/publishable key instead of fixing policies.** The key is meant to be public ([Wiz via search summary](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)).
- **Client-side filters such as `.eq('user_id', user.id)` as authorization.** My inference: any caller can omit them.

#### (g) Verifying the fix
- pgTAP, in the pattern the Supabase guide documents:
  1. Impersonate `authenticated` with a JWT claims setting for user A. Supabase documents the claims as available in `request.jwt.claims` ([Realtime auth docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx)).
  2. Assert that `select count(*) from public.order_summaries` equals A's row count, not the table total.
  3. Assert that `update profiles set role = 'admin'` raises `42501` (column grant), and that `update … set user_id = <B>` fails the `with check`.
  4. Run with `supabase test db`.

  Before the fix the count equals the table total. After it, it equals A's count — [Supabase RLS guide](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/database/postgres/row-level-security.mdx).
- Re-run splinter or the Security Advisor. `security_definer_view` (0010), `materialized_view_in_api` (0016), `auth_users_exposed` (0002), `rls_references_user_metadata` (0015), `function_search_path_mutable` (0011) and 0028/0029 should no longer list the objects you fixed — [splinter.sql](https://github.com/supabase/splinter/blob/main/splinter.sql).
- Repeat the black-box anon GET from (d). It should return `[]` or a permission error.

### Inferences
- Likely sources of these views in vibe-coded apps:
  - The view problem is a structural trap for AI-generated schemas. "Convenience" views that join `profiles` with `orders`, or that select from `auth.users`, are a natural way to satisfy a UI query in one call. They are owned by `postgres` and land in `public`. Lint 0002 (`auth_users_exposed`) exists for exactly the `auth.users` case.
  - I found no measured study of how often AI assistants emit non-invoker views. This is a reasoned pattern, not a statistic.
- How the 2026 grant change plays out:
  - Supabase's grant change addresses tables an agent forgets to protect.
  - A view the agent creates still needs an explicit `GRANT` under the new defaults, and the agent will likely add that grant to make the UI work.
  - The view then leaks unless `security_invoker` is set. So the 2026 change moves the failure from "forgot" to "granted without understanding". Lint 0010 remains the backstop.
- The common advice "UPDATE without WITH CHECK lets users reassign user_id" is inaccurate for PostgreSQL when USING already constrains ownership. Teach the real risks instead: permissive `with check (true)`, INSERT policies, OR-combined permissive policies, and column-level escalation.

### Gaps
- I could not read Matt Palmer's original page (mattpalmer.io), the Wiz Moltbook post, or the UpGuard report directly. Their figures come from mirrors and search summaries.
- Exact behaviour of the Supabase dashboard Table Editor and SQL editor when creating views in 2026 (for example, whether it now defaults to `security_invoker`) was not verified.
- Whether `supabase db lint` runs splinter (as opposed to plpgsql_check) was not verified. I cited running `splinter.sql` and the dashboard Security Advisor instead.
- No primary data on how Bolt, Replit or v0 provision Supabase or Firebase backends or set RLS or Rules. Only vendor blog claims.
- Firebase "test mode" rule text and expiry period come only from a vendor source; Firebase docs were unreachable.

---

## (19) WebSocket hijacking: CSWSH, cookie and SameSite interaction, channel-level authorization, and the 2025 to 2026 localhost dev-tool cases

### Takeaway
Browsers attach ambient cookies to the WebSocket upgrade request, and the handshake is not subject to CORS. A WebSocket server that authenticates by cookie and does not check `Origin` can therefore be driven by any website the victim visits. This is Cross-Site WebSocket Hijacking (Schneider, 2013; CWE-1385). SameSite=Lax/Strict cookies block the cross-*site* case in browsers that apply them, but not a same-site sibling subdomain. Unauthenticated localhost servers have no cookie to protect, so the Origin and Host checks are the only gate. That is why 2025 to 2026 produced a run of CVEs:
- Vite CVE-2025-24010
- webpack-dev-server CVE-2025-30360
- Next.js CVE-2025-48068
- Claude Code IDE extensions CVE-2025-52882
- MCP Inspector CVE-2025-49596
- OpenClaw CVE-2026-25253 and "ClawJacked"

The fix is an exact-match Origin allowlist at the handshake, real authentication (short-lived ticket or token in the first message), and authorization on every channel join and message. Neither Socket.IO's `cors` option nor `ws` does any of this by default.

### Cited Findings

#### (a) Mechanism, preconditions, impact
- Christian Schneider documented CSWSH on 2013-08-31: cookie- or HTTP-auth-authenticated WebSocket handshakes that a cross-site page can open as the victim. His primary countermeasure was to check the handshake's `Origin` on the server — [Schneider, "Cross-Site WebSocket Hijacking"](https://christian-schneider.net/CrossSiteWebSocketHijacking.html) (via search summary). The class is CWE-1385, "Missing Origin Validation in WebSockets" — [CWE-1385](https://cwe.mitre.org/data/definitions/1385.html).
- RFC 6455 §10.2 "Origin Considerations" covers server-side Origin checking and rejection with an HTTP error — [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455) (the section body was not retrievable here; summary via search). Exact wording is unverified. My recollection is that servers not meant to accept input from arbitrary web pages SHOULD verify Origin and reply 403, and that Origin does not constrain non-browser clients.
- OWASP: "Browsers include cookies in WebSocket handshake requests, making WebSocket applications vulnerable to Cross-Site WebSocket Hijacking". Validate `Origin` "on every handshake" with "an explicit allowlist… malicious JavaScript cannot override it". Use SameSite cookies "to strengthen CSWSH defenses". Include CSRF tokens in handshakes if you already use them. "Don't assume WebSocket connection equals unlimited access. Check authorization for each action" — [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html) ([src](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/WebSocket_Security_Cheat_Sheet.md)).
- Socket.IO's docs: "CORS only applies to HTTP long-polling… WebSocket connections are not subject to CORS restrictions. If you want to restrict who can actually reach your website, you can use the `allowRequest` option" — [Socket.IO "Handling CORS"](https://socket.io/docs/v4/handling-cors/) ([docs src](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/handling-cors.md)).
- `ws`: "If `verifyClient` is not set, then the handshake is automatically accepted" — [ws API doc](https://github.com/websockets/ws/blob/master/doc/ws.md).
- **SameSite:**
  - PortSwigger: "Since 2021, Chrome applies Lax SameSite restrictions by default" to cookies without an explicit attribute — [PortSwigger, Bypassing SameSite restrictions](https://portswigger.net/web-security/csrf/bypassing-samesite-restrictions) (via search summary).
  - Include Security (April 2025) dates Chrome's change to 2020 and notes not all browsers apply Lax by default — [Include Security, "CSWSH Exploitation in 2025"](https://blog.includesecurity.com/2025/04/cross-site-websocket-hijacking-exploitation-in-2025/) (via search summary).
  - PortSwigger's lab "SameSite Strict bypass via sibling domain" uses CSWSH from an XSS on a sibling domain. "As this sibling domain is part of the same site… the CSWSH attack [is not] mitigated by SameSite restrictions" — [PortSwigger lab](https://portswigger.net/web-security/csrf/bypassing-samesite-restrictions/lab-samesite-strict-bypass-via-sibling-domain) (via search summary).
- **Channel-level authorization (the second half of the class).**
  - Socket.IO middleware "will be executed only once per connection", and the socket "is not actually connected when the middleware gets executed" — [Socket.IO middlewares doc](https://socket.io/docs/v4/middlewares/) ([docs src](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/middlewares.md)). Connection-time auth does not authorize later `join` or event handlers.
  - Supabase Realtime: private channels need `config: { private: true }` on the client, RLS policies on `realtime.messages` (using `realtime.topic()` and `extension` = `broadcast`/`presence`), and the "Allow public access" setting disabled — [Supabase Realtime Authorization](https://supabase.com/docs/guides/realtime/authorization) ([docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx)).
  - Supabase Realtime caching: "Client access policies are cached for the duration of the connection". A revoked user "will keep receiving messages until their JWT expires or a new one is sent", so Supabase advises keeping JWT expiry short — [Supabase Realtime Authorization](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx).
  - Postgres Changes: "database records are sent only to clients who are allowed to read them based on your RLS policies". The docs caution that "RLS policies are not applied to `DELETE` statements". Tables in private schemas without RLS give "unfettered read access" to any granted role — [Supabase Postgres Changes](https://supabase.com/docs/guides/realtime/postgres-changes) ([docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/postgres-changes.mdx)).
- **Impact:** anything the authenticated socket can do — read the victim's stream, send messages or commands as the victim. Gitpod's 2023 CSWSH allowed "full account takeover" — [OWASP cheat sheet, citing GHSA-f53g-frr2-jhpf](https://github.com/advisories/GHSA-f53g-frr2-jhpf). For localhost tools: source theft, file read, or RCE (below).

#### (b) Incidents and CVEs (newest first; older labelled)
- **"ClawJacked" (Oasis Security, disclosed ~2026-02-26), OpenClaw gateway.**
  - A malicious website opened a WebSocket to the OpenClaw gateway on localhost.
  - Loopback was exempt from login rate limiting so local CLI sessions aren't locked out, which allowed password brute force at "hundreds of attempts per second" without throttling or logging.
  - Fixed in 2026.2.25 or 2026.2.26 (sources conflict). The fix reportedly enforces rate limits for localhost and blocks auto-approval from cross-origin browser contexts (unconfirmed against release notes).

  Sources: [The Hacker News](https://thehackernews.com/2026/02/clawjacked-flaw-lets-malicious-sites.html); [BleepingComputer](https://www.bleepingcomputer.com/news/security/clawjacked-attack-let-malicious-websites-hijack-openclaw-to-steal-data/amp/); [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-clawjacked-websocket-local-agent-hijack-20/) (all via search summary).
- **CVE-2026-25253 / GHSA-g8p2-7wf7-98mq, OpenClaw/clawdbot ≤ 2026.1.28, fixed 2026.1.29.**
  - Published 2026-01-31; CVSS 8.8; CWE-668.
  - The Control UI took `gatewayUrl` from the query string, auto-connected on load, and sent the stored gateway token in the WebSocket connect payload to any URL. That led to token theft, operator access and RCE, "even when the gateway listens only on loopback, because the victim's browser makes the outbound connection".
  - The fix requires user confirmation of a new gateway URL.

  Source: [GHSA-g8p2-7wf7-98mq](https://github.com/advisories/GHSA-g8p2-7wf7-98mq). This is the client-side mirror image of CSWSH: the WebSocket *client* trusted an attacker-chosen endpoint.
- **CVE-2025-52882 / GHSA-9f65-56v6-gxw7, Claude Code IDE integrations.**
  - Published 2025-06-23; CVSS v4 8.8; CWE-285 and CWE-1385.
  - The IDE integrations accepted WebSocket connections from arbitrary origins, so a visited webpage could:
    - in VS Code and forks: read files, list open files, receive selection and diagnostics events, and in limited Jupyter cases execute code if the user accepted a prompt
    - in JetBrains: receive selection, open-file and syntax-error events
  - Affected: `@anthropic-ai/claude-code` ≥ 0.2.116 < 1.0.24; VS Code extension 0.2.116 through 1.0.23; JetBrains plugin 0.1.1 through 0.1.8.
  - Fixed: 1.0.24 and JetBrains 0.1.9. The patch was released 2025-06-13.

  Source: [GHSA-9f65-56v6-gxw7](https://github.com/advisories/GHSA-9f65-56v6-gxw7). Datadog describes the pre-patch server as having no client authentication — [Datadog Security Labs](https://securitylabs.datadoghq.com/articles/claude-mcp-cve-2025-52882/) (via search summary).
- **CVE-2025-49596 / GHSA-7f8r-222p-6f5g, `@modelcontextprotocol/inspector` < 0.14.1, fixed 0.14.1.**
  - Published 2025-06-13; CVSS v4 9.4; CWE-306.
  - "Lack of authentication between the Inspector client and proxy" allowed unauthenticated requests to launch MCP commands over stdio, leading to RCE. Credit: Rémy Marot (Tenable).

  Source: [GHSA-7f8r-222p-6f5g](https://github.com/advisories/GHSA-7f8r-222p-6f5g). Oligo's research shows a browser drive-by path, including 0.0.0.0 / 127.0.0.1 targeting and DNS rebinding, and says 0.14.1 added a session token plus Host and Origin validation — [Oligo](https://www.oligo.security/blog/critical-rce-vulnerability-in-anthropic-mcp-inspector-cve-2025-49596) (via search summary). This is HTTP/SSE proxy rather than WebSocket, but it is the same localhost-from-browser trust failure.
- **CVE-2025-30360 / GHSA-9jgg-88mc-972h, webpack-dev-server ≤ 5.2.0, fixed 5.2.1.**
  - Published 2025-06-03; CVSS 6.5; CWE-346.
  - The Origin check, added after CVE-2018-14732, "always allows IP address `Origin` headers". A page served from an IP address could open the HMR WebSocket, learn update names, load `hot-update.js` via script tag, and read source.
  - Chromium 94+ was protected by private-network access blocking; non-Chromium browsers were not.

  Source: [GHSA-9jgg-88mc-972h](https://github.com/advisories/GHSA-9jgg-88mc-972h). Companion CVE-2025-30359 (GHSA-4v9v-hfq4-rm2v) is source theft via script tag; secondary sources say its first fix relied on `Sec-Fetch-*` headers and was incomplete — [GitLab advisory DB](https://advisories.gitlab.com/npm/webpack-dev-server/CVE-2025-30359/); [Fluid Attacks](https://db.fluidattacks.com/adv/npm/webpack-dev-server/CVE-2025-30360) (via search summary).
- **CVE-2025-48068, Next.js `next dev`.**
  - Missing Origin validation on the dev WebSocket (CSWSH) exposed client-component source with the App Router.
  - Vercel lists 13.0.0 through 14.2.29 and 15.0.0 through 15.2.1 as affected. Wiz lists 13.0 through 15.2.2.
  - Mitigation: upgrade, and `allowedDevOrigins` in `next.config.js`. Dev only; production is unaffected.

  Sources: [Vercel changelog](https://vercel.com/changelog/cve-2025-48068); [Wiz](https://www.wiz.io/vulnerability-database/cve/cve-2025-48068) (via search summary).
- **CVE-2025-24010 / GHSA-vg6x-rcgg-rjx6, Vite** (6.0.0 to 6.0.8, 5.0.0 to 5.4.11, ≤ 4.5.5; fixed 6.0.9, 5.4.12, 4.5.6).
  - Published 2025-01-20; CWE-346, CWE-350 and CWE-1385. Three issues:
    1. `server.cors` defaulted to `true` (`Access-Control-Allow-Origin: *`)
    2. no Origin validation on the HMR WebSocket (CSWSH: read changed file paths and error content, send messages)
    3. no Host validation, so DNS rebinding worked; `server.allowedHosts` was added
  - `legacy.skipWebSocketTokenCheck` is the opt-out from the new WebSocket token check.

  Source: [GHSA-vg6x-rcgg-rjx6](https://github.com/advisories/GHSA-vg6x-rcgg-rjx6).
- **CVE-2024-26135, MeshCentral CSWSH** (Praetorian, 2024) — [Praetorian](https://praetorian.com/blog/meshcentral-cross-site-websocket-hijacking-vulnerability) (versions not verified).
- **Historical:**
  - Gitpod CSWSH (2023, GHSA-f53g-frr2-jhpf), cited by OWASP — [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
  - CVE-2018-14732, the original webpack-dev-server Origin issue — [GHSA-9jgg-88mc-972h](https://github.com/advisories/GHSA-9jgg-88mc-972h)
  - Schneider 2013 — [christian-schneider.net](https://christian-schneider.net/CrossSiteWebSocketHijacking.html)

#### (c) Why vibe-coded apps are prone, and platform vs developer
- **Socket.IO.** `allowRequest` has default "`-`" (none). The `cors` option only configures CORS headers, which apply to HTTP long-polling. `origin: true` reflects any request Origin. A RegExp such as `/example\.com$/` "will reflect any request that is coming from an origin ending with 'example.com'" — [Socket.IO server options src](https://github.com/socketio/socket.io-website/blob/main/docs/server-options.md); [Handling CORS src](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/handling-cors.md). socket.io 4.8.4 was latest on 2026-09-25 ([npm](https://registry.npmjs.org/socket.io)).
- **`ws`.** No verification by default. `verifyClient` exists but "Use of `verifyClient` is discouraged. Rather handle client authentication in the `'upgrade'` event of the HTTP server" — [ws.md](https://github.com/websockets/ws/blob/master/doc/ws.md). ws 8.23.0 was latest on 2026-11-12 ([npm](https://registry.npmjs.org/ws)).
- **Supabase Realtime (the platform enforces when configured).**
  - RLS for Postgres Changes on INSERT/UPDATE, and RLS on `realtime.messages` for private Broadcast/Presence.
  - The developer must opt into `private: true`, write the policies, and disable "Allow public access" to *enforce* private channels. Public channels remain joinable by topic name with the public key.

  Source: [Realtime Authorization src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx).
- **Dev-tool servers (Vite, webpack-dev-server, Next.js dev).** These are platform-owned, and the fix is "upgrade". The developer owns not exposing dev servers (e.g. `--host 0.0.0.0` on shared networks) and configuring `server.allowedHosts` / `allowedDevOrigins` correctly — [Vite GHSA](https://github.com/advisories/GHSA-vg6x-rcgg-rjx6); [Vercel changelog](https://vercel.com/changelog/cve-2025-48068).
- **App builders.** Primary, quotable descriptions of how Lovable, Bolt, Replit or v0 scaffold WebSocket or realtime auth were not found. See Gaps.

#### (d) Safely testing your own app
- **Handshake Origin test** (your own endpoint). Send an upgrade request with a foreign Origin and confirm rejection (HTTP 403 or no `101 Switching Protocols`):
  ```
  curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" \
       -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" -H "Origin: https://not-my-site.example" \
       https://app.example.com/ws
  ```
  Then repeat with your real Origin, with `Origin: null`, with an IP-address Origin (the webpack-dev-server bypass shape), and with a look-alike suffix such as `https://evilexample.com` (the regex trap). OWASP's testing list includes "Origin validation: Connect from unauthorized domains" — [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html); OWASP WSTG "Testing WebSockets" — [WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/10-Testing_WebSockets).
- **Browser devtools.** While logged in to your app, open a page on a different origin you control and open a WebSocket to your endpoint. In DevTools → Network → WS, check whether the handshake completes and whether authenticated frames arrive. PortSwigger's CSWSH material describes the attack as CSRF on the handshake — [PortSwigger CSWSH](https://portswigger.net/web-security/websockets/cross-site-websocket-hijacking) (via search summary).
- **Channel authorization.** With test users A and B, have A emit `join` for B's room or subscribe to B's topic. Expect rejection and no frames. For Supabase, attempt to join a private channel using only the publishable key and expect failure — [Supabase Realtime Authorization](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx).
- **Local tools.** Confirm the installed versions of the tools in (b):
  - Vite ≥ 6.0.9 / 5.4.12 / 4.5.6
  - webpack-dev-server ≥ 5.2.1
  - Next.js ≥ 14.2.30 / 15.2.2
  - Claude Code ≥ 1.0.24
  - MCP Inspector ≥ 0.14.1
  - OpenClaw ≥ 2026.2.26

  Sources: advisories above.

#### (e) The fix (code; option names from current docs; illustrative)
Socket.IO 4.x: Origin gate, token auth, per-room checks. `allowRequest(req, callback)` with `callback(null, boolean)` is per the [server options doc](https://github.com/socketio/socket.io-website/blob/main/docs/server-options.md); `io.use` per the [middlewares doc](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/middlewares.md).
```js
import { Server } from 'socket.io';
const ALLOWED_ORIGINS = new Set(['https://app.example.com']); // exact strings, no regex suffixes

const io = new Server(httpServer, {
  cors: { origin: [...ALLOWED_ORIGINS], credentials: true }, // governs long-polling only
  allowRequest: (req, callback) => callback(null, ALLOWED_ORIGINS.has(req.headers.origin)),
  maxHttpBufferSize: 64 * 1024,
});

io.use(async (socket, next) => {                 // runs once per connection
  try { socket.data.user = await verifyAccessToken(socket.handshake.auth?.token); next(); }
  catch { next(new Error('unauthorized')); }
});

io.on('connection', (socket) => {
  socket.on('room:join', async (roomId, ack) => {
    if (!(await canAccessRoom(socket.data.user.id, roomId))) return ack?.({ ok: false });
    await socket.join(`room:${roomId}`);
    ack?.({ ok: true });
  });
  socket.on('message:send', async (msg, ack) => {
    if (!socket.rooms.has(`room:${msg.roomId}`)) return ack?.({ ok: false }); // re-check per message
    // validate msg shape/size, then persist/broadcast
  });
});
```

`ws` 8.x, following the library's recommended pattern: authenticate in the HTTP server's `upgrade` event with `noServer: true`, from the [ws README "Client authentication"](https://github.com/websockets/ws/blob/master/README.md#client-authentication). `maxPayload` is per [ws.md](https://github.com/websockets/ws/blob/master/doc/ws.md).
```js
import { createServer } from 'node:http';
import { WebSocketServer } from 'ws';
const ALLOWED_ORIGINS = new Set(['https://app.example.com']);
const server = createServer();
const wss = new WebSocketServer({ noServer: true, maxPayload: 64 * 1024 });

server.on('upgrade', (req, socket, head) => {
  socket.on('error', console.error);
  if (!ALLOWED_ORIGINS.has(req.headers.origin)) {
    socket.write('HTTP/1.1 403 Forbidden\r\n\r\n'); socket.destroy(); return;
  }
  authenticate(req, (err, user) => {             // e.g. single-use ticket or session + CSRF token
    if (err || !user) { socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n'); socket.destroy(); return; }
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit('connection', ws, req, user));
  });
});
```

Ticket or first-message authentication. OWASP: prefer sending the token in the first message over WSS. "Avoid tokens in URL query strings because they can leak into access logs." Accept only the auth message until it validates, close on failure or timeout, and rotate tokens on long-lived connections — [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).

Supabase Realtime private channel. Policy shape per the [docs src](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx):
```sql
create policy "members receive room broadcasts"
on realtime.messages for select to authenticated
using (
  exists (select 1 from public.rooms_users ru
          where ru.user_id = (select auth.uid())
            and ru.room_topic = (select realtime.topic())
            and realtime.messages.extension in ('broadcast'))
);
-- client: supabase.channel('room-1', { config: { private: true } })
-- dashboard: Realtime settings → disable "Allow public access"
```

Dev servers:
- upgrade first
- Vite: keep `server.allowedHosts` tight and do not enable `legacy.skipWebSocketTokenCheck`
- Next.js: set `allowedDevOrigins` only to origins you use

Sources: [Vite GHSA](https://github.com/advisories/GHSA-vg6x-rcgg-rjx6); [Vercel changelog](https://vercel.com/changelog/cve-2025-48068).

Defense in depth:
- SameSite=Lax or Strict on session cookies
- CSRF token in the handshake if you already use one
- per-user connection and message rate limits
- message size limits (OWASP suggests ≤ 64 KB)
- logging of connection and authorization events, since HTTP logs only capture the upgrade

Source: [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).

#### (f) Incorrect or incomplete fixes
- **Setting Socket.IO `cors.origin` and believing WebSockets are restricted.** They are not; CORS applies only to polling — [Socket.IO CORS doc](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/handling-cors.md).
- **`origin: true` or regex suffix matches.** `origin: true` reflects any Origin, and `/example\.com$/` accepts any origin "ending with" example.com, which includes look-alike registrable domains — [Socket.IO CORS doc](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/handling-cors.md).
- **Special-casing IP-address Origins as "local".** This was the webpack-dev-server CVE-2025-30360 bypass — [GHSA-9jgg-88mc-972h](https://github.com/advisories/GHSA-9jgg-88mc-972h).
- **Relying on `Sec-Fetch-*` headers alone.** Secondary sources report the original CVE-2025-30359 fix did this and was incomplete — [Fluid Attacks via search](https://db.fluidattacks.com/adv/npm/webpack-dev-server/CVE-2025-30360).
- **Origin check without authentication.** Non-browser clients can send any Origin. Origin only protects users' browsers — [RFC 6455 discussion via search](https://datatracker.ietf.org/doc/html/rfc6455); [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).
- **SameSite as the only control.** It does not stop same-site sibling subdomains (PortSwigger lab), and not every browser defaults to Lax — [PortSwigger lab](https://portswigger.net/web-security/csrf/bypassing-samesite-restrictions/lab-samesite-strict-bypass-via-sibling-domain); [Include Security](https://blog.includesecurity.com/2025/04/cross-site-websocket-hijacking-exploitation-in-2025/).
- **Authenticating at connect and never authorizing joins or messages.** Socket.IO middleware runs once per connection — [Socket.IO middlewares](https://github.com/socketio/socket.io-website/blob/main/docs/categories/02-Server/middlewares.md). OWASP requires per-action checks — [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html).
- **Long-lived JWTs on Supabase Realtime.** Authorization is cached until the JWT is refreshed or expires — [Realtime Authorization](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx).
- **Assuming RLS filters Postgres Changes `DELETE` events.** Supabase says it does not — [Postgres Changes](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/postgres-changes.mdx).
- **Treating loopback as trusted** (exempting localhost from rate limits or auto-approving pairing). This was the ClawJacked root cause — [The Hacker News](https://thehackernews.com/2026/02/clawjacked-flaw-lets-malicious-sites.html).
- **Tokens in the WebSocket URL query string.** They leak to logs — [OWASP WS cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html). Separately, a client that auto-connects to a URL taken from the query string leaks its token to an attacker endpoint — [GHSA-g8p2-7wf7-98mq](https://github.com/advisories/GHSA-g8p2-7wf7-98mq).

#### (g) Verifying the fix
- Automated integration test, for example with `socket.io-client` or `ws` from Node, where the Origin header can be set:
  1. Connect with `Origin: https://not-my-site.example` and a valid session: expect a 403 or `connect_error`.
  2. Connect with the allowed Origin and no token: expect 401 or `connect_error 'unauthorized'`.
  3. Connect as user A and emit `room:join` for B's room: expect `{ ok: false }` and no messages from B's room.
  4. Send an oversized frame: expect a close.

  Before the fix, (1) and (3) succeed; after it, both fail. The test design is mine; the behaviours are from the docs cited in (e).
- Supabase: a pgTAP or integration test that, as user A, cannot `select` from `realtime.messages` for a topic A is not a member of (policy shape above), plus a client test that `channel(topic, { config: { private: true } })` fails to subscribe for a non-member — [Realtime Authorization](https://github.com/supabase/supabase/blob/master/apps/docs/content/guides/realtime/authorization.mdx).
- Re-run the curl handshake probes from (d) in CI against staging, and check dependency versions with `npm ls vite webpack-dev-server next` against the fixed versions in (b).

### Inferences
- In the 2025 to 2026 CVE set, the vulnerable WebSocket servers were mostly *developer tools on localhost*: dev servers, IDE bridges and agent gateways. These are the tools vibe coders run all day. The production-app risk is the older CSWSH pattern plus missing per-room authorization.
- AI-scaffolded realtime code tends to pass `cors: { origin: "*" }` or `origin: true` to Socket.IO "to make it work", and to implement `join` as `socket.join(room)` without a membership check. This is a reasoned pattern from the documented defaults; I found no measured study.
- Supabase Realtime moves authorization into SQL. The view and RLS lessons from (12) apply directly: a permissive `realtime.messages` policy, or leaving "Allow public access" on, is the realtime equivalent of `using (true)`.
- Token-in-first-message designs avoid CSWSH because there is no ambient credential. They shift risk to XSS-reachable token storage, so they complement Origin checks rather than replace them.

### Gaps
- RFC 6455 §10.2's exact text could not be fetched (rfc-editor and IETF were blocked). The paraphrase above is from search summaries and memory and is marked as such.
- ClawJacked's exact fixed version (2026.2.25 vs 2026.2.26) and its CVE identifier, if any, were not confirmed against OpenClaw's own advisory.
- The Next.js CVE-2025-48068 affected range differs between Vercel and Wiz. The GHSA text was not read.
- No primary documentation was found on how Lovable, Bolt, Replit or v0 scaffold WebSocket or realtime authorization, or whether Next.js-based builders route realtime through Supabase Realtime, Pusher or Liveblocks by default.
- PortSwigger, Include Security, Oligo and Datadog pages were read only through search summaries.
