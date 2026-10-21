#!/opt/hermes/.venv/bin/python
"""Render data.json -> index.html + TRACKER.md.

Run: /opt/hermes/.venv/bin/python /opt/data/studio/tool-tracker/build.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

DIR = Path("/opt/data/studio/tool-tracker")
D = json.loads((DIR / "data.json").read_text())
E = lambda s: html.escape(str(s), quote=True)  # noqa: E731

live = [r for r in D["mcp"] if r["live"]]
off = [r for r in D["mcp"] if not r["live"]]
providers_mcp = len(live)
native_on = sum(1 for t in D["native_toolsets"] if t["state"] == "enabled")
native_all = len(D["native_toolsets"])
plugins_on = sum(1 for t in D["plugin_toolsets"] if t["state"] == "enabled")
crons_on = sum(1 for c in D["crons"] if c["enabled"])
svc_ok = sum(1 for s in D["services"] if s["ok"])
total_tool_names = sum(len(r.get("tool_names") or []) for r in D["mcp"])
sk = D["skills"]


def dot(ok: bool, muted: bool = False) -> str:
    cls = "ok" if ok else ("muted" if muted else "bad")
    return f'<span class="dot {cls}" aria-hidden="true"></span>'


def mcp_rows() -> str:
    out = []
    for r in D["mcp"]:
        sel = (f'{len(r["selected_tools"])} selected' if r["selected_tools"] else "all tools")
        state = "live" if r["live"] else ("off" if not r["enabled"] else "fail")
        ms = f'{r["connect_ms"]} ms' if r.get("connect_ms") else "—"
        lazy = "lazy" if r.get("lazy") else ""
        out.append(
            f'<tr data-search="{E(r["name"] + " " + r["target"])}">'
            f'<td class="name">{dot(r["live"], muted=not r["enabled"])}{E(r["name"])}'
            f'{" <span class=\'tag\'>" + lazy + "</span>" if lazy else ""}</td>'
            f'<td class="mono dim">{E(r["transport"])}</td>'
            f'<td class="mono dim ellip" title="{E(r["target"])}">{E(r["target"])}</td>'
            f'<td class="num">{r["tools"] or "–"}</td>'
            f'<td class="mono dim">{E(sel)}</td>'
            f'<td class="mono dim">{ms}</td>'
            f'<td class="mono {state}">{state}</td></tr>')
    return "\n".join(out)


def toolset_cards(items, kind) -> str:
    out = []
    for t in items:
        on = t["state"] == "enabled"
        out.append(
            f'<li class="{"on" if on else "offf"}">{dot(on, muted=not on)}'
            f'<span class="ts-name">{E(t["name"])}</span>'
            f'<span class="ts-label dim">{E(t["label"])}</span></li>')
    return "\n".join(out)


def service_rows() -> str:
    out = []
    for s in D["services"]:
        out.append(f'<tr><td class="name">{dot(s["ok"])}{E(s["name"])}</td>'
                   f'<td class="mono dim ellip">{E(s["detail"])}</td></tr>')
    return "\n".join(out)


def cron_rows() -> str:
    out = []
    for c in D["crons"]:
        out.append(
            f'<tr data-search="{E(c["name"])}" class="{"row-off" if not c["enabled"] else ""}">'
            f'<td class="name">{dot(c["enabled"], muted=not c["enabled"])}{E(c["name"])}</td>'
            f'<td class="mono dim">{E(c["schedule"])}</td>'
            f'<td class="mono dim ellip">{E(c["deliver"])}</td></tr>')
    return "\n".join(out)


def project_rows() -> str:
    out = []
    for p in D["projects"]:
        links = " ".join(
            f'<a class="pill" href="{E(u)}" target="_blank" rel="noopener">{E(l)}</a>'
            for l, u in p["live"] if u and not u.startswith("auto:"))
        next_html = (f'<p class="next"><span class="k">next</span> {E(p["next"])}</p>'
                     if p["next"] else "")
        out.append(
            f'<article class="proj" data-search="{E(p["title"] + " " + p["status"])}">'
            f'<header><h3>{E(p["title"])}</h3>'
            f'<span class="mono dim">topic {E(p["topic"] if p["topic"] else "—")}</span></header>'
            f'<p class="status">{E(p["status"])}</p>'
            f'{next_html}'
            f'<div class="links">{links}</div></article>')
    return "\n".join(out)


def tool_index() -> str:
    out = []
    for r in D["mcp"]:
        names = r.get("tool_names") or []
        if not names:
            continue
        chips = "".join(f'<code>{E(n)}</code>' for n in names)
        open_tag = "<details open>" if len(names) <= 24 else "<details>"
        out.append(
            f'<div class="tgroup" data-search="{E(r["name"] + " " + " ".join(names))}">'
            f'{open_tag}<summary><span class="tname">{E(r["name"])}</span>'
            f'<span class="tcount mono dim">{len(names)} tools</span></summary>'
            f'<div class="tchips">{chips}</div></details></div>')
    return "\n".join(out)


def cli_rows() -> str:
    return "\n".join(f'<tr><td class="name">{E(c["name"])}</td>'
                     f'<td class="mono dim ellip">{E(c["version"])}</td></tr>' for c in D["clis"])


HTML = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes · Tool Tracker</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%2308090b'/%3E%3Ccircle cx='8' cy='8' r='3' fill='%23c9764a'/%3E%3C/svg%3E">
<meta name="description" content="Live inventory of every tool, server, job and project on this Hermes install.">
<style>
  :root {{
    --bg:#08090b; --panel:#0e1013; --panel2:#12151a; --ink:#ecebe6; --dim:#a3a9b1;
    --line:#1d2126; --ok:#6fe0a6; --warn:#e3b169; --bad:#e06c62; --accent:#c9764a;
  }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15.5px/1.58 ui-sans-serif,system-ui,"Inter","Segoe UI",Roboto,sans-serif;
    -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:13px; }}
  .dim {{ color:var(--dim); }}
  a {{ color:inherit; }}
  .wrap {{ max-width:1220px; margin:0 auto; padding:0 28px; }}
  header.top {{ padding:64px 0 28px; border-bottom:1px solid var(--line); }}
  .eyebrow {{ display:flex; justify-content:space-between; align-items:baseline; gap:20px;
    font-family:ui-monospace,monospace; font-size:11.5px; letter-spacing:.16em;
    text-transform:uppercase; color:var(--dim); }}
  h1 {{ margin:14px 0 6px; font-size:clamp(34px,5vw,58px); line-height:1.02;
    font-weight:600; letter-spacing:-.03em; }}
  h1 em {{ font-style:normal; color:var(--accent); }}
  .lede {{ margin:0; max-width:62ch; color:var(--dim); font-size:16px; }}
  .stats {{ display:grid; grid-template-columns:repeat(5,1fr); gap:0;
    border-bottom:1px solid var(--line); }}
  .stat {{ padding:26px 22px 24px; border-right:1px solid var(--line); }}
  .stat:first-child {{ padding-left:28px; }}
  .stat:last-child {{ border-right:0; }}
  .stat b {{ display:block; font-size:30px; font-weight:600; letter-spacing:-.02em;
    font-variant-numeric:tabular-nums; }}
  .stat span {{ font-family:ui-monospace,monospace; font-size:11px; letter-spacing:.1em;
    text-transform:uppercase; color:#aab1b9; }}
  main {{ display:grid; grid-template-columns:186px 1fr; gap:52px; padding:44px 0 90px; }}
  main > * {{ min-width:0; }}
  table {{ table-layout:fixed; }}
  nav.toc {{ position:sticky; top:28px; align-self:start; font-family:ui-monospace,monospace;
    font-size:12px; }}
  nav.toc ol {{ list-style:none; margin:14px 0 0; padding:0; display:grid; gap:11px; }}
  nav.toc a {{ text-decoration:none; color:#949ba3; display:flex; gap:10px; align-items:baseline; }}
  nav.toc a:hover, nav.toc a:focus-visible {{ color:var(--ink); }}
  nav.toc input::placeholder {{ color:#6f767e; }}
  nav.toc a i {{ font-style:normal; color:#4c5259; }}
  .search input {{ width:100%; background:var(--panel); border:1px solid var(--line);
    color:var(--ink); padding:8px 10px; font:12px ui-monospace,monospace; border-radius:4px; }}
  .search input:focus {{ outline:none; border-color:#39424c; }}
  section {{ margin-bottom:62px; scroll-margin-top:24px; }}
  section > h2 {{ display:flex; align-items:baseline; gap:12px; margin:0 0 6px;
    font-size:19px; font-weight:600; letter-spacing:-.01em; }}
  section > h2 i {{ font-style:normal; font-family:ui-monospace,monospace; font-size:11px;
    color:var(--accent); letter-spacing:.1em; }}
  .sub {{ margin:0 0 18px; color:var(--dim); font-size:13.5px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; font-family:ui-monospace,monospace; font-size:11px;
    letter-spacing:.11em; text-transform:uppercase; color:#8d949c; font-weight:400;
    padding:0 12px 9px 0; border-bottom:1px solid var(--line); }}
  td {{ padding:11px 12px 11px 0; border-bottom:1px solid #191d22; vertical-align:middle; }}
  tr:hover td {{ background:#0d1014; }}
  .num, th.num {{ text-align:right; font-family:ui-monospace,monospace;
    font-variant-numeric:tabular-nums; padding-right:26px; }}
  td.name {{ white-space:nowrap; font-weight:500; overflow:hidden; text-overflow:ellipsis; }}
  .ellip {{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    display:block; }}
  .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:9px;
    vertical-align:middle; background:var(--ok); box-shadow:0 0 0 3px rgba(111,224,166,.09); }}
  .dot.muted {{ background:#4d545c; box-shadow:none; }}
  .dot.bad {{ background:var(--bad); box-shadow:0 0 0 3px rgba(224,108,98,.1); }}
  td.live {{ color:var(--ok); }} td.off {{ color:#5d646c; }} td.fail {{ color:var(--bad); }}
  .tag {{ font:10px ui-monospace,monospace; color:#a4abb3; border:1px solid #2a3037;
    padding:1px 5px; border-radius:3px; margin-left:7px; }}
  .row-off td {{ opacity:.5; }}
  ul.ts {{ list-style:none; margin:0; padding:0; display:grid;
    grid-template-columns:repeat(auto-fill,minmax(268px,1fr)); gap:2px 22px; }}
  ul.ts li {{ display:flex; align-items:baseline; padding:7px 0; border-bottom:1px solid #14171b; }}
  .ts-name {{ font-family:ui-monospace,monospace; font-size:12.5px; }}
  .ts-label {{ margin-left:auto; font-size:12px; text-align:right; }}
  ul.ts li.offf {{ opacity:.45; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:44px; }}
  .proj {{ border-top:1px solid var(--line); padding:18px 0 20px; }}
  .proj header {{ display:flex; align-items:baseline; justify-content:space-between; gap:16px; }}
  .proj h3 {{ margin:0; font-size:16.5px; font-weight:600; letter-spacing:-.01em; }}
  .proj .status {{ margin:8px 0 6px; color:#cfcdc7; font-size:14px; max-width:74ch; }}
  .proj .next {{ margin:0 0 12px; font-size:13px; color:var(--dim); max-width:74ch; }}
  .proj .k {{ font-family:ui-monospace,monospace; font-size:10.5px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--accent); margin-right:6px; }}
  .links {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .pill {{ text-decoration:none; font:11.5px ui-monospace,monospace; color:#cfcdc7;
    border:1px solid #262c33; padding:3px 9px; border-radius:999px; }}
  .pill:hover {{ border-color:var(--accent); color:#fff; }}
  .tgroup {{ border-bottom:1px solid #14171b; }}
  .tgroup summary {{ display:flex; align-items:baseline; gap:12px; padding:11px 0; cursor:pointer;
    list-style:none; }}
  .tgroup summary::-webkit-details-marker {{ display:none; }}
  .tgroup summary::before {{ content:"+"; font:13px ui-monospace,monospace; color:#5f767f; width:10px; }}
  .tgroup details[open] summary::before {{ content:"–"; }}
  .tname {{ font-family:ui-monospace,monospace; font-size:13px; color:var(--ink); }}
  .tcount {{ margin-left:auto; }}
  .tchips {{ display:flex; flex-wrap:wrap; gap:6px; padding:2px 0 16px 22px; }}
  .tchips code {{ font:11.5px ui-monospace,monospace; color:#c2c8cf; background:#11151a;
    border:1px solid #1e242b; padding:2px 7px; border-radius:3px; }}
  .tchips code:hover {{ border-color:var(--accent); color:#fff; }}
  footer {{ border-top:1px solid var(--line); padding:26px 0 60px; color:#5d646c;
    font:12px ui-monospace,monospace; display:flex; justify-content:space-between; gap:20px;
    flex-wrap:wrap; }}
  .reveal {{ opacity:0; transform:translateY(10px);
    animation:rise .5s cubic-bezier(.2,.7,.2,1) forwards; }}
  @keyframes rise {{ to {{ opacity:1; transform:none; }} }}
  @media (max-width:900px) {{
    .wrap {{ padding:0 18px; }}
    .stats {{ grid-template-columns:repeat(2,1fr); }}
    .stat {{ border-bottom:1px solid var(--line); }}
    .stat:nth-child(2n) {{ border-right:0; }}
    main {{ grid-template-columns:1fr; gap:26px; }}
    nav.toc {{ position:static; }}
    nav.toc ol {{ grid-template-columns:1fr; gap:9px; font-size:12px; }}
    nav.toc a {{ min-width:0; }}
    nav.toc a i {{ width:16px; flex:0 0 16px; }}
    .stat:last-child {{ grid-column:1 / -1; border-right:0; }}
    .grid2 {{ grid-template-columns:1fr; gap:0; }}
    .ellip {{ max-width:170px; }}
    table.mcp th:nth-child(2), table.mcp td:nth-child(2),
    table.mcp th:nth-child(3), table.mcp td:nth-child(3),
    table.mcp th:nth-child(5), table.mcp td:nth-child(5),
    table.mcp th:nth-child(6), table.mcp td:nth-child(6) {{ display:none; }}
    table.mcp td {{ padding-right:10px; }}
    td.name {{ white-space:normal; }}
    table.crons th:nth-child(3), table.crons td:nth-child(3) {{ display:none; }}
    .ellip {{ max-width:100%; }}
    body {{ overflow-x:hidden; }}
  }}
</style></head>
<body>
<header class="top"><div class="wrap">
  <div class="eyebrow"><span>Hermes Agent · {E(D["host"])}</span><span>{E(D["generated"])}</span></div>
  <h1>Tool <em>tracker</em></h1>
  <p class="lede">Every capability on this install, checked against the live system:
     {D["mcp_enabled"]} MCP servers hand-tested, {native_all} native toolsets,
     {len(D["crons"])} scheduled jobs and {len(D["projects"])} projects.</p>
</div></header>

<div class="wrap"><div class="stats">
  <div class="stat"><b>{len(live)}<span class="dim">/{D["mcp_enabled"]}</span></b><span>MCP servers live</span></div>
  <div class="stat"><b>{D["mcp_tools"]}</b><span>MCP tools exposed</span></div>
  <div class="stat"><b>{native_on}<span class="dim">/{native_all}</span></b><span>Native toolsets</span></div>
  <div class="stat"><b>{crons_on}<span class="dim">/{len(D["crons"])}</span></b><span>Cron jobs active</span></div>
  <div class="stat"><b>{svc_ok}<span class="dim">/{len(D["services"])}</span></b><span>Services healthy</span></div>
</div></div>

<main class="wrap">
  <nav class="toc">
    <div class="search"><input id="q" placeholder="filter…" aria-label="Filter rows"></div>
    <ol>
      <li><a href="#mcp"><i>01</i>MCP servers</a></li>
      <li><a href="#native"><i>02</i>Toolsets</a></li>
      <li><a href="#skills"><i>03</i>Skills</a></li>
      <li><a href="#services"><i>04</i>Services</a></li>
      <li><a href="#crons"><i>05</i>Scheduled</a></li>
      <li><a href="#projects"><i>06</i>Projects</a></li>
      <li><a href="#runtimes"><i>07</i>Runtimes</a></li>
      <li><a href="#tools"><i>08</i>Tool index</a></li>
    </ol>
  </nav>

  <div class="content">
    <section id="mcp" class="reveal">
      <h2><i>01</i> MCP servers</h2>
      <p class="sub">Each enabled server was connected for real with <code>hermes mcp test</code>;
         tool counts and handshake times are measured, not configured.</p>
      <table class="mcp"><thead><tr><th>Server</th><th>Transport</th><th>Target</th><th class="num">Tools</th>
        <th>Exposure</th><th>Handshake</th><th>State</th></tr></thead>
        <tbody>{mcp_rows()}</tbody></table>
    </section>

    <section id="native" class="reveal">
      <h2><i>02</i> Native &amp; plugin toolsets</h2>
      <p class="sub">{native_on} of {native_all} built-in toolsets enabled, {plugins_on} plugin toolsets on.
         Deferred MCP tools are reached through tool-slimmer.</p>
      <div class="grid2">
        <div><h3 class="mono dim" style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;margin:0 0 8px">Built-in</h3>
          <ul class="ts">{toolset_cards(D["native_toolsets"], "native")}</ul></div>
        <div><h3 class="mono dim" style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;margin:0 0 8px">Plugin</h3>
          <ul class="ts">{toolset_cards(D["plugin_toolsets"], "plugin")}</ul></div>
      </div>
    </section>

    <section id="skills" class="reveal">
      <h2><i>03</i> Skills, kits &amp; scripts</h2>
      <p class="sub">{sk["skills"]} skill files across {sk["bundles"]} bundles, plus {sk["plugin_skills"]} plugin skills.</p>
      <table><tbody>
        <tr><td class="name">Skill bundles</td><td class="num">{sk["bundles"]}</td><td class="mono dim">/opt/data/skills</td></tr>
        <tr><td class="name">SKILL.md files</td><td class="num">{sk["skills"]}</td><td class="mono dim">loaded on demand</td></tr>
        <tr><td class="name">Plugin skills</td><td class="num">{sk["plugin_skills"]}</td><td class="mono dim">/opt/data/plugins</td></tr>
        <tr><td class="name">Kits</td><td class="num">{len(sk["kits"])}</td><td class="mono dim">{E(", ".join(sk["kits"]))}</td></tr>
        <tr><td class="name">Helper scripts</td><td class="num">{sk["scripts"]}</td><td class="mono dim">/opt/data/scripts</td></tr>
        <tr><td class="name">Plugins installed</td><td class="num">{len(sk["plugins"])}</td><td class="mono dim">{E(", ".join(sk["plugins"][:8]))}…</td></tr>
      </tbody></table>
    </section>

    <section id="services" class="reveal">
      <h2><i>04</i> Services</h2>
      <p class="sub">Probed at generation time: sockets, HTTP health endpoints, remote event hosts.</p>
      <table><tbody>{service_rows()}</tbody></table>
    </section>

    <section id="crons" class="reveal">
      <h2><i>05</i> Scheduled jobs</h2>
      <p class="sub">{crons_on} of {len(D["crons"])} jobs enabled; disabled ones are kept for reference.</p>
      <table class="crons"><thead><tr><th>Job</th><th>Schedule</th><th>Delivers to</th></tr></thead>
      <tbody>{cron_rows()}</tbody></table>
    </section>

    <section id="projects" class="reveal">
      <h2><i>06</i> Projects · current progress</h2>
      <p class="sub">Live from the registry: what shipped, what is paused, what comes next.</p>
      {project_rows()}
    </section>

    <section id="runtimes" class="reveal">
      <h2><i>07</i> Runtimes</h2>
      <p class="sub">Version strings reported by the binaries themselves.</p>
      <table><tbody>{cli_rows()}</tbody></table>
    </section>

    <section id="tools" class="reveal">
      <h2><i>08</i> Tool index</h2>
      <p class="sub">Every tool each live server actually advertises — {total_tool_names} names, straight from the handshake.</p>
      {tool_index()}
    </section>
  </div>
</main>

<footer class="wrap">
  <span>generated {E(D["generated"])} · /opt/data/studio/tool-tracker</span>
  <span>refresh: bash tools-tracker.sh</span>
</footer>

<script>
  const q = document.getElementById('q');
  const rows = [...document.querySelectorAll('[data-search]')];
  q.addEventListener('input', () => {{
    const v = q.value.trim().toLowerCase();
    rows.forEach(r => {{ r.style.display = !v || r.dataset.search.toLowerCase().includes(v) ? '' : 'none'; }});
  }});
  const io = new IntersectionObserver(es => es.forEach(e => {{
    if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }}
  }}), {{ threshold:.12 }});
  document.querySelectorAll('section').forEach(s => io.observe(s));
</script>
</body></html>
"""

(DIR / "index.html").write_text(HTML)


# ---------------------------------------------------------------- markdown
def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


md = [f"# Hermes · Tool Tracker\n", f"_Generated {D['generated']} on {D['host']}_\n",
      f"**{len(live)}/{D['mcp_enabled']} MCP servers live · {D['mcp_tools']} MCP tools · "
      f"{native_on}/{native_all} native toolsets · {crons_on}/{len(D['crons'])} crons · "
      f"{svc_ok}/{len(D['services'])} services healthy · {len(D['projects'])} projects**\n",
      "## 1. MCP servers (live-tested)\n",
      md_table(["Server", "Transport", "Tools", "Exposure", "Handshake", "State"],
               [[r["name"], r["transport"], r["tools"] or "–",
                 f"{len(r['selected_tools'])} selected" if r["selected_tools"] else "all tools",
                 f"{r['connect_ms']} ms" if r.get("connect_ms") else "–",
                 "live" if r["live"] else ("disabled" if not r["enabled"] else "FAIL")] for r in D["mcp"]]),
      "\n## 2. Native & plugin toolsets\n",
      md_table(["Toolset", "State"], [[t["name"], t["state"]] for t in D["native_toolsets"] + D["plugin_toolsets"]]),
      "\n## 3. Services\n",
      md_table(["Service", "Detail", "State"], [[s["name"], s["detail"], "ok" if s["ok"] else "DOWN"] for s in D["services"]]),
      "\n## 4. Scheduled jobs\n",
      md_table(["Job", "Schedule", "State"], [[c["name"], c["schedule"], "on" if c["enabled"] else "off"] for c in D["crons"]]),
      "\n## 5. Skills\n",
      f"- {sk['skills']} SKILL.md files in {sk['bundles']} bundles; {sk['plugin_skills']} plugin skills\n"
      f"- Kits: {', '.join(sk['kits'])}\n- Helper scripts: {sk['scripts']}; plugins installed: {len(sk['plugins'])}\n",
      "\n## 6. Project progress\n"]
for p in D["projects"]:
    links = ", ".join(u for _, u in p["live"] if u and not u.startswith("auto:")) or "no public link"
    md.append(f"### {p['title']}\n- **Status:** {p['status']}\n- **Next:** {p['next']}\n- **Live:** {links}\n" f"- **Topic:** {p['topic']}\n")
md.append("\n## 7. Tool index (names per server)\n")
for r in D["mcp"]:
    ns = r.get("tool_names") or []
    if ns:
        md.append(f"- **{r['name']}** ({len(ns)}): " + ", ".join(f"`{n}`" for n in ns))
md.append("\n## 8. Runtimes\n")
md.append(md_table(["Runtime", "Version"], [[c["name"], c["version"]] for c in D["clis"]]))
(DIR / "TRACKER.md").write_text("\n".join(md) + "\n")
print(f"wrote index.html ({len(HTML)//1024} kB) and TRACKER.md")
