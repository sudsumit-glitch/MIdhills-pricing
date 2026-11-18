"""Repo structure checks: CLAUDE.md map, agent roster, STATE.md tasks."""
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
errors = []

cm = root / "CLAUDE.md"
if not cm.exists():
    errors.append("CLAUDE.md missing")
elif len(cm.read_text().splitlines()) >= 100:
    errors.append("CLAUDE.md must stay under 100 lines")

expected = {"sales", "docs", "analyst", "projects", "reviewer"}
agents = root / ".claude" / "agents"
found = {p.stem for p in agents.glob("*.md")} if agents.exists() else set()
if found != expected:
    errors.append(f"agent roster mismatch: have {sorted(found)}, want {sorted(expected)}")
for name in found & expected:
    text = (agents / f"{name}.md").read_text()
    for key in ("name:", "description:", "tools:", "model:"):
        if key not in text.split("---")[1]:
            errors.append(f"{name}.md frontmatter missing {key}")
    tools = re.search(r"^tools:(.*)$", text, re.M)
    tools = tools.group(1) if tools else ""
    if "send_message" in tools or "share_file" in tools or "forward" in tools:
        errors.append(f"{name}.md grants a send/share tool")
    if name == "reviewer" and re.search(r"\b(Write|Edit)\b", tools):
        errors.append("reviewer must not have Write/Edit")

st = root / "STATE.md"
if not st.exists():
    errors.append("STATE.md missing")
else:
    rows = [l for l in st.read_text().splitlines() if re.match(r"^\| [0-9] \|", l)]
    if len(rows) != 3:
        errors.append(f"STATE.md must list exactly 3 tasks, found {len(rows)}")
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) != 5 or not cells[2] or not cells[4].startswith("checks/"):
            errors.append(f"task row needs owner and a checks/ done-check: {r}")
        elif cells[3] == "done" and not (root / cells[4]).exists():
            errors.append(f"task {cells[0]} marked done but {cells[4]} does not exist")

if errors:
    print("\n".join(errors))
    sys.exit(1)
