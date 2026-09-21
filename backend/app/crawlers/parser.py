"""SCNU CMS adapter. Fixtures are synthetic; revalidate selectors against live HTML."""
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urljoin, urlsplit
from bs4 import BeautifulSoup
from app.reference import detail_url

class ParseError(ValueError):
    pass

@dataclass
class ListedNotice:
    external_id: str
    title: str
    posted_date: date
    original_url: str
    pinned: bool = False

@dataclass
class ParsedNotice:
    external_id: str
    title: str
    posted_date: date
    original_url: str
    body_text: str
    attachments: list[dict]
    image_only: bool
    content_hash: str

def parse_date(text):
    m = re.search(r"(?<!\d)(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})(?!\d)", text)
    if not m:
        return None
    try:
        return date(*map(int, m.groups()))
    except ValueError:
        return None

def external_id(anchor):
    for attr in ("href", "data-url"):
        value = anchor.get(attr, "")
        ids = parse_qs(urlsplit(value).query).get("nttSn")
        if ids and ids[0].isdigit():
            return ids[0]
    for attr in ("data-id", "data-nttsn", "data-ntt-sn"):
        val = anchor.get(attr)
        if val and str(val).isdigit():
            return str(val)
    handler = anchor.get("onclick", "") + " " + anchor.get("href", "")
    match = re.search(r"(?:nttSn\s*[=:]\s*|(?:goView|fn_view|nttInfo|selectNttInfo)\s*\(\s*)['\"]?(\d+)", handler)
    return match[1] if match else None

def parse_list(html: str, code: str) -> list[ListedNotice]:
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for tr in soup.select("table tr"):
        title_cell = tr.select_one("td.ta_l, td.taL, td.title, td.subject")
        candidates = title_cell.select("a") if title_cell else tr.select("a")
        for a in candidates:
            ident = external_id(a)
            if not ident or ident in seen:
                continue
            title = a.get_text(" ", strip=True)
            for decoration in a.select(".new, .ico_new, .hidden, .sr-only"):
                decoration.decompose()
            title = a.get_text(" ", strip=True)
            text = tr.get_text(" ", strip=True)
            posted = parse_date(text)
            if not title or not posted:
                raise ParseError("LIST_REQUIRED_FIELDS_MISSING")
            first = tr.find("td")
            pinned = bool(first and "공지" in first.get_text(" ", strip=True))
            rows.append(ListedNotice(ident, title[:1000], posted, detail_url(code, ident), pinned))
            seen.add(ident)
            break
    if not rows:
        if re.search(r"등록된\s*(게시물|게시글|자료|글)[이가]?\s*(없|존재하지)", soup.get_text(" ", strip=True)):
            return []
        raise ParseError("LIST_SELECTOR_MISMATCH")
    return rows

def plain_text(node):
    for el in node.select("script,style,noscript,iframe,object,form"):
        el.decompose()
    for el in node.select("br"):
        el.replace_with("\n")
    for el in node.select("p,div,tr,li,h1,h2,h3,h4"):
        el.append("\n")
    text = node.get_text(" ", strip=False)
    return "\n".join(re.sub(r"[ \t\r\f\v]+", " ", line).strip()
                     for line in text.splitlines() if line.strip()).strip()

def parse_detail(html: str, listed: ListedNotice) -> ParsedNotice:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("td.dragable, .bbsV_cont, .board_view_con, .view_cont")
    if body is None:
        raise ParseError("DETAIL_BODY_SELECTOR_MISMATCH")
    image_count = len(body.select("img"))
    title_node = soup.select_one("th.title, .bbs_View .title, .board_view .subject, .BD_title")
    title = title_node.get_text(" ", strip=True) if title_node else listed.title
    if not title:
        raise ParseError("DETAIL_TITLE_MISSING")
    attachments, seen = [], set()
    for a in soup.select("ul.file a, .file_down a, .bbsV_file a"):
        name = a.get_text(" ", strip=True)
        href = a.get("href", "")
        if not name or name in seen:
            continue
        resolved = urljoin(listed.original_url, href)
        url = urlsplit(resolved)
        safe = url.scheme == "https" and url.hostname == "www.scnu.ac.kr" and url.port in (None,443) and not url.username and not url.password
        # Store metadata only. No attachment is downloaded or executed.
        attachments.append({"name": name[:300], "url": resolved if safe and href and not href.startswith("#") else None})
        seen.add(name)
    text = plain_text(body)
    if not text and not image_count and not attachments:
        raise ParseError("DETAIL_EMPTY_BODY")
    title = re.sub(r"\s+", " ", title).strip()[:1000]
    payload = {"title": title, "body_text": text, "attachments": attachments,
               "posted_date": listed.posted_date.isoformat(), "original_url": listed.original_url}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return ParsedNotice(listed.external_id, title, listed.posted_date, listed.original_url,
        text, attachments, image_count > 0 and len(text) < 80, fingerprint)
