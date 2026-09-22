# Prompts the horizon selector dispatches to

`python3 scripts/horizon.py --next` names one of these. Each is written to be
pasted into a session with no memory of the one that wrote it: it restates what
it needs and ends with a test it can fail.

    P1-clear-blocker.md    rung 1 · an open human blocker is the oldest thing here
    P2-external-route.md   rung 2 · qualified outcomes are still zero
    P3-direction-step.md   rung 3 · the floor is clear; take the heading
    P4-year-one.md         rung 4 · no step is ready; take the trajectory's year

These are not governing documents. They gate nothing, and a session is free to
conclude that the prompt is asking for the wrong thing and say so — that
conclusion is the most useful output any of them can produce.

Not secret. This repository is public and these describe strategy, not
credentials. `_private/` is gitignored and does not survive a container, so
nothing that needs to persist goes there.
