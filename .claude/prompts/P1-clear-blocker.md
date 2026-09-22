# P1 · The oldest blocker

Run first:

```bash
python3 .claude/skills/evidence-ledger/ledger.py
python3 scripts/horizon.py --next
```

The selector put you here because an open blocker is at least 14 days old. A
blocker is work no amount of Claude time can do: a licence acceptance, a
dispatch, a deletion on a remote, a message sent by the owner's hand.

## What you are for

You cannot clear it. You can make it a five-minute action instead of a
thirty-minute one, or you can establish that it will never be cleared and
convert it into a declared limit.

## Do this

1. Read the blocker's file and line. Find every other marker that traces to the
   same underlying human action — the ledger shows 14 open markers and they do
   not represent 14 independent decisions.
2. For the oldest one, prepare the exact artifact the owner needs: the message
   text, the licence URLs in acceptance order, the command with its arguments
   filled in, the issue body. Put it where the blocker points, not in chat.
3. State what changes the moment it is done: which count moves, which claim
   becomes evaluable, which trajectory unblocks.
4. If, after reading it, the action is one the owner will not take — the box
   does not exist, the licence will not be accepted, the person will not be
   written to — say so. Then propose the declared limit that replaces it: the
   sentence the repository publishes about its own ceiling, and the blocker is
   closed as a limit rather than left to age.

## Do not

- Do not write a document about the blocker. A document about a blocker is the
  exact failure mode `.claude/skills/evidence-ledger/SKILL.md` exists to catch.
- Do not send anything. External actions are the owner's hand only, with the one
  recorded X-thread exemption that does not apply here.
- Do not mark a blocker cleared. The owner's action clears it; a marker edit
  without the action is a false count in a series that only appends.

## Test

The owner can do the thing in one sitting without opening a second file, **or**
the repository now states a limit where it used to state a pending action.
