# Prestic
Prestic is a profile manager and task scheduler for [restic](https://restic.net/). It works on all 
operating systems supported by restic but GUI and keyring functionality may vary by platform 
(see [keyring](https://pypi.org/project/keyring) and [pystray](https://pypi.org/project/pystray) 
for more details).

![Screenshot](https://github.com/ducalex/prestic/raw/master/screenshot.png)

# Usage

## Installation
- Install Python 3.6+
- Install dependencies: `pip install keyring pystray` (optional)
- Download `prestic.py` and put it somewhere in your PATH

### Start service on login
- Windows: Copy `service.bat` to your startup folder
- Linux: Add a link to `prestic.py --service` to your startup applications

## Command line
- Run profile-defined command: `prestic.py -p profilename`
- Run any restic command on profile: `prestic.py -p profilename snapshots`

## Keyring
The keyring allows you to let your operating system store repository passwords encrypted in your 
user profile. This is the best password method if it is available to you.

To use, add `password-keyring = name` to your prestic profile, where `name` can be anything you 
want to identify that password. Then to set a password run the following command: 
`keyring set prestic name`.


# Configuration file
Configuration is stored in $HOME/.prestic/config.ini. The file consists of profile blocks. You can use a 
single block or split in multiple blocks through inheritance. For example one profile could contain 
the repository configuration and then another one inherits from it and adds the backup command.

Lists can span multiple lines, as long as they are indented deeper than the first line of the value. 
 
````ini
# default is the profile used when no -p is given
[default]
inherit = my-profile # A single inherit can be used as an alias

[my-profile]
# (string) human-redable description:
description =
# (list) inherit options from other profiles
inherit =
# (string|list) default restic command to execute (if none provided):
command =
# (list) restic args for default command:
args =
# (list) restic flags for default command:
flags =
# (string) Run this profile periodically (will do nothing if command not set)
# Format is: `daily at 23:59` or `monthly at 23:59` or `mon,tue,wed at 23:59`. Hourly is also possible: `daily at *:30`
schedule =
# (int) Time to wait and retry if the repository is locked (seconds)
wait-for-lock =
# (string) sets cpu priority (idle, low, normal, high)
cpu-priority =
# (string) sets disk io priority (idle, low, normal, high)
io-priority =
# (int) limits downloads to a maximum rate in KiB/s.
limit-download =
# (int) limits uploads to a maximum rate in KiB/s.
limit-upload =
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
# (int) be verbose (specify level)
verbose = 2
# (list) Global flags applied before the restic command:
global-flags =
# (string) path to restic executable:
restic-path = restic
# (string) the following environment variables are supported:
aws-access-key-id =
aws-secret-access-key =
aws-default-region =
st-auth =
st-user =
st-key =
os-auth-url =
os-region-name =
os-username =
os-password =
os-tenant-id =
os-tenant-name =
os-user-domain-name =
os-project-name =
os-project-domain-name =
os-application-credential-id =
os-application-credential-name =
os-application-credential-secret =
os-storage-url =
os-auth-token =
b2-account-id =
b2-account-key =
azure-account-name =
azure-account-key =
google-project-id =
google-application-credentials =
rclone-bwlimit =
# (string) arbitrary environment variables can also be set in case one is missing above:
env.OTHER_ENV_VAR = VALUE
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
    /home/user
flags =
    --iexclude="*.lock"

# Where the my-backup profile will run daily at 12:00
# You can also issue manual commands:
# prestic -p my-backup
# prestic -p my-repo list snapshots
# prestic -p my-backup list snapshots
````
