#!/usr/bin/env python3
""" Prestic is a profile manager and task scheduler for restic """

import logging
import os
import shlex
import sys
import time
import mimetypes
import json
import urllib.parse
import re
from argparse import ArgumentParser
from configparser import ConfigParser
from copy import deepcopy
from datetime import datetime, timedelta
from getpass import getpass
from http.server import BaseHTTPRequestHandler
from io import StringIO, BytesIO
from math import floor, ceil
from pathlib import Path, PurePosixPath
from subprocess import Popen, PIPE, STDOUT
from socketserver import TCPServer
from threading import Thread

try:
    from base64 import b64decode
    from PIL import Image
    import pystray
except:
    pystray = None

try:
    import keyring
except:
    keyring = None


PROG_NAME = "prestic"
PROG_HOME = Path.home().joinpath("." + PROG_NAME)
PROG_ICON = (
    b"iVBORw0KGgoAAAANSUhEUgAAACAAAAAgBAMAAACBVGfHAAAAKlBMVEU3My+7UVNMOTPDsF5mRD5sXkuunIJvUUOOdFrQzsvx22rJs5yVhlz19vZPK"
    b"bxAAAAACnRSTlMB+yr6kmH65b/0S/q8VwAAAWpJREFUKM+Vkb9Lw0AUx4+jha6Z7BhKCtlPHUIW01Q6lpiAzoVb0g6FapYMrW20f4AUhGaKotwfEJ"
    b"Czi4XEH3GzQpH7X7xrmypuPnj33vvA3b33fQD83yCUV8ESoeI4wDbrIrXHBqcN6RJ0JSmAFjxIetVAlSQJcJeU8SFCens0yIHpJwjt41F3A8pm4mL"
    b"s4tQcrEDZUF0qLJYVAXYMcMKWvGSsDxQPmA0ZhtdskjwswwVQLFBROUjZNOt8vi+AzXsqNYthzKZ+Zzn7ADbvsWgUXhh79CljVxVHTFFXk3BCcTz7"
    b"6tl1MZen6ekb/zX1tehUXPG0KPMT2s4QufP4o4XekUb0ecZr5JiyUKKqEYKyV0JuZLjWiAOic7/diFZEvMg0Et3LG6CtAdndADhEJOIAPeVCqy2EW"
    b"lyhfg5KlLoU07i5XcXFSqBnIOdESTDG43mwBfAscKzqcO9nfbWAn8fGL3D+Z8E1K0+/AZb2itxu6ZQTAAAAAElFTkSuQmCC"
)
PROG_BUILD = "$Format:%h$"


class Profile:
    _options = [
        # (key, datatype, remap, default)
        ("inherit", "list", None, []),
        ("description", "str", None, "no description"),
        ("repository", "str", "flag.repo", None),
        ("repository-file", "str", "flag.repository-file", None),
        ("password", "str", "env.RESTIC_PASSWORD", None),
        ("password-command", "str", "env.RESTIC_PASSWORD_COMMAND", None),
        ("password-file", "str", "env.RESTIC_PASSWORD_FILE", None),
        ("password-keyring", "str", None, None),
        ("executable", "list", None, ["restic"]),
        ("command", "list", None, []),
        ("args", "list", None, []),
        ("schedule", "str", None, None),
        ("notifications", "bool", None, True),
        ("wait-for-lock", "str", None, None),
        ("cpu-priority", "str", None, None),
        ("io-priority", "str", None, None),
        ("limit-upload", "size", None, None),
        ("limit-download", "size", None, None),
        ("verbose", "int", "flag.verbose", None),
        ("no-cache", "bool", "flag.no-cache", None),
        ("no-lock", "bool", "flag.no-lock", None),
        ("option", "list", "flag.option", None),
        ("cache-dir", "str", "env.RESTIC_CACHE_DIR", None),
        ("key-hint", "str", "env.RESTIC_KEY_HINT", None),
    ]
    # Break down _options for easier access
    _keymap = {key: remap or key for key, datatype, remap, default in _options}
    _types = {remap or key: datatype for key, datatype, remap, default in _options}
    _defaults = {remap or key: default for key, datatype, remap, default in _options}

    def __init__(self, name, properties={}):
        self._properties = {"name": name}
        self._parents = []
        self.last_run = None
        self.next_run = None

        for key in properties:
            self[key] = properties[key]

    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, key):
        key = self._keymap.get(key, key)
        return self._properties.get(key, self._defaults.get(key))

    def __setitem__(self, key, value):
        key = self._keymap.get(key, key)
        datatype = self._types.get(key)
        if datatype == "list":
            self._properties[key] = shlex.split(value) if type(value) is str else list(value)
        elif datatype == "bool":
            self._properties[key] = value in [True, "true", "on", "yes", "1"]
        elif datatype == "size":  # if unit is not specified, KB is assumed.
            self._properties[key] = int(value) if str(value).isnumeric() else (parse_size(value) / 1024)
        else:  # if datatype == "str":
            self._properties[key] = str(value)
        if key == "schedule":
            self.next_run = self.find_next_run()

    def is_defined(self, key):
        return self._keymap.get(key, key) in self._properties

    def inherit(self, profile):
        for key, value in profile._properties.items():
            if not self.is_defined(key) and profile.is_defined(key):
                self[key] = deepcopy(value)
        self._parents.append([profile.name, profile._parents])

    def find_next_run(self, from_time=None):
        if self.schedule:
            weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

            from_time = (from_time or datetime.now()) + timedelta(minutes=1)
            next_run = from_time.replace(hour=0, minute=0, second=0)

            m_days = set(range(1, 32))
            w_days = set()

            for part in self.schedule.lower().replace(",", " ").split():
                if part == "monthly":
                    m_days = {1}
                elif part == "weekly":
                    w_days = {0}
                elif part == "daily":
                    w_days = {0, 1, 2, 3, 4, 5, 6}
                elif part == "hourly":
                    next_run = next_run.replace(hour=int(from_time.hour + 1), minute=int(0))
                elif part[0:3] in weekdays:
                    w_days.add(weekdays.index(part[0:3]))
                elif len(part.split(":")) == 2:
                    hour, minute = part.split(":")
                    hour = from_time.hour + 1 if hour == "*" else int(hour)
                    next_run = next_run.replace(hour=int(hour), minute=int(minute))

            for i in range(from_time.weekday(), from_time.weekday() + 32):
                if next_run.day in m_days and ((i % 7) in w_days or not w_days):
                    if next_run >= from_time:
                        return next_run
                next_run += timedelta(days=1)

        return None

    def set_last_run(self, last_run=None):
        self.last_run = last_run or datetime.now()
        self.next_run = self.find_next_run(self.last_run)

    def is_pending(self):
        return self.next_run and self.next_run <= datetime.now()

    def is_runnable(self):
        return self.command and (self["repository"] or self["repository-file"])

    def get_command(self, cmd_args=[]):
        args = [*self["executable"]]
        env = {}

        for key in self._properties:  # and defaults?
            if key.startswith("env."):
                env[key[4:]] = self[key]
            elif key.startswith("flag."):
                values = self[key] if type(self[key]) is list else [self[key]]
                for val in values:
                    if type(val) is bool and val:
                        args += [f"--{key[5:]}"]
                    elif type(val) is str:
                        args += [f"--{key[5:]}={val}"] if val.isalnum() else [f"--{key[5:]}", val]

        if self["password-keyring"]:
            username = shlex.quote(self["password-keyring"])
            python = shlex.quote(sys.executable)
            env["RESTIC_PASSWORD_COMMAND"] = f"{python} -m keyring get {PROG_NAME} {username}"
            if not keyring:
                logging.warning(f"keyring module missing, required by profile {self.name}")

        if self["limit-upload"]:
            args += [f"--limit-upload={self['limit-upload']}"]
        if self["limit-download"]:
            args += [f"--limit-download={self['limit-download']}"]
        if self["limit-upload"] or self["limit-download"]:
            env["RCLONE_BWLIMIT"] = f"{self['limit-upload'] or 'off'}:{self['limit-download'] or 'off'}"

        # Ignore default command if any argument was given
        if cmd_args:
            args += cmd_args
        elif self.command:
            args += self.command
            args += self.args

        return env, args

    def run(self, cmd_args=[], text_output=True, stdout=None, stderr=None):
        env, args = self.get_command(cmd_args)

        p_args = {"args": args, "env": {**os.environ, **env}, "stdout": stdout, "stderr": stderr}

        if text_output:
            p_args["universal_newlines"] = True
            p_args["encoding"] = "utf-8"
            p_args["errors"] = "replace"
            p_args["bufsize"] = 1

        if sys.platform == "win32":
            cpu_priorities = {"idle": 0x0040, "low": 0x4000, "normal": 0x0020, "high": 0x0080}
            p_args["creationflags"] = cpu_priorities.get(self["cpu-priority"], 0)
            # do not create a window/console if we capture ALL output
            if stdout != None or stderr != None:
                p_args["creationflags"] |= 0x08000000  # CREATE_NO_WINDOW

        self.last_run = datetime.now()
        self.next_run = None  # Disable scheduling while running

        logging.info(f"running: {' '.join(shlex.quote(s) for s in args)}\n")
        return Popen(**p_args)


class BaseHandler:
    def __init__(self, config_file=None):
        self.config_file = config_file or Path(PROG_HOME, "config.ini")
        self.running = False
        self.load_config()

    def load_config(self):
        config = ConfigParser()
        status = ConfigParser()
        config.optionxform = lambda x: str(x) if x.startswith("env.") else x.lower()

        if config.read(self.config_file):
            logging.info(f"configuration loaded from file {self.config_file}")
        elif config.read(Path(__file__).parent.joinpath("prestic.ini")):
            logging.info(f"configuration loaded from file prestic.ini")

        status.read(Path(PROG_HOME, "status.ini"))

        self.profiles = {
            "default": Profile("default"),
            **{k: Profile(k, dict(config[k])) for k in config.sections()},
        }

        # Process profile inheritance
        inherits = True
        while inherits:
            inherits = False
            for name, profile in self.profiles.items():
                if not profile["inherit"]:
                    continue

                inherits = True

                parent_name = profile["inherit"][0]
                parent = self.profiles.get(parent_name)

                if not parent:
                    exit(f"[error] profile {name} inherits non-existing parent {parent_name}")
                elif parent_name == profile.name:
                    exit(f"[error] profile {name} cannot inherit from itself")
                elif parent["inherit"]:
                    continue

                profile.inherit(parent)
                profile["inherit"].pop(0)

        self.tasks = [t for t in self.profiles.values() if t.is_runnable()]
        self.state = status

        # Setup task status
        for task in self.tasks:
            try:
                self.save_state(task.name, {"started": 0, "pid": 0}, False)
                task.set_last_run(datetime.fromtimestamp(status[task.name].getfloat("last_run")))
                # Do not try to catch up if the task was supposed to run less than one day ago
                # and is supposed to run again today
                if task.next_run > datetime.now() - timedelta(
                    days=1
                ) and task.find_next_run() < datetime.now() + timedelta(hours=12):
                    task.next_run = task.find_next_run()
            except:
                pass

    def save_state(self, section, values, write=True):
        if not self.state.has_section(section):
            self.state.add_section(section)
        self.state[section].update({k: str(v) for k, v in values.items()})
        if write:
            with Path(PROG_HOME, "status.ini").open("w") as fp:
                self.state.write(fp)

    def dump_profiles(self):
        print(f"\nAvailable profiles:")
        for name, profile in self.profiles.items():
            if repository := profile["repository"] or profile["repository-file"] or None:
                print(f"    > {name} ({profile.description}) [{repository}] {' '.join(profile.command)}")

    def run(self, profile=None, args=[]):
        logging.info(f"running {args} on {profile}!")
        self.running = True

    def stop(self):
        logging.info("shutting down...")
        self.running = False


class ServiceHandler(BaseHandler):
    """Run in service mode (task scheduler) and output to log files"""

    def set_status(self, message, busy=False):
        if message != self.status:
            logging.info(f"status: {message}")
            self.status = message

    def notify(self, message, title=None):
        pass

    def proc_scheduler(self):
        # TO DO: Handle missed tasks more gracefully (ie computer sleep). We shouldn't run a
        # missed task if its next schedule is soon anyway (like we do in load_config)
        logging.info("scheduler running with %d tasks" % len(self.tasks))
        for task in self.tasks:
            logging.info(f"    > {task.name} will next run {time_diff(task.next_run)}")

        while self.running:
            next_task = None
            sleep_time = 60
            try:
                for task in self.tasks:
                    if not task.next_run:
                        continue
                    if task.is_pending():  # or 'backup' in task['command']:
                        self.run_task(task)
                    if not next_task:
                        next_task = task
                    elif task.next_run and next_task.next_run and task.next_run < next_task.next_run:
                        next_task = task

                if next_task:
                    sleep_time = max(0, (next_task.next_run - datetime.now()).total_seconds())
                    self.set_status(f"{next_task.name} will run {time_diff(next_task.next_run)}")
                else:
                    self.set_status(f"no scheduled task")

            except Exception as e:
                logging.error(f"service_loop crashed: {type(e).__name__} '{e}'")
                self.notify(str(e), f"Unhandled exception: {type(e).__name__}")
                # raise e

            time.sleep(min(sleep_time, 10))

    def proc_webui(self):
        # TO DO: Stop the web server after a period of inactivity (to release memory but also for security)
        time.sleep(1)  # Wait for the gui to come up so we can show errors
        try:
            WebRequestHandler.profiles = self.profiles
            WebRequestHandler.token = ""
            self.webui_server = TCPServer(self.webui_listen, WebRequestHandler)
            self.webui_listen = self.webui_server.server_address  # In case we use automatic assignment
            self.webui_url = f"http://{self.webui_listen[0]}:{self.webui_listen[1]}/?token={WebRequestHandler.token}"
            logging.info(f"webui running at {self.webui_url}")
            self.webui_server.serve_forever()
        except Exception as e:
            logging.error(f"webui error: {type(e).__name__} '{e}'")
            self.notify(str(e), "Webui couldn't start")

    def run_task(self, task):
        try:
            log_file = Path(PROG_HOME, "logs", f"{time.strftime('%Y.%m.%d_%H.%M')}-{task.name}.txt")
            log_file.parent().mkdir(parents=True, exist_ok=True)
            log_fd = log_file.open("w", encoding="utf-8", errors="replace")
        except:
            log_file = Path("-")
            log_fd = None

        if "backup" in task.command:  # and task.verbose < 2:
            log_filter = re.compile("^unchanged\s/")
        else:
            log_filter = None

        self.save_state(task.name, {"started": time.time(), "log_file": log_file.name})
        self.set_status(f"running task {task.name}", True)
        if task["notifications"]:
            self.notify(f"Running task {task.name}")

        def task_log(line):
            if log_fd:
                log_fd.write(f"[{datetime.now()}] {line}\n")
                log_fd.flush()
            else:
                logging.info(f"[task_log] {line}")

        def try_run(cmd_args=[]):
            proc = task.run(cmd_args, stdout=PIPE, stderr=STDOUT)
            output = []

            self.save_state(task.name, {"pid": proc.pid})

            task_log(f"Repository: {task['repository'] or task['repository-file']}")
            task_log(f"Command line: {' '.join(shlex.quote(s) for s in proc.args)}")
            task_log(f"Restic output:\n ")

            for line in proc.stdout:
                line = line.rstrip("\r\n")
                if not log_filter or not log_filter.match(line):
                    output.append(line)
                    task_log(line)

            ret = proc.wait()

            task_log(f" \nRestic exit code: {ret}\n ")

            return output, ret

        output, ret = try_run()

        # This naive method could be a problem, we should check the lock time ourselves
        # see https://github.com/restic/restic/pull/2391
        if ret == 1 and "remove stale locks" in output[-1]:
            logging.warning("task failed because of a stale lock. attempting unlock...")
            if try_run(["unlock"])[1] == 0:
                output, ret = try_run()

        task.set_last_run()
        if log_fd:
            log_fd.close()

        if ret == 0:
            status_txt = f"task {task.name} finished successfully."
        elif ret == 3 and "backup" in task.command:
            status_txt = f"task {task.name} finished with some warnings..."
        else:
            status_txt = f"task {task.name} FAILED with exit code: {ret} !"
            if log_file.exists():
                os_open_url(Path(PROG_HOME, "logs", log_file))

        self.save_state(task.name, {"last_run": time.time(), "exit_code": ret, "pid": 0})
        self.set_status(status_txt)
        if task["notifications"] or ret != 0:
            self.notify(("\n".join(output[-4:]))[-220:].strip(), status_txt)

    def run(self, profile, args=[]):
        self.webui_listen = ("127.0.0.1", 8711)  # 0
        self.webui_server = None
        self.webui_url = None
        self.running = True
        self.status = None

        self.save_state("__prestic__", {"pid": os.getpid()})
        self.set_status("service started")

        Thread(target=self.proc_scheduler, name="scheduler").start()
        Thread(target=self.proc_webui, name="webui").start()

        if type(self) is ServiceHandler:
            while self.running:
                time.sleep(60)

    def stop(self, rc=0):
        logging.info("shutting down...")
        try:
            self.running = False
            if self.webui_server:
                self.webui_server.shutdown()
        finally:
            os._exit(rc)


class TrayIconHandler(ServiceHandler):
    """Show a tray icon when running in service mode (task scheduler)"""

    def set_status(self, message, busy=False):
        if message != self.status:
            self.gui.title = "Prestic backup manager\n" + (message or "idle")
            icon = self.icons["busy" if busy else "norm"]
            if self.gui.icon is not icon:
                self.gui.icon = icon
            # This can cause issues if the menu is currently open
            # but there is no way to know if it is...
            self.gui.update_menu()
        super().set_status(message, busy)

    def notify(self, message, title=None):
        if self.gui.HAS_NOTIFICATION:
            self.gui.notify(message, f"{PROG_NAME}: {title}" if title else PROG_NAME)
            time.sleep(5)  # 0.5s needed for stability, rest to give time for reading

    def run(self, profile, args=[]):
        try:
            icon = Image.open(BytesIO(b64decode(PROG_ICON))).convert("RGBA")
            self.icons = {
                "norm": icon,
                "busy": Image.alpha_composite(Image.new("RGBA", icon.size, (255, 0, 255, 255)), icon),
                "fail": Image.alpha_composite(Image.new("RGBA", icon.size, (255, 0, 0, 255)), icon),
            }

            def make_cb(fn, arg): # Binds fn to arg
                return lambda: fn(arg)

            def on_run_now_click(task):
                if task["notifications"]:
                    self.notify(f"{task.name} will run next")
                task.next_run = datetime.now()

            def on_log_click(task):
                if log_file := self.state[task.name].get("log_file", ""):
                    os_open_url(Path(PROG_HOME, "logs", log_file))

            def tasks_menu():
                for task in self.tasks:
                    task_menu = pystray.Menu(
                        pystray.MenuItem(task.description, lambda: 1),
                        pystray.Menu.SEPARATOR,
                        pystray.MenuItem(f"Next run: {time_diff(task.next_run)}", lambda: 1),
                        pystray.MenuItem(f"Last run: {time_diff(task.last_run)}", make_cb(on_log_click, task)),
                        pystray.Menu.SEPARATOR,
                        pystray.MenuItem("Run Now", make_cb(on_run_now_click, task)),
                    )
                    yield pystray.MenuItem(task.name, task_menu)

            self.gui = pystray.Icon(
                name=PROG_NAME,
                icon=icon,
                menu=pystray.Menu(
                    pystray.MenuItem("Tasks", pystray.Menu(tasks_menu)),
                    pystray.MenuItem("Open web interface", lambda: os_open_url(self.webui_url)),
                    pystray.MenuItem("Open prestic folder", lambda: os_open_url(PROG_HOME)),
                    pystray.MenuItem("Reload config", lambda: (self.load_config())),
                    pystray.MenuItem("Quit", lambda: self.stop()),
                ),
            )
            super().run(profile, args)
            self.gui.run()
        except Exception as e:
            logging.warning("pystray (gui) couldn't be initialized...")
            logging.warning(f"proc_gui error: {type(e).__name__} '{e}'")

    def stop(self, rc=0):
        self.gui.visible = False
        super().stop(rc)


class KeyringHandler(BaseHandler):
    """Keyring manager (basically a `keyring` clone)"""

    def run(self, profile, args=[]):
        if len(args) != 2 or args[0] not in ["get", "set", "del"]:
            exit("Usage: get|set|del username")
        try:
            if args[0] == "get":
                ret = keyring.get_password(PROG_NAME, args[1])
                if ret is None:
                    exit("Error: Not found")
                print(ret, end="")
            elif args[0] == "set":
                keyring.set_password(PROG_NAME, args[1], getpass())
                print("OK")
            elif args[0] == "del":
                keyring.delete_password(PROG_NAME, args[1])
                print("OK")
        except Exception as e:
            exit(f"Error: {repr(e)}")


class CommandHandler(BaseHandler):
    """Run a single command and output to stdout"""

    def run(self, profile_name, args=[]):
        profile = self.profiles.get(profile_name)
        if profile:
            logging.info(f"profile: {profile.name} ({profile.description})")
            try:
                exit(profile.run(args).wait())
            except OSError as e:
                logging.error(f"unable to start restic: {e}")
        else:
            logging.error(f"profile {profile_name} does not exist")
            self.dump_profiles()
        exit(-1)


class WebRequestHandler(BaseHTTPRequestHandler):
    """Handler"""

    icons = {"file": "&#128196;", "dir": "&#128193;", "snapshot": "&#128190;"}
    template = """
        <html>
        <head>
            <style>
                h2 {text-align:center;}
                pre {width: min-content;}
                table,pre {margin: 0 auto;}
                table {border-collapse: collapse; }
                thead th {text-align: left; font-weight: bold;}
                tbody tr:hover {background: #eee;}
                table, td, tr, th { border: 1px solid black; padding: .1em .5em;}
            </style>
        </head>
        <body>%s</body>
        </html>
    """

    profiles = {}
    snapshots = {}
    snapshots_data = {}

    def do_respond(self, code, content, content_type="text/html"):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        if type(content) is str:
            segments = []
            path = PurePosixPath(self.path)
            while str(path) != "/":
                segments.append(f"<a href='{path}'>{path.name}</a>")
                path = path.parent
            segments.append("<a href='/'>Home</a>")
            content = f"<h2>{' / '.join(reversed(segments))}</h2>" + content
            self.wfile.write((self.template % content).encode("utf-8"))
        elif type(content) is bytes:
            self.wfile.write(content)
        else:
            while True:
                data = content.read(64 * 1024)
                if not data:
                    break
                self.wfile.write(data)

    def do_GET(self):
        (scheme, netloc, path, query, fragment) = urllib.parse.urlsplit(self.path)
        path = PurePosixPath("/", urllib.parse.unquote(path))

        profile_name = path.parts[1] if len(path.parts) > 1 else ""
        snapshot_id = path.parts[2] if len(path.parts) > 2 else ""
        browse_path = str(PurePosixPath("/", *(path.parts[3:] if len(path.parts) > 3 else [""])))

        profile = self.profiles.get(profile_name)

        def gen_table(rows, header=None):
            content = "<table>"
            if header:
                content += "<thead><tr><th>" + ("</th><th>".join(header)) + "</th></tr></thead>"
            content += "<tbody>"
            for row in rows:
                content += "<tr><td>" + ("</td><td>".join(row)) + "</td></tr>"
            content += "</tbody></table>"
            return content

        if not profile_name:
            """list profiles"""
            table = []
            for p in self.profiles.values():
                if p["repository"] or p["repository-file"]:
                    table.append(
                        [
                            p["name"],
                            p["description"],
                            p["repository"],
                            f"<a href='/{p['name']}'>run now</a> | <a href='/{p['name']}'>view logs</a>",
                            f"<a href='/{p['name']}'>snapshots</a> | ...",
                        ]
                    )
            self.do_respond(200, gen_table(table, ["Name", "Description", "Repository", "Actions", "Restic"]))

        elif not profile:
            self.do_respond(404, "profile not found")

        elif not snapshot_id:
            """list snapshots"""
            proc = profile.run(["snapshots", "--json"], stdout=PIPE)
            if snapshots := json.load(proc.stdout):
                snapshots = sorted(snapshots, key=lambda x: x["time"])
                prev_id = None
                table = []
                for s in snapshots:
                    base_url = f"/{profile['name']}/{s['short_id']}"
                    table.append(
                        [
                            str(s["short_id"]),
                            str(format_date(s["time"])),
                            str(s["hostname"]),
                            str(s["tags"]),
                            str(s["paths"]),
                            f"<a href='{base_url}'>browse</a> | <a href='{base_url}?diff={prev_id}'>diff</a>",
                        ]
                    )
                    prev_id = s["short_id"]
                table.reverse()
                self.do_respond(200, gen_table(table, ["ID", "Time", "Host", "Tags", "Paths", "Actions"]))
            else:
                self.do_respond(200, "No snapshot found")

        elif query.startswith("diff="):
            """show snapshot diff"""
            proc = profile.run(["diff", snapshot_id, query[5:]], stdout=PIPE, text_output=False)
            self.do_respond(200, proc.stdout, "text/plain")

        elif query.startswith("dump="):
            """serve file"""
            proc = profile.run(["dump", snapshot_id, browse_path], stdout=PIPE, text_output=False)
            self.do_respond(200, proc.stdout, mimetypes.guess_type(browse_path))

        else:
            """list files"""
            if snapshot_id not in self.snapshots_data:
                self.snapshots_data[snapshot_id] = files = {}
                proc = profile.run(["ls", "--json", snapshot_id], stdout=PIPE)
                for line in proc.stdout:
                    f = json.loads(line)
                    if f and f["struct_type"] == "node":
                        parent_path = str(PurePosixPath(f["path"]).parent)
                        if parent_path not in files:
                            files[parent_path] = []
                        files[parent_path].append([f["name"], f["type"], f["size"] if "size" in f else "", f["mtime"]])

            if browse_path not in self.snapshots_data[snapshot_id]:
                if str(PurePosixPath(browse_path).parent) in self.snapshots_data[snapshot_id]:
                    proc = profile.run(["dump", snapshot_id, browse_path], stdout=PIPE, text_output=False)
                    self.do_respond(200, proc.stdout, mimetypes.guess_type(browse_path))
                else:
                    self.do_respond(404, "path not found")
                return

            base_url = PurePosixPath("/", profile.name, snapshot_id, browse_path[1:])
            files = sorted(self.snapshots_data[snapshot_id][browse_path], key=lambda x: x[1])
            table = []

            if len(base_url.parts) >= 4:
                table.append([f"{self.icons['dir']} <a href='{base_url.parent}'>..</a>", "", "", ""])

            for name, type, size, mtime in files:
                nav_link = f"{self.icons.get(type, '')} <a href='{base_url/name}'>{name}</a>"
                down_link = f"<a href='{base_url/name}?dump=1'>Download</a>"
                table.append([nav_link, str(size), format_date(mtime), down_link])

            self.do_respond(200, gen_table(table, ["Name", "Size", "Date modified", "Download"]))


def time_diff(time, from_time=None):
    if not time:
        return "never"
    from_time = from_time or datetime.now()
    time_diff = (time - from_time).total_seconds()
    days = floor(abs(time_diff) / 86400)
    hours = floor(abs(time_diff) / 3600) % 24
    minutes = floor(abs(time_diff) / 60) % 60
    suffix = "from now" if time_diff > 0 else "ago"
    if abs(time_diff) < 60:
        return "just now"
    return f"{days}d {hours}h {minutes}m {suffix}"


def os_open_url(path):
    if sys.platform == "win32":
        Popen(["start", str(path)], shell=True).wait()
    elif sys.platform == "darwin":
        Popen(["open", str(path)], shell=True).wait()
    else:
        Popen(["xdg-open", str(path)]).wait()


def format_date(dt):
    if type(dt) is str:
        dt = re.sub(r"\.[0-9]{3,}", "", dt)  # Python doesn't like variable ms precision
        dt = datetime.fromisoformat(dt)
    return str(dt)


def parse_size(size):
    if m := re.match(f"^\s*([\d\.]+)\s*([BKMGTP])B?$", f"{size}".upper()):
        return int(float(m.group(1)) * (2 ** (10 * "BKMGTP".index(m.group(2)))))
    elif m := re.match(f"^\s*([\d]+)\s*$", f"{size}"):
        return int(m.group(1))
    return 0


def main(argv=None):
    parser = ArgumentParser(description="Prestic Backup Manager (for restic)")
    parser.add_argument("-c", "--config", default=None, help="config file")
    parser.add_argument("-p", "--profile", default="default", help="profile to use")
    parser.add_argument("--service", const=True, action="store_const", help="start service")
    parser.add_argument("--gui", const=True, action="store_const", help="start service")
    parser.add_argument("--keyring", const=True, action="store_const", help="keyring management")
    parser.add_argument("command", nargs="...", help="restic command to run...")
    args = parser.parse_args(argv)

    logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

    if args.gui:
        handler = TrayIconHandler(args.config)
    elif args.service:
        handler = ServiceHandler(args.config)
    elif args.keyring:
        handler = KeyringHandler(args.config)
    else:
        handler = CommandHandler(args.config)

    try:
        handler.run(args.profile, args.command)
    except KeyboardInterrupt:
        handler.stop()


def gui():
    # Fixes some issues when invoked by pythonw.exe (but we should use .prestic/stderr.txt I suppose)
    sys.stdout = sys.stdout or open(os.devnull, "w")
    sys.stderr = sys.stderr or open(os.devnull, "w")
    main([*sys.argv[1:], "--gui"])


if __name__ == "__main__":
    main()

# TO DO: Icon should become red until a user acknowledges it when an error occurs in a task
