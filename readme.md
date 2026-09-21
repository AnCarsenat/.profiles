# Profiles

This project is intended to provide a small CLI that manages layered config profiles by creating symlinks from a profile directory into a target directory.

It is not limited to dotfiles. The same mechanism can manage shell configs, editor settings, application configs, service configuration files, and other file trees such as server configs, nginx, systemd units, or project-local configuration directories.

Important: this repository currently contains only a README and an empty `profiles/` directory. The actual `profiles` executable is not present yet, so this document should be treated as a clearer spec for the tool rather than a working implementation.

## Installation
```sh
cd ~
git clone "<repo-url>" .profiles
```

If the repo is checked out into a `profiles` folder instead of `.profiles`, you can rename it:

```sh
mv ~/profiles ~/.profiles
```

## Intended command overview

The command names below are the ones described in the original notes. They should be kept consistent and have explicit argument ordering.

```sh
profiles load <target-dir> <profile-path>
# Reset the target directory, then load all files from the named profile.

profiles add <target-dir> <profile-path>
# Apply the named profile on top of the current setup, overriding earlier files.

profiles remove <target-dir> <profile-path>
# Remove the overrides contributed by that profile.

profiles unload <target-dir> <profile-path>
# Remove a profile's managed files without affecting unrelated profiles.

profiles reset <target-dir>
# Restore the target directory to the default baseline profile.

profiles save <target-dir> <profile-path>
# Save tracked files such as ~/.config or other managed config directories into a profile.

profiles save -r <rules-path> <target-dir> <profile-path>
# Save files using a rule file that decides what to include.

profiles backup-to [-r] <backup-path>
# Back up current state, optionally using rules.
```

## Examples

```sh
profiles load ~ ~/.profiles/profiles/profile1
# Reset home and load profile1's managed files.

profiles add ~ ~/.profiles/profiles/profile2
# Override profile1 with profile2's files.

profiles remove ~ ~/.profiles/profiles/profile2
# Remove profile2's overrides.

profiles unload ~ ~/.profiles/profiles/profile1
# Remove profile1, similar to reset but only for profile1's entries.

profiles reset ~
# Restore the default baseline state.

profiles save ~ ~/.profiles/profiles/profile3
# Save dotfiles and config directories such as ~/.config into profile3.

profiles save -r ~/.profiles/rules ~ ~/.profiles/profiles/profile3

profiles backup-to ~/.profiles/profiles-backup/backup1
# Or: profiles backup-to -r ~/.profiles/profiles-backup/backup1
```

## Default rules example

Default rules should live in a dedicated rules directory, for example:

```text
~/.profiles/rules/default
```

A simple rule file can look like this:

```text
# ~/.profiles/rules/default
# Each line is a path relative to the target home directory.
# + means include, - means exclude.

+ .bashrc
+ .bash_profile
+ .bash_logout
+ .zshrc
+ .zprofile
+ .viminfo
+ .gitconfig
+ .python_history
+ .config/
+ .cargo/
+ .gradle/
+ .java/
+ .local/
+ .npm/
+ .nuget/
+ .pki/
+ .rustup/
+ .ssh/
+ .vscode/
+ .claude/
+ .copilot/
+ .cache/
+ .mozilla/
+ .thunderbird/
+ .steam/
+ .wakatime
+ .vscode-shared
+ .zcompdump
+ .steampath
+ .steampid
+
# keep these out of the saved snapshot unless explicitly wanted
- .cache/
- .Downloads/
- .Documents/
- .Pictures/
- .Videos/
- .Music/
- .Desktop/
- .Public/
```

Then save a profile using that rule set:

```sh
profiles save -r ~/.profiles/rules/default ~ ~/.profiles/profiles/default
```

This keeps the home config state reproducible without including large project or media directories by default.

## Reset model

The clean model is:

- `profiles save ~ ~/.profiles/profiles/default`
- creates the baseline snapshot
- `profiles reset ~`
- removes active layered profile symlinks and restores the `default` snapshot

If no `default` profile exists, `reset` should fail clearly instead of guessing.

Example:

```sh
profiles save ~ ~/.profiles/profiles/default
profiles load ~ ~/.profiles/profiles/profile1
profiles add ~ ~/.profiles/profiles/profile2
profiles reset ~
# restores the contents from ~/.profiles/profiles/default
```

If no baseline exists:

```sh
profiles reset ~
# error: no default profile found; run:
# profiles save ~ ~/.profiles/profiles/default
```

## What the tool should do

The intended behavior is:

- store profile definitions under a directory such as `~/.profiles/profiles/`
- create symlinks from files in a profile into the target directory
- support layered profiles, where newer profiles override older ones
- allow resetting, unloading, and removing a single profile cleanly
- save tracked files from the target directory back into a profile
- optionally use a rules file to decide which paths are included or excluded
- support generic config trees, not only home dotfiles
- run Python or shell scripts when a profile is loaded, so environment setup or config hooks can be executed

## Profile hooks

Each profile may optionally include hook scripts that run when the profile is activated:

```text
~/.profiles/profiles/profile1/
  env.sh
  env.py
  post-load.sh
  pre-load.sh
```

Suggested behavior:

- `pre-load.sh` runs before symlinks are applied
- `post-load.sh` runs after symlinks are applied
- `env.sh` or `env.py` may export environment variables or set up local runtime state
- hooks should be explicit, documented, and run in a controlled shell environment
- they should be able to set environment variables for the current session or prepare generated config files

Example:

```sh
# ~/.profiles/profiles/profile1/env.sh
export PATH="$HOME/.local/bin:$PATH"
export PROJECT_ENV="profile1"
```

```python
# ~/.profiles/profiles/profile1/env.py
import os
os.environ["PROJECT_ENV"] = "profile1"
```

The tool should not silently run arbitrary code without a clear profile hook convention.

## Intended design summary

The tool should create symlinks from a source profile directory into a target directory, while keeping a clear layer order so that later profiles can override earlier ones. A `reset` command should restore the default baseline profile, while `save` and `backup-to` should create reusable config snapshots. The same model can manage home dotfiles, server configuration directories, and any other file tree that benefits from layered, reversible configuration management.
