"""Writes cases/retro_blind_rows.json: the seven BLIND rows of 13.10 read through the meet.

POST HOC. The meet was proposed after these outcomes were known, by a reader of the
retrospective workbook, and this encoding was written by the session that audited the
outcomes. Nothing here is evidence for the meet. Its uses: show the evaluator on real text,
surface structural differences from 13.04, and fix definitions before a prospective test.

Encoding rules, applied to every row alike:
  R1  a frozen code maps to its obligation by readiness_meet.MAPPING_1304;
  R2  0 when the frozen row (or the dispatched brief's own text) states the defect as a
      property of the prompt; U with a named variable when it states an open question;
  R3  an obligation no frozen text establishes is resolved from the brief's text, which was
      readable before the run, and never from outcome evidence;
  R4  I is the strict definition fixed for the prospective protocol: explicit-path commits
      AND acceptance evaluated on the committed tree. The lenient reading (explicit paths
      alone) is reported beside it.
"""
import json, pathlib

ASTRA_BLOB = "docs/foundations/ASTRA-BRIEF.md @ blob 697be2bb"
harness = {"question": "where does the executor run, and on which tree? (frozen T2 row: 'Next observation: harness identity')",
           "domain": ["owner_mac_worktree", "clean_clone"]}
ask_harness = {"reveals": ["harness"], "cost": 1, "how": "one question to the dispatcher"}

def ev(t): return t

Q_ASTRA = {"holds": {"var": "harness", "in": ["clean_clone"]},
           "evidence": f"{ASTRA_BLOB} §A rule 7: 'verification_manifest.py must exit 0 before any commit'; "
                       "Known-open: 'claims_history.yaml entry 38 fails the append-only check in the working tree. "
                       "Do not commit around it.'; FORBIDDEN: 'touching ... claims_history.yaml'. On the owner's tree the "
                       "precondition cannot pass without the forbidden edit. The clean-checkout manifest at dispatch was not re-run here."}
I_STRICT_ASTRA = {"holds": False,
                  "evidence": f"{ASTRA_BLOB} §A: 'OUTPUT one commit per task' and rule 7 run in the working tree; no explicit-path "
                              "commit, no acceptance on the committed tree. (Lenient reading: also 0; no explicit paths.)"}
A_ASTRA = {"holds": True, "evidence": "§A: branch claude/<topic>; FORBIDDEN list; no owner-only act requested"}
T_ASTRA = {"holds": True, "evidence": "§A READ FIRST names the files; frozen core.evidence 14-17"}
X_MAC = {"holds": {"var": "harness", "in": ["owner_mac_worktree"]},
         "evidence": "§A: BLENDER /Applications/Blender.app, WORLD ~/Documents/GitHub/cc-framework/... (frozen V06)"}
X_ANY = {"holds": True, "evidence": "pure Python / generator; no Blender (frozen row fires no V06)"}

compiler_I = {"what": "the compiler appends: commit with explicit paths; run acceptance in a fresh worktree of the commit",
              "replaces": {"I": {"holds": True, "evidence": "compiled clause"}}}
fix_entry38 = {"what": "the owner lands or reverts the entry-38 surgery before dispatch (an owner act; the brief forbids the executor)",
               "replaces": {"Q": {"holds": True, "evidence": "owner act"}}}

rows = []
def astra(rid, x, extra_vars=None, A=None, T=None, V=None, obs=None, iv=None, note=""):
    variables = {"harness": harness} | (extra_vars or {})
    rows.append({
        "id": rid, "note": note,
        "variables": variables,
        "obligations": {"A": A or A_ASTRA, "I": I_STRICT_ASTRA, "T": T or T_ASTRA, "Q": Q_ASTRA,
                        "V": V, "X": x},
        "observations": {"ask-harness": ask_harness} | (obs or {}),
        "interventions": {"compiler-I": compiler_I, "owner-fixes-entry-38": fix_entry38} | (iv or {}),
    })

astra("RETRO-ASTRA-T1", X_ANY,
      extra_vars={"k7_scope": {"question": "does K7's 'audited' cover a mechanical SELF-AUDITED rung? (frozen T1 blocker)",
                               "domain": ["covers_mechanical", "independent_only"]}},
      A={"holds": {"var": "k7_scope", "in": ["independent_only"]},
         "evidence": "frozen V04: K7 forbids auditing a second device until QUEUE item 5 yields a viewer response; acceptance requires a rung for every device"},
      V={"holds": True, "evidence": "acceptance: audit_device.py --all exits 0 and prints a rung per device"},
      obs={"ask-owner-k7": {"reveals": ["k7_scope"], "cost": 2, "how": "one sentence from the owner"},
           "ask-both": {"reveals": ["harness", "k7_scope"], "cost": 3}},
      note="13.04 HOLD (V04). Outcome: acceptance PASS; K7 unresolved, owner adjudicates.")
astra("RETRO-ASTRA-T2", X_MAC,
      V={"holds": True, "evidence": "acceptance: two renders, identical_pixels true, unexpected []"},
      note="13.04 HOLD (V06). Outcome: acceptance UNVERIFIED (no committed receipt); V06 immaterial.")
astra("RETRO-ASTRA-T3", X_MAC,
      V={"holds": True, "evidence": "acceptance: face IDATs equal across arrangements, corner IDATs differ (mechanical)"},
      note="13.04 HOLD (V06; core 81). Outcome: PASS, independently reproduced; provisional FALSE HOLD.")
astra("RETRO-ASTRA-T4", X_MAC,
      T={"holds": {"var": "harness", "in": ["owner_mac_worktree"]},
         "evidence": "frozen V06: 8 of 12 camera/room names are not in the prompt and live in the .blend in another repo"},
      V={"holds": False, "evidence": "frozen A02: acceptance checks parse + presence, not whether a mapping is right; the builder grades itself"},
      iv={"owner-adjudicates-mappings": {"what": "a named adjudicator (the owner) checks each binding",
                                          "replaces": {"V": {"holds": True, "evidence": "owner review"}}}},
      note="13.04 HOLD (V06; verification 7/15). Outcome: content PASS; print leg FAIL at the run commit (uncommitted dependency).")
astra("RETRO-ASTRA-T5", X_MAC,
      V={"holds": False, "evidence": "frozen A04: 'loads in a bare three.js page' has no stated inspection method"},
      iv={"name-a-load-check": {"what": "state the headless load check and its pass condition",
                                 "replaces": {"V": {"holds": True, "evidence": "compiled check"}}}},
      note="13.04 HOLD (V06; goal 12). Outcome: size PASS; browser load UNVERIFIED.")
astra("RETRO-ASTRA-T6", X_ANY,
      V={"holds": False, "evidence": "frozen core blocker: 'no prose above the fold', 'nothing plays before an answer' have no mechanical check; the builder grades them"},
      iv={"independent-grader": {"what": "mechanical checks for the §5 rules, or a grader other than the builder",
                                  "replaces": {"V": {"holds": True, "evidence": "check or grader"}}}},
      note="13.04 HOLD (core 77). Outcome: FAIL at the run commit (uncommitted dependency); PASS at HEAD after a later run.")

rows.append({
    "id": "RETRO-FABLE-SPINE",
    "note": "13.04 READY. Outcome: PASS with one documented deviation at the room label; provisional TRUE READY.",
    "variables": {"room_label": {"question": "does the room label speak an MC-003 numeral, from a source the executor can read? (frozen predicted failure point)",
                                 "domain": ["speaks_numeral_readable", "no_numeral_or_unreadable"]}},
    "obligations": {
        "A": {"holds": True, "evidence": "FABLE-BRIEF standing constraints: explicit authority lines; K7 restated"},
        "I": {"holds": False, "evidence": "FABLE-BRIEF: 'Commit with explicit paths' binds the change set; acceptance 'verify_spine.py --check exits 0' is not run on the committed tree. Strict: 0. Lenient: 1."},
        "T": {"holds": True, "evidence": "frozen core.evidence 18"},
        "Q": {"holds": True, "evidence": "brief dated after the entry-38 fix; no conflicting precondition stated"},
        "V": {"holds": {"var": "room_label", "in": ["speaks_numeral_readable"]},
              "evidence": "acceptance requires the room label to fail under the MC-003 mutation; frozen pfp: its source is the world .blend in cc-framework, read-only, maybe unreachable"},
        "X": {"holds": True, "evidence": "pure Python gate; mutation in a scratch branch"},
    },
    "observations": {"read-room-label": {"reveals": ["room_label"], "cost": 1, "how": "open the room's label source once"}},
    "interventions": {"compiler-I": compiler_I},
})
doc = {"record": __doc__, "cases": rows}
pathlib.Path(__file__).with_name("cases").joinpath("retro_blind_rows.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(len(rows), "cases written")
