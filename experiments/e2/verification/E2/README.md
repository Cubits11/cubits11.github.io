E2 emission conformance. CONTRACT dependency: https://github.com/Cubits11/cc-framework/pull/65 (E1 d060fee). SITE E4: https://github.com/Cubits11/cubits11.github.io/pull/34.

`E2_CONTRACT_ROOT=/Users/pranavbhave/Developer/GitHub/e2-wave1-contract /tmp/cc-validation-20261023/bin/python experiments/e2/run/test_e2_rows.py`: pre exit1 (3 core regressions fail), post exit0 (5 pass). See pre.log/post.log.

roundtrip.log records exact commands: collect1320 synthetic items/3960rows -> governing validate0violations -> analyze, all exit0; E4, P1–P12 and adapter checks also0. Outputs are synthetic implementation evidence, no real guard runs or E2 outcomes. Analyzer remains stdlib-only. Collector loads the governing schema+validator from E2_CONTRACT_ROOT and needs their jsonschema runtime.

Original FT11 two-row fixture reproduced30violations against frozen schema; reconstructed single-row version reproduces15 (not claimed exact host-fixture identity). At the repaired boundary the synthetic FT11 call emits one conforming row; the original real FT11 call omits checked config/provenance and is refused with zero bytes written. No real hashes are fabricated. Full real collection records scorer-rendered UTF8 input and unrounded scalar scorer-output hashes, plus source-pinned item hashes; scores and event reduction are unchanged. Unknown policy identity remains explicitly recorded as unknown.
