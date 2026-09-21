# Profiles

Adds a utility tool which loads symlinks from @/profiles

## Installation
```sh
cd ~ && git clone "repo url" && mv profiles .profiles
```

## Using the tool
profiles load ~ ~/.profiles/profiles/profile1
# Runs profiles reset and loads all of profile1's dotiles into ~ 
profiles add ~ ~/.profiles/profiles/profile2
# Ovverried profile1's dotfiles with profile2's

profiles remove ~ ~/.profiles/profiles/profile2
# Removes profile2's overrides

profiles unload ~ ~/.profiles/profiles/profile1
# Remove profile1 (like profile reset but only with profile 1s stuff)

profiles load ~/.profiles/profiles/profile2
# Runs profiles reset and loads all of profile1's dotiles into ~ 

profiles reset
# Resets to default

profiles save ~ ~/.profiles/profiles/profile3
saves known dotfiles like
~/.config

profiles save -r ~/.profiles/rules ~ ~/.profiles/profile/profile3

profiles backup-to [[-r]] ~/.profiles/profiles-backup/backup1

## How the tool works
creates symlinks to 