# Prestic
Prestic is a profile manager and task scheduler for [restic](https://restic.net/). It works on all 
operating systems supported by restic but GUI and keyring functionality may vary by platform.

![Screenshot](https://github.com/ducalex/prestic/raw/master/screenshot.png)


# Installation

Python 3.6+ and [pip](https://pip.pypa.io/en/stable/installing/) are required. Then:
- `pip install http://github.com/ducalex/prestic/tarball/master#egg=prestic`

_Note: On Ubuntu you need to [add ~/.local/bin to your path](https://bugs.launchpad.net/ubuntu/+source/bash/+bug/1588562)
 if needed and run `sudo apt install gir1.2-appindicator3-0.1` for the gui to work._

_Note: If you prefer you can also directly download `prestic.py` and put it somewhere in your PATH 
 (it is standalone)._


### Start service on login
- Windows: Put a link to `prestic-gui.exe` in your `Startup` folder (run `where prestic-gui` to locate it if needed)
- Linux: Add command `prestic --service` to your startup applications


# Usage
- Run profile-defined command: `prestic -p profilename`
- Run any restic command on profile: `prestic -p profilename snapshots`
- Start service: `prestic --service`

## Keyring
The keyring allows you to let your operating system store repository passwords encrypted in your 
user profile. This is the best password method if it is available to you.

To use, add `password-keyring = name` to your prestic profile, where `name` can be anything you 
want to identify that password. Then to set a password run the following command: 
`prestic --keyring set name`.


# Configuration file
Configuration is stored in $HOME/.prestic/config.ini. The file consists of profile blocks. You can use a 
single block or split in multiple blocks through inheritance. For example one profile could contain 
the repository configuration and then another one inherits from it and adds the backup command.

Lists can span multiple lines, as long as they are indented deeper than the first line of the value. 
 
````ini
# default is the profile used when no -p is given (it is optional)
[default]
inherit = my-profile # A single inherit can be used as an alias

[my-profile]
# (string) human-redable description:
description =
# (list) inherit options from other profiles
inherit =
# (string) Run this profile periodically (will do nothing if command not set)
# Format is: `daily at 23:59` or `monthly at 23:59` or `mon,tue,wed at 23:59`. Hourly is also possible: `daily at *:30`
schedule =
# (string) sets cpu priority (idle, low, normal, high)
cpu-priority =
# (string) sets disk io priority (idle, low, normal, high)
io-priority =
# (int) Time to wait and retry if the repository is locked (seconds)
wait-for-lock =
# (string) path to restic executable:
restic-path = restic

# (string) repository uri:
repository = sftp:user@domain:folder
# (string) repository password (plain text)
password =
# (string) repository password (retrieve from file)
password-file =
# (string) repository password (retrieve from command)
password-command =
# (string) repository password (retrieve from OS keyring/locker)
password-keyring =
# (string) ID of key to try decrypting first, before other keys
key-hint =
# (int) limits downloads to a maximum rate in KiB/s.
limit-download =
# (int) limits uploads to a maximum rate in KiB/s.
limit-upload =
# (string|list) default restic command to execute (if none provided):
command =
# (list) restic arguments for default command:
args =
# (int) be verbose (specify level)
verbose = 2
# (string) set the cache directory
cache-dir = 
# (bool) do not use the local cache
no-cache = false
# (bool) do not lock the repo
no-lock = false
# (bool) json output
json = false
# (list) Other flags applied before the restic command:
global-flags =

# (string) environment variables can be set:
env.AWS_ACCESS_KEY_ID = VALUE
env.AWS_SECRET_ACCESS_KEY = VALUE

````

### Simple configuration example
````ini
[my-repo]
description = USB Storage
repository = /media/backup
password-keyring = my-repo

[my-backup]
description = Backup to USB Storage
inherit = my-repo
schedule = daily at 12:00
command = backup
args =
    /home/user/folder1
    /home/user/folder2
flags =
    --iexclude="*.lock"

# Where the my-backup profile will run daily at 12:00
# You can also issue manual commands:
# prestic -p my-backup
# prestic -p my-repo list snapshots
# prestic -p my-backup list snapshots # this overrides my-backup's command/args/flags
````
