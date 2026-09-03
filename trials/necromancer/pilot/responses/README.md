# Responses

One file per receipt, named `slot-<N>.json`, pasted verbatim from the
learner's reply. Nothing is edited. A receipt whose `instrument_hash` is not
the frozen one, or whose `slot` maps to a different arm than `freeze.json`
records, is refused by `scripts/trial_score.py` and left here unchanged.

`enrolment.csv` records the send date, the deadline, and each acceptance in arrival order — the slot is that order.

Empty until a human answers. Zero is the honest starting value.
