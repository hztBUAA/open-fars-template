#!/usr/bin/env python3
"""
Email notification script for Claude Code god-mode.
Sends structured notification emails via SMTP.

Configuration: reads from config.json in the same directory as this script
First run: use --init to generate config template.

Usage:
    python3 send-email.py --init                          # Generate config template
    python3 send-email.py --subject "Task Done" --body "Report..."
    python3 send-email.py --subject "Review" --body-file /path/to/report.md
    python3 send-email.py --subject "Alert" --body "msg" --attachment /path/to/file
"""

import argparse
import json
import smtplib
import subprocess
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

CONFIG_TEMPLATE = {
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_user": "your-email@qq.com",
    "smtp_auth_code": "your-smtp-authorization-code",
    "recipient": "your-email@qq.com",
    "sender_name": "Claude Code",
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(
            f"Config not found: {CONFIG_PATH}\n"
            f"Run: python3 {__file__} --init",
            file=sys.stderr,
        )
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    required = ["smtp_host", "smtp_port", "smtp_user", "smtp_auth_code", "recipient"]
    missing = [
        k for k in required
        if not config.get(k) or (isinstance(config[k], str) and config[k].startswith("your-"))
    ]
    if missing:
        print(
            f"Config incomplete — update these fields in {CONFIG_PATH}:\n"
            + "\n".join(f"  - {k}" for k in missing),
            file=sys.stderr,
        )
        sys.exit(1)

    return config


def init_config():
    if CONFIG_PATH.exists():
        print(f"Config already exists: {CONFIG_PATH}")
        print("Edit it directly to update settings.")
        return

    CONFIG_PATH.write_text(
        json.dumps(CONFIG_TEMPLATE, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Config created: {CONFIG_PATH}")
    print("Edit it with your SMTP credentials before sending emails.")


def _send_via_ssh_relay(
    config: dict, relay_host: str, msg, subject: str,
) -> bool:
    """Send email by SSH-ing into a relay host that has SMTP egress.

    Passes a self-contained Python script + base64-encoded email as stdin
    to 'ssh root@relay python3' to avoid shell escaping issues.
    """
    import base64
    import textwrap

    raw = msg.as_bytes()
    b64_data = base64.b64encode(raw).decode()

    # Build a complete Python script that reads the b64 data from itself
    script = textwrap.dedent(f"""\
        import base64, smtplib
        from email import message_from_bytes
        DATA = "{b64_data}"
        raw = base64.b64decode(DATA)
        msg = message_from_bytes(raw)
        with smtplib.SMTP_SSL("{config['smtp_host']}", {config['smtp_port']}) as s:
            s.login("{config['smtp_user']}", "{config['smtp_auth_code']}")
            s.send_message(msg)
        print("OK")
    """)

    try:
        # Pipe the script to 'ssh host python3 -' which reads from stdin
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
             f"root@{relay_host}", "python3", "-"],
            input=script,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            print(f"Email sent (via relay {relay_host}): {subject}")
            return True
        print(
            f"SSH relay failed: {result.stderr.strip() or result.stdout.strip()}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"SSH relay error: {e}", file=sys.stderr)
        return False


def send_email(
    config: dict, subject: str, body: str, attachment_path: str | None = None
) -> bool:
    sender_name = config.get("sender_name", "Claude Code")
    smtp_user = config["smtp_user"]

    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{smtp_user}>"
    msg["To"] = config["recipient"]
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment_path:
        path = Path(attachment_path)
        if path.exists():
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={path.name}",
            )
            msg.attach(part)
        else:
            print(f"Warning: attachment not found: {attachment_path}", file=sys.stderr)

    # Try direct SMTP first, fall back to SSH relay via smtp_relay_host
    try:
        with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=10) as server:
            server.login(smtp_user, config["smtp_auth_code"])
            server.send_message(msg)
        print(f"Email sent: {subject}")
        return True
    except OSError:
        # Direct SMTP unreachable (e.g., pod without SMTP egress) — relay via SSH
        relay_host = config.get("smtp_relay_host")
        if not relay_host:
            print(
                "Direct SMTP unreachable and no smtp_relay_host configured.",
                file=sys.stderr,
            )
            return False
        return _send_via_ssh_relay(config, relay_host, msg, subject)


def main():
    parser = argparse.ArgumentParser(description="Send notification email")
    parser.add_argument("--init", action="store_true", help="Generate config template")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--body-file", help="Read body from file")
    parser.add_argument("--attachment", help="Path to attachment file")
    args = parser.parse_args()

    if args.init:
        init_config()
        return

    if not args.subject:
        parser.error("--subject is required (or use --init to set up config)")

    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        parser.error("Either --body or --body-file is required")
        return

    config = load_config()
    success = send_email(config, args.subject, body, args.attachment)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
