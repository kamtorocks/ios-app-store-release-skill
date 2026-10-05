#!/usr/bin/env python3
"""Fetch Apple developer docs as Markdown and keep this skill's archive fresh.

Stdlib only (runs on macOS /usr/bin/python3). developer.apple.com/documentation
and /design/human-interface-guidelines pages are JavaScript apps: a plain web
fetch returns an empty shell. This script reads their DocC JSON channel
(/tutorials/data/<path>.json) instead, so it returns the real text.

Commands
  fetch URL [-o FILE]          Any page -> Markdown. DocC pages detected automatically.
                               URL may be a full URL or a bare path like
                               documentation/storekit/testing-in-app-purchases-with-sandbox
  sync [ID ...] [--diff]       Re-fetch archived sources (all, or the given ids) into
                               references/official/. Reports new / changed / unchanged / failed.
  status [--max-age DAYS]      Archive age per source; marks STALE past --max-age (default 30).
  guideline REF [REF ...]      Print App Review Guideline text from the archive.
                               REF: 5 | 2.1 | 2.1(a) | 3.1.2(c) | 5.1.1(v) | 4.8
  news [--days N] [--grep RE] [--limit N]
                               Live Apple Developer News (RSS): new requirements, deadlines,
                               guideline updates, SDK minimums.
"""
import argparse
import datetime as dt
import difflib
import email.utils
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SKILL_DIR = Path(__file__).resolve().parent.parent
ARCHIVE = SKILL_DIR / "references" / "official"
SOURCES = ARCHIVE / "sources.json"
MANIFEST = ARCHIVE / "_manifest.json"
GUIDELINES_ID = "review-guidelines"
APPLE = "https://developer.apple.com"
NEWS_RSS = APPLE + "/news/rss/news.rss"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari/605.1.15"


# ---------------------------------------------------------------- HTTP

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError) as e:
        # python.org installs on macOS often lack a CA bundle; curl uses the system store.
        if "CERTIFICATE" not in str(e).upper():
            raise
        out = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout), "-A", UA, url],
                             capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError("curl failed ({}): {}".format(out.returncode, out.stderr.strip()))
        return out.stdout


def docc_json_url(url):
    """Return the DocC JSON URL for a DocC-rendered page, else None."""
    if not re.match(r"^https?://", url):
        url = APPLE + "/" + url.lstrip("/")
    p = urlparse(url)
    if p.netloc != "developer.apple.com":
        return None
    path = p.path.rstrip("/")
    if path.startswith("/tutorials/data/") and path.endswith(".json"):
        return APPLE + path
    if path.startswith("/documentation/") or path.startswith("/design/human-interface-guidelines"):
        return APPLE + "/tutorials/data" + path.lower() + ".json"
    return None


def normalize_url(url):
    return url if re.match(r"^https?://", url) else APPLE + "/" + url.lstrip("/")


# ---------------------------------------------------------------- HTML -> Markdown

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em", "i", "kbd",
          "mark", "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u",
          "var", "br", "wbr", "del", "ins", "font"}
SKIP_TAGS = {"script", "style", "noscript", "svg", "button", "form", "nav", "footer",
             "template", "iframe", "select", "img", "picture", "video", "audio", "canvas",
             "head", "input", "label", "dialog"}
SKIP_CLASS = re.compile(r"(^|[\s-])(globalnav|localnav|ribbon|footer|breadcrumbs?|"
                        r"visuallyhidden|custom-tooltip-icon|sn-container-wrap|feedback|"
                        r"share-sheet|hide)([\s-]|$)")
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
WS = re.compile(r"[ \t\r\n\f\v\xa0​ ]+")


class Node(object):
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, attrs, [], parent


class TreeBuilder(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict((k, v or "") for k, v in attrs), self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, dict((k, v or "") for k, v in attrs), self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def find_first(node, pred):
    stack = [node]
    while stack:
        n = stack.pop(0)
        if isinstance(n, Node):
            if pred(n):
                return n
            stack[0:0] = [c for c in n.children if isinstance(c, Node)]
    return None


def find_all(node, pred):
    out, stack = [], [node]
    while stack:
        n = stack.pop()
        if isinstance(n, Node):
            if pred(n):
                out.append(n)
            stack.extend(c for c in n.children if isinstance(c, Node))
    return out


def skipped(n):
    return (n.tag in SKIP_TAGS or "hidden" in n.attrs
            or SKIP_CLASS.search(n.attrs.get("class", "")) is not None)


def wrap(s, mark):
    m = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S)
    lead, core, trail = m.groups()
    return "{}{}{}{}{}".format(lead, mark, core, mark, trail) if core else s


def has_block(n):
    for c in n.children:
        if isinstance(c, Node) and not skipped(c) and (c.tag not in INLINE or has_block(c)):
            return True
    return False


class HtmlToMd(object):
    def __init__(self, base):
        self.base = base

    def inline(self, n):
        if isinstance(n, str):
            return WS.sub(" ", n)
        if skipped(n):
            return ""
        t = n.tag
        if t == "br":
            return "\n"
        inner = "".join(self.inline(c) for c in n.children)
        if t in ("strong", "b"):
            return wrap(inner, "**")
        if t in ("em", "i"):
            return wrap(inner, "*")
        if t == "code":
            return wrap(inner, "`")
        if t == "a":
            href = n.attrs.get("href", "")
            txt = inner.strip()
            if txt and href and not href.startswith(("#", "javascript:")):
                lead = inner[: len(inner) - len(inner.lstrip())]
                trail = inner[len(inner.rstrip()):]
                return "{}[{}]({}){}".format(lead, txt, urljoin(self.base, href), trail)
        return inner

    @staticmethod
    def clean(s):
        lines = [WS.sub(" ", l).strip() for l in s.split("\n")]
        return "\n".join(l for l in lines if l)

    def children(self, n):
        parts, buf = [], []

        def flush():
            s = self.clean("".join(buf))
            del buf[:]
            if s:
                parts.append(s)

        for c in n.children:
            if isinstance(c, str):
                buf.append(self.inline(c))
            elif skipped(c):
                continue
            elif c.tag in INLINE and not has_block(c):
                buf.append(self.inline(c))
            else:
                flush()
                b = self.block(c)
                if b.strip():
                    parts.append(b)
        flush()
        return "\n\n".join(parts)

    def block(self, n):
        t = n.tag
        if t in HEADINGS:
            txt = self.clean("".join(self.inline(c) for c in n.children)).replace("\n", " ")
            return "#" * HEADINGS[t] + " " + txt if txt else ""
        if t == "p":
            return self.clean("".join(self.inline(c) for c in n.children)) if not has_block(n) else self.children(n)
        if t in ("ul", "ol"):
            return self.list(n, t == "ol")
        if t == "li":
            return self.list_item("- ", self.children(n))
        if t == "table":
            return self.table(n)
        if t == "pre":
            code = "".join(text_content(n)).strip("\n")
            return "```\n" + code + "\n```"
        if t == "blockquote":
            inner = self.children(n)
            return "\n".join(("> " + l) if l else ">" for l in inner.split("\n"))
        if t == "hr":
            return "---"
        if t == "dl":
            out = []
            for c in n.children:
                if isinstance(c, Node) and c.tag == "dt":
                    out.append("**" + self.clean(self.children(c)).replace("\n", " ") + "**")
                elif isinstance(c, Node) and c.tag == "dd":
                    out.append(self.children(c))
            return "\n\n".join(o for o in out if o.strip())
        return self.children(n)

    @staticmethod
    def list_item(marker, body):
        lines = body.split("\n")
        pad = " " * len(marker)
        return "\n".join([marker + lines[0]] + [(pad + l) if l.strip() else "" for l in lines[1:]])

    def list(self, n, ordered):
        items, i = [], 0
        for c in n.children:
            if not isinstance(c, Node) or skipped(c):
                continue
            body = self.children(c) if c.tag == "li" else self.block(c)
            if not body.strip():
                continue
            i += 1
            items.append(self.list_item("{}. ".format(i) if ordered else "- ", body))
        return "\n".join(items)

    def table(self, n):
        rows = []
        stack = [n]
        trs = []
        while stack:
            x = stack.pop(0)
            for c in x.children:
                if isinstance(c, Node):
                    if c.tag == "tr":
                        trs.append(c)
                    elif c.tag != "table":
                        stack.append(c)
        for tr in trs:
            cells = []
            for td in tr.children:
                if isinstance(td, Node) and td.tag in ("td", "th"):
                    txt = self.children(td).replace("\n\n", "<br>").replace("\n", " ")
                    cells.append(txt.replace("|", "\\|"))
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        w = max(len(r) for r in rows)
        rows = [r + [""] * (w - len(r)) for r in rows]
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
        out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(out)


def text_content(n):
    if isinstance(n, str):
        yield n
        return
    for c in n.children:
        for s in text_content(c):
            yield s


def finish(md):
    md = "\n".join(l.rstrip() for l in md.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def html_to_md(html, url):
    tb = TreeBuilder()
    tb.feed(html)
    root = tb.root
    main = find_first(root, lambda n: n.tag == "main") or find_first(root, lambda n: n.tag == "body") or root
    articles = find_all(main, lambda n: n.tag == "article")
    content = articles[0] if len(articles) == 1 else main
    md = finish(HtmlToMd(url).children(content))
    if "page you’re looking for can’t be found" in md or "page you're looking for can't be found" in md:
        raise RuntimeError("Apple returned its not-found page for " + url)
    return md


def html_last_updated(html):
    m = re.search(r"Last Updated:?\s*(?:<[^>]+>\s*)*([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    return m.group(1) if m else None


# ---------------------------------------------------------------- DocC JSON -> Markdown

class DoccToMd(object):
    def __init__(self, data):
        self.d = data
        self.refs = data.get("references", {})

    def ref_url(self, ident):
        u = self.refs.get(ident, {}).get("url", "")
        return APPLE + u if u.startswith("/") else u

    def ref_title(self, ident):
        r = self.refs.get(ident, {})
        return r.get("title") or ident.rstrip("/").rsplit("/", 1)[-1]

    def ref_link(self, ident, title=None):
        u = self.ref_url(ident)
        title = title or self.ref_title(ident)
        return "[{}]({})".format(title, u) if u else title

    def inl(self, items):
        out = []
        for it in items or []:
            t = it.get("type")
            if t == "text":
                out.append(it.get("text", ""))
            elif t == "codeVoice":
                out.append("`{}`".format(it.get("code", "")))
            elif t in ("emphasis", "newTerm"):
                out.append(wrap(self.inl(it.get("inlineContent")), "*"))
            elif t == "strong":
                out.append(wrap(self.inl(it.get("inlineContent")), "**"))
            elif t == "reference":
                title = it.get("overridingTitle")
                if it.get("overridingTitleInlineContent"):
                    title = self.inl(it["overridingTitleInlineContent"])
                if it.get("isActive", True):
                    out.append(self.ref_link(it.get("identifier", ""), title))
                else:
                    out.append(title or self.ref_title(it.get("identifier", "")))
            elif t == "link":
                out.append("[{}]({})".format(it.get("title") or it.get("destination"), it.get("destination")))
            elif t == "image":
                continue
            elif "inlineContent" in it:
                out.append(self.inl(it["inlineContent"]))
            else:
                out.append(it.get("text", ""))
        return "".join(out)

    def blocks(self, bs):
        parts = []
        for b in bs or []:
            s = self.block(b)
            if s and s.strip():
                parts.append(s)
        return "\n\n".join(parts)

    def block(self, b):
        t = b.get("type")
        if t == "heading":
            return "#" * min(6, max(2, b.get("level", 2))) + " " + b.get("text", "")
        if t == "paragraph":
            return self.inl(b.get("inlineContent"))
        if t in ("unorderedList", "orderedList"):
            items = []
            for i, it in enumerate(b.get("items", []), 1):
                marker = "{}. ".format(i) if t == "orderedList" else "- "
                items.append(HtmlToMd.list_item(marker, self.blocks(it.get("content"))))
            return "\n".join(items)
        if t == "aside":
            name = b.get("name") or (b.get("style") or "note").title()
            body = self.blocks(b.get("content"))
            lines = ("**{}:** {}".format(name, body)).split("\n")
            return "\n".join(("> " + l) if l else ">" for l in lines)
        if t == "codeListing":
            return "```{}\n{}\n```".format(b.get("syntax") or "", "\n".join(b.get("code", [])))
        if t == "table":
            rows = [[self.blocks(cell).replace("\n\n", "<br>").replace("\n", " ").replace("|", "\\|")
                     for cell in row] for row in b.get("rows", [])]
            if not rows:
                return ""
            w = max(len(r) for r in rows)
            rows = [r + [""] * (w - len(r)) for r in rows]
            if b.get("header") != "row":
                rows.insert(0, [""] * w)
            out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
            return "\n".join(out + ["| " + " | ".join(r) + " |" for r in rows[1:]])
        if t == "termList":
            out = []
            for it in b.get("items", []):
                term = self.inl(it.get("term", {}).get("inlineContent"))
                out.append(HtmlToMd.list_item("- ", "**{}**: {}".format(term, self.blocks(it.get("definition", {}).get("content")))))
            return "\n".join(out)
        if t == "row":
            return "\n\n".join(self.blocks(col.get("content")) for col in b.get("columns", []))
        if t == "tabNavigator":
            return "\n\n".join("**{}**\n\n{}".format(tab.get("title", ""), self.blocks(tab.get("content")))
                               for tab in b.get("tabs", []))
        if t == "links":
            return "\n".join("- " + self.ref_link(i) for i in b.get("items", []))
        if t in ("small", "dictionaryExample"):
            return self.inl(b.get("inlineContent")) or self.blocks(b.get("content"))
        if "content" in b and isinstance(b["content"], list):
            return self.blocks(b["content"])
        if "inlineContent" in b:
            return self.inl(b["inlineContent"])
        return ""

    def section(self, s):
        kind = s.get("kind")
        if kind == "content":
            return self.blocks(s.get("content"))
        if kind == "declarations":
            decls = []
            for d in s.get("declarations", []):
                decls.append("".join(tok.get("text", "") for tok in d.get("tokens", [])))
            return "```\n" + "\n".join(decls) + "\n```" if decls else ""
        if kind == "details":
            det = s.get("details", {})
            types = ", ".join(v.get("baseType") or v.get("arrayMode") and "array" or "" for v in det.get("value", []))
            return "## Details\n\n- Key: `{}`{}\n- Type: {}".format(
                det.get("rawKey") or det.get("name", ""),
                " (Xcode: {})".format(det["ideTitle"]) if det.get("ideTitle") else "", types or "?")
        if kind in ("properties", "parameters", "attributes", "possibleValues", "restParameters"):
            title = s.get("title") or kind.title()
            out = ["## " + title]
            for it in s.get("items", []) or s.get("values", []) or s.get("parameters", []):
                name = it.get("name", "")
                typ = "".join(x.get("text", "") for x in it.get("type", []) if isinstance(x, dict))
                req = " (required)" if it.get("required") else ""
                head = "- `{}`{}{}".format(name, " — " + typ if typ else "", req)
                body = self.blocks(it.get("content"))
                out.append(HtmlToMd.list_item("- ", head[2:] + ("\n\n" + body if body else "")))
            return "\n".join(out)
        if "content" in s:
            return self.blocks(s["content"])
        return ""

    def topic_list(self, sections, heading):
        out = []
        for sec in sections or []:
            lines = []
            for ident in sec.get("identifiers", []):
                abstract = self.inl(self.refs.get(ident, {}).get("abstract"))
                lines.append("- " + self.ref_link(ident) + (" — " + abstract if abstract else ""))
            if lines:
                out.append(("### " + sec["title"] + "\n\n" if sec.get("title") else "") + "\n".join(lines))
        return ("## " + heading + "\n\n" + "\n\n".join(out)) if out else ""

    def render(self):
        md = self.d.get("metadata", {})
        parts = ["# " + (md.get("title") or "Untitled")]
        meta = [md.get("roleHeading")] if md.get("roleHeading") else []
        plats = ["{} {}+".format(p.get("name"), p.get("introducedAt")) for p in md.get("platforms", [])
                 if p.get("introducedAt") and not p.get("unavailable")]
        if plats:
            meta.append(", ".join(plats))
        if meta:
            parts.append("> " + " · ".join(meta))
        if self.d.get("abstract"):
            parts.append(self.inl(self.d["abstract"]))
        for s in self.d.get("primaryContentSections", []):
            parts.append(self.section(s))
        for s in self.d.get("sections", []):
            if isinstance(s, dict):
                parts.append(self.section(s))
        parts.append(self.topic_list(self.d.get("topicSections"), "Topics"))
        parts.append(self.topic_list(self.d.get("seeAlsoSections"), "See Also"))
        return finish("\n\n".join(p for p in parts if p and p.strip()))


# ---------------------------------------------------------------- fetch

def fetch_md(url):
    """Return (markdown, apple_last_updated_or_None)."""
    url = normalize_url(url)
    j = docc_json_url(url)
    if j:
        data = json.loads(http_get(j))
        return DoccToMd(data).render(), None
    html = http_get(url)
    return html_to_md(html, url), html_last_updated(html)


def split_md(md, level):
    """Split on headings of exactly `level`; returns [(slug, text)]."""
    marker = re.compile(r"^#{%d} (.+)$" % level)
    chunks, cur_title, cur = [], "overview", []
    for line in md.split("\n"):
        m = marker.match(line)
        if m:
            if "".join(cur).strip():
                chunks.append((cur_title, "\n".join(cur)))
            cur_title, cur = m.group(1), [line]
        else:
            cur.append(line)
    if "".join(cur).strip():
        chunks.append((cur_title, "\n".join(cur)))
    out = []
    for i, (title, text) in enumerate(chunks):
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
        out.append(("{:02d}-{}".format(i, slug), finish(text)))
    return out


# ---------------------------------------------------------------- archive

def load_json(p, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def header(src, fetched, last_updated):
    bits = ["source: " + src["url"], "fetched: " + fetched]
    if last_updated:
        bits.append("apple-last-updated: " + last_updated)
    return "<!-- " + " | ".join(bits) + " -->\n"


def strip_header(text):
    return re.sub(r"\A<!--.*?-->\n", "", text, flags=re.S)


def read_existing(src):
    sid = src["id"]
    if src.get("split"):
        d = ARCHIVE / sid
        return {f.stem: strip_header(f.read_text()) for f in sorted(d.glob("*.md"))} if d.is_dir() else {}
    f = ARCHIVE / (sid + ".md")
    return {sid: strip_header(f.read_text())} if f.exists() else {}


def cmd_sync(args):
    sources = load_json(SOURCES, {}).get("sources", [])
    manifest = load_json(MANIFEST, {})
    wanted = set(args.ids)
    unknown = wanted - {s["id"] for s in sources}
    if unknown:
        sys.exit("unknown source id(s): " + ", ".join(sorted(unknown)))
    today = dt.date.today().isoformat()
    counts = {"new": 0, "changed": 0, "unchanged": 0, "failed": 0}
    for src in sources:
        if wanted and src["id"] not in wanted:
            continue
        sid = src["id"]
        try:
            md, last = fetch_md(src["url"])
        except Exception as e:  # report and keep the old copy
            counts["failed"] += 1
            print("FAILED    {:<34} {}".format(sid, e))
            continue
        files = dict(split_md(md, src["split"])) if src.get("split") else {sid: md}
        digest = hashlib.sha256("".join(files[k] for k in sorted(files)).encode()).hexdigest()
        old = read_existing(src)
        prev = manifest.get(sid, {})
        state = "new" if not old else ("unchanged" if prev.get("sha256") == digest else "changed")
        counts[state] += 1
        if state != "unchanged":
            if src.get("split"):
                d = ARCHIVE / sid
                d.mkdir(parents=True, exist_ok=True)
                for f in d.glob("*.md"):
                    f.unlink()
                for name, text in files.items():
                    (d / (name + ".md")).write_text(header(src, today, last) + text)
            else:
                (ARCHIVE / (sid + ".md")).write_text(header(src, today, last) + md)
        manifest[sid] = {"url": src["url"], "fetched": today, "sha256": digest,
                         "apple_last_updated": last or prev.get("apple_last_updated"),
                         "files": sorted(files)}
        note = " (Apple last updated {})".format(last) if last else ""
        print("{:<9} {:<34} {} file(s){}".format(state.upper(), sid, len(files), note))
        if state == "changed" and args.diff:
            a = "\n".join(old[k] for k in sorted(old)).splitlines()
            b = "\n".join(files[k] for k in sorted(files)).splitlines()
            diff = list(difflib.unified_diff(a, b, "archived", "live", n=1, lineterm=""))
            print("\n".join(diff[: args.diff_lines]))
            if len(diff) > args.diff_lines:
                print("... ({} more diff lines)".format(len(diff) - args.diff_lines))
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_index(sources, manifest)
    print("\n" + ", ".join("{} {}".format(v, k) for k, v in counts.items()))


def write_index(sources, manifest):
    rows = []
    for src in sources:
        m = manifest.get(src["id"], {})
        if src.get("split"):
            where = "`{}/` ({} files)".format(src["id"], len(m.get("files", [])))
        else:
            where = "`{}.md`".format(src["id"])
        when = m.get("fetched", "not fetched")
        if m.get("apple_last_updated"):
            when += " (Apple: {})".format(m["apple_last_updated"])
        rows.append("| {} | {} | {} | [live]({}) |".format(where, src.get("topic", ""), when, src["url"]))
    (ARCHIVE / "INDEX.md").write_text(
        "# Archived Apple docs\n\n"
        "Generated by `scripts/apple_docs.py sync`; edit `sources.json`, not this file. "
        "Each archived file starts with its source URL and fetch date. The live page is the authority; "
        "this is a dated cache for grep.\n\n"
        "| file | covers | fetched | source |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")


def cmd_status(args):
    sources = load_json(SOURCES, {}).get("sources", [])
    manifest = load_json(MANIFEST, {})
    today = dt.date.today()
    stale = 0
    for src in sources:
        m = manifest.get(src["id"])
        if not m:
            print("MISSING  {:<34} run: sync {}".format(src["id"], src["id"]))
            stale += 1
            continue
        age = (today - dt.date.fromisoformat(m["fetched"])).days
        flag = "STALE" if age > args.max_age else "ok"
        stale += flag == "STALE"
        extra = "  Apple last updated {}".format(m["apple_last_updated"]) if m.get("apple_last_updated") else ""
        print("{:<8} {:<34} fetched {} ({}d){}".format(flag, src["id"], m["fetched"], age, extra))
    if stale:
        print("\n{} source(s) stale or missing. Refresh: python3 {} sync".format(stale, Path(__file__).name))


# ---------------------------------------------------------------- guideline lookup

LIST_PREFIX = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+")


def indent_of(line):
    m = LIST_PREFIX.match(line)
    return len(m.group(1)) if m else len(line) - len(line.lstrip())


def block_from(lines, i):
    base = indent_of(lines[i])
    out = [lines[i]]
    j = i + 1
    while j < len(lines):
        l = lines[j]
        if l.strip() and (indent_of(l) <= base or l.startswith("#")):
            break
        out.append(l)
        j += 1
    while out and not out[-1].strip():
        out.pop()
    return out, j


def bold_item(lines, label, start=0, stop=None):
    pat = re.compile(r"^\s*(?:(?:[-*]|\d+\.)\s+)?\*\*" + re.escape(label) + r"(?!\.?\d)")
    for i in range(start, stop if stop is not None else len(lines)):
        if pat.match(lines[i]):
            return i
    return -1


def lookup_guideline(lines, ref):
    m = re.fullmatch(r"(\d+(?:\.\d+)*)((?:\([a-z]+\))*)", ref.replace(" ", "").lower())
    if not m:
        return None
    base, subs = m.group(1), re.findall(r"\(([a-z]+)\)", m.group(2))
    base = re.sub(r"^(\d+)\.0$", r"\1", base)  # rejection letters cite section intros as "4.0"
    if "." not in base:
        pat = re.compile(r"^#{1,6} " + re.escape(base) + r"\.\s")
        for i, l in enumerate(lines):
            if pat.match(l):
                j = i + 1
                while j < len(lines) and not re.match(r"^#{1,3} ", lines[j]):
                    j += 1
                return lines[i:j]
        return None
    if subs:
        i = bold_item(lines, "{}({})".format(base, subs[0]))
        if i >= 0:
            return block_from(lines, i)[0]
    i = bold_item(lines, base)
    if i < 0:
        return None
    block, end = block_from(lines, i)
    if subs:
        rel = bold_item(block, "({})".format(subs[0]), 1)
        return block_from(block, rel)[0] if rel >= 0 else None
    # 3.1.2 style: the lettered parts are sibling items "3.1.2(a) ...", not children.
    lvl = indent_of(lines[i])
    while True:
        k = end
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k < len(lines) and indent_of(lines[k]) == lvl and bold_item(lines, base + "(", k, k + 1) == k:
            more, end = block_from(lines, k)
            block += [""] + more
        else:
            return block


def cmd_guideline(args):
    d = ARCHIVE / GUIDELINES_ID
    files = sorted(d.glob("*.md")) if d.is_dir() else []
    if not files:
        sys.exit("guidelines not archived yet: python3 {} sync {}".format(Path(__file__).name, GUIDELINES_ID))
    lines = []
    for f in files:
        lines += strip_header(f.read_text()).split("\n")
    m = load_json(MANIFEST, {}).get(GUIDELINES_ID, {})
    print("App Review Guidelines — archived {}, Apple last updated {}. Live: {}\n".format(
        m.get("fetched", "?"), m.get("apple_last_updated", "?"), APPLE + "/app-store/review/guidelines/"))
    rc = 0
    for ref in args.refs:
        block = lookup_guideline(lines, ref)
        print("=== §{} ===".format(ref))
        if block:
            print("\n".join(block).rstrip() + "\n")
        else:
            rc = 1
            print("not found in archive. Try: grep -rn '{}' {}\n".format(ref, d))
    sys.exit(rc)


# ---------------------------------------------------------------- news

def cmd_news(args):
    root = ET.fromstring(http_get(NEWS_RSS))
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    rx = re.compile(args.grep, re.I) if args.grep else None
    shown = 0
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or ""
        try:
            when = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            when = None
        if when and when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        if when and when < cutoff:
            continue
        text = WS.sub(" ", re.sub(r"<[^>]+>", " ", desc)).strip()
        if rx and not (rx.search(title) or rx.search(text)):
            continue
        print("{}  {}\n  {}\n  {}\n".format(when.date().isoformat() if when else "????-??-??", title, link,
                                            text[:400] + ("…" if len(text) > 400 else "")))
        shown += 1
        if shown >= args.limit:
            break
    if not shown:
        print("no items in the last {} days{}".format(args.days, " matching /{}/".format(args.grep) if rx else ""))


def cmd_fetch(args):
    md, last = fetch_md(args.url)
    if last:
        md = "<!-- apple-last-updated: {} -->\n".format(last) + md
    if args.output:
        Path(args.output).write_text(md)
        print("wrote {} ({} chars)".format(args.output, len(md)))
    else:
        sys.stdout.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("fetch")
    p.add_argument("url")
    p.add_argument("-o", "--output")
    p = sub.add_parser("sync")
    p.add_argument("ids", nargs="*")
    p.add_argument("--diff", action="store_true", help="print a unified diff for changed sources")
    p.add_argument("--diff-lines", type=int, default=200)
    p = sub.add_parser("status")
    p.add_argument("--max-age", type=int, default=30)
    p = sub.add_parser("guideline")
    p.add_argument("refs", nargs="+")
    p = sub.add_parser("news")
    p.add_argument("--days", type=int, default=120)
    p.add_argument("--grep")
    p.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    handlers = {"fetch": cmd_fetch, "sync": cmd_sync, "status": cmd_status,
                "guideline": cmd_guideline, "news": cmd_news}
    if args.cmd not in handlers:
        ap.print_help()
        sys.exit(2)
    try:
        handlers[args.cmd](args)
    except urllib.error.HTTPError as e:
        sys.exit("HTTP {} for {}".format(e.code, e.url))
    except (urllib.error.URLError, RuntimeError, OSError) as e:
        sys.exit("network error: {}".format(e))


if __name__ == "__main__":
    main()
