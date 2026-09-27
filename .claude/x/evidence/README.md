# Evidence for the X gate

Each experiment was written down, with its predictions and its decision rule, and
hashed before it ran. The hash and time are in the `.sha256` file beside it. Those
records were kept by the session that ran the experiments. The commit came later, so
nothing external fixes the order.

| File | What it is |
|---|---|
| `x_predeclared.json` | X5–X9: principal binding, read-back, approval issuer, credentials in the caller, partial threads. Base `f2249c1`. |
| `x_pairs.py` | The X5–X9 harness. Nothing reaches X or GitHub: requests, git, credentials and the signing-key fetch are fixtures. |
| `x_pairs_base.json`, `x_pairs_patched.json` | Its output on `distribute.py` at `f2249c1` and on this branch. |
| `x10_predeclared.json` | X10: a file a session plants in the repository, invisible to `git status`, running where the credentials are. |
| `x10.py` | The X10 harness. Its docstring says how the base inputs were made. |
| `x10_base.json`, `x10_patched.json` | Its output on the base and on this branch. |
| `e2e_inventory.py`, `e2e_inventory.json` | `scripts/x_mcp_inventory.py` driving the real xurl v1.3.2 against a local stand-in for `api.x.com/mcp`. The token is a fixture string. |
| `mutants.py`, `mutants.json` | 25 mutants, each removing or weakening one guard. Each is killed by the test it names. |

## Results

**X5–X9.** Every base run came out as predicted.

- The base published as a different account.
- It recorded no read-back.
- It admitted an unsigned approval as readily as the owner's.
- It needed the credentials in the calling process.
- It left no receipt for a thread that failed partway, and admitted it again.

On this branch, each of these is refused or recorded.

**X10.** On the base:

- `git status --porcelain` was empty after four files were planted.
- The planted `__future__`, `json`, `yaml` and root-level `contextlib` ran inside
  `distribute.py --help` with the credentials in its environment, and the command
  exited 0.
- The gate ran all four and a forged cached-bytecode file for `distribute.py`.

On this branch, none ran and both processes answered normally. The predeclared setup
named only `scripts/__future__.pyc`; the other plants go beyond it and are reported
as such.

The first X5–X9 base run used an earlier revision of `x_pairs.py`, whose X7 fields
were named differently. The committed base result is a rerun with the committed
harness. Its outcomes are the same.

## Rerun

```sh
python3 .claude/x/evidence/x_pairs.py <checkout> out.json
python3 .claude/x/evidence/x10.py <distribute.py> <x_gate_mcp.py> <label> .gitignore
python3 .claude/x/evidence/e2e_inventory.py <xurl v1.3.2 binary> . <workdir>
python3 .claude/x/evidence/mutants.py . python3
```

`mutants.py` rewrites the files under test and restores them. Run it on a clean tree.
