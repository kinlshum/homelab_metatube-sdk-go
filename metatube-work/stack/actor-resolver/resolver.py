#!/usr/bin/env python3

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import socket
import uuid
from datetime import datetime, timezone
from http.client import HTTPException
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor, wait

METATUBE_URL = os.getenv("METATUBE_URL", "http://metatube:8080").rstrip("/")
PROVIDER_BRIDGE_URL = os.getenv("PROVIDER_BRIDGE_URL", "http://provider-bridge:9210").rstrip("/")
CACHE_FILE = os.getenv("CACHE_FILE", "/data/cache.json")
OVERRIDES_FILE = os.getenv("OVERRIDES_FILE", "/data/overrides.json")
FLARE_URL = os.getenv("FLARE_URL", "http://flaresolverr:8191/v1")
CACHE_TTL = int(os.getenv("CACHE_TTL", "604800"))
NAME_PARSER_VERSION = 10  # Re-evaluate cached actors with identity, alias, and cup-size fixes.
RESOLVE_BUDGET = 75.0  # Leave room before Emby's 90-second lookup deadline.
SOURCE_TIMEOUT = 25.0
ACTOR_DB_LOOKUP_URL = os.getenv("ACTOR_DB_LOOKUP_URL", "http://192.168.10.167:8080/admin/api/actor-dictionary-result")
_request_context = threading.local()
UNRESOLVED_CACHE_TTL = 60
SOURCE_PRIORITY = ("AV-LEAGUE", "Minnano-AV", "XsList", "JavLibrary", "JAV.LINK",
                   "JAVModel", "JavDB", "JAVDatabase", "Babepedia", "Gfriends")
_configured_sources = (value.strip() for value in os.getenv(
    "SOURCE_ORDER", ",".join(SOURCE_PRIORITY)).split(","))
SOURCE_ORDER = (SOURCE_PRIORITY[:-1] +
                tuple(dict.fromkeys(value for value in _configured_sources
                                        if value and value not in SOURCE_PRIORITY)) +
                ("Gfriends",))
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "120"))
_lock = threading.Lock()
_event_lock = threading.Lock()
TRACE_FILE = os.getenv("TRACE_FILE", "/data/resolve-events.jsonl")
TRACE_READ_ALLOWED_IPS = set(value.strip() for value in os.getenv(
    "TRACE_READ_ALLOWED_IPS", "192.168.10.167,192.168.10.170,127.0.0.1,::1"
).split(",") if value.strip())


class SourceIdentityMismatch(Exception):
    def __init__(self, url):
        super().__init__("source identity differs")
        self.url = url


class NoActorMatch(LookupError):
    def __init__(self, name, source_status, rejected_urls):
        super().__init__(f"no actor match for {name}")
        self.source_status = source_status
        self.rejected_urls = rejected_urls


def append_resolve_event(event):
    """Keep a bounded, persistent receipt of resolver ingress and its result."""
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _event_lock:
        try:
            os.makedirs(os.path.dirname(TRACE_FILE), exist_ok=True)
            with open(TRACE_FILE, "a", encoding="utf-8") as stream:
                stream.write(line)
            if os.path.getsize(TRACE_FILE) > 2_000_000:
                with open(TRACE_FILE, "r", encoding="utf-8") as stream:
                    tail = stream.readlines()[-500:]
                temporary = TRACE_FILE + ".tmp"
                with open(temporary, "w", encoding="utf-8") as stream:
                    stream.writelines(tail)
                os.replace(temporary, TRACE_FILE)
        except OSError as error:
            print("resolver trace write failed: " + type(error).__name__, flush=True)


def recent_resolve_events(name):
    with _event_lock:
        try:
            with open(TRACE_FILE, "r", encoding="utf-8") as stream:
                lines = stream.readlines()[-500:]
        except FileNotFoundError:
            return []
        except OSError:
            return []
    events = []
    seen_requests = set()
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        request_id = event.get("request_id")
        if request_id and request_id in seen_requests:
            continue
        if not name or event.get("name") == name:
            events.append(event)
            if request_id:
                seen_requests.add(request_id)
        if len(events) >= (20 if name else 50):
            break
    return events


def request_timeout():
    remaining = getattr(_request_context, 'deadline', time.monotonic() + TIMEOUT) - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('actor lookup deadline reached')
    return min(TIMEOUT, SOURCE_TIMEOUT, remaining)


def collect_sources(tasks, deadline, labels=None, outcomes=None, rejected_urls=None):
    """Collect independently, in input order, without waiting for slow sources.

    Workers only return source facts; they never write the resolver cache.
    Propagate the absolute deadline through multi-request provider lookups.
    """
    if not tasks or time.monotonic() >= deadline:
        return []
    run_id = getattr(_request_context, 'run_id', '')
    def collect(function, argument):
        _request_context.deadline = deadline
        _request_context.run_id = run_id
        try:
            return function(argument)
        finally:
            del _request_context.deadline
            del _request_context.run_id
    pool = ThreadPoolExecutor(max_workers=min(8, len(tasks)))
    futures = [pool.submit(collect, function, argument) for function, argument in tasks]
    try:
        done, _ = wait(futures, timeout=max(0, deadline - time.monotonic()))
        results = []
        for index, future in enumerate(futures):
            label = labels[index] if labels else None
            if future not in done:
                future.cancel()
                if label and outcomes is not None:
                    outcomes[label] = "timed out"
                continue
            try:
                value = future.result()
                if label and outcomes is not None:
                    outcomes[label] = "found" if value else "no match"
                if value:
                    results.append(value)
            except Exception as error:
                if label and outcomes is not None:
                    outcomes[label] = ("identity mismatch" if isinstance(error, SourceIdentityMismatch) else
                                       "timed out" if isinstance(error, (TimeoutError, socket.timeout)) else "source error")
                if label and rejected_urls is not None and isinstance(error, SourceIdentityMismatch):
                    rejected_urls[label] = error.url
                # Do not leak provider URLs, credentials or exception internals.
                pass
        return results
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def request_json(url):
    headers = {"Accept": "application/json"}
    if url.startswith(METATUBE_URL + "/v1/actors/"):
        run_id = getattr(_request_context, 'run_id', '')
        if run_id:
            headers["X-MetaTube-Run-ID"] = run_id
            headers["X-MetaTube-Client"] = "actor-resolver"
    request = urllib.request.Request(url, headers=headers)
    return json.loads(read_with_retry(request))


def request_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return read_with_retry(request).decode("utf-8", errors="replace")


def read_with_retry(request):
    """Retry idempotent source GETs only, with fresh connections and a deadline."""
    for attempt in range(3):
        delay = 0.25 * (2 ** attempt)
        try:
            with urllib.request.urlopen(request, timeout=request_timeout()) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            retryable = error.code in (429, 500, 502, 503, 504)
            retry_after = error.headers.get('Retry-After', '') if error.headers else ''
            if retry_after.isdigit():
                delay = max(delay, int(retry_after))
            error.close()
            if not retryable or attempt == 2:
                raise
        except (urllib.error.URLError, ConnectionError, socket.timeout, HTTPException):
            if attempt == 2:
                raise
        if request.get_method() != 'GET' or delay >= request_timeout():
            raise TimeoutError('actor source retry budget exhausted')
        time.sleep(delay)


def flare_text(url):
    timeout = request_timeout()
    payload = json.dumps({"cmd": "request.get", "url": url, "maxTimeout": int(timeout * 1000)}).encode()
    request = urllib.request.Request(FLARE_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if result.get("status") != "ok":
        raise RuntimeError(result.get("message", "FlareSolverr request failed"))
    return result.get("solution", {}).get("response", "")


def clean_html(value):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def identity_key(value):
    return re.sub(r"[^a-z0-9\u3040-\u30ff\u3400-\u9fff]", "", value.casefold())


def same_identity(left, right):
    if identity_key(left) == identity_key(right):
        return True
    if japanese(left) or japanese(right):
        return False
    return sorted(re.findall(r"[a-z0-9]+", left.casefold())) == sorted(re.findall(r"[a-z0-9]+", right.casefold()))


def enrichment_identities(values):
    identities = list(dict.fromkeys(value for value in values if value))
    for value in tuple(identities):
        words = value.split()
        if len(words) == 2 and not japanese(value):
            reversed_name = " ".join(reversed(words))
            if reversed_name not in identities:
                identities.append(reversed_name)
    return identities


def profile_value(document, label):
    pattern = rf"<span[^>]*>\s*{re.escape(label)}\s*:?</span>\s*<span[^>]*>(.*?)</span>"
    match = re.search(pattern, document, re.IGNORECASE | re.DOTALL)
    return clean_html(match.group(1)) if match else ""


def minnano_value(document, label):
    pattern = rf"<span[^>]*>\s*{re.escape(label)}\s*</span>\s*<p[^>]*>(.*?)</p>"
    match = re.search(pattern, document, re.IGNORECASE | re.DOTALL)
    return clean_html(match.group(1)) if match else ""


def minnano_values(document, label):
    pattern = rf"<span[^>]*>\s*{re.escape(label)}\s*</span>\s*<p[^>]*>(.*?)</p>"
    return [clean_html(match) for match in re.findall(pattern, document, re.IGNORECASE | re.DOTALL)]


def minnano_detail(actor_id):
    homepage = f"https://www.minnano-av.com/actress{actor_id}.html"
    document = minnano_text(homepage)
    found = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                      document, re.IGNORECASE | re.DOTALL)
    schema = json.loads(unescape(found.group(1))) if found else {}
    if not isinstance(schema, dict):
        schema = next((x for x in schema if isinstance(x, dict) and x.get('@type') == 'Person'), {})
    if '@graph' in schema:
        schema = next((x for x in schema['@graph'] if x.get('@type') == 'Person'), {})
    aliases = []
    name_aliases = {}
    for key in ('alternateName', 'additionalName'):
        value = schema.get(key) or []
        aliases.extend(value if isinstance(value, list) else [value])
    heading = re.search(r'<h1[^>]*>(.*?)</h1>', document, re.I | re.S)
    heading_name = ''
    if heading:
        heading_name = clean_html(re.split(r'<span\b', heading.group(1), flags=re.I)[0])
        for span in re.findall(r'<span[^>]*>(.*?)</span>', heading.group(1), re.I | re.S):
            aliases.extend(x.strip() for x in re.split(r'[/／]', clean_html(span)) if x.strip())
    for former in minnano_values(document, "別名"):
        former_match = re.match(r"(.+?)(?:【[^】]+】)?\s*（(.+?)）", former)
        if former_match:
            original_alias = former_match.group(1).strip()
            aliases.append(original_alias)
            values = [value.strip() for value in former_match.group(2).split("/") if value.strip()]
            aliases.extend(values)
            latin = latin_alias(values)
            if latin:
                name_aliases[original_alias] = latin
        elif former:
            aliases.append(former)
    size = minnano_value(document, "サイズ")
    height_match = re.search(r"T(\d+)", size)
    cup_match = re.search(r"([A-Z])カップ", size)
    debut = minnano_value(document, "デビュー作品")
    debut_match = re.search(r"（(\d{4})年(\d{2})月\s*(\d{2})日）", debut)
    sign_match = re.search(r"）\s*([^\s<]+座)", minnano_value(document, "生年月日"))
    return {
        "id": str(actor_id), "name": schema.get("name") or heading_name, "provider": "Minnano-AV",
        "homepage": homepage, "aliases": list(dict.fromkeys(value for value in aliases if value)),
        "name_aliases": name_aliases,
        "images": [schema["image"]] if schema.get("image") else [],
        "birthday": schema.get("birthDate", ""),
        "debut_date": "-".join(debut_match.groups()) if debut_match else "",
        "debut_title": re.sub(r"（\d{4}年\d{2}月\s*\d{2}日）\s*$", "", debut).strip(),
        "av_appearance_period": minnano_value(document, "AV出演期間"), "tags": [],
        "blood_type": "", "cup_size": cup_match.group(1) if cup_match else "",
        "measurements": "/".join(re.findall(r"[BWH]\d+", size)), "nationality": "日本",
        "height": int(height_match.group(1)) if height_match else 0,
        "hobby": minnano_value(document, "趣味・特技"), "skill": "",
        "summary": "", "sign": sign_match.group(1) if sign_match else "",
    }


def minnano_text(url):
    """A direct challenge is not a missing identity; use our configured solver."""
    try:
        return request_text(url)
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 503):
            raise
        return flare_text(url)


def minnano_search_detail(names):
    identities = [names] if isinstance(names, str) else list(names)
    for name in identities:
        if not name:
            continue
        url = "https://www.minnano-av.com/search_result.php?" + urllib.parse.urlencode({
            "search_scope": "actress", "search_word": name, "search": "Go"
        })
        document = minnano_text(url)
        candidates = re.findall(r'(?:https://www\.minnano-av\.com/)?actress(\d+)\.html', document)
        for actor_id in dict.fromkeys(candidates):
            detail = minnano_detail(actor_id)
            # A Western name alone is ambiguous; verify the original Japanese
            # name against the profile or one of its former-name aliases.
            if exact_match(detail, [identities[0]]):
                return detail
    return None


def xslist_search_detail(name):
    url = "https://xslist.org/search?" + urllib.parse.urlencode({"query": name, "lg": "en"})
    document = flare_text(url)
    anchors = re.findall(r'<a\b([^>]*)>(.*?)</a>', document, re.IGNORECASE | re.DOTALL)
    for attributes, body in anchors:
        href = re.search(r'href="(?:https://xslist\.org)?/en/model/(\d+)\.html"', attributes, re.I)
        if not href:
            continue
        actor_id = href.group(1)
        title_match = re.search(r'title="([^"]*)"', attributes, re.I)
        title = title_match.group(1) if title_match else ""
        label = clean_html(title or body)
        parts = [value.strip() for value in re.split(r"\s+-\s+", label) if value.strip()]
        original = next((value for value in parts if japanese(value)), "")
        western = next((value for value in parts if not japanese(value)), "")
        if not original or identity_key(original) != identity_key(name):
            continue
        image = re.search(rf'https://xslist\.org/kojav/model2/\d+/{re.escape(actor_id)}\.jpg', document)
        context = clean_html(body)
        birthday_match = re.search(r"(?:Born|Birthday)\D+(\d{1,2})/(\d{1,2})/(\d{4})", context, re.I)
        birthday = ""
        if birthday_match:
            month, day, year = birthday_match.groups()
            birthday = f"{year}-{int(month):02d}-{int(day):02d}"
        return {
            "id": actor_id, "name": original, "provider": "XsList",
            "homepage": f"https://xslist.org/en/model/{actor_id}.html",
            "aliases": [western] if western else [],
            "images": [image.group(0)] if image else [], "birthday": birthday,
            "debut_date": "", "debut_title": "", "av_appearance_period": "",
            "tags": [], "blood_type": "", "cup_size": "", "measurements": "",
            "nationality": "日本", "height": 0, "hobby": "", "skill": "",
            "summary": "", "sign": "",
        }
    return None


def javlibrary_detail(name):
    search_url = "https://www.javlibrary.com/ja/vl_searchbykeyword.php?" + urllib.parse.urlencode({
        "keyword": name
    })
    document = flare_text(search_url)
    stars = re.findall(
        r'href="(?:https://www\.javlibrary\.com/ja/)?vl_star\.php\?s=([a-z0-9]+)"[^>]*>(.*?)</a>',
        document, re.IGNORECASE | re.DOTALL,
    )
    for actor_id, label in stars:
        if identity_key(clean_html(label)) != identity_key(name):
            continue
        homepage = f"https://www.javlibrary.com/en/vl_star.php?s={actor_id}"
        english = flare_text(homepage)
        heading = re.search(r"Videos\s+starring\s+([^<\r\n]+)", english, re.IGNORECASE)
        western = clean_html(heading.group(1)) if heading else ""
        return {
            "id": actor_id, "name": name, "provider": "JavLibrary",
            "homepage": homepage, "aliases": [western] if western else [], "images": [],
            "birthday": "", "debut_date": "", "debut_title": "",
            "av_appearance_period": "", "tags": [], "blood_type": "",
            "cup_size": "", "measurements": "", "nationality": "日本",
            "height": 0, "hobby": "", "skill": "", "summary": "", "sign": "",
        }
    return None


def normalize_cup_size(raw):
    """Keep the Japanese cup letter, not Babepedia's conversion sentence."""
    value = str(raw or "").strip().upper()
    japanese_size = re.search(r"\bJP:\s*\d{2,3}\s*([A-Z]{1,3})\b", value)
    if japanese_size:
        return japanese_size.group(1)
    match = re.match(r"^(?:\d{2,3}\s*)?([A-Z]{1,3})(?:\s|$|\b)", value)
    if not match or match.group(1) in {"N", "NA", "NAN", "UNK"}:
        return ""
    return match.group(1)


def babepedia_detail(names):
    originals = {identity_key(name) for name in names if japanese(name)}
    rejected_url = ""
    for name in names:
        if not name or japanese(name):
            continue
        search_url = "https://www.babepedia.com/ajax-search.php?" + urllib.parse.urlencode({"term": name})
        try:
            response = flare_text(search_url)
            pre = re.search(r"<pre[^>]*>(.*?)</pre>", response, re.IGNORECASE | re.DOTALL)
            results = json.loads(unescape(pre.group(1)) if pre else response)
        except (json.JSONDecodeError, OSError, RuntimeError):
            continue
        match = next((item for item in results if same_identity(item.get("label", ""), name)), None)
        if not match:
            continue
        actor_name = match["label"].strip()
        slug = match.get("value", actor_name).replace(" ", "_")
        homepage = f"https://www.babepedia.com/babe/{urllib.parse.quote(slug)}"
        document = flare_text(homepage)
        aliases_match = re.search(r'<h2[^>]*id="aka"[^>]*>(.*?)</h2>', document, re.IGNORECASE | re.DOTALL)
        aliases = [value.strip() for value in clean_html(aliases_match.group(1)).split(" - ") if value.strip()] if aliases_match else []
        if originals and not any(identity_key(alias) in originals for alias in aliases if japanese(alias)):
            rejected_url = homepage
            continue
        born = profile_value(document, "Born")
        date_match = re.search(r"(\d{1,2})(?:st|nd|rd|th)? of ([A-Za-z]+) (\d{4})", born)
        birthday = ""
        if date_match:
            months = {month: index for index, month in enumerate(
                ("January", "February", "March", "April", "May", "June", "July", "August",
                 "September", "October", "November", "December"), 1)}
            birthday = f"{date_match.group(3)}-{months[date_match.group(2)]:02d}-{int(date_match.group(1)):02d}"
        images = re.findall(r'<div[^>]*id="profbox2".*?<a[^>]*class="img"[^>]*href="([^"]+)"', document,
                            re.IGNORECASE | re.DOTALL)
        bio = re.search(r'<p[^>]*id="biotext"[^>]*>(.*?)</p>', document, re.IGNORECASE | re.DOTALL)
        return {
            "id": slug, "name": actor_name, "provider": "Babepedia", "homepage": homepage,
            "aliases": aliases, "images": [urllib.parse.urljoin(homepage, value) for value in images],
            "birthday": birthday, "debut_date": "", "blood_type": "",
            "cup_size": normalize_cup_size(profile_value(document, "Bra/cup size")),
            "measurements": profile_value(document, "Measurements").removesuffix(" ("),
            "nationality": profile_value(document, "Nationality"),
            "height": int(match.group(1)) if (match := re.search(r"(\d+) cm", profile_value(document, "Height"))) else 0,
            "hobby": "", "skill": "", "summary": clean_html(bio.group(1)) if bio else ""
        }
    if rejected_url:
        raise SourceIdentityMismatch(rejected_url)
    return None


def javdatabase_detail(names):
    japanese_names = {identity_key(name) for name in names if japanese(name)}
    rejected_url = ""
    for name in names:
        if not name or japanese(name):
            continue
        url = "https://www.javdatabase.com/?" + urllib.parse.urlencode({"s": name, "post_type": "idols"})
        try:
            search = flare_text(url)
        except (OSError, RuntimeError):
            continue
        links = list(dict.fromkeys(re.findall(r'https://www\.javdatabase\.com/idols/[a-z0-9_-]+/?', search)))
        for homepage in links[:12]:
            try:
                document = flare_text(homepage)
            except (OSError, RuntimeError):
                continue
            heading = re.search(r'<h1[^>]*class="idol-name"[^>]*>(.*?)</h1>', document, re.IGNORECASE | re.DOTALL)
            actor_name = re.sub(r"\s*-\s*JAV\s*Profile\s*$", "", clean_html(heading.group(1))) if heading else ""
            if not same_identity(actor_name, name):
                continue
            if japanese_names:
                jp = re.search(r"\bJP:\s*([\u3040-\u30ff\u3400-\u9fff]+)", clean_html(document))
                if not jp or identity_key(jp.group(1)) not in japanese_names:
                    rejected_url = homepage
                    continue
            def labeled(label):
                found = re.search(rf'<b[^>]*>\s*{re.escape(label)}\s*:?</b>(.*?)(?:<b|<br|</p>)', document,
                                  re.IGNORECASE | re.DOTALL)
                return clean_html(found.group(1)) if found else ""
            image = re.search(r'<div[^>]*class="idol-portrait".*?<img[^>]*(?:data-src|src)="([^"]+)"', document,
                              re.IGNORECASE | re.DOTALL)
            return {
                "id": homepage.rstrip("/").rsplit("/", 1)[-1], "name": actor_name,
                "provider": "JAVDatabase", "homepage": homepage, "aliases": [],
                "images": [urllib.parse.urljoin(homepage, image.group(1))] if image else [],
                "birthday": labeled("DOB"), "debut_date": "", "blood_type": "", "cup_size": "",
                "measurements": labeled("Measurements"), "nationality": "",
                "height": int(match.group(1)) if (match := re.search(r"(\d+)", labeled("Height"))) else 0,
                "hobby": "", "skill": "", "summary": ""
            }
    if rejected_url:
        raise SourceIdentityMismatch(rejected_url)
    return None


def javlink_detail(names):
    originals = {identity_key(name) for name in names if japanese(name)}
    if not originals:
        return None
    for name in names:
        if japanese(name) or len(name.split()) != 2:
            continue
        slug = "-".join(name.casefold().split())
        homepage = f"https://jav.link/jav/{urllib.parse.quote(slug)}/"
        try:
            document = request_text(homepage)
        except (OSError, TimeoutError):
            continue
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", document, re.I | re.S)
        title = clean_html(heading.group(1)) if heading else ""
        matched = re.match(r"(.+?)\s+-\s+([\u3040-\u30ff\u3400-\u9fff]+)", title)
        if not matched or identity_key(matched.group(2)) not in originals:
            continue
        text = clean_html(document)
        born = re.search(r"Born\s*:\s*(\d{2})/(\d{2})/(\d{4})", text, re.I)
        size = {}
        for field in ("Breast", "Waist", "Hip", "Height"):
            found = re.search(rf"{field}\s*:\s*(\d+)\s*cm", text, re.I)
            size[field] = found.group(1) if found else ""
        return {"provider": "JAV.LINK", "id": slug, "homepage": homepage,
                "name": matched.group(2), "aliases": [matched.group(1)], "images": [],
                "birthday": f"{born.group(3)}-{born.group(1)}-{born.group(2)}" if born else "",
                "measurements": "/".join(f"{code}{size[field]}" for field, code in
                                         (("Breast", "B"), ("Waist", "W"), ("Hip", "H")) if size[field]),
                "height": int(size["Height"]) if size["Height"] else 0}
    return None


def javmodel_detail(names):
    originals = {identity_key(name) for name in names if japanese(name)}
    if not originals:
        return None
    for name in names:
        if japanese(name) or len(name.split()) != 2:
            continue
        slug = "-".join(name.casefold().split())
        homepage = f"https://javmodel.com/jav/{urllib.parse.quote(slug)}/"
        try:
            document = request_text(homepage)
        except (OSError, TimeoutError):
            continue
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", document, re.I | re.S)
        subheading = re.search(r"<h2[^>]*>(.*?)</h2>", document, re.I | re.S)
        title = clean_html(heading.group(1)) if heading else ""
        subtitle = clean_html(subheading.group(1)) if subheading else ""
        matched_japanese = next((part for part in re.findall(r"[\u3040-\u30ff\u3400-\u9fff]+", subtitle)
                                 if identity_key(part) in originals), "")
        if not matched_japanese or not same_identity(title, name):
            continue
        text = clean_html(document)
        born = re.search(r"Born\s*:\s*(\d{2})/(\d{2})/(\d{4})", text, re.I)
        return {"provider": "JAVModel", "id": slug, "homepage": homepage,
                "name": matched_japanese, "aliases": [title], "images": [],
                "birthday": f"{born.group(3)}-{born.group(1)}-{born.group(2)}" if born else ""}
    return None


def javdb_detail(identity):
    if not identity:
        return None
    external = identity.get("external_ids") or {}
    actor_id = external.get("JavDB") or external.get("JavdbActor") or external.get("javdb")
    if not actor_id or not re.fullmatch(r"[A-Za-z0-9]+", str(actor_id)):
        return None
    homepage = f"https://javdb.com/actors/{actor_id}"
    try:
        document = request_text(homepage)
    except (OSError, TimeoutError):
        return None
    text = clean_html(document)
    original = identity.get("japanese_name") or ""
    if not original or identity_key(original) not in {identity_key(part) for part in re.findall(r"[\u3040-\u30ff\u3400-\u9fff]+", text[:3000])}:
        raise SourceIdentityMismatch(homepage)
    return {"provider": "JavDB", "id": str(actor_id), "homepage": homepage,
            "name": original, "aliases": [], "images": []}


def japanese(value):
    return any("\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff" for char in value)


def latin_alias(values):
    for value in values:
        value = re.sub(r'/\s*\d{1,3}\s*[岁歳]\s*$', '', value or '').strip()
        # Never interpret a social handle, URL, mixed-language biography, or
        # digit-bearing account name as a person's Romanized name.
        if re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)*){0,3}", value):
            return ' '.join(value.split())
    return ""


def western_name(details, aliases, original_name=""):
    """Choose a Western name from sources whose Romanization order is known."""
    for detail in details:
        mapped = detail.get("name_aliases", {}).get(original_name, "")
        if mapped and detail.get("provider") == "Minnano-AV":
            return mapped
    for provider in ("JavLibrary", "Minnano-AV"):
        for detail in details:
            if detail.get("provider") != provider:
                continue
            value = latin_alias([detail.get("name", ""), *detail.get("aliases", [])])
            words = value.split()
            if len(words) == 2:
                return " ".join(reversed(words))
            if value:
                return value
    return latin_alias(aliases)


def clean_aliases(values, canonical_name):
    primary_latin = canonical_name.split(" (", 1)[0].strip()
    primary_tokens = sorted(re.findall(r"[a-z0-9]+", primary_latin.casefold()))
    canonical_match = re.search(r"\(JAP、(?:(?:\d{4}|\?)、)?([^()]+)\)\s*$", canonical_name)
    primary_japanese = canonical_match.group(1).strip() if canonical_match else ""
    cleaned = []
    for value in values:
        value = re.sub(r"^Also known as:\s*", "", value or "", flags=re.IGNORECASE).strip()
        if not value:
            continue
        if not valid_actor_label(value):
            continue
        # Bare AIKA/あいか belongs to the verified 1990 single-name performer.
        # Other Aika performers keep their qualified Japanese identity instead.
        if value.casefold() in {"aika", "あいか"} and primary_japanese != "あいか":
            continue
        # Age annotations are source facts, not durable identity aliases.
        if re.search(r'/\s*\d{1,3}\s*[岁歳]\s*$', value):
            continue
        # Profile pages can mix a video caption into the alias list. An age
        # embedded in a longer label describes that caption, not a performer.
        if re.search(r'\d{1,3}\s*[岁歳才]', value):
            continue
        if value.casefold() in {primary_latin.casefold(), primary_japanese.casefold(), canonical_name.casefold()}:
            continue
        value_tokens = sorted(re.findall(r"[a-z0-9]+", value.casefold()))
        if primary_tokens and value_tokens == primary_tokens:
            continue
        if re.search(r"\([^)]*JAP[、,][^)]*\)$", value, re.IGNORECASE):
            continue
        if value and value.casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(value)
    return cleaned


def valid_actor_label(value):
    """Reject scraped captions with unmatched brackets before using them as names."""
    closing = {')': '(', '）': '（', ']': '[', '】': '【'}
    stack = []
    for character in value:
        if character in closing.values():
            stack.append(character)
        elif character in closing and (not stack or stack.pop() != closing[character]):
            return False
    return not stack


def japanese_profile_name(detail):
    """Return an actual Japanese identity label, never a source UI caption."""
    for value in [detail.get("name", ""), *detail.get("aliases", [])]:
        value = (value or "").strip()
        if value and japanese(value) and valid_actor_label(value) and not re.search(r"[A-Za-z:]", value):
            return value
    return ""


def reject_ambiguous_stage_name(name, details, outcomes, rejected_urls):
    """A shared one-word stage name cannot join unrelated provider profiles."""
    if japanese(name) or len(name.split()) != 1 or not details:
        return
    subjects = {identity_key(subject) for detail in details
                if (subject := japanese_profile_name(detail))}
    years = {birthday[:4] for detail in details
             if (birthday := iso_date(detail.get("birthday")))}
    if len(subjects) == 1 and (not years or max(years) == min(years)):
        return
    reason = ("identity conflict: shared single-name search matched different profiles"
              if len(subjects) > 1 or len(years) > 1 else
              "identity unverified: no Japanese profile name for single-name search")
    for detail in details:
        provider = detail.get("provider", "")
        subject = japanese_profile_name(detail) or "none"
        year = iso_date(detail.get("birthday"))[:4] or "unknown"
        outcomes[provider] = f"{reason}; Japanese={subject}; birth year={year}"
        if detail.get("homepage"):
            rejected_urls[provider] = detail["homepage"]
    raise NoActorMatch(name, outcomes, rejected_urls)


def lookup_name(value):
    value = re.sub(r"^\[JAV_CUSTOM_PROVIDER\]\s*", "", value.strip())
    # Legacy Emby Person names sometimes have an IMDb/provider URL appended to
    # the display name. It is an external ID, never part of the actor identity.
    value = re.split(r"-imdb-", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    canonical = re.search(r"\(JAP、(?:(?:\d{4}|\?)、)?([^()]+)\)\s*$", value)
    if canonical:
        return canonical.group(1).strip()
    parenthetical = re.search(r"\(([^()]*)\)\s*$", value)
    if parenthetical and japanese(parenthetical.group(1)):
        return parenthetical.group(1).strip()
    return value


def mapped_canonical_name(value):
    value = re.sub(r"^\[JAV_CUSTOM_PROVIDER\]\s*", "", value.strip())
    value = re.split(r"-imdb-", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return value if re.search(r"\([^()]*、[^()]*、[^()]+\)\s*$", value) else ""


def actor_db_identity(name):
    """Use the existing read-only Admin2 Actor DB view for an exact identity.

    A provider timeout must never invent a name or block Emby indefinitely.
    """
    if not ACTOR_DB_LOOKUP_URL or not japanese(name):
        return None
    query = urllib.parse.urlencode({"name": name, "mode": "stored"})
    try:
        request = urllib.request.Request(ACTOR_DB_LOOKUP_URL + "?" + query,
                                         headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.load(response)
    except (OSError, ValueError, TimeoutError):
        return None
    actor = payload.get("actor_db") or {}
    aliases = [row.get("alias", "") for row in actor.get("mapping", [])]
    if name != actor.get("japanese_name") and name not in aliases:
        return None
    western = latin_alias([actor.get("western_name", ""), actor.get("name", "").split(" (", 1)[0]])
    canonical = re.fullmatch(r"[^()]+ \(JAP、((?:19|20)\d{2})、([^()]+)\)", actor.get("name", ""))
    birth_year = canonical.group(1) if canonical and canonical.group(2) == actor.get("japanese_name") else ""
    return {"western_name": western, "actor_id": actor.get("actor_id", ""),
            "japanese_name": actor.get("japanese_name", ""),
            "birth_year": birth_year,
            "external_ids": actor.get("external_ids") or {}} if western else None


def iso_date(value):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", value or "")
    return match.group(0) if match and match.group(1) != "0001" else ""


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    temporary = CACHE_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temporary, CACHE_FILE)


def actor_override(name, aliases):
    try:
        with open(OVERRIDES_FILE, encoding="utf-8") as handle:
            entries = json.load(handle).get("actors", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    identities = {value.casefold() for value in [name, *aliases] if value}
    for entry in entries:
        mapped = [entry.get("original", ""), entry.get("canonical", ""), *entry.get("aliases", [])]
        if any(value and value.casefold() in identities for value in mapped):
            return entry
    return None


def exact_match(candidate, identities):
    names = [candidate.get("name", ""), *candidate.get("aliases", [])]
    folded = {value.casefold() for value in identities if value}
    return any(value and value.casefold() in folded for value in names)


def actor_detail(result):
    provider = urllib.parse.quote(result["provider"], safe="")
    actor_id = urllib.parse.quote(str(result["id"]), safe="")
    if result["provider"] == "Minnano-AV":
        return minnano_detail(actor_id)
    if result["provider"] == "XsList":
        return request_json(
            f"{PROVIDER_BRIDGE_URL}/v1/providers/{provider}/actors/{actor_id}"
        )
    return request_json(f"{METATUBE_URL}/v1/actors/{provider}/{actor_id}?lazy=false").get("data")


def first(details, field):
    for detail in details:
        value = detail.get(field)
        if isinstance(value, str) and value.strip().casefold() in {"n/a", "unknown", "none", "-", "—"}:
            continue
        if value not in (None, "", 0, [], {}):
            return value, detail["provider"]
    return "", ""


def first_date(details, field):
    for detail in details:
        value = iso_date(detail.get(field))
        if value:
            return value, detail["provider"]
    return "", ""


def first_from(details, field, preferred_providers):
    ordered = sorted(
        details,
        key=lambda detail: preferred_providers.index(detail["provider"])
        if detail["provider"] in preferred_providers else len(preferred_providers),
    )
    return first_date(ordered, field) if field.endswith("_date") else first(ordered, field)


def place_of_birth(details):
    value, source = first(details, "place_of_birth")
    if value:
        return value, source
    for detail in details:
        summary = detail.get("summary", "")
        match = re.search(r"(?:出身地|Place of birth)[：:]\s*([^\n。,|]+)", summary, re.IGNORECASE)
        if match:
            return match.group(1).strip(), detail["provider"]
    return "", ""


def merge(name, details, identity=None):
    details = sorted(details, key=lambda item: len(SOURCE_PRIORITY) if item["provider"] == "Gfriends"
                     else SOURCE_PRIORITY.index(item["provider"])
                     if item["provider"] in SOURCE_PRIORITY else len(SOURCE_PRIORITY) - 1)
    usable_details = [item for item in details if item["provider"] != "Gfriends"]
    placeholder_only = not usable_details
    if placeholder_only:
        # Existing Actor DB identities may guide discovery, but a Gfriends-only
        # result must never launder those facts into a publishable profile.
        identity = None
    aliases = []
    images = []
    external_ids = {}
    urls = {}
    for detail in details:
        if detail["provider"] in {row["provider"] for row in usable_details}:
            external_ids[detail["provider"]] = str(detail["id"])
        if detail.get("homepage"):
            urls[detail["provider"]] = detail["homepage"]
        if detail not in usable_details:
            if placeholder_only and detail["provider"] == "Gfriends":
                for value in detail.get("images", []):
                    if value and value not in images:
                        images.append(value)
            continue
        for value in [detail.get("name", ""), *detail.get("aliases", [])]:
            if value and value.casefold() not in {item.casefold() for item in aliases}:
                aliases.append(value)
        for value in detail.get("images", []):
            if value and value not in images:
                images.append(value)

    original = name if japanese(name) else next(
        (value for detail in usable_details if (value := japanese_profile_name(detail))), name)
    english = (identity or {}).get("western_name") or western_name(usable_details, aliases, original)
    birthday, birthday_source = first_date(usable_details, "birthday")
    year = birthday[:4] if birthday else (identity or {}).get("birth_year", "")
    canonical_name = english or original
    if english and original:
        canonical_name = f"{english} (JAP、{year}、{original})" if year else f"{english} (JAP、{original})"
    override = None if placeholder_only else actor_override(name, aliases)
    if override:
        preferred = override.get("canonical", "").strip()
        original = override.get("original", original).strip()
        year = str(override.get("birth_year", year or "?")).strip()
        if preferred:
            canonical_name = f"{preferred} (JAP、{year or '?'}、{original})"
        for value in override.get("aliases", []):
            if value and value.casefold() not in {item.casefold() for item in aliases}:
                aliases.append(value)

    aliases = clean_aliases(aliases, canonical_name)
    if override:
        for value in override.get("historical_aliases", []):
            if value and value.casefold() not in {item.casefold() for item in aliases}:
                aliases.append(value)

    fields = {}
    aliases.sort(key=lambda value: (
        0 if re.search(r"[\u3400-\u9fff]", value) else
        1 if re.search(r"[\u3040-\u30ff]", value) else 2,
        value.casefold(), value))
    provenance = {}
    for field in ("debut_date", "debut_title", "av_appearance_period", "blood_type",
                  "cup_size", "measurements", "nationality", "height", "hobby", "skill",
                  "summary", "sign"):
        if field in ("debut_date", "debut_title", "av_appearance_period"):
            value, source = first_from(usable_details, field, ("Minnano-AV",))
        else:
            value, source = first(usable_details, field)
        fields[field] = value
        if source:
            provenance[field] = source
    if birthday:
        provenance["birthday"] = birthday_source
    elif year and identity:
        provenance["birth_year"] = "Actor DB"
    if identity and identity.get("western_name"):
        provenance["western_name"] = "Actor DB"
    fields["place_of_birth"], source = place_of_birth(usable_details)
    if source:
        provenance["place_of_birth"] = source
    # Some providers put a Japanese prefecture in their `nationality` slot.
    # Keep that as birthplace; never print Tokyo/Osaka as a nationality.
    locality = str(fields["nationality"] or "").strip()
    if re.fullmatch(r"[\u3400-\u9fff]{2,8}[都道府県]", locality):
        if not fields["place_of_birth"]:
            fields["place_of_birth"] = locality
            provenance["place_of_birth"] = provenance.get("nationality", "Provider")
        fields["nationality"] = "日本"
        provenance["nationality"] = "Derived from Japanese prefecture"
    source_birthday = birthday
    if override:
        override_birthday = iso_date(override.get("birthday"))
        # A stale override must not replace a date returned by the two highest
        # priority actor profiles. Keep the override only as a fallback when
        # those profiles have not supplied a verified birthday.
        if override_birthday and birthday_source not in ("AV-LEAGUE", "Minnano-AV"):
            birthday = override_birthday
            provenance["birthday"] = "Curated override"
        fields["debut_date"] = override.get("debut_date", fields["debut_date"])
        fields["debut_title"] = override.get("debut_title", fields["debut_title"])
        fields["av_appearance_period"] = override.get(
            "av_appearance_period", fields["av_appearance_period"]
        )
        if override.get("debut_date"):
            provenance["debut_date"] = "Minnano-AV"
        external_ids.update(override.get("external_ids", {}))
        urls.update(override.get("urls", {}))

    conflicts = {}
    for field in ("birthday", "blood_type", "cup_size", "measurements", "height"):
        values = {}
        for detail in usable_details:
            value = iso_date(detail.get(field)) if field == "birthday" else detail.get(field)
            if isinstance(value, str) and value.strip().casefold() in {"n/a", "unknown", "none", "-", "—"}:
                continue
            if value not in (None, "", 0):
                values.setdefault(str(value), []).append(detail["provider"])
        if len(values) > 1:
            conflicts[field] = values
    if (override and (override_birthday := iso_date(override.get("birthday")))
            and source_birthday and override_birthday != source_birthday):
        birthday_conflicts = conflicts.setdefault("birthday", {})
        birthday_conflicts.setdefault(source_birthday, [birthday_source])
        birthday_conflicts.setdefault(override_birthday, []).append("Curated override")

    # Choose the same verified source priority used for names and facts.
    stable_provider = next((provider for provider in SOURCE_PRIORITY
                            if provider in external_ids), details[0]["provider"])
    stable_id = external_ids.get(stable_provider) or str(details[0]["id"])
    return {
        "id": f"{stable_provider}:{stable_id}",
        "name": canonical_name,
        "original_name": original,
        "provider": "JAVActorResolver",
        "homepage": urls.get(stable_provider, ""),
        "aliases": aliases,
        "images": images,
        "birthday": birthday,
        "debut_date": iso_date(fields["debut_date"]),
        "debut_title": fields["debut_title"],
        "av_appearance_period": fields["av_appearance_period"],
        "tags": list(dict.fromkeys(
            value for detail in usable_details for value in detail.get("tags", []) if value
        )) if not override else list(dict.fromkeys([
            *(value for detail in usable_details for value in detail.get("tags", []) if value),
            *override.get("tags", []),
        ])),
        "blood_type": fields["blood_type"],
        "cup_size": fields["cup_size"],
        "measurements": fields["measurements"],
        "nationality": fields["nationality"],
        "height": fields["height"],
        "hobby": fields["hobby"],
        "skill": fields["skill"],
        "summary": fields["summary"],
        "place_of_birth": fields["place_of_birth"],
        "sign": fields["sign"],
        "external_ids": external_ids,
        "urls": urls,
        "provenance": provenance,
        "conflicts": conflicts,
        "sources": [detail["provider"] for detail in details],
    }


def resolve(name, refresh=False, run_id=''):
    deadline = time.monotonic() + RESOLVE_BUDGET
    _request_context.deadline = deadline
    _request_context.run_id = run_id
    try:
        return resolve_with_deadline(name, refresh, deadline)
    finally:
        del _request_context.deadline
        del _request_context.run_id


def resolve_with_deadline(name, refresh, deadline):
    preferred_name = mapped_canonical_name(name)
    name = lookup_name(name)
    key = name.casefold()
    override = actor_override(name, [])
    search_name = override.get("original", "").strip() if override else name
    with _lock:
        cache = load_cache()
        cached = cache.get(key)
        ttl = CACHE_TTL if cached and latin_alias([cached['record']['name'].split(' (', 1)[0]]) else UNRESOLVED_CACHE_TTL
        if cached and cached.get('name_parser_version') == NAME_PARSER_VERSION and not refresh and time.time() - cached["saved_at"] < ttl:
            record = dict(cached["record"])
            if preferred_name and any(source != "Gfriends" for source in record.get("sources", [])):
                record["name"] = preferred_name
            return record

    identity = actor_db_identity(search_name)
    outcomes = {provider: "not returned by search" for provider in SOURCE_ORDER}
    rejected_urls = {}

    search_url = f"{METATUBE_URL}/v1/actors/search?" + urllib.parse.urlencode({
        "q": search_name.strip(), "fallback": "true"
    })
    # Bound even the initial search: socket timeouts are not whole-request
    # deadlines when a peer keeps trickling bytes.
    search_outcome = {}
    searched = collect_sources([(request_json, search_url)], min(deadline, time.monotonic() + SOURCE_TIMEOUT),
                               ["MetaTube search"], search_outcome)
    if search_outcome.get("MetaTube search") != "found":
        outcomes = {provider: "search incomplete" for provider in SOURCE_ORDER}
    results = searched[0].get("data", []) if searched else []
    identities = [search_name.strip()]
    matched = [result for result in results if exact_match(result, identities)]
    placeholder_results = [result for result in matched if result['provider'] == 'Gfriends']
    primary_results = [result for result in matched if result['provider'] != 'Gfriends']
    tasks = [(actor_detail, result) for result in primary_results]
    labels = [result["provider"] for result in primary_results]
    present = {result['provider'] for result in primary_results}
    for provider, lookup in (
        ("XsList", xslist_search_detail),
        ("JavLibrary", javlibrary_detail),
        ("Minnano-AV", minnano_search_detail),
    ):
        if provider in present:
            continue
        argument = (search_name.strip(), identity["western_name"]) if provider == "Minnano-AV" and identity else search_name.strip()
        tasks.append((lookup, argument))
        labels.append(provider)
    # Reserve time for secondary evidence, but do not serialize independent
    # primary sources behind a slow/challenged optional provider.
    details = collect_sources(tasks, min(deadline, time.monotonic() + 40), labels, outcomes, rejected_urls)
    enrichment_names = [search_name.strip()]
    for detail in details:
        enrichment_names.extend([detail.get("name", ""), *detail.get("aliases", [])])
    if identity:
        enrichment_names.append(identity["western_name"])
    secondary = [("JAVDatabase", javdatabase_detail), ("Babepedia", babepedia_detail),
                 ("JAV.LINK", javlink_detail), ("JAVModel", javmodel_detail),
                 ("JavDB", javdb_detail)]
    details.extend(collect_sources([(lookup, identity if provider == "JavDB" else enrichment_identities(enrichment_names))
                                    for provider, lookup in secondary],
                                   deadline, [provider for provider, _ in secondary], outcomes, rejected_urls))
    if details:
        outcomes["Gfriends"] = "placeholder (not needed)"
    elif placeholder_results:
        details = collect_sources([(actor_detail, result) for result in placeholder_results],
                                  deadline, ["Gfriends"] * len(placeholder_results),
                                  outcomes, rejected_urls)
    if not details:
        raise NoActorMatch(name, outcomes, rejected_urls)
    if not identity:
        reject_ambiguous_stage_name(search_name.strip(), details, outcomes, rejected_urls)
    record = merge(search_name.strip(), details, identity)
    record["source_status"] = outcomes
    record["source_priority"] = list(SOURCE_PRIORITY)
    record["rejected_urls"] = rejected_urls
    record["source_search_status"] = search_outcome.get("MetaTube search", "not started")
    if identity and any(source != "Gfriends" for source in record["sources"]):
        record["actor_db_identity"] = identity["actor_id"]
    if preferred_name and any(source != "Gfriends" for source in record["sources"]):
        record["name"] = preferred_name
        if preferred_name.casefold() not in {value.casefold() for value in record["aliases"]}:
            record["aliases"].append(preferred_name)
    with _lock:
        cache = load_cache()
        cache[key] = {"saved_at": time.time(), "record": record, "name_parser_version": NAME_PARSER_VERSION}
        save_cache(cache)
    return record


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        if parsed.path == "/trace/recent":
            if self.client_address[0] not in TRACE_READ_ALLOWED_IPS:
                self.send_json(403, {"error": "not allowed"})
                return
            name = urllib.parse.parse_qs(parsed.query).get("name", [""])[0].strip()
            if len(name) > 100:
                self.send_json(400, {"error": "name must be up to 100 characters"})
                return
            self.send_json(200, {"events": recent_resolve_events(name)})
            return
        if parsed.path != "/resolve":
            self.send_json(404, {"error": "not found"})
            return
        query = urllib.parse.parse_qs(parsed.query)
        name = query.get("name", [""])[0].strip()
        if not name:
            self.send_json(400, {"error": "name is required"})
            return
        started = time.monotonic()
        event = {"request_id": str(uuid.uuid4()), "started_at": datetime.now(timezone.utc).isoformat(),
                 "name": name[:100], "client_ip": self.client_address[0], "status": "started"}
        # Make slow or interrupted lookups visible in the Admin request view.
        append_resolve_event(event)
        try:
            record = resolve(name, query.get("refresh", [""])[0] == "true", event["request_id"])
        except NoActorMatch as error:
            event.update(status="not_found", duration_ms=round((time.monotonic() - started) * 1000),
                         error_type=type(error).__name__, source_status=error.source_status)
            append_resolve_event(event)
            self.send_json(404, {"error": "no actor match", "source_status": error.source_status,
                                 "rejected_urls": error.rejected_urls,
                                 "source_priority": list(SOURCE_PRIORITY)})
            return
        except Exception as error:
            event.update(status="failed", duration_ms=round((time.monotonic() - started) * 1000),
                         error_type=type(error).__name__)
            append_resolve_event(event)
            self.send_json(404, {"error": str(error)})
            return
        event.update(status="resolved", duration_ms=round((time.monotonic() - started) * 1000),
                     formed_name=record.get("name", ""), sources=record.get("sources", []),
                     external_ids=record.get("external_ids", {}))
        append_resolve_event(event)
        try:
            self.send_json(200, {"data": record})
        except (BrokenPipeError, ConnectionResetError):
            # A disconnected client is not a second 404 response.
            return

    def log_message(self, message, *args):
        print(f"{self.client_address[0]} {message % args}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9211), Handler).serve_forever()
