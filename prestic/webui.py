#!/usr/bin/env python3
""" Prestic-web is a full web-based gui for restic """

from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
import logging
import mimetypes
import json
import urllib.parse
import re

from prestic import BaseHandler, Profile, time_diff, os_open_file, PIPE, STDOUT


class PresticRequestHandler(BaseHTTPRequestHandler):
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
            """ list profiles """
            table = []
            for p in self.profiles.values():
                if p["repository"] or p["repository-file"]:
                    table.append(
                        [
                            p["name"],
                            p["description"],
                            p["repository"],
                            f"<a href='/{p['name']}'>snapshots</a> | ...",
                        ]
                    )
            self.do_respond(200, gen_table(table, ["Name", "Description", "Repository", "Action"]))

        elif not profile:
            self.do_respond(404, "profile not found")

        elif not snapshot_id:
            """ list snapshots """
            proc = profile.run(["snapshots", "--json"], stdout=PIPE)
            snapshots = json.load(proc.stdout)
            if snapshots:
                snapshots = sorted(snapshots, key=lambda x: x["time"], reverse=True)
                table = []
                for s in snapshots:
                    table.append(
                        [
                            f"<a href='/{profile['name']}/{s['short_id']}'>{s['short_id']}</a>",
                            str(format_date(s["time"])),
                            str(s["hostname"]),
                            str(s["paths"]),
                        ]
                    )
                self.do_respond(200, gen_table(table, ["ID", "Created", "Host", "Paths"]))
            else:
                self.do_respond(200, "No snapshot found")

        elif query == "dump":
            """ serve file """
            proc = profile.run(["dump", snapshot_id, browse_path], stdout=PIPE, text_output=False)
            self.do_respond(200, proc.stdout, mimetypes.guess_type(browse_path))

        else:
            """ list files """
            if snapshot_id not in self.snapshots_data:
                self.snapshots_data[snapshot_id] = files = {}
                proc = profile.run(["ls", "--json", snapshot_id], stdout=PIPE)
                for line in proc.stdout:
                    f = json.loads(line)
                    if f and f["struct_type"] == "node":
                        parent_path = str(PurePosixPath(f["path"]).parent)
                        if parent_path not in files:
                            files[parent_path] = []
                        files[parent_path].append(
                            [f["name"], f["type"], f["size"] if "size" in f else "", f["mtime"]]
                        )

            if browse_path not in self.snapshots_data[snapshot_id]:
                if str(PurePosixPath(browse_path).parent) in self.snapshots_data[snapshot_id]:
                    proc = profile.run(
                        ["dump", snapshot_id, browse_path], stdout=PIPE, text_output=False
                    )
                    self.do_respond(200, proc.stdout, mimetypes.guess_type(browse_path))
                else:
                    self.do_respond(404, "path not found")
                return

            base_path = PurePosixPath("/", profile.name, snapshot_id, browse_path[1:])
            files = sorted(self.snapshots_data[snapshot_id][browse_path], key=lambda x: x[1])
            table = []

            if len(base_path.parts) >= 4:
                table.append(
                    [f"{self.icons['dir']} <a href='{base_path.parent}'>..</a>", "", "", ""]
                )

            for name, type, size, mtime in files:
                nav_link = f"{self.icons.get(type, '')} <a href='{base_path/name}'>{name}</a>"
                down_link = f"<a href='{base_path/name}?dump'>Download</a>"
                table.append([nav_link, str(size), format_date(mtime), down_link])

            self.do_respond(200, gen_table(table, ["Name", "Size", "Date modified", "Download"]))


class WebHandler(BaseHandler):
    """ Experimental Web UI Service """

    def run(self, *args):
        mimetypes.init()
        logging.info("Server address: http://127.0.0.1:8728")
        PresticRequestHandler.profiles = self.profiles
        self.server = TCPServer(("127.0.0.1", 8728), PresticRequestHandler)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        super().stop()


def format_date(dt):
    if type(dt) is str:
        dt = re.sub(r"\.[0-9]{3,}", "", dt)  # Python doesn't like variable ms precision
        dt = datetime.fromisoformat(dt)
    return str(dt)
    # return time_diff(dt)
    # return dt.strftime("%Y-%m-%d %H:%M:%S")


def start_webui():
    try:
        logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.DEBUG)
        handler = WebHandler()
        handler.run()
    except KeyboardInterrupt:
        handler.stop()


if __name__ == "__main__":
    start_webui()
