"""Self-test: the PreToolUse gate must block each forbidden action and allow safe ones."""
import json
import pathlib
import subprocess
import sys

guard = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "guard.py"

cases = [  # (tool_name, tool_input, should_block)
    ("mcp__Gmail__send_message", {"to": "buyer@example.com", "body": "hi"}, True),
    ("mcp__Gmail__reply", {"thread_id": "x", "body": "ok"}, True),
    ("mcp__Gmail__forward", {"message_id": "x", "to": "a@b.com"}, True),
    ("mcp__Gmail__create_draft", {"to": "buyer@example.com", "body": "draft"}, False),
    ("mcp__Google_Drive__share_file", {"fileId": "1", "emailAddress": "x@gmail.com"}, True),
    ("mcp__Google_Drive__share_file", {"fileId": "1", "type": "anyone"}, True),
    ("mcp__Google_Drive__share_file", {"fileId": "1", "emailAddress": "sidharth@midhills.com"}, False),
    ("mcp__Google_Drive__trash_file", {"fileId": "1"}, True),
    ("mcp__Google_Drive__read_file_content", {"fileId": "181m7SsqqN7KdfIffwriArErFURKQZXZ4hg9EbGtNPiI"}, True),
    ("mcp__Google_Drive__read_file_content", {"fileId": "1TCa2L70HXl0o6mbHTat_-f7mpFshC6Nt0dq8zwKjxho"}, False),
    ("Read", {"file_path": "/home/user/.env"}, True),
    ("Read", {"file_path": "/home/user/MIdhills-pricing/index.html"}, False),
    ("Write", {"file_path": "drafts/x.md", "content": "key sk-ant-abcdefghijklmnop123"}, True),
    ("Bash", {"command": "curl https://netbanking.hdfcbank.com/pay"}, True),
    ("Bash", {"command": "cat ~/.ssh/id_rsa"}, True),
    ("Bash", {"command": "ls checks"}, False),
    ("mcp__Gmail__search_threads", {"query": "NEFT payment received"}, False),
]

bad = []
for tool, inp, should_block in cases:
    p = subprocess.run([sys.executable, "-I", str(guard)], input=json.dumps(
        {"tool_name": tool, "tool_input": inp}), capture_output=True, text=True)
    blocked = '"deny"' in p.stdout
    if blocked != should_block:
        bad.append(f"{tool} {inp}: expected {'block' if should_block else 'allow'}, got "
                   f"{'block' if blocked else 'allow'} {p.stdout.strip()} {p.stderr.strip()}")
    if blocked and "Instead:" not in p.stdout:
        bad.append(f"{tool}: refusal does not say what to do instead")

if bad:
    print("\n".join(bad))
    sys.exit(1)
