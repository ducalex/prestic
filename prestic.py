#!/usr/bin/env python
""" Prestic is a profile manager and task scheduler for restic """

import argparse
import configparser
import os
import math
import shlex
import shutil
import subprocess
import time
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

try:
    from base64 import b64decode
    from io import BytesIO
    from PIL import Image
    import pystray
except:
    pystray = None


PROG_NAME = 'prestic'
PROG_FOLDER = os.path.join(os.path.expanduser('~'), '.' + PROG_NAME)
PROG_ICON = (
    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAC+lBMVEVHcExIQj+FemQSIB8RFRBYLCdaQkBpLTVZTTRMVksfImRGHyFtSDZ8MzVrKStZVVZJQzhWLS+EOz2OP0FpOTE9Ix8hGRVgTUaPN0aNblZziGIzO3WDf32fREWvTE6cRUd9SUp+Q0SeR0ipRUe4Tk+9UFKyS00sLywEBQheNTqYMl9LX20VGkmCd2mSgWtlYVqaQEKvSky9VVeiR0hnWUt7blt2Z1ttZV6pl3C3olaSiE+ok3mWg26LQ0'
    b'TCUVO0TE1kSj+AcV6Je2ZHPTqLOTu0S02qTE18LS+Hd2SZinVeTUSPOz1oJix/enCvpprHsJqgmY1iaGR0MzStV1l8SEllNjd7e3vT1NT6+vv9/v/t7u+enqB8REVCNipqY1xva2bLy8twcHEXEwtdYGMiFhRrb3Pj4+dxcXRSTCrHxsBzcWRZWltiYmRVUUpiWy+/v7ptZDBzajB8czRdWjo1LyROSR8/Liu6qWCvnGMoEhRIGBpdLC+voEvfzGSQdUh3LjB+TD2blUnFs1bZxmCRNThlXTvEs1h1bDXUwV5u'
    b'ZTGQhEG9rVSNgUOCeDrNvFpmXi0AABGTg2GqlIGznYaHdmOqlH2Rf2uklkhcUzV1aE6TgGygkk2vn0yhlUiwolCwgnGQr3THWVvCV1jMWVvLpFzMt2HMw2THVliNfGm2oX+0o2y5qF69qGezn3OynIG9UFKlkXqsmIDBqI66ooi5pHvEua2+tKjPtZjYvJ7HrpG5rZ319vf////HxsW9pZLTuZqtopbe3t/KysrKwrmdinLErJPU0tPv8PB+fn5eXl6Tg3KCdWSRkZCoqKlmWUt5bWCznoe8vLyzsayXlHXc29'
    b'bJuaeGdGXo6Oefm3/q1me/r1SfkkV9cjpyaTyhj26cjkv132z44W57XUXRv1yLfjqJe1OShUrNu1neymLt12nZxV/DsFOpl2mfjmmRgV+4qE/x3Gn/7XP+5m+kl0fk0GT75G6mmFTOvGKdjGG/q3TFsHHLtnHSt6Gym4pGCc3iAAAAn3RSTlMAAggRGxgeKUI/GxQ1Tz91XYl9j18lB06kz8eRE77WyvjO+Pz++u1DJrP29ZF5q1i8/P7YiM/FotT17tDytP3+se3dsPbjuIrn98vMeLP5/NslluvQn2Lf/f77'
    b'wMyHwki4ZAyWM9rIw1PiiYp8MZf9Iqz9/J1mtu/9W2ve/vTexKqH0fVoZ92Nz3dS46Je74M/0qbflfO6lUbUWcmpq+bKfVYgAAADJ0lEQVQ4y2NgwASMTIwMVAKMjAzMDMwsrGxszDAhJnYOTi4om5uHl5ePn0FAUEhYWERUjIFRjJGBUVxCUkqai4FJhomBTUhWTk5egUFRSVlFVU1WhIFNXZRBQ1Nr/gJtHQ1dPX1RA5WFCxctMmRQUTEyWrjYyJjPxNTM3MJyydJly6ysbUxNbO0WL7czWm7PsMhuuf3CxY'
    b'uXSzg4rrBZuWr16tVr1q5b5+Tsorxw8XqjxUAFixavX6/i6ubu4LFh46bNK7esXLdp3WZPL3dhNzWVhYtVGNavX2Sk5O2joeHrt3Wb//YdQLBz17ZdAYEMGkHGwSqGDIbKSiGhfAyMYeG790Ts3bd9//7tBw5G7omKlmFgVHeO8WYQCoqNi2dgYEuIOLR3z+7DG49sOHps96G9x6MSkxg4k8VTGFhFWVKBCgLTIk+cjNpz+NTpFRt2R5w5cXCPLjOTfjIbOFbS+cXEMjL3nD1zPPLw6XPnLxyMvHjpeGRWkkxi'
    b'thg4THOyc5PyLl/Zsyfy4NVT567tv3R9z57d+bEsufz8kGhNMU8sKCy6cWX3lQObdm7evP3CpevHLxWXlMaWCECjpexc+c1bt+/cPb0T6In9+3feu3v3/q0HDyu8KiFWVFU/Wv3w5uOaJ3ee3tt8dNPGp89u1zx/8aC2rrqeHWyHYH1DY1Pzy5uvXt++/+btu2f33z9++eFVU6OIjzsrWAFfCx9La9uDjx8/vXj+/P6dzy++vPz66UU7CwM3KyLx8HS8fPDg4adPH98/efX108MPD752MiMnLrGu7ppXDx8+/P'
    b'rg851XXx9+fXHrRU8BsoKk3r6bXz99/frpy7dnr4HUpw/P+1mRFTAW9JQvffzqy4fv3+6//vDl8dI1P3jQUvCEiWt//vr1++ebN2t+//q5ZYMZet5gnuT/x3/f331H9/39u+/P9snijGJiqCo49DaDkwsQbN95JI4xSYMbLZcETjn1dyoIWE/z+FE+XSAlCT0jzZj5ZqLurFmz4nNbZz+vyWBGl2cQzVs9ewbYbcy9c6YXYMgzsPS/nssBdhljEjO2DM7SPy9DFF0GAMQBYCsctATDAAAAAElFTkSuQmCC'
)


class PresticProfile:
    aliases = {
        'repository': '-r',
        'limit-download': '--limit-download',
        'limit-upload': '--limit-upload',
        'verbose': '--verbose',
        'repository-file': 'env.RESTIC_REPOSITORY_FILE',
        'password': 'env.RESTIC_PASSWORD',
        'password-command': 'env.RESTIC_PASSWORD_COMMAND',
        'password-file': 'env.RESTIC_PASSWORD_FILE',
        'cache-dir': 'env.RESTIC_CACHE_DIR',
        'key-hint': 'env.RESTIC_KEY_HINT',
        'progress-fps': 'env.RESTIC_PROGRESS_FPS',
        'aws-access-key-id': 'env.AWS_ACCESS_KEY_ID',
        'aws-secret-access-key': 'env.AWS_SECRET_ACCESS_KEY',
        'aws-default-region': 'env.AWS_DEFAULT_REGION',
        'st-auth': 'env.ST_AUTH',
        'st-user': 'env.ST_USER',
        'st-key': 'env.ST_KEY',
        'os-auth-url': 'env.OS_AUTH_URL',
        'os-region-name': 'env.OS_REGION_NAME',
        'os-username': 'env.OS_USERNAME',
        'os-password': 'env.OS_PASSWORD',
        'os-tenant-id': 'env.OS_TENANT_ID',
        'os-tenant-name': 'env.OS_TENANT_NAME',
        'os-user-domain-name': 'env.OS_USER_DOMAIN_NAME',
        'os-project-name': 'env.OS_PROJECT_NAME',
        'os-project-domain-name': 'env.OS_PROJECT_DOMAIN_NAME',
        'os-application-credential-id': 'env.OS_APPLICATION_CREDENTIAL_ID',
        'os-application-credential-name': 'env.OS_APPLICATION_CREDENTIAL_NAME',
        'os-application-credential-secret': 'env.OS_APPLICATION_CREDENTIAL_SECRET',
        'os-storage-url': 'env.OS_STORAGE_URL',
        'os-auth-token': 'env.OS_AUTH_TOKEN',
        'b2-account-id': 'env.B2_ACCOUNT_ID',
        'b2-account-key': 'env.B2_ACCOUNT_KEY',
        'azure-account-name': 'env.AZURE_ACCOUNT_NAME',
        'azure-account-key': 'env.AZURE_ACCOUNT_KEY',
        'google-project-id': 'env.GOOGLE_PROJECT_ID',
        'google-application-credentials': 'env.GOOGLE_APPLICATION_CREDENTIALS',
        'rclone-bwlimit': 'env.RCLONE_BWLIMIT',
    }

    def __init__(self, name, properties={}):
        self.properties = {
            'name': name,
            'description': 'no description',
            'inherit': [],
            'command': [],
            'args': [],
            'flags': [],
            'wait-for-lock': '0',
            'cpu-priority': None,
            'io-priority': None,
            'schedule': None,
            'restic-path': 'restic',
            'global-flags': [],
        }

        self.defined = set('name')
        self.parents = []

        for key in properties:
            self[key] = properties[key]

        self.next_run = None
        self.last_run = None
        self.set_last_run()

    def __contains__(self, key):
        return self.aliases.get(key, key) in self.defined

    def __getitem__(self, key):
        return self.properties.get(self.aliases.get(key, key))

    def __setitem__(self, key, value):
        key = self.aliases.get(key, key)
        if type(self[key]) is list and type(value) is not list:
            value = shlex.split(value)
        self.properties[key] = value
        self.defined.add(key)

        if key == 'password-keyring' and not shutil.which('keyring'):
            print('[warning] keyring command missing, required by profile "%s"' % self['name'])

    def inherit(self, profile):
        for key in profile.defined:
            if key not in self:
                self[key] = deepcopy(profile[key])
        self.parents.append([profile['name'], profile.parents])

    def set_last_run(self, last_run=None):
        if not self['schedule']:
            return

        if not last_run or last_run < (datetime.now() - timedelta(days=1)):
            from_time = datetime.now() + timedelta(minutes=1)
        else:
            from_time = last_run

        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        sched_days = set()
        sched_months = set()
        sched_hour = 0
        sched_minute = 0

        for part in self['schedule'].lower().replace(',', ' ').split():
            if part == 'monthly':
                sched_months.update(range(1, 13))
            elif part == 'daily':
                sched_days.update(range(0, 7))
            elif part[0:3] in weekdays:
                sched_days.add(weekdays.index(part))
            else:
                time_parts = part.split(':')
                if len(time_parts) == 2:
                    sched_hour = from_time.hour + 1 if time_parts[0] == '*' else int(time_parts[0])
                    sched_minute = int(time_parts[1])

        self.next_run = from_time.replace(hour=sched_hour, minute=sched_minute, second=0)
        self.last_run = last_run

        if sched_months:  # This is wrong but for now good enough
            self.next_run += timedelta(weeks=4)

        if sched_days:
            for i in range(from_time.weekday(), from_time.weekday() + 7):
                if (i % 7) in sched_days and self.next_run >= from_time:
                    break
                self.next_run += timedelta(days=1)

    def is_pending(self):
        return self.next_run and self.next_run <= datetime.now()

    def is_runnable(self):
        return self.get_repository() and self['command']

    def get_repository(self):
        if self['repository']:
            return self['repository']
        elif self['repository-file']:
            return 'file:' + self['repository-file']
        return None

    def get_command(self, cmd_args=[]):
        args = [self['restic-path']] + self['global-flags']
        env = {}

        if self['password-keyring']:
            username = self['password-keyring']
            env['RESTIC_PASSWORD_COMMAND'] = 'keyring get %s "%s"' % (PROG_NAME, username)
            # password = keyring.get_password(PROG_NAME, username)

        for key, value in self.properties.items():
            if value != None:
                if key.startswith('env.'):
                    env[key[4:]] = str(value)
                elif key.startswith('-'):
                    args += [key, str(value)]

        # Ignore default command if any argument was given
        if self['command'] and not cmd_args:
            args += self['command']
            args += self['args']
            args += self['flags']
        else:
            args += cmd_args

        return env, args

    def run(self, cmd_args=[], capture_output=False):
        env, args = self.get_command(cmd_args)

        p_args = {'args': args, 'env': {**os.environ, **env}}

        if capture_output:
            p_args['stdout'] = subprocess.PIPE
            p_args['stderr'] = subprocess.STDOUT
            p_args['universal_newlines'] = True
            p_args['bufsize'] = 1

        self.set_last_run()

        proc_handle = subprocess.Popen(**p_args)

        cpu_priorities = {'idle': 15, 'low': 5, 'normal': 0, 'high': -15}
        io_priorities = {'idle': 3, 'low': 2, 'normal': 1, 'high': 0}

        if self['cpu-priority'] in cpu_priorities:
            pass
        if self['io-priority'] in io_priorities:
            pass
        if self['wait-for-lock']:
            pass

        return proc_handle


class PresticHandler:
    def __init__(self, base_path, profile_name, args=[]):
        self.base_path = base_path
        self.profile_name = profile_name
        self.args = args
        self.running = False

        if not os.path.isfile(self.base_path) and not self.base_path.endswith('.ini'):
            os.makedirs(os.path.join(self.base_path, 'logs'), exist_ok=True)
            os.makedirs(os.path.join(self.base_path, 'cache'), exist_ok=True)

        self.use_storage = os.path.isdir(self.base_path)

        self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        config.optionxform = lambda x: str(x) if x.startswith('env.') else x.lower()

        if config.read(self.base_path):
            print('[info] profiles loaded from file ' + self.base_path)
        elif config.read(os.path.join(self.base_path, 'config.ini')):
            print('[info] profiles loaded from folder ' + self.base_path)

        self.profiles = {
            'default': PresticProfile('default'),
            **{k: PresticProfile(k, dict(config[k])) for k in config.sections()},
        }

        inherits = True
        while inherits:
            inherits = False
            for profile in self.profiles.values():
                if not profile['inherit']:
                    continue

                inherits = True

                parent_name = profile['inherit'][0]
                parent = self.profiles.get(parent_name)

                if not parent:
                    exit(
                        '[error] profile "%s" inherits non-existing parent "%s"'
                        % (profile['name'], parent_name)
                    )
                elif parent_name == profile['name']:
                    exit('[error] profile "%s" cannot inherit from itself' % profile['name'])
                elif parent['inherit']:
                    continue

                profile.inherit(parent)
                profile['inherit'].pop(0)

    def run(self, *args):
        self.running = True

    def stop(self):
        self.running = False


class PresticService(PresticHandler):
    """ Run in service mode (task scheduler) and output to files """

    def set_task_status(self, section, values):
        if not self.status.has_section(section):
            self.status.add_section(section)
        self.status[section].update({k: str(v) for k, v in values.items()})
        if self.use_storage:
            with open(os.path.join(self.base_path, 'status.ini'), 'w') as fp:
                self.status.write(fp)

    def set_status(self, status):
        print('[info] status: %s' % status)
        if self.icon:
            self.icon.visible = True
            self.icon.title = 'Prestic backup manager\n' + (status if status else 'idle')
            # This can cause issues if the menu is currently open
            # but there is no way to know if it is...
            self.icon.update_menu()

    def notify(self, message, title=None):
        if self.icon:
            self.icon.visible = True
            self.icon.notify(message, title)
            time.sleep(1)

    def initialize(self):
        self.set_task_status('__prestic__', {'pid': os.getpid()})

        self.tasks = [t for t in self.profiles.values() if t.is_runnable()]

        for task in self.tasks:
            try:
                ts = float(self.status[task['name']].get('last_run', '0'))
                if ts and ts > 0:
                    task.set_last_run(datetime.fromtimestamp(ts))
            except:
                pass
            print('[info]    > %s will next run %s' % (task['name'], time_diff(task.next_run)))
            self.set_task_status(task['name'], {'started': 0, 'pid': 0})

    def run_task(self, task):
        self.set_status('running task %s' % task['name'])

        proc = task.run(capture_output=True)
        cmd_line = ' '.join(shlex.quote(s) for s in task.get_command()[1])
        output = []

        self.set_task_status(task['name'], {'started': datetime.now().timestamp(), 'pid': proc.pid})

        if self.use_storage:
            fn = '%s-%s.txt' % (task['name'], datetime.now().strftime('%Y.%m.%d_%H.%M'))
            log_fd = open(os.path.join(self.base_path, 'logs', fn), 'w')
            log_fd.write('Repository: %s\n' % task.get_repository())
            log_fd.write('Command line: %s\n' % cmd_line)
            log_fd.write('Date: %s\n\n' % datetime.now())
            log_fd.flush()
        else:
            log_fd = None

        for line in proc.stdout:
            print('[restic] ' + line.rstrip())
            output.append(line.rstrip())
            if log_fd:
                log_fd.write(line)
                log_fd.flush()

        ret = proc.wait()

        if log_fd:
            log_fd.write('\nProcess exit code: %d' % ret)
            log_fd.close()

        if ret == 0:
            status_txt = 'task "%s" finished' % task['name']
        elif ret == 3 and 'backup' in task['command']:
            status_txt = 'task "%s" finished with some warnings...' % task['name']
        else:
            status_txt = 'task "%s" FAILED! (exit code: %d)' % (task['name'], ret)

        self.notify(('\n'.join(output[-3:]))[-220:], 'Prestic: ' + status_txt)
        self.set_status(status_txt)
        self.set_task_status(
            task['name'],
            {'last_run': datetime.now().timestamp(), 'exit_code': ret, 'pid': 0},
        )

    def run(self, *args):
        self.running = True
        self.icon = None
        self.status = configparser.ConfigParser()
        self.status.read(os.path.join(self.base_path, 'status.ini'))

        def service_loop(*args):
            self.set_status('service started')

            while self.running:
                try:
                    next_task = None
                    sleep_time = 60

                    for task in self.tasks:
                        if task.next_run:
                            if task.is_pending():  # or 'backup' in task['command']:
                                self.run_task(task)
                            if not next_task or task.next_run < next_task.next_run:
                                next_task = task

                    if next_task:
                        sleep_time = max(
                            0, next_task.next_run.timestamp() - datetime.now().timestamp()
                        )
                        self.set_status(
                            '%s will run %s' % (next_task['name'], time_diff(next_task.next_run))
                        )

                except Exception as e:
                    print('[error] service_loop crashed: ' + repr(e))
                    self.notify(repr(e), 'Prestic service_loop crashed')
                    # raise e

                time.sleep(min(sleep_time, 60))
            self.quit()

        self.initialize()

        if pystray:

            def on_folder_click():
                os_open_file(self.base_path)

            def on_reload_click():
                # But what if a task is in progress?
                self.load_config()
                self.initialize()

            def on_quit_click():
                self.quit()

            def tasks_menu():
                for task in self.tasks:
                    next_run = time_diff(task.next_run)
                    last_run = time_diff(task.last_run)

                    if task.is_pending():
                        next_run = 'now (pending)'

                    yield pystray.MenuItem(
                        task['name'],
                        pystray.Menu(
                            pystray.MenuItem(task['description'], lambda x: x, enabled=False),
                            pystray.Menu.SEPARATOR,
                            pystray.MenuItem('Next run: %s' % next_run, lambda x: x, enabled=False),
                            pystray.MenuItem('Last run: %s' % last_run, lambda x: x, enabled=False),
                            pystray.Menu.SEPARATOR,
                            pystray.MenuItem('Run Now', lambda x: x),
                        ),
                    )

            self.icon = pystray.Icon(PROG_NAME, Image.open(BytesIO(b64decode(PROG_ICON))))
            self.icon.menu = pystray.Menu(
                pystray.MenuItem('Tasks', pystray.Menu(tasks_menu)),
                pystray.MenuItem('Open prestic folder', on_folder_click),
                pystray.MenuItem('Reload config', on_reload_click),
                pystray.MenuItem('Quit', on_quit_click),
            )
            self.icon.run(setup=service_loop)
        else:
            print('[warning] pystray not installed, gui features won\'t be available')
            service_loop()

    def quit(self, rc=0):
        print('[info] shutting down...')
        if self.icon:
            self.icon.visible = False
            # icon.stop()
        os._exit(rc)


class PresticCommand(PresticHandler):
    """ Run a single command and output to stdout """

    def run(self):
        profile = self.profiles.get(self.profile_name)
        if profile:
            cmd_line = ' '.join(shlex.quote(s) for s in profile.get_command(self.args)[1])
            print("[info] profile: %s (%s)" % (profile['name'], profile['description']))
            print("[info] running: %s\n" % cmd_line)
            exit(profile.run(self.args).wait())
        else:
            print('[error] profile "%s" does not exist' % self.profile_name)
            print('[info] Available profiles:')
            for profile in self.profiles.values():
                if profile.get_repository():
                    print(
                        '[info]    > %s (%s) [%s]'
                        % (profile['name'], profile['description'], profile.get_repository())
                    )
                    # if profile.parents:
                    #     print('[info]        > inheritance: %s' % profile.parents)
                    # if profile['command']:
                    #     print('[info]        > command: %s' % profile['command'])
                    # print('[info]        > command: %s' % str(profile.get_command()))
            exit(-1)


def time_diff(time, from_time=None):
    if not time:
        return 'never'
    from_time = from_time if from_time else datetime.now()
    time_diff = time.timestamp() - from_time.timestamp()
    return '%dd %dh %dm %s' % (
        math.floor(abs(time_diff) / 86400),
        math.floor(abs(time_diff) / 3600) % 24,
        math.floor(abs(time_diff) / 60) % 60,
        'from now' if time_diff > 0 else 'ago'
    )


def os_open_file(path):
    path = os.path.normpath(path)
    for command in [['xdg-open', path], ['start', path], ['open', path]]:
        try:
            if subprocess.run(command, shell=True).returncode == 0:
                break
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description='Restic Backup Manager', prog=PROG_NAME)
    parser.add_argument('-c', '--config', default=PROG_FOLDER, help='config file or directory')
    parser.add_argument('-p', '--profile', default='default', help='profile to use')
    parser.add_argument('--service', const=True, action="store_const", help='start service')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='restic command to run...')
    args = parser.parse_args()

    if args.service:
        handler = PresticService(args.config, args.profile, args.command)
    else:
        handler = PresticCommand(args.config, args.profile, args.command)

    handler.run()


if __name__ == '__main__':
    main()
