#!/usr/bin/env python3
"""
gnusha.org public-inbox collector for the Bitcoin development mailing list.

gnusha hosts a public-inbox v1 git mirror of bitcoindev@googlegroups.com,
including the imported Linux Foundation bitcoin-dev history. Full history
is cloned via git, not scraped from HTML/Atom.

Mirror docs: https://gnusha.org/pi/bitcoindev/_/text/mirror/

    git clone --mirror https://gnusha.org/pi/bitcoindev
    git clone --mirror git://gnusha.org/pi-bitcoindev

Output: data/mailing_lists/emails.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.jsonl_merge import email_key, load_jsonl_index, write_jsonl
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

# gnusha currently lists one Bitcoin public inbox. bitcoin-core-dev is not hosted.
GNUSHA_INBOXES = {
    "bitcoin-dev": {
        "list_name": "bitcoin-dev",
        "https_url": "https://gnusha.org/pi/bitcoindev",
        "git_url": "git://gnusha.org/pi-bitcoindev",
        "web_url": "https://gnusha.org/pi/bitcoindev/",
        "repo_name": "bitcoindev.git",
    },
}

GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "LC_ALL": "C",
}


class GnushaCollector:
    """Clone/fetch gnusha public-inbox git mirrors and emit emails.jsonl."""

    def __init__(self, inboxes: Optional[Dict[str, Dict[str, str]]] = None):
        self.inboxes = inboxes or GNUSHA_INBOXES
        self.data_dir = get_data_dir() / "mailing_lists"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mirror_dir = self.data_dir / "gnusha"
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        self.emails_file = self.data_dir / "emails.jsonl"
        self.manifest_file = self.data_dir / "gnusha_manifest.json"

    def collect(self, fetch: bool = True, parse_only: bool = False) -> Dict[str, Any]:
        """Fetch mirrors if needed, then parse every message into emails.jsonl."""
        logger.info("Starting gnusha.org public-inbox collection")

        if not parse_only:
            for inbox in self.inboxes.values():
                self._sync_mirror(inbox, fetch=fetch)

        all_emails: List[Dict[str, Any]] = []
        inbox_stats: Dict[str, Any] = {}
        head_shas: Dict[str, str] = {}

        for key, inbox in self.inboxes.items():
            repo = self._repo_path(inbox)
            if not (repo / "HEAD").exists() and not (repo / ".git").exists():
                logger.error("Mirror missing for %s at %s", key, repo)
                continue
            git_dir = self._git_dir(repo)
            head_shas[key] = self._head_sha(git_dir)
            emails = list(self._parse_repo(inbox))
            all_emails.extend(emails)
            dates = [e["date"] for e in emails if e.get("date")]
            inbox_stats[key] = {
                "count": len(emails),
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None,
                "head_sha": head_shas[key],
            }
            logger.info(
                "Parsed %s emails from %s (%s to %s)",
                len(emails),
                key,
                inbox_stats[key]["earliest"],
                inbox_stats[key]["latest"],
            )

        unique = self._dedupe(all_emails)
        self._write_emails(unique)
        manifest = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://gnusha.org/pi/bitcoindev",
            "inboxes": inbox_stats,
            "unique_emails": len(unique),
            "head_sha": head_shas.get("bitcoin-dev"),
            "output": str(self.emails_file.relative_to(project_root)),
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
        logger.info("Wrote %s unique emails to %s", len(unique), self.emails_file)
        return manifest

    def collect_update(self, fetch: bool = True) -> Dict[str, Any]:
        """Fetch mirror updates and merge only new messages since last head_sha."""
        logger.info("Starting gnusha incremental update")
        prior_manifest: Dict[str, Any] = {}
        if self.manifest_file.exists():
            try:
                prior_manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prior_manifest = {}

        old_sha = prior_manifest.get("head_sha")
        if not old_sha:
            inbox_meta = (prior_manifest.get("inboxes") or {}).get("bitcoin-dev") or {}
            old_sha = inbox_meta.get("head_sha")

        for inbox in self.inboxes.values():
            self._sync_mirror(inbox, fetch=fetch)

        existing = load_jsonl_index(self.emails_file, email_key) if self.emails_file.exists() else {}
        prior_count = len(existing)
        new_emails: List[Dict[str, Any]] = []
        inbox_stats: Dict[str, Any] = {}
        new_sha = ""

        for key, inbox in self.inboxes.items():
            repo = self._repo_path(inbox)
            git_dir = self._git_dir(repo)
            new_sha = self._head_sha(git_dir)

            if not old_sha and prior_count > 0:
                logger.info(
                    "No head_sha in manifest but %s emails exist; bootstrapping to %s",
                    prior_count,
                    new_sha[:12],
                )
                old_sha = new_sha

            if old_sha and old_sha == new_sha:
                logger.info("Mirror %s unchanged at %s", key, new_sha[:12])
                dates = [e.get("date") for e in existing.values() if e.get("date")]
                inbox_stats[key] = {
                    "count": prior_count,
                    "earliest": min(dates) if dates else None,
                    "latest": max(dates) if dates else None,
                    "head_sha": new_sha,
                    "new_this_run": 0,
                }
                continue

            blobs = self._blobs_since(git_dir, old_sha, new_sha)
            logger.info(
                "Parsing %s changed blobs for %s (%s -> %s)",
                len(blobs),
                key,
                (old_sha or "none")[:12],
                new_sha[:12],
            )
            parsed = 0
            for path, sha, raw in self._cat_blobs(git_dir, blobs):
                email_data = self._parse_raw_email(raw, inbox, path)
                if email_data:
                    parsed += 1
                    new_emails.append(email_data)
            merge_records, added = _merge_emails(existing, new_emails)
            existing = merge_records
            dates = [e.get("date") for e in existing.values() if e.get("date")]
            inbox_stats[key] = {
                "count": len(existing),
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None,
                "head_sha": new_sha,
                "new_this_run": added,
            }
            logger.info("Merged %s new emails from %s (%s parsed)", added, key, parsed)

        write_jsonl(
            self.emails_file,
            existing.values(),
            sort_key=lambda e: (e.get("date") or "", e.get("message_id") or ""),
        )
        manifest = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://gnusha.org/pi/bitcoindev",
            "inboxes": inbox_stats,
            "unique_emails": len(existing),
            "head_sha": new_sha,
            "prior_count": prior_count,
            "new_this_run": len(existing) - prior_count,
            "output": str(self.emails_file.relative_to(project_root)),
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
        logger.info(
            "Gnusha update complete: %s total emails (+%s new)",
            len(existing),
            manifest["new_this_run"],
        )
        return manifest

    def _repo_path(self, inbox: Dict[str, str]) -> Path:
        return self.mirror_dir / inbox["repo_name"]

    def _sync_mirror(self, inbox: Dict[str, str], fetch: bool = True) -> Path:
        repo = self._repo_path(inbox)
        if (repo / "HEAD").exists():
            if fetch:
                logger.info("Fetching updates for %s", repo)
                self._run_git(["fetch", "--prune", "origin"], cwd=repo)
            else:
                logger.info("Using existing mirror %s (fetch skipped)", repo)
            return repo

        logger.info("Cloning %s into %s", inbox["https_url"], repo)
        repo.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._run_git(
                ["clone", "--mirror", inbox["https_url"], str(repo)],
                cwd=repo.parent,
            )
        except subprocess.CalledProcessError:
            logger.warning("HTTPS clone failed; retrying via git://")
            if repo.exists():
                shutil.rmtree(repo, ignore_errors=True)
            self._run_git(
                ["clone", "--mirror", inbox["git_url"], str(repo)],
                cwd=repo.parent,
            )
        return repo

    def _run_git(self, args: List[str], cwd: Path, timeout: int = 3600) -> subprocess.CompletedProcess:
        cmd = ["git", *args]
        logger.debug("Running %s (cwd=%s)", " ".join(cmd), cwd)
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            env={**os.environ, **GIT_ENV},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.error("git failed (%s): %s", result.returncode, stderr[-2000:])
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    def _parse_repo(self, inbox: Dict[str, str]) -> Iterator[Dict[str, Any]]:
        repo = self._repo_path(inbox)
        git_dir = self._git_dir(repo)
        blobs = list(self._list_email_blobs(git_dir))
        logger.info("Found %s candidate blobs in %s", len(blobs), inbox["list_name"])
        parsed = 0
        skipped = 0
        for path, sha, raw in self._cat_blobs(git_dir, blobs):
            try:
                email_data = self._parse_raw_email(raw, inbox, path)
            except Exception as e:
                skipped += 1
                logger.debug("Parse failed for %s: %s", path, e)
                continue
            if email_data:
                parsed += 1
                if parsed % 2500 == 0:
                    logger.info("Parsed %s/%s emails...", parsed, len(blobs))
                yield email_data
            else:
                skipped += 1
        logger.info("Blob parse for %s: %s ok, %s skipped", inbox["list_name"], parsed, skipped)

    def _git_dir(self, repo: Path) -> Path:
        if (repo / "HEAD").exists() and (repo / "objects").exists():
            return repo
        return repo / ".git"

    def _head_sha(self, git_dir: Path) -> str:
        result = self._run_git(["--git-dir", str(git_dir), "rev-parse", "HEAD"], cwd=git_dir)
        return (result.stdout or "").strip()

    def _blobs_since(self, git_dir: Path, old_sha: Optional[str], new_sha: str) -> List[Tuple[str, str]]:
        if not old_sha:
            return self._list_email_blobs(git_dir)
        if old_sha == new_sha:
            return []
        result = self._run_git(
            ["--git-dir", str(git_dir), "diff", "--name-only", old_sha, new_sha],
            cwd=git_dir,
        )
        changed = {p.strip() for p in (result.stdout or "").splitlines() if p.strip()}
        if not changed:
            return []
        return [(path, sha) for path, sha in self._list_email_blobs(git_dir) if path in changed]

    def _list_email_blobs(self, git_dir: Path) -> List[Tuple[str, str]]:
        """Return (path, blob_sha) for files in HEAD that look like public-inbox messages."""
        result = self._run_git(
            ["--git-dir", str(git_dir), "ls-tree", "-r", "-z", "HEAD"],
            cwd=git_dir,
        )
        blobs: List[Tuple[str, str]] = []
        for entry in result.stdout.split("\0"):
            if not entry.strip():
                continue
            # format: <mode> <type> <sha>\t<path>
            meta, _, path = entry.partition("\t")
            parts = meta.split()
            if len(parts) < 3 or parts[1] != "blob":
                continue
            mode, _, sha = parts[0], parts[1], parts[2]
            if mode not in {"100644", "100755", "120000"}:
                continue
            if path.startswith(".") or path.endswith((".idx", ".lock", ".sqlite")):
                continue
            blobs.append((path, sha))
        return blobs

    def _cat_blobs(
        self, git_dir: Path, blobs: List[Tuple[str, str]]
    ) -> Iterator[Tuple[str, str, bytes]]:
        if not blobs:
            return
        proc = subprocess.Popen(
            ["git", "--git-dir", str(git_dir), "cat-file", "--batch"],
            cwd=str(git_dir),
            env={**os.environ, **GIT_ENV},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=0,
        )
        assert proc.stdin is not None and proc.stdout is not None
        try:
            for path, sha in blobs:
                proc.stdin.write(f"{sha}\n".encode("ascii"))
                proc.stdin.flush()
                header = proc.stdout.readline()
                if not header:
                    break
                # "<sha> <type> <size>\n" or "<sha> missing\n"
                header_text = header.decode("ascii", errors="replace").rstrip("\n")
                fields = header_text.split()
                if len(fields) < 3 or fields[1] == "missing":
                    logger.debug("Skipping missing blob %s (%s)", sha, path)
                    continue
                try:
                    size = int(fields[2])
                except ValueError:
                    logger.warning("Unexpected cat-file header for %s: %s", sha, header_text)
                    continue
                raw = _readexact(proc.stdout, size)
                # trailing newline after payload
                _readexact(proc.stdout, 1)
                yield path, sha, raw
        finally:
            proc.stdin.close()
            proc.wait(timeout=60)

    def _parse_raw_email(
        self, raw: bytes, inbox: Dict[str, str], git_path: str
    ) -> Optional[Dict[str, Any]]:
        if not raw or not _looks_like_email(raw):
            return None
        msg = None
        for pol in (policy.default, policy.compat32):
            try:
                msg = BytesParser(policy=pol).parsebytes(raw)
                break
            except Exception:
                continue
        if msg is None:
            return None

        from_header = _header(msg, "From")
        date_header = _header(msg, "Date")
        subject = _header(msg, "Subject")
        message_id = _normalize_msgid(_header(msg, "Message-ID") or _header(msg, "Message-Id"))
        if not from_header and not message_id:
            return None

        date_iso = _parse_date(date_header)
        body = _extract_body(msg)
        quoted_text = _identify_quoted_text(body)
        original_text = _remove_quoted_text(body)
        msgid_url = message_id.strip("<>") if message_id else ""
        source_url = f"{inbox['web_url']}{msgid_url}/" if msgid_url else inbox["web_url"]

        return {
            "list_name": inbox["list_name"],
            "message_id": message_id,
            "from": from_header,
            "date": date_iso,
            "subject": subject,
            "body": body,
            "original_text": original_text,
            "quoted_text": quoted_text,
            "in_reply_to": _header(msg, "In-Reply-To"),
            "references": _header(msg, "References"),
            "source": "gnusha_public_inbox",
            "source_url": source_url,
            "git_path": git_path,
        }

    def _dedupe(self, emails: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: Set[str] = set()
        unique: List[Dict[str, Any]] = []
        for email in emails:
            key = _email_id(email)
            if key in seen:
                continue
            seen.add(key)
            unique.append(email)
        unique.sort(key=lambda e: (e.get("date") or "", e.get("message_id") or ""))
        return unique

    def _write_emails(self, emails: List[Dict[str, Any]]) -> None:
        tmp = self.emails_file.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for email in emails:
                f.write(json.dumps(email, ensure_ascii=False) + "\n")
        tmp.replace(self.emails_file)


def _readexact(fp: Any, n: int) -> bytes:
    """Read exactly n bytes from a pipe; a single read() can return short."""
    buf = bytearray()
    while len(buf) < n:
        chunk = fp.read(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _header(msg: Any, name: str) -> str:
    value = msg.get(name)
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value).strip()


def _normalize_msgid(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith("<"):
        value = f"<{value}>"
    if not value.endswith(">"):
        value = f"{value}>"
    return value


def _parse_date(date_header: str) -> Optional[str]:
    if not date_header:
        return None
    try:
        dt = parsedate_to_datetime(date_header)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return date_header


def _decode_payload(payload: bytes, charset: Optional[str]) -> str:
    if not payload:
        return ""
    candidates = []
    if charset:
        cleaned = charset.strip().strip("\"'").replace(" ", "")
        if cleaned:
            candidates.append(cleaned)
    candidates.extend(["utf-8", "latin-1"])
    seen = set()
    for enc in candidates:
        key = enc.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return payload.decode(enc, errors="replace")
        except LookupError:
            continue
    return payload.decode("utf-8", errors="replace")


def _extract_body(msg: Any) -> str:
    body_parts: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != "text/plain":
                continue
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition.lower():
                continue
            payload = part.get_payload(decode=True)
            if payload:
                body_parts.append(_decode_payload(payload, part.get_content_charset()))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(_decode_payload(payload, msg.get_content_charset()))
        elif isinstance(msg.get_payload(), str):
            body_parts.append(msg.get_payload())
    return "\n".join(body_parts)


def _identify_quoted_text(text: str) -> str:
    patterns = [
        r"^>.*$",
        r"^On .* wrote:.*$",
        r"^-----Original Message-----.*$",
    ]
    quoted_lines = []
    for line in text.split("\n"):
        for pattern in patterns:
            if re.match(pattern, line):
                quoted_lines.append(line)
                break
    return "\n".join(quoted_lines)


def _remove_quoted_text(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if not re.match(r"^>", line))


def _looks_like_email(raw: bytes) -> bool:
    sample = raw[:65536].lstrip().lower()
    if not sample:
        return False
    return (
        sample.startswith(b"from:")
        or sample.startswith(b"from ")
        or sample.startswith(b"return-path:")
        or sample.startswith(b"received:")
        or b"\nfrom:" in sample
        or b"\nmessage-id:" in sample
    )


def _merge_emails(
    existing: Dict[str, Dict[str, Any]], updates: Iterable[Dict[str, Any]]
) -> tuple[Dict[str, Dict[str, Any]], int]:
    added = 0
    for email in updates:
        key = email_key(email)
        if not key:
            continue
        if key not in existing:
            added += 1
        existing[key] = email
    return existing, added


def _email_id(email: Dict[str, Any]) -> str:
    msg_id = (email.get("message_id") or "").strip()
    if msg_id:
        return f"msgid:{msg_id.lower()}"
    return "fallback:{from}|{date}|{subject}".format(
        **{
            "from": (email.get("from") or "").lower(),
            "date": email.get("date") or "",
            "subject": (email.get("subject") or "").lower(),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Bitcoin mailing-list history from gnusha.org public-inbox"
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not git fetch; parse the existing local mirror only",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Skip clone/fetch entirely (fails if the mirror is missing)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch mirror and merge only new messages since last head_sha",
    )
    args = parser.parse_args()
    collector = GnushaCollector()
    if args.update:
        collector.collect_update(fetch=not args.no_fetch)
    else:
        collector.collect(fetch=not args.no_fetch, parse_only=args.parse_only)
    logger.info("gnusha.org collection complete")


if __name__ == "__main__":
    main()
