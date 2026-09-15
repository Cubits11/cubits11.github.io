# Research conformance: prior-art review

The five previously unresolved references in `DIRECTION.yaml` can now be identified from public primary sources. This review resolves citation identity and the specific assertions below. It does not establish novelty, independently reproduce another study, or validate this repository's proposed contracts. Search and access date: 2026-09-13 UTC.

## Findings and consequences

**Preregistration as Code already connects analysis plans to executable code.** Peikert and colleagues' 2021 tutorial describes drafting an executable report before collection, initially using simulated data, and later rerunning it with observed data. The authors' public `preregistration.Rmd` is a concrete example. Therefore, publishing analysis code at preregistration time cannot be the proposed contribution here. The relevant question is whether a declared population, denominator, calibration universe and decision rule remain consistent with the execution. The publisher's full-text fetch was rate-limited during this review; its indexed section 5.6 and the authors' public implementation support this bounded finding. [1, 2]

**The August 2026 safeguard study exists and reports the quoted count.** Ilya Shulepov's arXiv preprint examines 39 frozen repository–operator cases. Thirteen were initially evaluable and bounded restoration increased that set to 24; excluding one equivalent mutation left 23 non-equivalent mutations, of which the chosen workflows detected two. This is a result for selected mutations and workflows, with substantial initial execution attrition. It is not an estimate of how often research repositories are irreproducible. The abstract confirms the four mutation classes: seed, dependency pin, data split and fold count. The paper links frozen software artifacts, which have not been independently replayed here. [3]

The practical consequence is to compare future semantic mutations against these existing classes and account separately for execution failure, equivalent mutations and detected defects. Installing a new mutation framework before choosing a bounded scientific question would add dependencies without supplying that comparison. The planned distinction between reproducibility choices and scientific-intent drift remains a hypothesis about contribution, not an established novelty result.

**RO-Crate provides a reusable packaging reference.** Version 1.2 specifies `ro-crate-metadata.json` for attached packages and permits an accompanying `ro-crate-preview.html`. The human-readable preview is optional. Its metadata graph describes research objects and their context. A conformance record can borrow this machine-readable plus human-readable structure without claiming RO-Crate compliance or installing a new library. The website currently labels 1.3 as its newest release; the finding here deliberately refers to the inspected 1.2 specification. [4]

**Build attestations establish provenance, with explicit limits.** GitHub documents links to the build workflow, repository and commit, and states that attestations do not guarantee an artifact is secure. That supports the repository's separation between provenance and scientific validity. It does not show that a bound program used the correct denominator or tested an informative hypothesis. No attestation service is required to perform the next local research comparison. This review verifies the GitHub artifact-attestation portion of the original combined reference; it does not separately evaluate the in-toto specification. [5]

**FAIR4RS covers version identity, qualified references and provenance.** The Research Software Alliance's summary of the 2022 principles identifies distinct software-version identifiers, references to other research objects and software, and detailed provenance. Those principles support retaining source identity and relationships in records. They do not themselves certify that executed analysis agrees with a scientific design. [6]

## What remains blocked

These references are usable for the bounded statements above. A systematic novelty search is still outstanding: the queries below resolve named citation debts but do not supply a screened corpus, exhaustive coverage or citation-chain analysis. The proposed contribution should remain phrased as a research question.

The repository's E2 path still requires the authorized host and authenticated model-license steps specified in its freeze. Those constraints cannot be removed by simplifying software. Invitations, third-party responses and independent observations likewise require real external action. The evidence ledger counts marker occurrences, rather than distinct unresolved actions: for example, E3's statement that no pending-license marker is created is nevertheless counted as an open marker. Its total should not be presented as fourteen independently actionable tasks.

The immediate operational improvement is to keep Git responsible for repository history and remove concurrent Drive synchronization of this checkout. The next research improvement is to use these identified references when defining the smallest comparative experiment, retaining the frozen historical results and correction dispositions. Nothing in this review licenses retrofitting a new contract onto an already observed experiment.

## Search record and limits

Queries included `"Preregistration as Code"`, `"Preregistration as Code" "2021" simulated`, `"repository" "safeguards" "mutation" research 2026`, `research software "23" "mutants" safeguards`, and targeted searches of the RO-Crate specification, GitHub artifact-attestation documentation and FAIR4RS principles. The broader numeric mutation query was noisy; the repository/safeguard query identified the exact August preprint. Primary sources were then opened to confirm the relevant assertions. No Google Drive connector was needed.

This is targeted source verification and comparative analysis, not an empirical replication or systematic literature review. No downloaded package was executed, no new runtime dependency was added, and no measured claim was revised on the strength of the literature search.

## Sources

1. Peikert et al. (2021), [Reproducible Research in R: A Tutorial on How to Do the Same Thing More Than Once](https://www.mdpi.com/2624-8611/3/4/53), especially section 5.6. Publisher result indexed; full-text open returned HTTP 429.
2. Aaron Peikert and contributors, [repro-tutorial/preregistration.Rmd](https://github.com/aaronpeikert/repro-tutorial/blob/main/preregistration.Rmd). Author-maintained implementation; mutable main-branch reference, not a frozen execution pin.
3. Ilya Shulepov (27 August 2026), [Mutation Testing for Reproducibility Safeguards in Machine Learning Research Software: An Empirical Study](https://arxiv.org/abs/2608.27100v1). Preprint; abstract and submission record inspected.
4. RO-Crate community, [RO-Crate Structure, version 1.2](https://www.researchobject.org/ro-crate/specification/1.2/structure). Specification.
5. GitHub, [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations). Official documentation, accessed 13 September 2026.
6. Research Software Alliance (August 2022), [FAIR for Research Software (FAIR4RS): A summary](https://www.researchsoft.org/blog/2022-08/), reproducing the 2022 FAIR4RS principles and linking their DOI.
