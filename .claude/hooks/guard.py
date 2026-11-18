#!/usr/bin/env python3
"""PreToolUse gate for Midhills. Blocks outward or irreversible actions.

Blocks: sending email, sharing Drive files outside the company, deleting,
credentials/secrets, bank and payment actions. Every refusal says what to do
instead. Exit 0 with a JSON "deny" decision = blocked; plain exit 0 = allowed.
"""
import json
import re
import sys

COMPANY_DOMAINS = ("midhills.com", "midhills.in")
BANK_LOGIN_FILE_ID = "181m7SsqqN7KdfIffwriArErFURKQZXZ4hg9EbGtNPiI"  # Drive "Bank Login"

SEND_TOOLS = {
    "mcp__Gmail__send_message": "sending email",
    "mcp__Gmail__reply": "replying to email",
    "mcp__Gmail__forward": "forwarding email",
}
DELETE_TOOLS = {
    "mcp__Gmail__trash_message", "mcp__Gmail__trash_thread", "mcp__Gmail__delete_draft",
    "mcp__Gmail__delete_label", "mcp__Google_Drive__trash_file",
    "mcp__Google_Calendar__delete_event",
}
SECRET_PATH = re.compile(
    r"(\.env\b|\.pem\b|id_rsa|id_ed25519|\.ssh/|credentials|\.netrc|secret|token|"
    r"bank[\s_-]*login|password|passwd|\b2fa\b|\botp\b)", re.I)
SECRET_VALUE = re.compile(
    r"(sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|"
    r"AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[bap]-[A-Za-z0-9-]{10,})")
BANK = re.compile(
    r"(netbanking|hdfcbank|icicibank|onlinesbi|axisbank|kotak\.com|razorpay|payu|paytm|"
    r"stripe\.com|paypal|\bupi\b|neft|rtgs|imps|swift transfer|wire transfer|make[_ ]payment|"
    r"pay[_ ]invoice|initiate[_ ]payment)", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def deny(reason, instead):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"BLOCKED by Midhills gate: {reason}. Instead: {instead}",
    }}))
    sys.exit(0)


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        deny("hook input unreadable", "retry; if it repeats, tell Sumit the gate is broken")
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}
    text = "\n".join(strings(inp))

    if tool in SEND_TOOLS:
        deny(f"{SEND_TOOLS[tool]} needs Sumit's yes",
             "save a draft with mcp__Gmail__create_draft (or drafts/ in the repo) and list it "
             "in STATE.md under 'Awaiting Sumit'")

    if tool in DELETE_TOOLS:
        deny("deleting or trashing needs Sumit's yes",
             "list the item and the reason in STATE.md under 'Awaiting Sumit'")

    if tool == "mcp__Google_Drive__share_file":
        external = [d for d in EMAIL.findall(text) if not d.lower().endswith(COMPANY_DOMAINS)]
        if external or re.search(r"\b(anyone|anyoneWithLink|domain)\b", text) or not EMAIL.search(text):
            deny("sharing a Drive file outside midhills.com/midhills.in (or by link)",
                 "keep the file private and ask Sumit to share it himself")

    if "Bank Login" in text or BANK_LOGIN_FILE_ID in text:
        deny("the 'Bank Login' file holds credentials and is off limits",
             "do not open it; if a task needs bank data, ask Sidharth for an export without credentials")

    if tool in ("Read", "Edit", "Write", "Grep", "Glob", "NotebookEdit"):
        path = str(inp.get("file_path") or inp.get("path") or (inp.get("pattern") if tool == "Glob" else "") or "")
        if SECRET_PATH.search(path):
            deny(f"'{path}' looks like a credential or secrets file",
                 "work without it; if access is truly needed, report it to Sumit, never read it")

    if tool in ("Write", "Edit", "NotebookEdit", "mcp__Gmail__create_draft",
                "mcp__Google_Drive__create_file", "mcp__Google_Drive__update_file"):
        if SECRET_VALUE.search(text):
            deny("the content contains what looks like an API key, token or private key",
                 "remove the secret; reference the environment's secret store by name instead")

    if tool == "Bash":
        cmd = str(inp.get("command", ""))
        if SECRET_VALUE.search(cmd) or re.search(
                r"(cat|less|head|tail|grep|cp|scp|curl).*(\.env\b|id_rsa|\.pem\b|\.netrc|credentials)", cmd):
            deny("the command reads or exposes credentials",
                 "work without the secret; report missing access to Sumit")
        if re.search(r"\b(sendmail|mailx?|mutt|swaks)\b|smtp", cmd, re.I):
            deny("sending email from the shell", "save a draft instead and list it in STATE.md")

    read_only = re.search(r"__(search|get|list|read|download)_", tool)
    if BANK.search(tool) or (tool in ("Bash", "WebFetch") or (tool.startswith("mcp__") and not read_only)) \
            and BANK.search(text):
        if True:
            deny("bank or payment action",
                 "put the payment details in STATE.md under 'For Sidharth' (finance) or 'Awaiting Sumit'")

    sys.exit(0)


if __name__ == "__main__":
    main()
