#!/usr/bin/env python3
"""
Collect the Cryptography mailing list (metzdowd pipermail) covering Bitcoin's
pre-history: Satoshi's announcement through the start of bitcoin-dev.

Default window: 2008-01 through 2011-12.
Source: https://www.metzdowd.com/pipermail/cryptography/

Output:
  data/mailing_lists/cryptography.jsonl
  data/mailing_lists/cryptography_raw/{year}-{Month}.txt.gz
  data/mailing_lists/cryptography_manifest.json

Does not write to emails.jsonl (that file is the gnusha bitcoin-dev dump).
"""

from __future__ import annotations

import argparse
import calendar
import gzip
import json
import re
import sys
import time
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.jsonl_merge import email_key, load_jsonl_index, write_jsonl
from src.utils.logger import setup_logger
from src.utils.paths import get_data_dir

logger = setup_logger()

PIPERMAIL = "https://www.metzdowd.com/pipermail/cryptography"
UA = "BitcoinGovernanceResearch/1.0 (academic; +https://bitcoincommons.org)"


class CryptographyMLCollector:
    def __init__(self, delay: float = 0.4) -> None:
        self.delay = delay
        self.data_dir = get_data_dir() / "mailing_lists"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.data_dir / "cryptography_raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.emails_file = self.data_dir / "cryptography.jsonl"
        self.manifest_file = self.data_dir / "cryptography_manifest.json"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "*/*"})
        self._last_request = 0.0

    def collect(self, start: str = "2008-01", end: str = "2011-12") -> Dict[str, Any]:
        start_y, start_m = _parse_year_month(start)
        end_y, end_m = _parse_year_month(end)
        months = _month_range(start_y, start_m, end_y, end_m)
        logger.info(
            "Starting cryptography mailing-list collection (%s months: %s to %s)",
            len(months),
            start,
            end,
        )

        emails: List[Dict[str, Any]] = []
        downloaded = 0
        missing = 0
        parse_errors = 0
        for year, month_name in months:
            filename = f"{year}-{month_name}.txt.gz"
            url = f"{PIPERMAIL}/{filename}"
            raw_path = self.raw_dir / filename
            try:
                payload = self._download_month(url, raw_path)
            except FileNotFoundError:
                missing += 1
                logger.info("No archive for %s-%s", year, month_name)
                continue
            except Exception as exc:
                parse_errors += 1
                logger.warning("Failed to download %s: %s", url, exc)
                continue
            downloaded += 1
            month_emails = _parse_mbox_bytes(payload, filename)
            emails.extend(month_emails)
            logger.info("%s: %s messages", filename, len(month_emails))

        emails = _dedupe(emails)
        emails.sort(key=lambda e: (e.get("date") or "", e.get("message_id") or ""))
        tmp = self.emails_file.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for email in emails:
                fh.write(json.dumps(email, ensure_ascii=False) + "\n")
        tmp.replace(self.emails_file)

        dates = [e.get("date") for e in emails if e.get("date")]
        manifest = {
            "source": PIPERMAIL,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "start": start,
            "end": end,
            "months_expected": len(months),
            "months_downloaded": downloaded,
            "months_missing": missing,
            "parse_errors": parse_errors,
            "emails": len(emails),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info("Cryptography list: %s emails (%s to %s)", len(emails), manifest["date_min"], manifest["date_max"])
        return manifest

    def collect_update(self) -> Dict[str, Any]:
        """Fetch months since the last stored message and merge new emails."""
        prior: Dict[str, Any] = {}
        if self.manifest_file.exists():
            try:
                prior = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prior = {}
        start = prior.get("date_max") or prior.get("end") or "2008-01"
        start_y, start_m = _parse_year_month(str(start)[:7])
        end = datetime.now(timezone.utc).strftime("%Y-%m")
        logger.info("Cryptography incremental update from %s to %s", f"{start_y}-{start_m:02d}", end)

        existing = load_jsonl_index(self.emails_file, email_key) if self.emails_file.exists() else {}
        prior_count = len(existing)
        months = _month_range(start_y, start_m, *_parse_year_month(end))
        downloaded = missing = 0
        new_count = 0

        for year, month_name in months:
            filename = f"{year}-{month_name}.txt.gz"
            url = f"{PIPERMAIL}/{filename}"
            raw_path = self.raw_dir / filename
            try:
                payload = self._download_month(url, raw_path)
            except FileNotFoundError:
                missing += 1
                continue
            except Exception as exc:
                logger.warning("Failed to download %s: %s", url, exc)
                continue
            downloaded += 1
            month_emails = _parse_mbox_bytes(payload, filename)
            month_new = 0
            for email in month_emails:
                key = email_key(email)
                if not key or key in existing:
                    continue
                existing[key] = email
                new_count += 1
                month_new += 1
            logger.info("%s: +%s new messages", filename, month_new)

        write_jsonl(
            self.emails_file,
            existing.values(),
            sort_key=lambda e: (e.get("date") or "", e.get("message_id") or ""),
        )
        dates = [e.get("date") for e in existing.values() if e.get("date")]
        manifest = {
            "source": PIPERMAIL,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "start": f"{start_y}-{start_m:02d}",
            "end": end,
            "months_checked": len(months),
            "months_downloaded": downloaded,
            "months_missing": missing,
            "emails": len(existing),
            "prior_count": prior_count,
            "new_this_run": new_count,
            "date_min": min(dates) if dates else prior.get("date_min"),
            "date_max": max(dates) if dates else prior.get("date_max"),
        }
        self.manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        logger.info("Cryptography update: %s total emails (+%s new)", len(existing), new_count)
        return manifest

    def _download_month(self, url: str, dest: Path) -> bytes:
        if dest.exists() and dest.stat().st_size > 0:
            return dest.read_bytes()
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, timeout=60)
        self._last_request = time.monotonic()
        if resp.status_code == 404:
            raise FileNotFoundError(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return resp.content


def _parse_year_month(value: str) -> Tuple[int, int]:
    year_s, month_s = value.split("-", 1)
    return int(year_s), int(month_s)


def _month_range(sy: int, sm: int, ey: int, em: int) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    year, month = sy, sm
    while (year, month) <= (ey, em):
        out.append((year, calendar.month_name[month]))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return out


def _parse_mbox_bytes(gz_payload: bytes, archive_name: str) -> List[Dict[str, Any]]:
    try:
        raw = gzip.decompress(gz_payload)
    except OSError:
        raw = gz_payload
    chunks = re.split(rb"\n(?=From )", raw)
    emails: List[Dict[str, Any]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        parsed = _parse_one_email(chunk, archive_name)
        if parsed:
            emails.append(parsed)
    return emails


def _parse_one_email(raw: bytes, archive_name: str) -> Optional[Dict[str, Any]]:
    # Drop the mbox From_ separator so the parser sees real headers.
    if raw.startswith(b"From "):
        nl = raw.find(b"\n")
        if nl != -1:
            raw = raw[nl + 1 :]
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
    body = _extract_body(msg)
    return {
        "list_name": "cryptography",
        "message_id": message_id,
        "from": from_header,
        "date": _parse_date(date_header),
        "subject": subject,
        "body": body,
        "original_text": _remove_quoted_text(body),
        "quoted_text": _identify_quoted_text(body),
        "in_reply_to": _header(msg, "In-Reply-To"),
        "references": _header(msg, "References"),
        "source": "metzdowd_pipermail",
        "source_url": f"{PIPERMAIL}/{archive_name}",
        "archive": archive_name,
    }


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
    quoted_lines = []
    for line in text.split("\n"):
        if re.match(r"^>", line) or re.match(r"^On .* wrote:", line):
            quoted_lines.append(line)
    return "\n".join(quoted_lines)


def _remove_quoted_text(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if not re.match(r"^>", line))


def _dedupe(emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for email in emails:
        msgid = (email.get("message_id") or "").strip().lower()
        key = msgid or "|".join(
            [
                (email.get("from") or "").lower(),
                email.get("date") or "",
                (email.get("subject") or "").lower(),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(email)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect metzdowd cryptography mailing list")
    parser.add_argument("--start", default="2008-01", help="First month YYYY-MM")
    parser.add_argument("--end", default="2011-12", help="Last month YYYY-MM")
    parser.add_argument("--all", action="store_true", help="Entire pipermail archive (2001-present)")
    parser.add_argument("--update", action="store_true", help="Fetch months since last manifest and merge new emails")
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()
    collector = CryptographyMLCollector(delay=args.delay)
    if args.update:
        collector.collect_update()
        return
    start, end = args.start, args.end
    if args.all:
        start, end = "2001-03", datetime.now(timezone.utc).strftime("%Y-%m")
    collector = CryptographyMLCollector(delay=args.delay)
    collector.collect(start=start, end=end)


if __name__ == "__main__":
    main()
