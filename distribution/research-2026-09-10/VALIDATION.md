# Correction package validation — September 10, 2026

Status: implemented locally; no commit, push, deployment, X approval, or X publication performed. The replacement post is prepared for review. The public URLs in the package are intended destinations, not evidence of deployment.

## Evidence and behavior checked

- Seven correction tests pass: frozen-byte preservation, original report-body preservation, formal disposition/history agreement, both audit counterexamples, correction-first evidence routing, all eleven constructed overlap tables and invalid-input refusal, and preservation of off-window observation times.
- Ten distribution tests pass, including refusal of rejected claims, refusal to approve or dispatch pending source bindings, source drift, unknown metrics, invalid timestamps, cumulative-snapshot handling and comparison-cohort isolation.
- The claim registry, claim history, history reconstruction and mutation checks passed. All pre-existing history entries remain in order; both new dispositions retain their original claim IDs.
- Generated surfaces, internal links, frontend structure, social metadata, public discovery exclusions and distribution preview consistency were checked. The new example was served locally with HTTP 200. Browser automation timed out, so visual browser inspection is not claimed.
- The three timestamped X observations remain at their actual capture completion times. No observation enters a comparison window, and unavailable metrics remain null.

## Release limitation

The canonical release run initially stopped on missing social-image metadata on the new page. That was fixed and the acquisition check passed. The remaining manifest checks were then run individually through the end. A stale flagship editorial source map was regenerated and its check passed.

The film render gate still reports twelve stale receipts because their recorded facts-file hash differs from the current file. The same twelve receipts also disagree with the facts file in the starting commit, as recorded in [the baseline comparison](film-baseline-check.json). The current facts file incorporates the claim dispositions, so a release needs real rerendering and inspection against current inputs. Neither film files nor their historical render receipts were rewritten to conceal this failure. A completely green canonical release run is not claimed.

Under the repository's commit rule, this package remains uncommitted while that release gate fails. The distribution preview binds exact current source hashes and labels uncommitted bindings as pending. Approval and dispatch still require committed sources; the preview creates neither authorization nor publication.

## Review artifacts

- [Formal E6 disposition](../../experiments/e6/CORRECTION-2026-09-10.md)
- [Formal E7B disposition](../../experiments/e7b/CORRECTION-2026-09-10.md)
- [Correction-first example](../../overlap/index.html)
- [Exact next post](../NEXT-POST.md)
- [Timed analytics](../analytics/README.md)

The earlier campaign and outreach dossier bodies are preserved as history with superseded notices. The new post makes no empirical, universal-system, priority, or viral-traction claim.
