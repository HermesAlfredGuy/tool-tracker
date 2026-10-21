#!/opt/hermes/.venv/bin/python
"""Collect the live tool + project inventory into data.json.

Run:  /opt/hermes/.venv/bin/python /opt/data/studio/tool-tracker/collect.py [--fast]
      --fast skips the (slow) live MCP connection tests and keeps the previous results.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml

HOME = Path("/opt/data")
OUT = Path("/opt/data/studio/tool-tracker/data.json")
HERMES = "/usr/local/bin/hermes"
ENV = {**os.environ, "HOME": "/opt/data", "PATH": os.environ.get("PATH", "")}


def run(cmd, timeout=60, cwd=None):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, cwd=cwd, env=ENV)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"__error__ {e}"


def http(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tool-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.headers.get("location") or "")
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("location") or "") if e.headers else ""
    except Exception:  # noqa: BLE001
        return 0, ""


def port_open(port, host="127.0.0.1", timeout=2.5):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        s.close()


def version_of(binary, args=("--version",), timeout=20):
    out = run([binary, *args], timeout=timeout).strip().splitlines()
    return out[0].strip()[:90] if out else "missing"


# ---------------------------------------------------------------- MCP servers
def mcp_config():
    cfg = yaml.safe_load((HOME / "config.yaml").read_text())
    servers = cfg.get("mcp_servers") or {}
    rows = []
    for name, s in servers.items():
        s = s or {}
        if s.get("url"):
            kind = "http"
            target = s["url"]
        else:
            kind = "stdio"
            cmd = s.get("command", "")
            args = " ".join(str(a) for a in (s.get("args") or []))
            target = f"{cmd} {args}".strip()
        inc = ((s.get("tools") or {}).get("include")) or []
        rows.append({
            "name": name,
            "enabled": bool(s.get("enabled", True)),
            "transport": kind,
            "target": target,
            "lazy": bool(s.get("lazy")),
            "selected_tools": inc,
        })
    return rows


_live_cache: dict = {}


def mcp_live(name):
    out = run([HERMES, "mcp", "test", name], timeout=90)
    out = re.sub(r".*install out of sync.*\n", "", out)
    ok = "✓ Connected" in out
    tools = re.search(r"Tools discovered: (\d+)", out)
    ms = re.search(r"Connected \((\d+)ms\)", out)
    names = re.findall(r"^    (\S+) {2,}\S", out, flags=re.M)
    return {
        "live": ok,
        "tools": int(tools.group(1)) if tools else 0,
        "tool_names": names,
        "connect_ms": int(ms.group(1)) if ms else None,
        "error": "" if ok else out.strip().splitlines()[-1][:160] if out.strip() else "no output",
    }


# ---------------------------------------------------------------- toolsets
def toolsets():
    out = run([HERMES, "tools", "list"], timeout=90)
    native, plugin = [], []
    mode = None
    for line in out.splitlines():
        if line.startswith("Built-in toolsets"):
            mode = native
            continue
        if line.startswith("Plugin toolsets"):
            mode = plugin
            continue
        if line.startswith("MCP servers"):
            mode = None
            continue
        m = re.match(r"\s*([✓✗])\s+(enabled|disabled)\s+(\S+)\s+(.*)$", line)
        if m and mode is not None:
            mode.append({"state": m.group(2), "name": m.group(3), "label": m.group(4).strip()})
    return native, plugin


# ---------------------------------------------------------------- services
def services():
    demo_tunnel = ""
    try:
        tfile = HOME / "demo" / "tunnel-url.txt"
        if tfile.exists():
            demo_tunnel = tfile.read_text().strip()
    except Exception:  # noqa: BLE001
        pass
    if not demo_tunnel:
        for f in (HOME / "demo").glob("*tunnel*"):
            if f.is_file() and f.suffix in (".log", ".txt"):
                m = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", f.read_text(errors="ignore"))
                if m:
                    demo_tunnel = m[-1]
                    break
    host_code, _ = http("https://nd96-8d938128.nip.io/host")
    kayak_code, _ = http("https://kayak-8d938128.nip.io/")
    gateway_pid = None
    try:
        gateway_pid = json.loads((HOME / "gateway.pid").read_text()).get("pid")
    except Exception:  # noqa: BLE001
        pass
    du = run("df -h /opt/data | tail -1", timeout=20).split()
    load = os.getloadavg()
    return [
        {"name": "Hermes gateway", "detail": f"pid {gateway_pid}", "ok": bool(gateway_pid)},
        {"name": "Telegram bridge", "detail": "channel -1003852072951", "ok": True},
        {"name": "Itlala demo · Next :9100", "detail": str(http("http://127.0.0.1:9100/")[0]), "ok": http("http://127.0.0.1:9100/")[0] in (200, 307, 308)},
        {"name": "Typesense :8108", "detail": "health " + str(http("http://127.0.0.1:8108/health")[0]), "ok": http("http://127.0.0.1:8108/health")[0] == 200},
        {"name": "Demo tunnel (cloudflared)", "detail": ("quick tunnel up" if demo_tunnel else "no tunnel url"),
         "ok": bool(demo_tunnel) and http(demo_tunnel)[0] in (200, 301, 307, 308)},
        {"name": "Blender bridge :9876", "detail": "blender 4.5.9 + mcp-for-blender", "ok": port_open(9876)},
        {"name": "ND96 host (Oracle VM)", "detail": f"HTTP {host_code}", "ok": host_code == 200},
        {"name": "ND96 kayak (Oracle VM)", "detail": f"HTTP {kayak_code}", "ok": kayak_code == 200},
        {"name": "Disk /opt/data", "detail": f"{du[2]} used of {du[1]} ({du[4]})" if len(du) > 4 else "n/a", "ok": len(du) > 4},
        {"name": "Load average", "detail": f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}", "ok": load[0] < os.cpu_count() * 1.5},
    ]


# ---------------------------------------------------------------- crons
def crons():
    try:
        raw = json.loads((HOME / "cron" / "jobs.json").read_text())
    except Exception:  # noqa: BLE001
        return []
    jobs = raw.get("jobs", []) if isinstance(raw, dict) else raw
    jobs = [j for j in jobs if isinstance(j, dict)]
    rows = []
    for j in jobs:
        sch = j.get("schedule") or {}
        rows.append({
            "name": j.get("name") or j.get("id", "")[:8],
            "schedule": sch.get("display") or sch.get("expr") or json.dumps(sch)[:40],
            "enabled": bool(j.get("enabled")),
            "deliver": re.sub(r"telegram:-?\d+:(\d+)", r"telegram topic \1",
                              str(j.get("deliver") or j.get("channel") or "origin")),
        })
    rows.sort(key=lambda r: (not r["enabled"], r["name"].lower()))
    return rows


# ---------------------------------------------------------------- skills / files
def skills():
    root = HOME / "skills"
    dirs = [d for d in root.iterdir() if d.is_dir()]
    count = len(list(root.rglob("SKILL.md")))
    plugin = len(list((HOME / "plugins").rglob("SKILL.md")))
    kits = [d.name for d in (HOME / "kits").iterdir() if d.is_dir()]
    scripts = len(list((HOME / "scripts").glob("*.py"))) + len(list((HOME / "scripts").glob("*.sh")))
    return {
        "bundles": len(dirs),
        "skills": count,
        "plugin_skills": plugin,
        "kits": kits,
        "scripts": scripts,
        "plugins": sorted([p.name for p in (HOME / "plugins").iterdir() if p.is_dir() and not p.name.startswith(".")]),
    }


def projects():
    reg = json.loads((HOME / "projects" / "REGISTRY.json").read_text())
    out = []
    for p in reg["projects"]:
        live = p.get("live") or []
        out.append({
            "id": p["id"],
            "title": p.get("title", p["id"]),
            "topic": p.get("topic"),
            "status": p.get("status", ""),
            "live": [[str(l[0]), str(l[1])] for l in live][:4],
            "video": p.get("video"),
            "next": ("" if str(p.get("next") or "").strip().rstrip(".").lower()
                     in ("", "none", "n/a", "-", "null", "tbd") else str(p["next"]).strip()),
        })
    return out


def clis():
    godot_bin = "/opt/data/tools/godot/Godot_v4.7.2-stable_linux.x86_64"
    blender_bin = "/opt/data/tools/blender-4.5.9/blender"
    rows = [
        ("Hermes Agent", version_of(HERMES, ("--version",))),
        ("Node.js", version_of("node", ("-v",))),
        ("Python", version_of("python3", ("-V",))),
        ("FFmpeg", version_of("ffmpeg", ("-version",)).split(" Copyright")[0]),
        ("Godot", version_of(godot_bin, ("--version",))),
        ("Blender", version_of(blender_bin, ("--version",))),
        ("gh CLI", version_of("gh", ("--version",))),
        ("uv / uvx", version_of("uvx", ("--version",))),
        ("npx", version_of("npx", ("--version",))),
    ]
    return [{"name": n, "version": v} for n, v in rows]


def main(fast=False):
    prev = {}
    if OUT.exists():
        try:
            prev = {r["name"]: r for r in json.loads(OUT.read_text()).get("mcp", [])}
        except Exception:  # noqa: BLE001
            prev = {}
    servers = mcp_config()
    enabled = [s for s in servers if s["enabled"]]

    def work(s):
        if fast and s["name"] in prev and prev[s["name"]].get("tools"):
            p = prev[s["name"]]
            return {**s, "live": p["live"], "tools": p["tools"],
                    "tool_names": p.get("tool_names", []),
                    "connect_ms": p["connect_ms"], "error": p.get("error", ""), "cached": True}
        return {**s, **mcp_live(s["name"]), "cached": False}

    with ThreadPoolExecutor(max_workers=6) as pool:
        tested = list(pool.map(work, enabled))
    disabled = [{**s, "live": False, "tools": 0, "tool_names": [], "connect_ms": None,
                 "error": "disabled in config", "cached": False} for s in servers if not s["enabled"]]
    mcp_rows = sorted(tested, key=lambda r: -r["tools"]) + disabled

    native, plugin = toolsets()
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "generated_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "mcp": mcp_rows,
        "mcp_enabled": len(enabled),
        "mcp_tools": sum(r["tools"] for r in mcp_rows),
        "native_toolsets": native,
        "plugin_toolsets": plugin,
        "services": services(),
        "crons": crons(),
        "skills": skills(),
        "clis": clis(),
        "projects": projects(),
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tmp.replace(OUT)
    live = sum(1 for r in mcp_rows if r["live"])
    print(f"collected: {live}/{len(enabled)} MCP live, {data['mcp_tools']} MCP tools, "
          f"{len(data['crons'])} crons, {len(data['projects'])} projects -> {OUT}")


if __name__ == "__main__":
    import sys
    main(fast="--fast" in sys.argv)
