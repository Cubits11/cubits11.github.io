# X on this repository

Two MCP servers connect a Claude Code session to X.

- **xgate** (`scripts/x_gate_mcp.py`) is the one process that holds the publishing
  credentials. Once step 7's rules are applied, it is also the one path by which a
  session can post. It exposes four tools:
  `x_gate_status`, `x_publish_dry_run`, `x_cycle` (record due metrics and replies)
  and `x_publish`.
- **xapi** is X's hosted MCP server at `https://api.x.com/mcp`, reached through
  `xurl` v1.3.2. It is for reading. Step 7 denies every tool it does not mark
  read-only.

Every step below that touches a credential, a key or an account runs in the owner's
own terminal, not in a Claude session. `python3 scripts/x_setup.py doctor` checks
each step and prints `ok` or `todo` for each; it prints no secret.

## What a dispatch must pass

`x_publish` sends nothing to X unless every row holds. Each row names the code that
enforces it and the test that fails when that code is removed.

| | Condition | Enforced in | Test (killed mutants) |
|---|---|---|---|
| 1 | The caller names the revision it reviewed (12+ hex characters of it) | `x_gate_mcp.py` `publish` | `test_the_gate_holds_the_credentials_and_never_returns_them` (G2) |
| 2 | That revision carries an approval row | `distribute.py` `dispatch_preconditions` | `test_dispatch_refuses_without_an_approval_or_a_clean_pushed_tree` (M8) |
| 3 | The approval carries an SSH signature, by a signing key on GitHub account Cubits11, over the action, draft id, revision, digest of the posts and the principal | `verify_approval` | `test_only_an_owner_signature_admits_a_dispatch` (M4) |
| 4 | The tree is clean and HEAD is on a remote | `dispatch_preconditions` | the same test (M9, M10) |
| 5 | The revision was not published, in whole or in part | `dispatch_preconditions` | `test_partial_thread_is_recorded_and_blocks_redispatch` (M5, M7) |
| 6 | `GET /2/users/me` with the credentials returns the recorded principal, before the first post | `check_principal` | `test_publish_refuses_credentials_that_act_as_another_account` (M1) |

After posting, the gate fetches each post back and records whether its text matches
the approved text (`readback`; `test_readback_matches_what_was_approved_and_flags_what_was_not`;
M2, M3, M6). The comparison expands X's t.co links from the post's own entities and
decodes `&amp;`, so a post with a link is not reported as altered. A thread that fails
partway is recorded as `PARTIAL` with the ids already live, and blocks re-dispatch.

## Where the secrets are, and what keeps a session from them

| Secret | File | Used by | Kept from a session by |
|---|---|---|---|
| OAuth 1.0a publishing keys (four) | `~/.config/glassroot/x-credentials`, mode 600 | xgate, when a tool needs them | `sandbox.credentials.files` deny; `Read` and `Edit` deny rules; no tool returns them |
| Approval signing key | `~/.config/glassroot/approval-key` | `ssh-keygen`, in the owner's terminal | the same entries |
| xurl OAuth 2.0 token and app secret | `~/.xurl/auth.yml`, plaintext, mode 600 | xurl | `sandbox.credentials.files` deny; `Read`, `Edit` and `Bash(xurl *)` deny rules |

The gate's MCP configuration gives it the path of the credentials file, not the
values. Once step 1 removes them from the shell that starts Claude Code, the values
never enter Claude Code's environment, so its shell and its other MCP servers do not
inherit them.

A session can write anywhere in the repository, so the processes that hold
credentials load nothing from it by name:

- `x_gate_mcp.py` removes every repository directory from `sys.path` before its
  first import and compiles `distribute.py` from its source text, so no cached
  bytecode is read. It refuses to start under a virtualenv inside the repository:
  that virtualenv's `pyvenv.cfg`, which a session can edit, decides where the
  standard library is loaded from.
- `distribute.py` and `x_setup.py`, run as scripts, remove the repository's
  directories from `sys.path` before they import anything. Installed packages stay.
- The launcher in `mcp-servers.json` refuses a `GLASSROOT_PYTHON` inside the
  repository before anything runs. It then fetches `origin/main` and starts the gate
  only if `scripts/distribute.py` and `scripts/x_gate_mcp.py` match it byte for byte.

Experiment X10 was predeclared in `evidence/x10_predeclared.json` before it ran. On
`main` before this change, a bytecode file planted in `scripts/` ran inside
`distribute.py` with the credentials in its environment. `git status` did not show
the file, because `*.pyc` is in `.gitignore`, and the command still exited 0.
This branch also drops `*.pyc` from `.gitignore`. Python 3 writes bytecode only
under `__pycache__/`, so a `.pyc` anywhere else now shows in `git status`, and the
clean-tree checks refuse it. That change came after X10 and was not part of its
predeclared patch.
`test_nothing_planted_in_the_repository_runs_where_credentials_are` fails if any
of these guards is removed (mutants MX1 to MX4, MX7).
`test_the_template_launcher_starts_only_the_gate_on_main` fails if either launcher
check is removed (MX5, MX6). `evidence/mutants.json` lists all 25 mutants and the
test that kills each.

## Setup

Run `python3 scripts/x_setup.py doctor` after each step.

### 0. Keep the current token

Do not revoke the OAuth 1.0a access token `distribute.py` uses. It published
try-a, try-b and try-c on 2026-09-07, and the gate uses the same four values.

### 1. Put the publishing credentials in a file

```sh
mkdir -p ~/.config/glassroot && chmod 700 ~/.config/glassroot
( umask 077 && ${EDITOR:-nano} ~/.config/glassroot/x-credentials )
```

The file holds the four lines `distribute.py` reads from the environment today:

```
X_API_KEY=...
X_API_KEY_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

The loader refuses:

- a file other users can read;
- a line that is not one of these names;
- a file that lacks one of them.

Its errors name lines and names, never values. Then remove the four variables from
any shell profile that starts Claude Code. `doctor` reports them if they are still set.

### 2. Record the account the credentials act as

```sh
X_CREDENTIALS_FILE=~/.config/glassroot/x-credentials python3 scripts/distribute.py principal
git add distribution/traction/principal.json && git commit -m "principal: record the X account id" && git push
```

It reads `GET /2/users/me` and writes the numeric id beside `PranavBhave_`. It
refuses if the credentials act as a different account. Do this before signing any
approval: the signed payload contains the id.

### 3. Make the approval key and register it on GitHub

With a FIDO2 security key, where each signature needs a touch:

```sh
ssh-keygen -t ed25519-sk -f ~/.config/glassroot/approval-key -C glassroot-approval
```

Without one, where each signature needs the passphrase. Never `ssh-add` this key:

```sh
ssh-keygen -t ed25519 -f ~/.config/glassroot/approval-key -C glassroot-approval
```

Then open GitHub → Settings → SSH and GPG keys → New SSH key, choose Key type
**Signing Key**, and paste `~/.config/glassroot/approval-key.pub`.

`verify_approval` accepts a signature from any signing key that
`https://api.github.com/users/Cubits11/ssh_signing_keys` lists. If that list also
holds an everyday signing key loaded in ssh-agent, then any process that can reach
the agent can sign approvals with it.

### 4. Apply the user settings

Merge `.claude/x/user-settings.json` into `~/.claude/settings.json`, then restart
Claude Code. User settings apply in every project on this machine, and the files
they protect are this machine's. Claude Code merges `deny` entries from every
settings scope. It honours `mask` entries, which this template does not use, only
from user or managed settings.

The rules:

- deny sandboxed commands and the file tools `~/.config/glassroot` and `~/.xurl`;
- deny `xurl` as a Bash command;
- unset the X variables for sandboxed commands;
- turn off the unsandboxed retry;
- allow the gate's two read tools;
- ask before `x_cycle` and `x_publish`.

### 5. Add the gate, once this branch is on main

```sh
python3 scripts/x_setup.py commands --python /path/to/python3
```

`--python` must be outside the repository and able to import PyYAML. The command
refuses otherwise. The command prints two `claude mcp add-json --scope local` lines
with this clone's paths filled in. Run them from the clone's root. The launcher
starts the gate only while its two files match `origin/main`, so the gate cannot
start before this branch merges.

### 6. Add the X reader

1. In the X developer portal, create an app for reading, if the account's tier
   allows a second app. Without one, use the publishing app's OAuth 2.0 client. Its
   permission level stays at Read and Write for publishing, so the reader's token
   can write.
2. Set up OAuth 2.0 user authentication for it:
   - Web App type;
   - callback `http://localhost:8080/callback`;
   - app permissions **Read**.
3. Install and authorize xurl:

```sh
go install github.com/xdevplatform/xurl@v1.3.2
read -rs XS && ~/go/bin/xurl auth apps add glassroot-read --client-id <CLIENT ID> --client-secret "$XS" \
  --redirect-uri http://localhost:8080/callback; unset XS
~/go/bin/xurl --app glassroot-read auth oauth2
~/go/bin/xurl --app glassroot-read whoami
```

- `go install` checks the module against sum.golang.org. `npx @xdevplatform/xurl`
  downloads a binary at install time without a checksum.
- `xurl auth apps add` takes the secret only as a flag, so `read -rs` keeps it out
  of shell history.
- xurl v1.3.2 requests every OAuth 2.0 scope, including posting and direct
  messages. Read the permissions X lists on the consent screen before approving.
- Run `whoami` without `-u`: with `-u NAME`, xurl looks up NAME instead of the
  token's own account.

### 7. Freeze what xapi offers, and apply the rules

```sh
python3 scripts/x_mcp_inventory.py --server xapi --out distribution/x/xapi-inventory.json \
  -- ~/go/bin/xurl --app glassroot-read mcp
```

It asks the server for every tool and records each tool's schema and hints. It
writes `xapi-inventory.permissions.json` beside the inventory:

- `allow` holds each tool the server marks `readOnlyHint: true`;
- `deny` holds every other tool.

Review the list, merge the rules into `~/.claude/settings.json`, and commit both
files. They hold tool names and schemas, and no token (see `evidence/e2e_inventory.json`).

After any update to X's server or to xurl, run the comparison:

```sh
python3 scripts/x_mcp_inventory.py --server xapi --compare distribution/x/xapi-inventory.json \
  -- ~/go/bin/xurl --app glassroot-read mcp
```

It exits 1 when a tool was added, removed or changed. A tool added after the freeze
matches no rule and falls to the session's permission mode.

### 8. Approve, sign, dispatch

```sh
python3 scripts/distribute.py approve --draft-id <id> --basis "<who approved, on what record>" \
  --sign-with ~/.config/glassroot/approval-key
```

Commit what it changed and push. In a Claude session, the sequence is:

1. `x_gate_status` shows the draft as approved and signed.
2. `x_publish_dry_run` shows the exact requests.
3. `x_publish` takes the draft id and the revision prefix that status showed. The
   session asks before it runs.

Commit the receipt it writes to `publications.json`.

## What this does not do

- It does not stop a process that runs as the owner outside Claude Code's sandbox
  from reading `~/.config/glassroot` or `~/.xurl`. The deny rules bind sandboxed
  commands and Claude's file tools only. MCP servers run outside the sandbox.
- It does not narrow the xurl token. xurl v1.3.2 hardcodes every scope. Whether the
  **Read** app permission limits an OAuth 2.0 token on X is not verified here.
- It does not prove X's own read-back. `readback_ok` compares what X returns with
  what was approved. It is recorded, not enforced after the fact: the posts are
  already live.
- It does not guard the replay record. Deleting a receipt from `publications.json`
  re-admits its approval. Removing the row takes a commit and a push, which the
  history keeps.
- It connects no ChatGPT gateway. A remote MCP endpoint for ChatGPT would need an
  OAuth 2.1 server and a public tunnel in front of the process that holds the
  credentials. Nothing here builds either.

## What was checked, and against what

Checked from primary sources:

- **xurl v1.3.2 source.** Module hash `h1:VMDfdAlsQFAoQfKol0V5toK5B6EQqygtJ4M0jBZfsN0=`,
  matching sum.golang.org. It establishes:
  - `xurl mcp` bridges stdio to `https://api.x.com/mcp` with the OAuth 2.0 user token;
  - the default redirect is `http://localhost:8080/callback`;
  - every scope is requested;
  - tokens are stored in plaintext in `~/.xurl/auth.yml`;
  - `whoami -u` looks up a name;
  - `apps add` requires the secret as a flag.
- **The Claude Code documentation** on MCP, permissions, sandboxing and settings. It
  establishes:
  - `sandbox.credentials` `deny` entries are merged from every settings scope, and
    `mask` entries are honoured only from user or managed settings;
  - deny takes precedence over ask, and ask over allow;
  - the sandbox binds the Bash tool and not MCP servers;
  - user-scope and local-scope servers are stored in `~/.claude.json`, a protected path.
- **The bridge end to end.** The real xurl v1.3.2 ran against a local stand-in for
  X's endpoint (`evidence/e2e_inventory.json`):
  - it sent the fixture token;
  - it kept the MCP session id;
  - the inventory paginated;
  - the comparison exited 0 unchanged and 1 on an added tool.

Not verifiable from the container where this was built, because its network policy
blocks `x.com` and `docs.x.com`:

- the tools X's MCP server actually exposes, and their hints (step 7 records them);
- whether X's endpoint advertises OAuth metadata, which Claude Code's own OAuth
  client would need in place of xurl;
- whether the Read app permission limits an OAuth 2.0 token;
- whether `docs.x.com/mcp` serves X's documentation over MCP;
- the response shape of `/users/{user}/ssh_signing_keys`.

  For the last one, dispatch refuses when GitHub cannot be read or lists no key.
