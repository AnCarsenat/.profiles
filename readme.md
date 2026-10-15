# profiles

Layered, reversible config profiles with symlinks.

`profiles` links files from a **profile** (a directory tree) into a **target** (your home, `/etc`, a project folder, any directory). You can stack profiles so later ones override earlier ones, remove any layer cleanly, and undo every file change.

```sh
profiles load common hypr    # home now uses common, with hypr on top
profiles add laptop          # stack laptop on top
profiles remove hypr         # hypr's files go away, common shows through again
profiles undo                # changed your mind
profiles                     # what's active and is anything wrong?
```

> **Status:** specification. This README describes the intended behavior; the executable is not implemented yet.

---

## Design principles

1. **Simple like `ls`.** No arguments shows useful state. Output is short, plain text, and scriptable (`--json`). Silence means success.
2. **Never destroy a file.** `profiles` only deletes symlinks and empty directories it created itself. Any real file it has to move out of the way is stashed and put back later.
3. **All or nothing.** Every change to files is planned, checked, then applied as one transaction. If any step fails, the file changes are rolled back.
4. **Always reversible.** Every transaction is journaled. `profiles undo` reverts the last one.
5. **Say what will happen.** Every command that changes files accepts `-n` / `--dry-run` and prints the exact plan.
6. **No surprise code.** A profile's hooks never run until you explicitly trust that profile, and must be trusted again whenever they change.

---

## Install

```sh
git clone <repo-url> ~/.profiles
mkdir -p ~/.local/bin
ln -s ~/.profiles/bin/profiles ~/.local/bin/profiles
```

This clone is the **store**. It defaults to `~/.profiles` and can be moved by setting `PROFILES_HOME`.

To manage system targets with `sudo`, also install a root-owned copy in root's `PATH`. `sudo` doesn't search `~/.local/bin`, and root should never run an executable your user account can modify:

```sh
sudo install -m 755 ~/.profiles/bin/profiles /usr/local/bin/profiles
```

This is a copy, so run it again after updating the repo.

---

## Concepts

| Term | Meaning |
|---|---|
| **Store** | `$PROFILES_HOME`, by default `~/.profiles`. Profiles live in its `profiles/` directory, rules files in `rules/`. |
| **Profile** | A directory whose `files/` tree mirrors the target. Referenced by name (`hypr`) or by path (`./my-profile`). |
| **Target** | The directory profiles are linked into. Default `~`; see below for how it is chosen. |
| **Stack** | The ordered list of active profiles for a target. The top one wins when two provide the same file. |
| **Original files** | Files in the target that `profiles` doesn't manage, whether they were there before or created since. They sit below the stack: a path no active profile provides shows its original file, if there is one. |
| **Stash** | Where original files are kept while a profile occupies their path. They come back when no active profile needs that path anymore. |

Each target has its own stack, so `~` and `/etc/nginx` are managed independently.

The target is chosen in this order: `-t`, then the `target` field of the profiles named on the command line, then `PROFILES_TARGET`, then `~`. Naming profiles with different `target` fields in one command is refused.

---

## Profile layout

```text
~/.profiles/profiles/hypr/
├── profile.toml          # optional metadata
├── files/                # mirrors the target
│   └── .config/
│       ├── hypr/hyprland.conf
│       ├── kitty/theme.conf
│       └── waybar/config.jsonc
├── env                   # optional environment variables (see "Environment")
└── hooks/                # optional scripts (see "Hooks")
    ├── pre-load
    ├── post-load
    ├── pre-unload
    └── post-unload
```

Only the contents of `files/` are linked. Metadata, hooks and `env` never end up in the target.

### `profile.toml`

All fields are optional.

```toml
description = "Hyprland session"
requires    = ["common"]          # stacked below this profile automatically
conflicts   = ["niri"]            # refuse to be active at the same time (both ways)
target      = "~"                 # default target for this profile
fold        = [".config/nvim"]    # link this directory as a whole (see below)
```

`requires`: loading or adding `hypr` puts `common` directly below it if `common` isn't already active. Removing `common` while `hypr` is active is refused; remove both together instead. Removing `hypr` leaves `common` active.

### Files vs. folded directories

By default `profiles` links **files**, creating real directories as needed. This lets several profiles contribute to the same directory: `common` can provide `.config/kitty/kitty.conf` while `hypr` provides `.config/kitty/theme.conf`.

A directory listed in `fold` is linked as a single symlink instead. Use this for self-contained configs that no other profile adds to.

- Files a **lower** profile provides inside a folded directory are hidden by the fold, as with any override.
- If a **higher** profile provides a file inside a folded directory, the plan fails with a conflict rather than guessing.
- If two active profiles fold the same directory, the higher one wins, as for files.
- If an original directory exists at that path, it is stashed as a whole.

---

## Commands

```text
profiles [status]                 Show the target, stack and link health
profiles ls [<profile>]           List profiles, or the files one provides
profiles which <path>...          Show which profile provides a path

profiles load <profile>...        Replace the stack with these profiles
profiles add <profile>...         Put profiles on top of the stack
profiles remove <profile>...      Take profiles out of the stack   (alias: unload)
profiles reset                    Remove every profile; only original files remain
profiles sync [<path>...]         Re-apply the stack (after changing a profile's file list or profile.toml)

profiles new <profile>            Create an empty profile
profiles save [--adopt] [--include-secrets] [-r <rules>] <profile> [<path>...]
                                  Copy (or move) files from the target into a profile
profiles backup [-r <rules>] <dir>  Copy the target's current files to a directory

profiles diff [<profile>...]      Like --dry-run: show what sync, or loading these profiles, would change
profiles doctor                   Find and explain problems
profiles undo [<id>]              Revert the last transaction, or back to <id>
profiles log                      Show the transaction journal

profiles trust <profile>          Allow a profile's hooks to run
profiles env [--write-environment-d]  Print (or write) environment variables for the active stack
```

Paths can be absolute (`~/.config/hypr`) or relative to the target (`.config/hypr`).

Editing a file that is already in a profile takes effect immediately, since the target links to it. Adding, removing or renaming files in a profile, or changing its `profile.toml` (such as `fold` or `requires`), needs `sync`.

`profiles` (status) and `profiles doctor` exit with code 3 when they find a problem, so scripts can check health.

### Common options

Options may appear anywhere on the command line.

| Option | Effect |
|---|---|
| `-t, --target <dir>` | Target directory (see "Concepts" for the default). |
| `-n, --dry-run` | Print the plan, change nothing. |
| `-q, --quiet` | Print only errors. |
| `-v, --verbose` | Print every action. |
| `--json` | Machine-readable output. |
| `--no-hooks` | Skip hooks for this run. |
| `-y, --yes` | Don't ask for confirmation (for scripts and session startup). |
| `--force` | Replace drifted paths. Their current contents are kept in the journal, so `undo` brings them back. |

`profiles` asks for confirmation, when run in a terminal, before a plan that stashes original files. Without a terminal and without `-y`, such a plan is refused.

Several profiles may be given at once. They are stacked in the order written, left at the bottom.

---

## Examples

### See what's going on

```console
$ profiles
target  /home/elian
stack   common → hypr → laptop
links   142 ok · 1 drifted
  drifted  .config/waybar/config.jsonc   replaced by a regular file — run `profiles doctor`
```

```console
$ profiles ls
* common    Shared shell, editor and git config
* hypr      Hyprland session
  niri      Niri session
* laptop    Battery and display tweaks
```

The `*` marks profiles active on the current target.

```console
$ profiles ls hypr
.config/hypr/hyprland.conf
.config/kitty/theme.conf         overridden by laptop
.config/waybar/config.jsonc      overrides common
```

```console
$ profiles which ~/.config/waybar/config.jsonc
hypr   (also provided by: common)
```

### Switch desktop setups

```sh
profiles load common hypr     # Hyprland setup
profiles load common niri     # Niri setup: hypr's files are removed, niri's linked
```

With `requires = ["common"]` in both profiles, this shortens to `profiles load hypr`.

To pick the setup automatically per session, call it from a session wrapper before starting the compositor:

```sh
#!/bin/sh
# /usr/local/bin/niri-session-wrapper
profiles load -qy niri
exec niri-session
```

Notes:

- `load` replaces the whole stack, so a profile like `laptop` must be listed too (`profiles load -qy niri laptop`) or be required by `niri`.
- This switches files for the whole target, so two sessions running at the same time cannot use different stacks.

### Preview, apply, undo

```console
$ profiles add laptop -n
link     .config/hypr/monitors.conf  → laptop
replace  .config/kitty/theme.conf    hypr → laptop
stash    .config/kanshi/config       (original file, restored when laptop is removed)
run      laptop/hooks/post-load      (trusted)

$ profiles add laptop
Stash 1 original file? [y/N] y
$ profiles undo
```

### Capture your current config

```sh
profiles new hypr
profiles save hypr ~/.config/hypr ~/.config/waybar
```

`save` **copies** into the profile and leaves the target untouched. It needs paths, a rules file (`-r`), or both. With both, only the files under the given paths that the rules include are saved. With neither, it refuses rather than guessing.

- If a path is a link into another profile, the file it points to is copied, so the profile gets its own version.
- If a path is already a link into the same profile, it is skipped: the file is already there.
- Files the profile already has at those paths are overwritten; the old versions are kept in the journal, so `undo` brings them back.

Add `--adopt` to move the files into the profile and replace them with links in the same transaction. The profile must be active, and adopting a path that a higher profile overrides is refused, since the link would point to that profile instead. For a new profile, activate it first; an empty profile changes nothing. So instead of the example above:

```sh
profiles new hypr
profiles add hypr
profiles save --adopt hypr ~/.config/hypr ~/.config/waybar
```

Adopted files belong to the profile from then on: removing the profile removes them from the target, and they stay in the profile.

Save using a rules file instead of listing paths:

```sh
profiles save -r ~/.profiles/rules/default common
```

### Manage something other than home

```sh
profiles -t ./my-project add dev-tools
sudo env PROFILES_HOME=/srv/profiles profiles -t /etc/nginx load web-prod
```

Targets you don't own require running as their owner (for `/etc`, that means `sudo`). `profiles` never escalates privileges itself.

Under `sudo`, `~` resolves to root's home, so pass `PROFILES_HOME` explicitly as above. State is kept in root's state directory, so always manage a given system target as root.

For system targets, the links point into the store, so:

- Every service reading those files must be able to read the store. A store inside a home directory with mode `700` is unreadable to services running as their own user, such as `nginx` workers, and hidden from services sandboxed with `ProtectHome=`. Put the store for system targets somewhere like `/srv/profiles`, owned by root, since its hooks run as root.
- Files needed early at boot (such as systemd units) must not live on a filesystem mounted later, such as a separate `/home`.

---

## Rules files

A rules file decides which paths `save` and `backup` include. Paths are relative to the target.

```text
# ~/.profiles/rules/default

# Shell and tools
+ .bashrc
+ .bash_profile
+ .zshrc
+ .zprofile
+ .gitconfig

# Application config
+ .config/**

# Never: caches, app state, large data
- .config/**/Cache/**
- .config/**/*.log
- .config/chromium/**
- .config/Code/User/workspaceStorage/**
```

- One rule per line: `+` includes, `-` excludes, `#` starts a comment.
- `*` matches within one path segment, `**` matches zero or more whole segments, and a trailing `/` matches a directory and everything in it.
- Rules are read top to bottom and **the last matching rule wins**.
- Paths not matched by any rule are excluded.
- `profiles save -r <rules> -n <profile>` lists exactly which files would be saved.

### What belongs in a profile

Profiles are for **configuration**: files you write by hand or deliberately change. They are not for **state** that applications rewrite constantly, such as `.cache`, `.local/share`, browser profiles (`.mozilla`), Steam data, toolchains (`.rustup`, `.cargo`, `.npm`) or shell history.

Many applications save files by writing a new file and renaming it over the old one. That replaces the symlink with a regular file, and the profile silently stops being in control. `profiles doctor` detects this (see "Drift"), but the real fix is to keep state out of profiles.

For a full copy of home including state, use `backup` with a rules file that includes it; `backup` copies instead of linking.

### Secrets

`save` refuses paths that usually contain secrets, such as `.ssh/id_*`, `.gnupg/`, `.netrc` and files named `*token*` or `*.key`, and reports them. Use `--include-secrets` only if the store is never pushed to a shared or public git remote.

---

## Safety model

### What `profiles` will touch

- Symlinks it created, recorded in its state file, **and** still pointing into the store. A symlink you edited or replaced by hand is left alone and reported.
- Directories it created, and only once they are empty.
- Original files that block a link: these are **moved to the stash**, never deleted, and restored when no active profile needs the path anymore.
- Files inside a profile, only through `save`, `new`, and `undo` of those.

Everything else in the target is left alone.

### Transactions

Each command that changes files:

1. Takes a lock on the target, so two runs can't interleave.
2. Builds a complete plan.
3. Checks every step: permissions, conflicts, drift, trust, free space for the stash.
4. Runs the `pre-*` hooks of every profile leaving or joining the stack, applies the plan while recording each step in the journal, then runs their `post-*` hooks.
5. If a file step fails, reverses the steps already applied and reports what went wrong.

Each step is written to the journal before it is performed. If a run is interrupted (crash, power loss, `kill`), the next command finds the unfinished transaction, rolls it back, and reports it before doing anything else.

The journal keeps the last 100 transactions per target, along with the file contents they replaced; older entries are dropped and can no longer be undone.

`profiles undo` reverts the most recent transaction, running the matching hooks (undoing an `add` runs the unload hooks). `profiles log` lists past transactions; `profiles undo <id>` reverts every transaction after `<id>`, refusing if a path has drifted since.

### Drift

Drift is when the target no longer matches what `profiles` recorded: a symlink replaced by a regular file, deleted, or pointed somewhere else. `profiles` never overwrites drifted paths without `--force`.

A **broken** link is different: the link is intact, but its file in the profile was removed or renamed, or the whole profile was deleted from the store. Broken links are reported by `profiles`, and `sync` removes them safely, since they are still links `profiles` created. A deleted profile in the stack is reported until you `remove` it. `profiles doctor` explains each case and how to resolve it:

```console
$ profiles doctor
.config/waybar/config.jsonc
  was:  link → hypr
  now:  regular file (modified 2026-10-14 18:02)
  fix:  profiles save --adopt hypr .config/waybar/config.jsonc   keep your edits in hypr
        profiles sync --force .config/waybar/config.jsonc        discard them (undo brings them back)
```

### Where state lives

```text
${XDG_STATE_HOME:-~/.local/state}/profiles/<target-id>/
├── state.json     target path, stack, and every managed link
├── journal/       one entry per transaction
└── stash/         original files, with their paths, modes and owners
```

Trust records are not tied to a target and live in `${XDG_STATE_HOME:-~/.local/state}/profiles/trust.json`.

`<target-id>` is derived from the target's absolute path. State is kept outside both the store and the target, so neither a `git pull` in the store nor a cleanup of the target can corrupt it.

---

## Hooks

Hooks are executable files in a profile's `hooks/` directory:

| Hook | Runs |
|---|---|
| `pre-load` | Before the profile's links are applied |
| `post-load` | After the profile's links are applied |
| `pre-unload` | Before the profile's links are removed |
| `post-unload` | After the profile's links are removed |

Rules:

- **Trust first.** `profiles trust <profile>` records a hash of its hooks; if any hook changes, it must be trusted again. A command that would run untrusted hooks is refused (exit code 3), unless you pass `--no-hooks`.
- Hooks run with the target as working directory and get `PROFILES_TARGET` (target path), `PROFILES_PROFILE` (profile name), `PROFILES_DIR` (profile directory) and `PROFILES_ACTION` (`load` or `unload`) in their environment.
- A failing `pre-*` hook aborts the transaction before any file changes. A failing `post-*` hook is reported (exit code 5), but the links stay as applied.
- Whatever a hook does itself is outside the transaction: `undo` can't reverse it.
- Any language works, as long as the file is executable and has a shebang.
- `--dry-run` lists which hooks would run, without running them.

---

## Environment

A hook runs as a child process, so variables it exports disappear when it exits; it cannot change your shell or session. Environment variables are declared in a profile's `env` file instead:

```sh
# ~/.profiles/profiles/hypr/env
PATH=$HOME/.local/bin:$PATH
XCURSOR_THEME=Bibata
```

One `NAME=value` per line, `#` comments, `$VAR` and `${VAR}` references, no other shell syntax. Files are applied from the bottom of the stack up, so a later profile overrides an earlier one, and `$VAR` refers to the value set so far.

`profiles` doesn't expand references itself. They are expanded where the variables are applied: by your shell for `eval`, and by systemd for `environment.d`. So `$PATH` and `$HOME` take their values from that session, not from the shell that last ran `profiles`.

Apply them in either or both ways:

```sh
# In ~/.zshrc or ~/.bashrc: current shell
eval "$(profiles env)"

# For the whole graphical session (systemd user environment)
profiles env --write-environment-d    # writes ~/.config/environment.d/90-profiles.conf
```

`--write-environment-d` only works for your home target, since there is one `environment.d` per user. After it has been used once, the file is rewritten after every change to the home stack. Changes take effect in new shells, and for `environment.d`, at the next login.

---

## Backups

```sh
profiles backup ~/backups/2026-10-15
profiles backup -r ~/.profiles/rules/full ~/backups/2026-10-15
```

`backup` copies the target's current files, following managed links to their contents, so the backup is self-contained and doesn't depend on the store. Without `-r`, it copies every path currently managed by `profiles`. The backup directory must not exist yet, or be empty.

To turn a backup into a profile (first remove any app state from it, see "What belongs in a profile"):

```sh
profiles new restored
cp -a ~/backups/2026-10-15/. ~/.profiles/profiles/restored/files/
profiles load restored
```

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error; no file was changed, or every change was rolled back |
| 2 | Bad usage |
| 3 | Refused: a conflict, drift, untrusted hooks, or a confirmation that couldn't be asked. From `status` and `doctor`: problems found |
| 4 | Target is locked by another run |
| 5 | Files changed, but a `post-*` hook failed |

---

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `PROFILES_HOME` | `~/.profiles` | Store location (profiles in `profiles/`, rules in `rules/`) |
| `PROFILES_TARGET` | `~` | Default target |
| `NO_COLOR` | unset | Disable colored output |

---

## Non-goals

- **Templating.** Profiles contain literal files. If you need generated files, have a `post-load` hook write them.
- **Package installation.** Use your package manager; a hook can call it if you want.
- **Different stacks per running session.** One target has one stack at a time.
- **Syncing between machines.** Put the store in git.