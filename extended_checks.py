# -*- coding: utf-8 -*-
"""
extended_checks.py — 10-Category GEO Agent-Readiness Audit
90+ individual checks across:
  1. Structured Data & Schema
  2. Semantic HTML
  3. Accessibility for Agents
  4. Internal Linking
  5. Meta & Discoverability
  6. Machine Readability
  7. Entity & Authority
  8. Citability & Answer-Readiness
  9. Performance & Crawlability
  10. Agent Interactivity (WebMCP)
"""

import re
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


# ─── CHECK RESULT HELPER ─────────────────────────────────────────────────────

def check(name, status, detail="", category=""):
    """Create a standardised check result. status: pass|fail|warn|info"""
    return {"name": name, "status": status, "detail": detail, "category": category}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. STRUCTURED DATA & SCHEMA (Enhanced)
# ═══════════════════════════════════════════════════════════════════════════════

def check_structured_data(soup, html):
    cat = "Structured Data & Schema"
    results = []

    # JSON-LD blocks
    jsonld_scripts = soup.find_all("script", type="application/ld+json")
    results.append(check(
        "JSON-LD blocks found",
        "pass" if jsonld_scripts else "fail",
        f"{len(jsonld_scripts)} block(s)" if jsonld_scripts else "No JSON-LD structured data found",
        cat
    ))

    # Parse all schema types
    all_types = []
    all_data = []
    for script in jsonld_scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if "@graph" in item:
                    for g in item["@graph"]:
                        t = g.get("@type", "Unknown")
                        all_types.append(t if isinstance(t, str) else ", ".join(t))
                        all_data.append(g)
                else:
                    t = item.get("@type", "Unknown")
                    all_types.append(t if isinstance(t, str) else ", ".join(t))
                    all_data.append(item)
        except (json.JSONDecodeError, TypeError):
            results.append(check("JSON-LD parse error", "fail", "One or more JSON-LD blocks contain invalid JSON", cat))

    # Schema types
    type_set = set(all_types)
    results.append(check(
        f"Schema types: {', '.join(type_set) if type_set else 'None'}",
        "pass" if type_set else "fail",
        f"{len(type_set)} unique type(s)" if type_set else "No schema types detected",
        cat
    ))

    # Essential types check
    essential = {"Organization", "WebSite", "WebPage", "BreadcrumbList"}
    found_essential = essential & type_set
    missing_essential = essential - type_set
    results.append(check(
        "Essential schema types (Org, WebSite, WebPage, Breadcrumb)",
        "pass" if len(found_essential) >= 3 else "warn" if found_essential else "fail",
        f"Found: {', '.join(found_essential) or 'None'}" + (f" | Missing: {', '.join(missing_essential)}" if missing_essential else ""),
        cat
    ))

    # Product/Offer schema
    product_types = {"Product", "Offer", "AggregateOffer"}
    has_product = bool(product_types & type_set)
    results.append(check(
        "Product/Offer schema",
        "pass" if has_product else "info",
        "Product schema found" if has_product else "No product schema (expected on product pages)",
        cat
    ))

    # Speakable markup
    has_speakable = any("speakable" in json.dumps(d).lower() for d in all_data) if all_data else False
    has_speakable = has_speakable or bool(soup.find(attrs={"itemprop": "speakable"}))
    results.append(check(
        "Speakable markup",
        "pass" if has_speakable else "warn",
        "Speakable property found" if has_speakable else "No Speakable markup — helps voice assistants and AI read key content",
        cat
    ))

    # sameAs references
    same_as_found = any("sameAs" in d for d in all_data) if all_data else False
    results.append(check(
        "sameAs references",
        "pass" if same_as_found else "warn",
        "sameAs links found (social profiles, authority signals)" if same_as_found else "No sameAs — add social/authority links to Organisation schema",
        cat
    ))

    # Microdata
    microdata = soup.find_all(attrs={"itemscope": True})
    results.append(check(
        "Microdata elements",
        "pass" if microdata else "info",
        f"{len(microdata)} itemscope element(s)" if microdata else "No Microdata (JSON-LD preferred)",
        cat
    ))

    # RDFa
    rdfa = soup.find_all(attrs={"typeof": True})
    results.append(check(
        "RDFa markup",
        "info",
        f"{len(rdfa)} RDFa element(s)" if rdfa else "No RDFa detected",
        cat
    ))

    # Nested schema depth
    nested = sum(1 for d in all_data if any(isinstance(v, dict) and "@type" in v for v in d.values() if isinstance(v, dict)))
    results.append(check(
        "Rich nested schema (depth > 1)",
        "pass" if nested else "warn",
        f"{nested} nested schema item(s)" if nested else "Schema is flat — consider nesting Offer inside Product, etc.",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SEMANTIC HTML
# ═══════════════════════════════════════════════════════════════════════════════

def check_semantic_html(soup, html):
    cat = "Semantic HTML"
    results = []

    # Single H1
    h1s = soup.find_all("h1")
    results.append(check(
        "Single H1 tag found",
        "pass" if len(h1s) == 1 else "warn" if h1s else "fail",
        f"{len(h1s)} H1 tag(s)" + (f": \"{h1s[0].get_text(strip=True)[:80]}\"" if len(h1s) == 1 else ""),
        cat
    ))

    # Heading hierarchy
    headings = soup.find_all(re.compile(r'^h[1-6]$'))
    heading_levels = [int(h.name[1]) for h in headings]
    hierarchy_ok = True
    for i in range(1, len(heading_levels)):
        if heading_levels[i] > heading_levels[i-1] + 1:
            hierarchy_ok = False
            break
    results.append(check(
        "Heading hierarchy is logical (no skipped levels)",
        "pass" if hierarchy_ok and headings else "warn" if headings else "fail",
        f"Headings: {' → '.join(f'H{l}' for l in heading_levels[:15])}" if headings else "No headings found",
        cat
    ))

    # Semantic elements
    semantic_tags = {
        "article": soup.find_all("article"),
        "section": soup.find_all("section"),
        "nav": soup.find_all("nav"),
        "aside": soup.find_all("aside"),
        "main": soup.find_all("main"),
        "header": soup.find_all("header"),
        "footer": soup.find_all("footer"),
        "figure": soup.find_all("figure"),
        "figcaption": soup.find_all("figcaption"),
        "time": soup.find_all("time"),
    }
    found_semantic = {k: len(v) for k, v in semantic_tags.items() if v}
    results.append(check(
        "Semantic HTML5 elements used",
        "pass" if len(found_semantic) >= 4 else "warn" if found_semantic else "fail",
        f"Found: {', '.join(f'{k}({v})' for k, v in found_semantic.items())}" if found_semantic else "No semantic elements — use <article>, <nav>, <main>, etc.",
        cat
    ))

    # <main> element
    results.append(check(
        "<main> element present",
        "pass" if semantic_tags["main"] else "warn",
        "Main content area defined" if semantic_tags["main"] else "No <main> — helps AI identify primary content",
        cat
    ))

    # <article> element
    results.append(check(
        "<article> element present",
        "pass" if semantic_tags["article"] else "info",
        f"{len(semantic_tags['article'])} article(s)" if semantic_tags["article"] else "No <article> tags",
        cat
    ))

    # <nav> element
    results.append(check(
        "<nav> element present",
        "pass" if semantic_tags["nav"] else "warn",
        f"{len(semantic_tags['nav'])} nav(s)" if semantic_tags["nav"] else "No <nav> — navigation not semantically marked",
        cat
    ))

    # Content-to-markup ratio
    text_len = len(soup.get_text(separator=" ", strip=True))
    html_len = len(html)
    ratio = (text_len / html_len * 100) if html_len > 0 else 0
    results.append(check(
        f"Content-to-HTML ratio: {ratio:.1f}%",
        "pass" if ratio >= 20 else "warn" if ratio >= 10 else "fail",
        f"{text_len:,} text chars / {html_len:,} HTML chars",
        cat
    ))

    # <time> elements with datetime
    time_tags = soup.find_all("time")
    time_with_dt = [t for t in time_tags if t.get("datetime")]
    results.append(check(
        "<time> elements with datetime attribute",
        "pass" if time_with_dt else "info",
        f"{len(time_with_dt)} time element(s) with datetime" if time_with_dt else "No <time datetime> — helps AI parse dates",
        cat
    ))

    # Lists usage
    lists = soup.find_all(["ul", "ol", "dl"])
    results.append(check(
        "Lists used for structured content",
        "pass" if lists else "info",
        f"{len(lists)} list(s) found" if lists else "No lists found",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ACCESSIBILITY FOR AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

def check_accessibility(soup, html):
    cat = "Accessibility for Agents"
    results = []

    # Language declared
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "") if html_tag else ""
    results.append(check(
        f"Language declared: \"{lang}\"" if lang else "Language declared",
        "pass" if lang else "fail",
        f"html lang=\"{lang}\"" if lang else "No lang attribute on <html> — AI can't determine content language",
        cat
    ))

    # Skip to content link
    skip_link = soup.find("a", href="#content") or soup.find("a", href="#main") or soup.find("a", class_=re.compile(r'skip', re.I))
    results.append(check(
        "Skip to content link",
        "pass" if skip_link else "info",
        "Skip navigation link found" if skip_link else "No skip link (minor for AI agents)",
        cat
    ))

    # All images have alt attributes
    images = soup.find_all("img")
    images_with_alt = [img for img in images if img.get("alt") is not None]
    images_with_good_alt = [img for img in images if img.get("alt", "").strip()]
    results.append(check(
        "All images have alt attributes",
        "pass" if len(images_with_alt) == len(images) and images else "warn" if images_with_alt else "fail" if images else "info",
        f"{len(images_with_alt)}/{len(images)} images have alt" + (f" ({len(images_with_good_alt)} non-empty)" if images else ""),
        cat
    ))

    # Implicit landmarks via semantic HTML
    landmarks = soup.find_all(["header", "nav", "main", "aside", "footer"])
    results.append(check(
        "Implicit landmarks (semantic structure)",
        "pass" if len(landmarks) >= 3 else "warn" if landmarks else "fail",
        f"{len(landmarks)} landmark element(s)",
        cat
    ))

    # ARIA landmarks
    aria_roles = soup.find_all(attrs={"role": True})
    results.append(check(
        "ARIA role attributes",
        "pass" if aria_roles else "info",
        f"{len(aria_roles)} element(s) with ARIA roles" if aria_roles else "No explicit ARIA roles (semantic HTML may suffice)",
        cat
    ))

    # Link text quality
    links = soup.find_all("a", href=True)
    bad_link_texts = []
    for link in links:
        text = link.get_text(strip=True).lower()
        if text in ("click here", "here", "read more", "more", "link", "this", ""):
            bad_link_texts.append(text or "(empty)")
    results.append(check(
        "Link text quality (no empty/generic anchors)",
        "pass" if not bad_link_texts else "warn",
        f"{len(bad_link_texts)} poor link text(s): {', '.join(list(set(bad_link_texts))[:5])}" if bad_link_texts else f"All {len(links)} links have descriptive text",
        cat
    ))

    # Form labels
    inputs = soup.find_all(["input", "select", "textarea"])
    inputs_without_label = []
    for inp in inputs:
        inp_type = inp.get("type", "text")
        if inp_type in ("hidden", "submit", "button", "reset"):
            continue
        inp_id = inp.get("id", "")
        has_label = bool(soup.find("label", attrs={"for": inp_id})) if inp_id else False
        has_aria = bool(inp.get("aria-label") or inp.get("aria-labelledby"))
        has_placeholder = bool(inp.get("placeholder"))
        if not has_label and not has_aria:
            inputs_without_label.append(inp.get("name", inp.get("id", "unnamed")))
    results.append(check(
        "Form inputs have labels/ARIA",
        "pass" if not inputs_without_label else "warn",
        f"{len(inputs_without_label)} input(s) missing labels" if inputs_without_label else f"All form inputs labelled",
        cat
    ))

    # tabindex elements (keyboard-accessible)
    tabindex = soup.find_all(attrs={"tabindex": True})
    results.append(check(
        "Interactive elements are keyboard-accessible",
        "pass" if tabindex or not inputs else "info",
        f"{len(tabindex)} elements with tabindex" if tabindex else "No explicit tabindex",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INTERNAL LINKING
# ═══════════════════════════════════════════════════════════════════════════════

def check_internal_linking(soup, html, base_url):
    cat = "Internal Linking"
    results = []
    parsed_base = urlparse(base_url)

    all_links = soup.find_all("a", href=True)
    internal_links = []
    external_links = []
    anchor_links = []

    for link in all_links:
        href = link.get("href", "")
        if href.startswith("#"):
            anchor_links.append(href)
        elif href.startswith(("http://", "https://")):
            link_parsed = urlparse(href)
            if link_parsed.netloc == parsed_base.netloc:
                internal_links.append(href)
            else:
                external_links.append(href)
        elif href.startswith("/") or not href.startswith(("mailto:", "tel:", "javascript:")):
            internal_links.append(href)

    results.append(check(
        f"Internal links: {len(internal_links)}",
        "pass" if len(internal_links) >= 5 else "warn" if internal_links else "fail",
        f"{len(internal_links)} internal, {len(external_links)} external, {len(anchor_links)} anchor",
        cat
    ))

    # Link density
    text_len = len(soup.get_text(separator=" ", strip=True))
    words = text_len / 5 if text_len > 0 else 1  # rough word count
    link_density = len(all_links) / (words / 100)
    results.append(check(
        f"Link density: {link_density:.1f} links per 100 words",
        "pass" if 2 <= link_density <= 15 else "warn",
        "Good link density" if 2 <= link_density <= 15 else "Too sparse" if link_density < 2 else "Very high link density",
        cat
    ))

    # Navigation structure
    navs = soup.find_all("nav")
    nav_links = sum(len(n.find_all("a")) for n in navs)
    results.append(check(
        f"Navigation structure: {len(navs)} nav(s), {nav_links} links",
        "pass" if navs else "warn",
        f"{len(navs)} <nav> element(s) with {nav_links} links" if navs else "No <nav> elements found",
        cat
    ))

    # Breadcrumbs
    breadcrumbs = (
        soup.find(class_=re.compile(r'breadcrumb', re.I)) or
        soup.find(attrs={"aria-label": re.compile(r'breadcrumb', re.I)}) or
        soup.find(attrs={"itemtype": re.compile(r'BreadcrumbList', re.I)})
    )
    results.append(check(
        "Breadcrumb navigation",
        "pass" if breadcrumbs else "warn",
        "Breadcrumbs found" if breadcrumbs else "No breadcrumbs — helps AI understand page hierarchy",
        cat
    ))

    # Anchor/hash links (for deep linking)
    ids_on_page = len(soup.find_all(id=True))
    results.append(check(
        f"Anchor targets (id attributes): {ids_on_page}",
        "pass" if ids_on_page >= 3 else "info",
        f"{ids_on_page} elements with id (deep-linkable sections)" if ids_on_page else "No id attributes for deep linking",
        cat
    ))

    # Pagination
    pagination = soup.find(class_=re.compile(r'pagination|pager', re.I)) or soup.find("link", rel="next")
    results.append(check(
        "Pagination links",
        "pass" if pagination else "info",
        "Pagination detected" if pagination else "No pagination (may not be needed)",
        cat
    ))

    # Nofollow links
    nofollow_links = [l for l in all_links if "nofollow" in (l.get("rel", []) if isinstance(l.get("rel"), list) else [l.get("rel", "")])]
    results.append(check(
        f"Nofollow links: {len(nofollow_links)}",
        "info",
        f"{len(nofollow_links)} link(s) with rel=nofollow" if nofollow_links else "No nofollow links",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 5. META & DISCOVERABILITY
# ═══════════════════════════════════════════════════════════════════════════════

def check_meta_discoverability(soup, html, url):
    cat = "Meta & Discoverability"
    results = []

    # Title tag
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else ""
    title_len = len(title_text)
    results.append(check(
        f"Title tag ({title_len} chars)",
        "pass" if 30 <= title_len <= 70 else "warn" if title_text else "fail",
        f"\"{title_text[:80]}\"" if title_text else "No title tag — critical for discoverability",
        cat
    ))

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = meta_desc.get("content", "") if meta_desc else ""
    desc_len = len(desc_text)
    results.append(check(
        f"Meta description ({desc_len} chars)",
        "pass" if 100 <= desc_len <= 160 else "warn" if desc_text else "fail",
        f"\"{desc_text[:120]}...\"" if len(desc_text) > 120 else f"\"{desc_text}\"" if desc_text else "No meta description",
        cat
    ))

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    canonical_href = canonical.get("href", "") if canonical else ""
    results.append(check(
        "Canonical URL set",
        "pass" if canonical_href else "warn",
        f"Canonical: {canonical_href[:100]}" if canonical_href else "No canonical URL — risk of duplicate content for AI",
        cat
    ))

    # Open Graph tags
    og_tags = {}
    for og in soup.find_all("meta", attrs={"property": re.compile(r'^og:')}):
        og_tags[og.get("property", "")] = og.get("content", "")
    essential_og = {"og:title", "og:description", "og:image", "og:type", "og:url"}
    found_og = essential_og & set(og_tags.keys())
    results.append(check(
        f"Open Graph tags: {len(og_tags)}",
        "pass" if len(found_og) >= 4 else "warn" if og_tags else "fail",
        f"Found: {', '.join(sorted(og_tags.keys())[:8])}" if og_tags else "No Open Graph tags — poor social/AI sharing",
        cat
    ))

    # Twitter Card tags
    twitter_tags = {}
    for tw in soup.find_all("meta", attrs={"name": re.compile(r'^twitter:')}):
        twitter_tags[tw.get("name", "")] = tw.get("content", "")
    results.append(check(
        f"Twitter Card tags: {len(twitter_tags)}",
        "pass" if twitter_tags else "info",
        f"Found: {', '.join(sorted(twitter_tags.keys())[:5])}" if twitter_tags else "No Twitter Card tags",
        cat
    ))

    # Hreflang
    hreflangs = soup.find_all("link", rel="alternate", hreflang=True)
    results.append(check(
        "Hreflang tags",
        "pass" if hreflangs else "info",
        f"{len(hreflangs)} hreflang tag(s)" if hreflangs else "No hreflang — add if multilingual",
        cat
    ))

    # Favicon
    favicon = soup.find("link", rel=re.compile(r'icon', re.I))
    results.append(check(
        "Favicon linked",
        "pass" if favicon else "info",
        "Favicon found" if favicon else "No favicon link",
        cat
    ))

    # Robots meta
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    robots_content = robots_meta.get("content", "") if robots_meta else ""
    has_noindex = "noindex" in robots_content.lower() if robots_content else False
    results.append(check(
        "Robots meta tag",
        "warn" if has_noindex else "pass" if robots_meta else "info",
        f"content=\"{robots_content}\"" if robots_content else "No robots meta (defaults to index,follow)",
        cat
    ))

    # Pinterest nopin
    nopin = soup.find("meta", attrs={"name": "pinterest"})
    results.append(check(
        "Pinterest meta.txt.yml",
        "info",
        f"Pinterest meta: {nopin.get('content', '')}" if nopin else "No Pinterest-specific meta",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MACHINE READABILITY
# ═══════════════════════════════════════════════════════════════════════════════

def check_machine_readability(soup, html, resp_headers=None):
    cat = "Machine Readability"
    results = []

    # Doctype
    has_doctype = html.strip().lower().startswith("<!doctype")
    results.append(check(
        "Valid DOCTYPE declaration",
        "pass" if has_doctype else "warn",
        "<!DOCTYPE html> found" if has_doctype else "No DOCTYPE",
        cat
    ))

    # Charset
    charset = soup.find("meta", charset=True) or soup.find("meta", attrs={"http-equiv": "Content-Type"})
    results.append(check(
        "Character encoding declared",
        "pass" if charset else "warn",
        f"Charset: {charset.get('charset', charset.get('content', ''))}" if charset else "No charset meta — may cause encoding issues",
        cat
    ))

    # Viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    results.append(check(
        "Viewport meta tag",
        "pass" if viewport else "warn",
        f"Viewport: {viewport.get('content', '')[:60]}" if viewport else "No viewport tag",
        cat
    ))

    # JS framework detection
    frameworks = []
    root = soup.find(id="root") or soup.find(id="__next") or soup.find(id="app")
    if root and len(root.get_text(strip=True)) < 50:
        frameworks.append("React/Next.js (empty root)")
    if soup.find(id="__nuxt"):
        frameworks.append("Vue/Nuxt")
    if soup.find(attrs={"ng-app": True}) or soup.find("app-root"):
        frameworks.append("Angular")

    results.append(check(
        "JS framework analysis",
        "warn" if frameworks else "pass",
        f"Detected: {', '.join(frameworks)} — content may be JS-dependent" if frameworks else "No SPA framework detected — content in raw HTML",
        cat
    ))

    # SSR indicators
    text_len = len(soup.get_text(separator=" ", strip=True))
    html_len = len(html)
    ratio = (text_len / html_len * 100) if html_len > 0 else 0
    results.append(check(
        f"Server-side rendering: text ratio {ratio:.1f}%",
        "pass" if ratio >= 15 else "warn" if ratio >= 5 else "fail",
        "Good text-to-HTML ratio — likely SSR" if ratio >= 15 else "Low text content — may be client-rendered",
        cat
    ))

    # Noscript warnings
    noscript = soup.find_all("noscript")
    noscript_warnings = [ns for ns in noscript if "javascript" in ns.get_text().lower()]
    results.append(check(
        "No JavaScript-required warnings",
        "pass" if not noscript_warnings else "warn",
        f"{len(noscript_warnings)} noscript JS warning(s)" if noscript_warnings else "No JS-required noscript messages",
        cat
    ))

    # Bot-specific blocking meta tags
    bot_metas = {}
    for meta_name in ["googlebot", "google-extended", "bingbot"]:
        tag = soup.find("meta", attrs={"name": meta_name})
        if tag:
            bot_metas[meta_name] = tag.get("content", "")
    results.append(check(
        "Bot-specific meta directives",
        "warn" if any("noindex" in v.lower() for v in bot_metas.values()) else "info",
        f"Found: {', '.join(f'{k}={v}' for k, v in bot_metas.items())}" if bot_metas else "No bot-specific meta tags",
        cat
    ))

    # X-Robots-Tag
    x_robots = resp_headers.get("X-Robots-Tag", "") if resp_headers else ""
    results.append(check(
        "X-Robots-Tag header",
        "warn" if "noindex" in x_robots.lower() else "info" if x_robots else "info",
        f"X-Robots-Tag: {x_robots}" if x_robots else "No X-Robots-Tag header",
        cat
    ))

    # data-nosnippet
    nosnippet = soup.find_all(attrs={"data-nosnippet": True})
    results.append(check(
        f"data-nosnippet elements: {len(nosnippet)}",
        "info",
        f"{len(nosnippet)} element(s) excluded from AI snippets" if nosnippet else "No data-nosnippet attributes",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ENTITY & AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

def check_entity_authority(soup, html, base_url):
    cat = "Entity & Authority"
    results = []

    # Author information
    author_meta = soup.find("meta", attrs={"name": "author"})
    author_schema = any("author" in json.dumps(d).lower() for d in _extract_jsonld(soup))
    author_link = soup.find("a", rel="author") or soup.find(class_=re.compile(r'author', re.I))
    results.append(check(
        "Author information detected",
        "pass" if author_meta or author_schema or author_link else "warn",
        "Author found" + (" (meta)" if author_meta else "") + (" (schema)" if author_schema else "") + (" (link/element)" if author_link else "") if (author_meta or author_schema or author_link) else "No author information — reduces E-E-A-T signals",
        cat
    ))

    # Publication date
    date_meta = soup.find("meta", attrs={"property": "article:published_time"})
    date_time = soup.find("time", attrs={"datetime": True})
    date_schema = any("datePublished" in json.dumps(d) for d in _extract_jsonld(soup))
    results.append(check(
        "Publication date found",
        "pass" if date_meta or date_time or date_schema else "warn",
        "Date found" + (" (meta)" if date_meta else "") + (" (time)" if date_time else "") + (" (schema)" if date_schema else "") if (date_meta or date_time or date_schema) else "No publication date — AI may treat content as undated",
        cat
    ))

    # Modified date
    date_modified = soup.find("meta", attrs={"property": "article:modified_time"})
    modified_schema = any("dateModified" in json.dumps(d) for d in _extract_jsonld(soup))
    results.append(check(
        "Last modified date",
        "pass" if date_modified or modified_schema else "info",
        "Modified date found" if date_modified or modified_schema else "No dateModified — helpful for freshness signals",
        cat
    ))

    # Organization signals
    org_schema = any(d.get("@type") in ("Organization", "Corporation", "LocalBusiness") for d in _extract_jsonld(soup))
    results.append(check(
        "Organization schema",
        "pass" if org_schema else "warn",
        "Organization/Corporation schema found" if org_schema else "No organization schema",
        cat
    ))

    # Legal pages check (linked from this page)
    links = [a.get("href", "").lower() for a in soup.find_all("a", href=True)]
    link_text = [a.get_text(strip=True).lower() for a in soup.find_all("a", href=True)]
    legal_keywords = ["privacy", "terms", "legal", "cookie", "disclaimer", "imprint", "about"]
    found_legal = [kw for kw in legal_keywords if any(kw in l for l in links) or any(kw in t for t in link_text)]
    results.append(check(
        f"Legal/trust pages linked: {len(found_legal)}",
        "pass" if len(found_legal) >= 2 else "warn" if found_legal else "info",
        f"Found links to: {', '.join(found_legal)}" if found_legal else "No legal page links detected",
        cat
    ))

    # Logo linked
    logo = soup.find("img", class_=re.compile(r'logo', re.I)) or soup.find("img", alt=re.compile(r'logo', re.I))
    results.append(check(
        "Logo/brand image found",
        "pass" if logo else "info",
        "Logo image detected" if logo else "No logo detected in HTML",
        cat
    ))

    # Contact information
    contact_links = [a for a in soup.find_all("a", href=True) if a.get("href", "").startswith(("tel:", "mailto:"))]
    results.append(check(
        "Contact information (tel/mailto links)",
        "pass" if contact_links else "info",
        f"{len(contact_links)} contact link(s)" if contact_links else "No tel:/mailto: links",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CITABILITY & ANSWER-READINESS
# ═══════════════════════════════════════════════════════════════════════════════

def check_citability(soup, html):
    cat = "Citability & Answer-Readiness"
    results = []

    # FAQ-style content
    faq_schema = any(d.get("@type") == "FAQPage" for d in _extract_jsonld(soup))
    faq_elements = soup.find_all(class_=re.compile(r'faq|accordion', re.I))
    results.append(check(
        "FAQ/Q&A content detected",
        "pass" if faq_schema or faq_elements else "warn",
        ("FAQPage schema found. " if faq_schema else "") + (f"{len(faq_elements)} FAQ elements" if faq_elements else "No FAQ elements") if (faq_schema or faq_elements) else "No FAQ content — great for AI answer snippets",
        cat
    ))

    # Tables
    tables = soup.find_all("table")
    tables_with_headers = [t for t in tables if t.find("th")]
    results.append(check(
        f"Tables: {len(tables)} ({len(tables_with_headers)} with headers)",
        "pass" if tables_with_headers else "info" if tables else "info",
        f"{len(tables)} table(s), {len(tables_with_headers)} with <th>" if tables else "No tables (good for comparison data)",
        cat
    ))

    # Definition lists
    dl_lists = soup.find_all("dl")
    results.append(check(
        "Definition lists (<dl>)",
        "pass" if dl_lists else "info",
        f"{len(dl_lists)} definition list(s)" if dl_lists else "No <dl> lists (good for key-value data)",
        cat
    ))

    # Lead paragraph (first substantial <p>)
    paragraphs = soup.find_all("p")
    lead_p = None
    for p in paragraphs[:5]:
        text = p.get_text(strip=True)
        if len(text) > 50:
            lead_p = text
            break
    results.append(check(
        "Lead paragraph in first 5 <p> tags",
        "pass" if lead_p else "warn",
        f"Lead: \"{lead_p[:120]}...\"" if lead_p and len(lead_p) > 120 else f"Lead: \"{lead_p}\"" if lead_p else "No substantial lead paragraph — AI uses first paragraph for summaries",
        cat
    ))

    # Ordered/unordered lists
    ols = soup.find_all("ol")
    uls = soup.find_all("ul")
    results.append(check(
        f"Structured lists: {len(ols)} ordered, {len(uls)} unordered",
        "pass" if ols or uls else "info",
        f"{len(ols)} <ol> + {len(uls)} <ul>" if ols or uls else "No lists — helpful for step-by-step and comparison content",
        cat
    ))

    # Deep linkable sections (headings with ids)
    headings = soup.find_all(re.compile(r'^h[1-6]$'))
    headings_with_id = [h for h in headings if h.get("id") or (h.parent and h.parent.get("id"))]
    results.append(check(
        f"Deep-linkable headings: {len(headings_with_id)}/{len(headings)}",
        "pass" if headings_with_id else "warn" if headings else "info",
        f"{len(headings_with_id)} headings have id attributes" if headings_with_id else "No headings with id — limits deep citation",
        cat
    ))

    # Blockquotes (citation content)
    blockquotes = soup.find_all("blockquote")
    results.append(check(
        f"Blockquotes: {len(blockquotes)}",
        "info",
        f"{len(blockquotes)} blockquote(s) — quotable content" if blockquotes else "No blockquotes",
        cat
    ))

    # Code blocks
    code_blocks = soup.find_all("pre") + soup.find_all("code")
    results.append(check(
        f"Code blocks: {len(code_blocks)}",
        "info",
        f"{len(code_blocks)} code element(s)" if code_blocks else "No code blocks",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 9. PERFORMANCE & CRAWLABILITY
# ═══════════════════════════════════════════════════════════════════════════════

def check_performance(soup, html):
    cat = "Performance & Crawlability"
    results = []

    # Image dimensions
    images = soup.find_all("img")
    imgs_with_dimensions = [img for img in images if img.get("width") and img.get("height")]
    results.append(check(
        f"Images with width/height attributes: {len(imgs_with_dimensions)}/{len(images)}",
        "pass" if len(imgs_with_dimensions) == len(images) and images else "warn" if imgs_with_dimensions else "fail" if images else "info",
        f"{len(imgs_with_dimensions)}/{len(images)} images have explicit dimensions" if images else "No images",
        cat
    ))

    # Lazy loading
    lazy_images = [img for img in images if img.get("loading") == "lazy"]
    hero_not_lazy = True
    if images and images[0].get("loading") == "lazy":
        hero_not_lazy = False
    results.append(check(
        f"Lazy loading: {len(lazy_images)}/{len(images)} images",
        "pass" if lazy_images else "info",
        f"{len(lazy_images)} lazy-loaded" + (" (first image is lazy — may delay LCP)" if not hero_not_lazy else ""),
        cat
    ))

    # Render-blocking scripts
    scripts = soup.find_all("script", src=True)
    blocking_scripts = [s for s in scripts if not s.get("defer") and not s.get("async") and not s.get("type") == "module"]
    head_scripts = soup.find("head")
    head_blocking = [s for s in (head_scripts.find_all("script", src=True) if head_scripts else []) if not s.get("defer") and not s.get("async")]
    results.append(check(
        f"Render-blocking scripts in <head>: {len(head_blocking)}",
        "pass" if not head_blocking else "warn",
        f"{len(head_blocking)} blocking script(s) in head" if head_blocking else "No render-blocking scripts in <head>",
        cat
    ))

    # Font-display
    style_tags = soup.find_all("style")
    link_stylesheets = soup.find_all("link", rel="stylesheet")
    font_display_found = bool(re.search(r'font-display\s*:', html))
    results.append(check(
        "font-display CSS property",
        "pass" if font_display_found else "info",
        "font-display detected (controls font loading)" if font_display_found else "No font-display found",
        cat
    ))

    # DOM size (element count)
    all_elements = soup.find_all()
    dom_size = len(all_elements)
    results.append(check(
        f"DOM size: {dom_size:,} elements",
        "pass" if dom_size < 1500 else "warn" if dom_size < 3000 else "fail",
        f"{dom_size:,} elements — " + ("Good" if dom_size < 1500 else "Large DOM" if dom_size < 3000 else "Very large DOM — may slow crawling"),
        cat
    ))

    # Inline styles count
    inline_styles = soup.find_all(style=True)
    results.append(check(
        f"Inline styles: {len(inline_styles)}",
        "pass" if len(inline_styles) < 20 else "warn",
        f"{len(inline_styles)} elements with inline style" if inline_styles else "No inline styles",
        cat
    ))

    # External resources count
    total_external = len(scripts) + len(link_stylesheets)
    results.append(check(
        f"External resources: {total_external}",
        "pass" if total_external < 30 else "warn",
        f"{len(scripts)} scripts + {len(link_stylesheets)} stylesheets",
        cat
    ))

    # iframes
    iframes = soup.find_all("iframe")
    results.append(check(
        f"Iframes: {len(iframes)}",
        "pass" if not iframes else "info",
        f"{len(iframes)} iframe(s) — content inside may not be crawlable" if iframes else "No iframes",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 10. AGENT INTERACTIVITY (WebMCP)
# ═══════════════════════════════════════════════════════════════════════════════

def check_agent_interactivity(soup, html, base_url, fetch_fn=None):
    cat = "Agent Interactivity"
    results = []

    # WebMCP declarative tools (data-tool attributes, mcp-related)
    mcp_elements = soup.find_all(attrs={"data-tool": True})
    mcp_elements += soup.find_all(attrs={"data-mcp": True})
    mcp_elements += soup.find_all(attrs={"data-action": True})
    results.append(check(
        "WebMCP declarative tools detected",
        "pass" if mcp_elements else "info",
        f"{len(mcp_elements)} MCP tool element(s)" if mcp_elements else "No WebMCP declarative attributes (data-tool, data-mcp, data-action)",
        cat
    ))

    # Check for /.well-known/mcp.json
    if fetch_fn:
        mcp_url = urljoin(base_url, "/.well-known/mcp.json")
        try:
            resp, err = fetch_fn(mcp_url, timeout=8)
            if resp and resp.status_code == 200:
                results.append(check("/.well-known/mcp.json found", "pass", "MCP manifest detected", cat))
            else:
                results.append(check("/.well-known/mcp.json", "info", "No MCP manifest file", cat))
        except Exception:
            results.append(check("/.well-known/mcp.json", "info", "Could not check", cat))
    else:
        results.append(check("/.well-known/mcp.json", "info", "Not checked", cat))

    # Imperative API patterns
    api_patterns = re.findall(r'(/api/|/v\d+/|/graphql|/rest/)', html)
    results.append(check(
        "API endpoint patterns in HTML",
        "pass" if api_patterns else "info",
        f"Found patterns: {', '.join(list(set(api_patterns))[:5])}" if api_patterns else "No API endpoint patterns detected",
        cat
    ))

    # JavaScript SDK / agent polyfill patterns
    sdk_patterns = re.findall(r'(mcp-sdk|agent-sdk|webmcp|tool-use|function[_-]calling)', html.lower())
    results.append(check(
        "Agent SDK/polyfill references",
        "pass" if sdk_patterns else "info",
        f"Found: {', '.join(set(sdk_patterns))}" if sdk_patterns else "No agent SDK references detected",
        cat
    ))

    # Forms (agent-actionable)
    forms = soup.find_all("form")
    forms_with_action = [f for f in forms if f.get("action")]
    forms_with_labels = []
    for form in forms:
        inputs = form.find_all(["input", "select", "textarea"])
        labeled = sum(1 for i in inputs if i.get("name") or i.get("aria-label"))
        if labeled == len(inputs) and inputs:
            forms_with_labels.append(form)
    results.append(check(
        f"Forms ready for AI agents: {len(forms_with_labels)}/{len(forms)}",
        "pass" if forms_with_labels else "info" if not forms else "warn",
        f"{len(forms)} form(s), {len(forms_with_labels)} fully labelled" if forms else "No forms detected",
        cat
    ))

    # Search form
    search_form = soup.find("form", attrs={"role": "search"}) or soup.find("input", attrs={"type": "search"})
    results.append(check(
        "Search functionality for agents",
        "pass" if search_form else "info",
        "Search form/input detected" if search_form else "No search input detected",
        cat
    ))

    # OpenAPI / Swagger patterns
    openapi = re.findall(r'(swagger|openapi|api-docs)', html.lower())
    results.append(check(
        "OpenAPI/Swagger references",
        "pass" if openapi else "info",
        f"Found: {', '.join(set(openapi))}" if openapi else "No OpenAPI/Swagger references",
        cat
    ))

    # Product actions (add to cart, buy now)
    action_buttons = soup.find_all("button", string=re.compile(r'add to cart|buy now|subscribe|sign up', re.I))
    action_buttons += soup.find_all("input", attrs={"type": "submit", "value": re.compile(r'add|buy|subscribe', re.I)})
    results.append(check(
        f"Actionable elements (add-to-cart, buy, subscribe): {len(action_buttons)}",
        "info",
        f"{len(action_buttons)} action button(s)" if action_buttons else "No obvious action buttons",
        cat
    ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Extract all JSON-LD data
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_jsonld(soup):
    """Extract all JSON-LD items as flat list of dicts."""
    items = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                items.extend(data)
            elif "@graph" in data:
                items.extend(data["@graph"])
            else:
                items.append(data)
        except (json.JSONDecodeError, TypeError):
            pass
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# CMS DETECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# CMS-specific known defaults for blocking/exposing
CMS_PROFILES = {
    "shopify": {
        "name": "Shopify",
        "url_patterns": ["/collections/", "/products/", "/cart", "/checkouts"],
        "sensitive_defaults_blocked": ["/cart", "/checkouts", "/account"],
        "sensitive_defaults_exposed": ["/collections/", "/products/", "/pages/"],
        "schema_defaults": ["Product", "Organization", "BreadcrumbList", "WebSite"],
        "known_issues": [
            "Shopify themes often render product variants via JS — prices may not be in HTML for non-default variants",
            "Default robots.txt blocks /cart, /checkouts but allows /collections and /products",
            "Theme app extensions can inject JS-only content that crawlers miss",
            "product.metafields are often not exposed in default schema output",
            "Shopify's default JSON-LD often lacks AggregateRating and Review schema",
            "Pagination on collections uses ?page=N which is crawlable but may lack rel=next/prev",
        ],
        "customer_paths": ["/account", "/account/login", "/account/register", "/account/addresses", "/account/orders"],
    },
    "woocommerce": {
        "name": "WooCommerce",
        "url_patterns": ["/product/", "/product-category/", "/shop/", "/my-account/"],
        "sensitive_defaults_blocked": ["/wp-admin", "/wp-login.php"],
        "sensitive_defaults_exposed": ["/wp-json/", "/product/", "/product-category/"],
        "schema_defaults": ["Product", "Organization"],
        "known_issues": [
            "WooCommerce default schema is often incomplete — missing brand, sku, availability fields",
            "wp-json REST API exposes product data by default — may leak pricing/inventory",
            "Plugin conflicts (Yoast, Rank Math, WooCommerce schema) can output duplicate JSON-LD",
            "/my-account/ often indexed unless manually noindexed",
            "Variable products may only show parent price in schema, not variant-specific",
            "Default WooCommerce pagination uses /page/N/ which is generally crawlable",
        ],
        "customer_paths": ["/my-account/", "/my-account/orders/", "/my-account/edit-account/", "/my-account/edit-address/", "/checkout/"],
    },
    "magento": {
        "name": "Magento / Adobe Commerce",
        "url_patterns": ["/catalog/product/", "/catalog/category/", "/customer/", "/catalogsearch/"],
        "sensitive_defaults_blocked": ["/customer/", "/checkout/", "/admin/"],
        "sensitive_defaults_exposed": ["/catalog/product/", "/catalog/category/", "/catalogsearch/"],
        "schema_defaults": ["Product", "Organization", "BreadcrumbList"],
        "known_issues": [
            "Magento's full-page cache (FPC) may serve different content to bots vs users",
            "Varnish CDN can strip/modify headers for bot requests",
            "Default Magento schema often lacks Review and AggregateRating",
            "Layered navigation creates massive URL proliferation — facet URLs often not canonicalised",
            "GraphQL endpoint (/graphql) is exposed by default — may leak product data",
            "Customer account paths need explicit robots.txt blocking",
        ],
        "customer_paths": ["/customer/account/", "/customer/account/login/", "/customer/account/create/", "/checkout/", "/checkout/cart/"],
    },
    "bigcommerce": {
        "name": "BigCommerce",
        "url_patterns": ["/products/", "/categories/", "/cart.php", "/login.php"],
        "sensitive_defaults_blocked": ["/cart.php", "/login.php", "/account.php"],
        "sensitive_defaults_exposed": ["/products/", "/categories/", "/brands/"],
        "schema_defaults": ["Product", "Organization", "BreadcrumbList"],
        "known_issues": [
            "Stencil themes use Handlebars templating — content generally in HTML but custom sections may be JS-dependent",
            "BigCommerce default JSON-LD is relatively complete but may lack AggregateRating",
            "Faceted search URLs (/categories/?filter=) not always canonicalised",
            "Customer account pages at /account.php need verification",
            "Default pagination is crawlable but may lack structured next/prev links",
        ],
        "customer_paths": ["/account.php", "/login.php", "/account.php?action=order_status", "/account.php?action=address_book"],
    },
}


def detect_cms(soup, html, url):
    """Detect CMS platform from HTML signatures."""
    detections = {}

    # Shopify
    shopify_signals = 0
    if "shopify" in html.lower():
        shopify_signals += 2
    if "cdn.shopify.com" in html:
        shopify_signals += 3
    if soup.find("meta", attrs={"name": "shopify-digital-wallet"}):
        shopify_signals += 3
    if soup.find("link", href=re.compile(r'cdn\.shopify\.com')):
        shopify_signals += 2
    if re.search(r'Shopify\.theme', html):
        shopify_signals += 3
    if "/collections/" in url or "/products/" in url:
        shopify_signals += 1
    if soup.find("script", string=re.compile(r'Shopify\.(shop|theme|currency)', re.I)):
        shopify_signals += 2
    detections["shopify"] = shopify_signals

    # WooCommerce
    woo_signals = 0
    if "woocommerce" in html.lower():
        woo_signals += 3
    if soup.find("body", class_=re.compile(r'woocommerce', re.I)):
        woo_signals += 3
    if soup.find("link", href=re.compile(r'wc-blocks|woocommerce')):
        woo_signals += 2
    if "/wp-content/" in html:
        woo_signals += 2
    if "/product/" in url or "/product-category/" in url:
        woo_signals += 1
    if soup.find("meta", attrs={"name": "generator", "content": re.compile(r'WooCommerce', re.I)}):
        woo_signals += 3
    if soup.find("meta", attrs={"name": "generator", "content": re.compile(r'WordPress', re.I)}):
        woo_signals += 1
    detections["woocommerce"] = woo_signals

    # Magento
    magento_signals = 0
    if "magento" in html.lower() or "mage" in html.lower():
        magento_signals += 2
    if soup.find("script", string=re.compile(r'require\.config|Magento_', re.I)):
        magento_signals += 3
    if soup.find("script", src=re.compile(r'mage/|requirejs')):
        magento_signals += 3
    if re.search(r'(catalog/product|catalogsearch|customer/account)', url):
        magento_signals += 1
    if soup.find("body", class_=re.compile(r'catalog-product|catalog-category|cms-', re.I)):
        magento_signals += 3
    if "X-Magento" in str(html[:500]):
        magento_signals += 2
    detections["magento"] = magento_signals

    # BigCommerce
    bc_signals = 0
    if "bigcommerce" in html.lower():
        bc_signals += 3
    if soup.find("script", src=re.compile(r'bigcommerce\.com|stencil')):
        bc_signals += 3
    if soup.find("link", href=re.compile(r'bigcommerce')):
        bc_signals += 2
    if re.search(r'/cart\.php|/login\.php|/account\.php', url):
        bc_signals += 2
    if soup.find("meta", attrs={"name": "platform", "content": re.compile(r'BigCommerce', re.I)}):
        bc_signals += 3
    detections["bigcommerce"] = bc_signals

    # Return best match
    best = max(detections, key=detections.get)
    confidence = detections[best]

    if confidence >= 5:
        return best, "high", confidence
    elif confidence >= 3:
        return best, "medium", confidence
    elif confidence >= 1:
        return best, "low", confidence
    else:
        return None, "none", 0


def detect_page_type(soup, html, url):
    """Detect if page is a Product page, Collection/Category page, or Other."""
    url_lower = url.lower()
    jsonld_items = _extract_jsonld(soup)
    jsonld_types = set()
    for item in jsonld_items:
        t = item.get("@type", "")
        if isinstance(t, list):
            jsonld_types.update(t)
        else:
            jsonld_types.add(t)

    # Product page detection
    product_signals = 0
    if "Product" in jsonld_types or "product" in jsonld_types:
        product_signals += 5
    if re.search(r'/products?/[^/]+', url_lower):
        product_signals += 3
    if re.search(r'/catalog/product/', url_lower):
        product_signals += 3
    if soup.find(attrs={"itemprop": "price"}) or soup.find(attrs={"itemprop": "priceCurrency"}):
        product_signals += 3
    if soup.find(class_=re.compile(r'product-single|product-detail|product-page|pdp', re.I)):
        product_signals += 2
    if soup.find("button", string=re.compile(r'add.to.cart|buy.now', re.I)):
        product_signals += 2
    if soup.find("select", class_=re.compile(r'variant|option|size|color', re.I)):
        product_signals += 1

    # Collection/Category page detection
    collection_signals = 0
    if "ItemList" in jsonld_types or "CollectionPage" in jsonld_types or "ProductCollection" in jsonld_types:
        collection_signals += 5
    if re.search(r'/collections?/[^/]+|/product-category/|/catalog/category/|/categories/', url_lower):
        collection_signals += 3
    if re.search(r'/shop/?$|/shop/\?|/store/?$', url_lower):
        collection_signals += 2
    product_cards = soup.find_all(class_=re.compile(r'product-card|product-item|product-grid|product-list|collection-product', re.I))
    if len(product_cards) >= 3:
        collection_signals += 3
    if soup.find(class_=re.compile(r'collection|category-products|product-listing', re.I)):
        collection_signals += 2
    if soup.find(class_=re.compile(r'pagination|pager', re.I)) and product_cards:
        collection_signals += 1
    if soup.find(class_=re.compile(r'filter|facet|refine', re.I)):
        collection_signals += 1

    if product_signals >= 5:
        return "product", product_signals
    elif collection_signals >= 4:
        return "collection", collection_signals
    elif product_signals >= 3:
        return "product", product_signals
    elif collection_signals >= 2:
        return "collection", collection_signals
    else:
        return "other", 0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. E-COMMERCE: PRODUCT PAGE CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def check_product_page(soup, html, url, cms_id=None):
    cat = "E-Commerce: Product Page"
    results = []
    jsonld_items = _extract_jsonld(soup)
    product_schema = [d for d in jsonld_items if d.get("@type") in ("Product", ["Product"])]

    # ── PRICE & VARIANT VISIBILITY ────────────────────────────────────────

    # Price in raw HTML
    text = soup.get_text()
    prices_in_html = re.findall(r'[\$£€A-Z]{0,3}\s?\d+[\.,]\d{2}', text)
    price_elements = soup.find_all(class_=re.compile(r'price|cost|amount', re.I))
    price_itemprop = soup.find_all(attrs={"itemprop": "price"})
    results.append(check(
        "Product price visible in HTML",
        "pass" if prices_in_html or price_elements or price_itemprop else "fail",
        f"{len(prices_in_html)} price pattern(s), {len(price_elements)} price class(es), {len(price_itemprop)} itemprop(s)" if (prices_in_html or price_elements or price_itemprop) else "No price visible in raw HTML — AI agents cannot extract pricing",
        cat
    ))

    # Price in schema
    offer_data = [d for d in jsonld_items if d.get("@type") in ("Offer", "AggregateOffer")]
    schema_price = any("price" in d for d in offer_data)
    if not offer_data:
        for pd in product_schema:
            offers = pd.get("offers", {})
            if isinstance(offers, dict):
                offer_data = [offers]
            elif isinstance(offers, list):
                offer_data = offers
            schema_price = any("price" in d for d in offer_data)
    results.append(check(
        "Price in Product/Offer schema",
        "pass" if schema_price else "fail",
        "Price found in Offer schema" if schema_price else "No price in schema — AI may not extract correct pricing",
        cat
    ))

    # Currency in schema
    has_currency = any("priceCurrency" in d for d in offer_data)
    results.append(check(
        "Price currency (priceCurrency) in schema",
        "pass" if has_currency else "warn",
        "priceCurrency found" if has_currency else "No priceCurrency — AI may guess wrong currency",
        cat
    ))

    # Availability in schema
    has_availability = any("availability" in d for d in offer_data)
    results.append(check(
        "Stock availability in schema",
        "pass" if has_availability else "warn",
        "Availability found" if has_availability else "No availability status — AI can't tell if product is in stock",
        cat
    ))

    # Variant selector in HTML
    variant_selects = soup.find_all("select", class_=re.compile(r'variant|option|size|color|selector', re.I))
    variant_inputs = soup.find_all("input", attrs={"name": re.compile(r'variant|option|size|color', re.I)})
    variant_swatches = soup.find_all(class_=re.compile(r'swatch|variant-option|color-option', re.I))
    variant_elements = variant_selects + variant_inputs + variant_swatches
    results.append(check(
        "Product variants visible in HTML",
        "pass" if variant_elements else "info",
        f"{len(variant_elements)} variant element(s) in HTML" if variant_elements else "No variant selectors found (single-product or JS-rendered variants)",
        cat
    ))

    # Variant prices in HTML (not just default)
    if variant_elements:
        variant_data_attrs = soup.find_all(attrs={"data-price": True})
        variant_json = re.findall(r'"variants?"?\s*:\s*\[', html)
        results.append(check(
            "Variant-specific prices accessible",
            "pass" if variant_data_attrs or variant_json else "warn",
            f"{len(variant_data_attrs)} data-price attrs, variant JSON: {'found' if variant_json else 'not found'}" if (variant_data_attrs or variant_json) else "Variant prices may only be accessible via JS",
            cat
        ))

    # ── PRODUCT IMAGES & ALT TEXT ─────────────────────────────────────────

    images = soup.find_all("img")
    product_images = soup.find_all("img", class_=re.compile(r'product|gallery|featured|hero', re.I))
    if not product_images:
        # Try within product container
        product_container = soup.find(class_=re.compile(r'product-single|product-detail|product-media|product-image', re.I))
        if product_container:
            product_images = product_container.find_all("img")

    results.append(check(
        f"Product images found: {len(product_images)}",
        "pass" if product_images else "warn",
        f"{len(product_images)} product image(s)" if product_images else "No product images detected in HTML",
        cat
    ))

    # Alt text on product images
    if product_images:
        imgs_with_alt = [img for img in product_images if img.get("alt", "").strip()]
        imgs_no_alt = [img for img in product_images if not img.get("alt", "").strip()]
        results.append(check(
            f"Product images with alt text: {len(imgs_with_alt)}/{len(product_images)}",
            "pass" if len(imgs_with_alt) == len(product_images) else "warn",
            f"{len(imgs_no_alt)} product image(s) missing alt text" if imgs_no_alt else "All product images have descriptive alt text",
            cat
        ))

        # Alt text quality (not generic like "product image")
        generic_alts = [img for img in imgs_with_alt if img.get("alt", "").strip().lower() in ("product image", "image", "photo", "picture", "product", "thumbnail")]
        results.append(check(
            "Product image alt text is descriptive",
            "pass" if not generic_alts else "warn",
            f"{len(generic_alts)} image(s) with generic alt text" if generic_alts else "Alt text appears descriptive",
            cat
        ))

    # Image in schema
    schema_image = any("image" in d for d in product_schema)
    results.append(check(
        "Product image in schema",
        "pass" if schema_image else "warn",
        "Image property found in Product schema" if schema_image else "No image in Product schema",
        cat
    ))

    # ── REVIEWS & RATINGS SCHEMA ──────────────────────────────────────────

    has_aggregate_rating = any(d.get("@type") == "AggregateRating" for d in jsonld_items)
    has_review_schema = any(d.get("@type") == "Review" for d in jsonld_items)
    product_has_rating = any("aggregateRating" in d for d in product_schema)
    product_has_reviews = any("review" in d for d in product_schema)

    results.append(check(
        "AggregateRating schema",
        "pass" if has_aggregate_rating or product_has_rating else "warn",
        "AggregateRating found" if has_aggregate_rating or product_has_rating else "No AggregateRating — AI can't surface star ratings",
        cat
    ))

    results.append(check(
        "Review schema",
        "pass" if has_review_schema or product_has_reviews else "warn",
        "Review schema found" if has_review_schema or product_has_reviews else "No Review schema — customer reviews not structured for AI",
        cat
    ))

    # Rating value completeness
    if has_aggregate_rating or product_has_rating:
        for d in jsonld_items:
            if d.get("@type") == "AggregateRating":
                has_value = "ratingValue" in d
                has_count = "reviewCount" in d or "ratingCount" in d
                results.append(check(
                    "AggregateRating fields complete",
                    "pass" if has_value and has_count else "warn",
                    ("ratingValue: " + ("✓" if has_value else "✗") + " | reviewCount: " + ("✓" if has_count else "✗")),
                    cat
                ))
                break

    # Reviews visible in HTML (not just schema)
    review_elements = soup.find_all(class_=re.compile(r'review|testimonial|customer-feedback', re.I))
    results.append(check(
        f"Reviews visible in HTML: {len(review_elements)} element(s)",
        "pass" if review_elements else "info",
        f"{len(review_elements)} review element(s) in HTML" if review_elements else "No review content in raw HTML — may be JS-loaded",
        cat
    ))

    # ── ADD TO CART / PURCHASE SIGNALS ────────────────────────────────────

    atc_buttons = soup.find_all("button", string=re.compile(r'add.to.cart|add.to.bag|buy.now', re.I))
    atc_inputs = soup.find_all("input", attrs={"value": re.compile(r'add.to.cart|add.to.bag|buy', re.I)})
    atc_forms = soup.find_all("form", attrs={"action": re.compile(r'cart|basket|checkout', re.I)})
    atc_total = len(atc_buttons) + len(atc_inputs) + len(atc_forms)

    results.append(check(
        "Add-to-cart functionality exposed",
        "pass" if atc_total else "warn",
        f"{atc_total} add-to-cart element(s) in HTML" if atc_total else "No add-to-cart in raw HTML — action engines can't identify purchase path",
        cat
    ))

    # ── PRODUCT-SPECIFIC SCHEMA COMPLETENESS ──────────────────────────────

    if product_schema:
        pd = product_schema[0]
        key_fields = {"name": pd.get("name"), "description": pd.get("description"), "image": pd.get("image"), "sku": pd.get("sku"), "brand": pd.get("brand"), "offers": pd.get("offers")}
        present = {k: v for k, v in key_fields.items() if v}
        missing = {k for k, v in key_fields.items() if not v}
        results.append(check(
            f"Product schema completeness: {len(present)}/{len(key_fields)}",
            "pass" if len(missing) <= 1 else "warn" if len(missing) <= 3 else "fail",
            f"Present: {', '.join(present.keys())} | Missing: {', '.join(missing) or 'None'}",
            cat
        ))

    # ── CMS-SPECIFIC PRODUCT CHECKS ──────────────────────────────────────

    if cms_id and cms_id in CMS_PROFILES:
        profile = CMS_PROFILES[cms_id]
        for issue in profile["known_issues"][:3]:
            if "product" in issue.lower() or "variant" in issue.lower() or "schema" in issue.lower() or "price" in issue.lower():
                results.append(check(
                    f"{profile['name']} known issue",
                    "info",
                    issue,
                    cat
                ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 12. E-COMMERCE: COLLECTION / CATEGORY PAGE CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def check_collection_page(soup, html, url, cms_id=None):
    cat = "E-Commerce: Collection Page"
    results = []
    jsonld_items = _extract_jsonld(soup)

    # ── PRODUCT CARDS VISIBLE WITHOUT JS (Priority 1) ─────────────────────

    # Detect product cards/items in raw HTML
    product_cards = soup.find_all(class_=re.compile(r'product-card|product-item|product-grid-item|product-tile|grid-item|collection-product|product-block', re.I))
    product_links = soup.find_all("a", href=re.compile(r'/products?/[^/]+|/product/[^/]+', re.I))
    product_list_items = soup.find_all(attrs={"itemtype": re.compile(r'schema\.org/Product', re.I)})

    total_product_signals = len(product_cards) + len(set(a.get("href", "") for a in product_links))

    results.append(check(
        f"Product cards visible in HTML: {len(product_cards)}",
        "pass" if product_cards else "fail",
        f"{len(product_cards)} product card(s) found in raw HTML" if product_cards else "No product cards in raw HTML — AI crawlers see an empty collection",
        cat
    ))

    # Prices visible on product cards
    if product_cards:
        cards_with_prices = 0
        for card in product_cards[:20]:
            card_text = card.get_text()
            if re.search(r'[\$£€]\s?\d+[\.,]?\d*', card_text):
                cards_with_prices += 1
        results.append(check(
            f"Product card prices in HTML: {cards_with_prices}/{min(len(product_cards), 20)}",
            "pass" if cards_with_prices >= len(product_cards) * 0.5 else "warn" if cards_with_prices else "fail",
            f"{cards_with_prices} card(s) show prices in raw HTML" if cards_with_prices else "No prices visible on product cards — likely JS-rendered",
            cat
        ))

    # Product names/titles on cards
    if product_cards:
        cards_with_names = 0
        for card in product_cards[:20]:
            h_tags = card.find_all(re.compile(r'^h[2-6]$'))
            named_links = card.find_all("a", string=True)
            title_class = card.find(class_=re.compile(r'title|name|heading', re.I))
            if h_tags or named_links or title_class:
                cards_with_names += 1
        results.append(check(
            f"Product names on cards: {cards_with_names}/{min(len(product_cards), 20)}",
            "pass" if cards_with_names >= len(product_cards) * 0.5 else "warn",
            f"{cards_with_names} card(s) have product names in HTML",
            cat
        ))

    # Product images on cards
    if product_cards:
        cards_with_images = sum(1 for card in product_cards[:20] if card.find("img"))
        cards_images_with_alt = sum(1 for card in product_cards[:20] if card.find("img") and card.find("img").get("alt", "").strip())
        results.append(check(
            f"Product images on cards: {cards_with_images}/{min(len(product_cards), 20)}",
            "pass" if cards_with_images else "warn",
            f"{cards_with_images} cards with images ({cards_images_with_alt} have alt text)",
            cat
        ))

    # Product links crawlable
    unique_product_links = set(a.get("href", "") for a in product_links if a.get("href"))
    results.append(check(
        f"Product links crawlable: {len(unique_product_links)}",
        "pass" if unique_product_links else "fail",
        f"{len(unique_product_links)} unique product link(s) in HTML" if unique_product_links else "No product links — AI can't navigate to individual products",
        cat
    ))

    # ── FILTER / FACET URLs CRAWLABLE (Priority 2) ────────────────────────

    filter_elements = soup.find_all(class_=re.compile(r'filter|facet|refine|sidebar-filter', re.I))
    filter_links = []
    for el in filter_elements:
        filter_links.extend(el.find_all("a", href=True))

    filter_forms = soup.find_all("form", class_=re.compile(r'filter|facet|refine', re.I))
    filter_selects = soup.find_all("select", class_=re.compile(r'filter|sort|refine', re.I))

    results.append(check(
        f"Filter/facet elements: {len(filter_elements)}",
        "pass" if filter_elements else "info",
        f"{len(filter_elements)} filter container(s), {len(filter_links)} filter link(s)" if filter_elements else "No filter/facet UI detected",
        cat
    ))

    if filter_links:
        # Check if filter links are actual URLs (crawlable) vs JS-only
        crawlable_filters = [a for a in filter_links if a.get("href", "").startswith(("/", "http")) and a.get("href") != "#"]
        js_filters = [a for a in filter_links if a.get("href", "") in ("#", "javascript:void(0)", "")]
        results.append(check(
            f"Filter links crawlable: {len(crawlable_filters)}/{len(filter_links)}",
            "pass" if crawlable_filters and not js_filters else "warn" if crawlable_filters else "fail",
            f"{len(crawlable_filters)} crawlable, {len(js_filters)} JS-only" if filter_links else "",
            cat
        ))

    # Sort options
    sort_elements = soup.find_all(class_=re.compile(r'sort-by|sort-option|sorting', re.I))
    sort_selects = soup.find_all("select", id=re.compile(r'sort', re.I))
    results.append(check(
        "Sort options available",
        "pass" if sort_elements or sort_selects else "info",
        f"{len(sort_elements) + len(sort_selects)} sort element(s)" if sort_elements or sort_selects else "No sort options detected",
        cat
    ))

    # ── PAGINATION / LOAD-MORE (Priority 3) ───────────────────────────────

    pagination = soup.find(class_=re.compile(r'pagination|pager|page-nav', re.I))
    next_link = soup.find("a", string=re.compile(r'^(next|›|»|→)', re.I)) or soup.find("a", rel="next")
    prev_link = soup.find("a", string=re.compile(r'^(prev|‹|«|←)', re.I)) or soup.find("a", rel="prev")
    link_next = soup.find("link", rel="next")
    link_prev = soup.find("link", rel="prev")
    load_more = soup.find("button", string=re.compile(r'load.more|show.more|view.more', re.I))
    infinite_scroll = bool(re.search(r'infinite.scroll|infiniteScroll|data-infinite', html, re.I))

    results.append(check(
        "Pagination present",
        "pass" if pagination or next_link else "warn" if load_more else "fail" if total_product_signals >= 10 else "info",
        ("Pagination found" if pagination else "") +
        (" | Next link: ✓" if next_link else "") +
        (" | Load-more button: ✓" if load_more else "") +
        (" | Infinite scroll detected" if infinite_scroll else "") or
        "No pagination — products may be truncated for AI",
        cat
    ))

    if pagination:
        page_links = pagination.find_all("a", href=True)
        crawlable_pages = [a for a in page_links if a.get("href", "").startswith(("/", "http", "?"))]
        results.append(check(
            f"Pagination links crawlable: {len(crawlable_pages)}",
            "pass" if crawlable_pages else "warn",
            f"{len(crawlable_pages)} crawlable page link(s)" if crawlable_pages else "Pagination may be JS-driven",
            cat
        ))

    # rel=next/prev in <head>
    results.append(check(
        "rel=next/prev in <head>",
        "pass" if link_next or link_prev else "warn",
        f"{'rel=next ✓' if link_next else 'rel=next ✗'} | {'rel=prev ✓' if link_prev else 'rel=prev ✗'}",
        cat
    ))

    # Infinite scroll warning
    if infinite_scroll and not pagination:
        results.append(check(
            "Infinite scroll without pagination fallback",
            "fail",
            "Infinite scroll detected with no HTML pagination — AI crawlers cannot access beyond first page",
            cat
        ))

    # ── COLLECTION SCHEMA (Priority 4) ────────────────────────────────────

    has_itemlist = any(d.get("@type") in ("ItemList", "CollectionPage", "ProductCollection") for d in jsonld_items)
    results.append(check(
        "Collection/ItemList schema",
        "pass" if has_itemlist else "warn",
        "ItemList/CollectionPage schema found" if has_itemlist else "No ItemList schema — AI can't understand this as a product collection",
        cat
    ))

    if has_itemlist:
        itemlist = next((d for d in jsonld_items if d.get("@type") in ("ItemList", "CollectionPage", "ProductCollection")), {})
        has_elements = "itemListElement" in itemlist
        has_count = "numberOfItems" in itemlist
        results.append(check(
            "ItemList content completeness",
            "pass" if has_elements else "warn",
            f"itemListElement: {'✓' if has_elements else '✗'} | numberOfItems: {'✓' if has_count else '✗'}",
            cat
        ))

    # BreadcrumbList for collection hierarchy
    has_breadcrumb = any(d.get("@type") == "BreadcrumbList" for d in jsonld_items)
    results.append(check(
        "BreadcrumbList schema for collection hierarchy",
        "pass" if has_breadcrumb else "warn",
        "BreadcrumbList found — AI can trace category hierarchy" if has_breadcrumb else "No BreadcrumbList — add for collection hierarchy",
        cat
    ))

    # Collection title/description
    h1 = soup.find("h1")
    collection_desc = soup.find(class_=re.compile(r'collection-desc|category-desc|collection-text', re.I))
    meta_desc = soup.find("meta", attrs={"name": "description"})
    results.append(check(
        "Collection title (H1) present",
        "pass" if h1 else "warn",
        f"H1: \"{h1.get_text(strip=True)[:80]}\"" if h1 else "No H1 — AI can't identify collection name",
        cat
    ))
    results.append(check(
        "Collection description present",
        "pass" if collection_desc else "info",
        "Collection description element found" if collection_desc else "No collection description element (meta description may suffice)",
        cat
    ))

    # ── CMS-SPECIFIC COLLECTION CHECKS ────────────────────────────────────

    if cms_id and cms_id in CMS_PROFILES:
        profile = CMS_PROFILES[cms_id]
        for issue in profile["known_issues"]:
            if any(kw in issue.lower() for kw in ["collection", "category", "pagination", "facet", "filter", "layered"]):
                results.append(check(
                    f"{profile['name']} known issue",
                    "info",
                    issue,
                    cat
                ))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 13. CMS PLATFORM & CUSTOMER DATA PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

def check_cms_and_customer_data(soup, html, url, cms_id=None, cms_confidence="none", robots_txt="", fetch_fn=None):
    cat = "CMS & Customer Data Protection"
    results = []

    # ── CMS DETECTION ─────────────────────────────────────────────────────

    if cms_id and cms_id in CMS_PROFILES:
        profile = CMS_PROFILES[cms_id]
        results.append(check(
            f"CMS Detected: {profile['name']}",
            "pass",
            f"Confidence: {cms_confidence} — platform-specific checks enabled",
            cat
        ))
    else:
        results.append(check(
            "CMS Detection",
            "info",
            "No specific CMS detected — generic checks applied",
            cat
        ))
        # Apply generic checks and return
        results.extend(_generic_customer_data_checks(soup, html, robots_txt))
        return results

    # ── CMS DEFAULT BLOCKS ────────────────────────────────────────────────

    robots_lower = robots_txt.lower()
    profile = CMS_PROFILES[cms_id]

    # Check that sensitive defaults ARE blocked
    for path in profile["sensitive_defaults_blocked"]:
        is_blocked = f"disallow: {path}".lower() in robots_lower or f"disallow: {path}/".lower() in robots_lower
        results.append(check(
            f"Default block: {path}",
            "pass" if is_blocked else "warn",
            f"{path} {'is blocked' if is_blocked else 'is NOT blocked'} in robots.txt" + (f" — should be blocked for {profile['name']}" if not is_blocked else ""),
            cat
        ))

    # Check that public defaults are accessible
    for path in profile["sensitive_defaults_exposed"][:3]:
        is_blocked = f"disallow: {path}".lower() in robots_lower
        results.append(check(
            f"Public path: {path}",
            "pass" if not is_blocked else "warn",
            f"{path} {'is accessible' if not is_blocked else 'is BLOCKED — may hide key content'} in robots.txt",
            cat
        ))

    # ── CUSTOMER DATA PROTECTION ──────────────────────────────────────────

    results.append(check(
        f"--- Customer Data Protection ({profile['name']}) ---",
        "info",
        "Checking customer account paths are protected from AI crawlers",
        cat
    ))

    for path in profile["customer_paths"]:
        # Check robots.txt
        path_blocked_robots = any(
            f"disallow: {path}".lower() in robots_lower or
            f"disallow: {path}/".lower() in robots_lower
            for _ in [1]
        )

        # Check if path has noindex in the HTML meta (if we could fetch it)
        results.append(check(
            f"Customer path protected: {path}",
            "pass" if path_blocked_robots else "warn",
            f"{'Blocked in robots.txt' if path_blocked_robots else 'NOT blocked in robots.txt — customer data may be exposed to AI crawlers'}",
            cat
        ))

    # ── CMS DEFAULT SCHEMA QUALITY ────────────────────────────────────────

    jsonld_items = _extract_jsonld(soup)
    jsonld_types = set()
    for item in jsonld_items:
        t = item.get("@type", "")
        if isinstance(t, list):
            jsonld_types.update(t)
        else:
            jsonld_types.add(t)

    expected_schema = set(profile["schema_defaults"])
    found_schema = expected_schema & jsonld_types
    missing_schema = expected_schema - jsonld_types
    results.append(check(
        f"{profile['name']} expected schema: {len(found_schema)}/{len(expected_schema)}",
        "pass" if not missing_schema else "warn",
        f"Found: {', '.join(found_schema) or 'None'}" + (f" | Missing: {', '.join(missing_schema)}" if missing_schema else ""),
        cat
    ))

    # ── CMS KNOWN ISSUES ──────────────────────────────────────────────────

    for issue in profile["known_issues"]:
        results.append(check(
            f"{profile['name']} advisory",
            "info",
            issue,
            cat
        ))

    # ── CMS-SPECIFIC ADDITIONAL CHECKS ────────────────────────────────────

    if cms_id == "shopify":
        results.extend(_shopify_specific(soup, html, robots_lower))
    elif cms_id == "woocommerce":
        results.extend(_woocommerce_specific(soup, html, robots_lower))
    elif cms_id == "magento":
        results.extend(_magento_specific(soup, html, robots_lower))
    elif cms_id == "bigcommerce":
        results.extend(_bigcommerce_specific(soup, html, robots_lower))

    return results


def _generic_customer_data_checks(soup, html, robots_txt):
    """Generic customer data checks when no CMS is detected."""
    cat = "CMS & Customer Data Protection"
    results = []
    robots_lower = robots_txt.lower()

    generic_customer_paths = ["/account", "/login", "/register", "/checkout", "/cart", "/my-account", "/customer", "/user/", "/profile"]
    for path in generic_customer_paths:
        is_blocked = f"disallow: {path}" in robots_lower
        results.append(check(
            f"Customer path: {path}",
            "pass" if is_blocked else "info",
            f"{'Blocked' if is_blocked else 'Not explicitly blocked'} in robots.txt",
            cat
        ))

    # Check for login forms in HTML
    login_forms = soup.find_all("form", attrs={"action": re.compile(r'login|signin|auth', re.I)})
    password_fields = soup.find_all("input", attrs={"type": "password"})
    results.append(check(
        "Login form on page",
        "info" if login_forms or password_fields else "pass",
        f"{len(login_forms)} login form(s), {len(password_fields)} password field(s)" if (login_forms or password_fields) else "No login forms on this page",
        cat
    ))

    return results


def _shopify_specific(soup, html, robots_lower):
    """Shopify-specific additional checks."""
    cat = "CMS & Customer Data Protection"
    results = []

    # Shopify CDN assets accessible
    cdn_refs = re.findall(r'cdn\.shopify\.com', html)
    results.append(check(
        f"Shopify CDN references: {len(cdn_refs)}",
        "pass" if cdn_refs else "info",
        f"{len(cdn_refs)} CDN references — assets should be crawlable",
        cat
    ))

    # Shopify metafields exposure
    metafields = re.findall(r'metafield|metafields', html, re.I)
    results.append(check(
        "Product metafields in HTML",
        "pass" if metafields else "info",
        f"{len(metafields)} metafield reference(s)" if metafields else "No metafields in HTML — extended product data not exposed",
        cat
    ))

    # Theme app extensions
    app_blocks = soup.find_all(class_=re.compile(r'shopify-app-block|app-block', re.I))
    results.append(check(
        f"Shopify app blocks: {len(app_blocks)}",
        "info" if app_blocks else "pass",
        f"{len(app_blocks)} app block(s) — content may be JS-injected" if app_blocks else "No app blocks detected",
        cat
    ))

    # Shopify preview/design mode paths
    preview_blocked = "disallow: /checkouts" in robots_lower
    results.append(check(
        "Shopify /checkouts blocked",
        "pass" if preview_blocked else "warn",
        "/checkouts is blocked" if preview_blocked else "/checkouts not blocked in robots.txt",
        cat
    ))

    return results


def _woocommerce_specific(soup, html, robots_lower):
    """WooCommerce-specific additional checks."""
    cat = "CMS & Customer Data Protection"
    results = []

    # wp-json REST API exposure
    wpjson_blocked = "disallow: /wp-json" in robots_lower
    results.append(check(
        "WordPress REST API (/wp-json) exposure",
        "pass" if wpjson_blocked else "warn",
        "/wp-json is blocked" if wpjson_blocked else "/wp-json is accessible — may expose product/user data to AI crawlers",
        cat
    ))

    # wp-admin blocked
    wpadmin_blocked = "disallow: /wp-admin" in robots_lower
    results.append(check(
        "WordPress admin (/wp-admin) blocked",
        "pass" if wpadmin_blocked else "fail",
        "/wp-admin is blocked" if wpadmin_blocked else "/wp-admin is NOT blocked — critical security issue",
        cat
    ))

    # Duplicate schema plugins
    schema_scripts = soup.find_all("script", type="application/ld+json")
    if len(schema_scripts) > 3:
        results.append(check(
            f"Potential duplicate schema ({len(schema_scripts)} JSON-LD blocks)",
            "warn",
            "Multiple JSON-LD blocks — check for Yoast/Rank Math/WooCommerce schema conflicts",
            cat
        ))

    # xmlrpc exposure
    xmlrpc_blocked = "disallow: /xmlrpc" in robots_lower
    results.append(check(
        "XML-RPC endpoint",
        "pass" if xmlrpc_blocked else "info",
        "xmlrpc is blocked" if xmlrpc_blocked else "xmlrpc not explicitly blocked (common WordPress endpoint)",
        cat
    ))

    return results


def _magento_specific(soup, html, robots_lower):
    """Magento-specific additional checks."""
    cat = "CMS & Customer Data Protection"
    results = []

    # GraphQL endpoint
    graphql_blocked = "disallow: /graphql" in robots_lower
    results.append(check(
        "Magento GraphQL endpoint exposure",
        "pass" if graphql_blocked else "warn",
        "/graphql is blocked" if graphql_blocked else "/graphql is accessible — may expose product catalog data",
        cat
    ))

    # Catalog search exposure
    catalogsearch_blocked = "disallow: /catalogsearch" in robots_lower
    results.append(check(
        "Catalog search (/catalogsearch) exposure",
        "info",
        "/catalogsearch is " + ("blocked" if catalogsearch_blocked else "accessible") + " in robots.txt",
        cat
    ))

    # Customer account
    customer_blocked = "disallow: /customer" in robots_lower
    results.append(check(
        "Customer account (/customer) blocked",
        "pass" if customer_blocked else "fail",
        "/customer is blocked" if customer_blocked else "/customer is NOT blocked — customer data may be exposed",
        cat
    ))

    # Admin panel
    admin_patterns = ["/admin", "/admin_", "/backend"]
    admin_blocked = any(f"disallow: {p}" in robots_lower for p in admin_patterns)
    results.append(check(
        "Admin panel blocked",
        "pass" if admin_blocked else "warn",
        "Admin path is blocked" if admin_blocked else "Admin path not explicitly blocked in robots.txt",
        cat
    ))

    return results


def _bigcommerce_specific(soup, html, robots_lower):
    """BigCommerce-specific additional checks."""
    cat = "CMS & Customer Data Protection"
    results = []

    # account.php
    account_blocked = "disallow: /account.php" in robots_lower
    results.append(check(
        "BigCommerce /account.php blocked",
        "pass" if account_blocked else "warn",
        "/account.php is blocked" if account_blocked else "/account.php not explicitly blocked",
        cat
    ))

    # cart.php
    cart_blocked = "disallow: /cart.php" in robots_lower
    results.append(check(
        "BigCommerce /cart.php blocked",
        "pass" if cart_blocked else "warn",
        "/cart.php is blocked" if cart_blocked else "/cart.php not explicitly blocked",
        cat
    ))

    # Stencil theme detection
    stencil = bool(re.search(r'stencil|cornerstone', html, re.I))
    results.append(check(
        "Stencil theme detected",
        "info" if stencil else "info",
        "Stencil/Cornerstone theme — content generally server-rendered" if stencil else "Custom theme detected",
        cat
    ))

    return results

CATEGORY_CONFIG = [
    {"key": "structured_data", "icon": "🧬", "name": "Structured Data & Schema", "fn": "check_structured_data"},
    {"key": "semantic_html", "icon": "🏗", "name": "Semantic HTML", "fn": "check_semantic_html"},
    {"key": "accessibility", "icon": "♿", "name": "Accessibility for Agents", "fn": "check_accessibility"},
    {"key": "internal_linking", "icon": "🔗", "name": "Internal Linking", "fn": "check_internal_linking"},
    {"key": "meta", "icon": "🔍", "name": "Meta & Discoverability", "fn": "check_meta_discoverability"},
    {"key": "machine_readability", "icon": "🤖", "name": "Machine Readability", "fn": "check_machine_readability"},
    {"key": "entity_authority", "icon": "🏛", "name": "Entity & Authority", "fn": "check_entity_authority"},
    {"key": "citability", "icon": "💬", "name": "Citability & Answer-Readiness", "fn": "check_citability"},
    {"key": "performance", "icon": "⚡", "name": "Performance & Crawlability", "fn": "check_performance"},
    {"key": "agent_interactivity", "icon": "🔌", "name": "Agent Interactivity (WebMCP)", "fn": "check_agent_interactivity"},
    # E-commerce & CMS (conditionally added)
    {"key": "product_page", "icon": "🛍", "name": "E-Commerce: Product Page", "fn": "check_product_page", "conditional": "product"},
    {"key": "collection_page", "icon": "📦", "name": "E-Commerce: Collection Page", "fn": "check_collection_page", "conditional": "collection"},
    {"key": "cms_customer_data", "icon": "🔐", "name": "CMS & Customer Data Protection", "fn": "check_cms_and_customer_data", "conditional": "always"},
]


def run_extended_audit(url, html, resp_headers=None, fetch_fn=None, robots_txt=""):
    """Run all categories of extended checks. Returns dict of category results + CMS/page info."""
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Detect CMS and page type
    cms_id, cms_confidence, cms_score = detect_cms(soup, html, url)
    page_type, page_type_score = detect_page_type(soup, html, url)

    results = {}
    for cat_conf in CATEGORY_CONFIG:
        fn_name = cat_conf["fn"]
        key = cat_conf["key"]

        # Skip conditional categories that don't apply
        conditional = cat_conf.get("conditional")
        if conditional == "product" and page_type != "product":
            continue
        if conditional == "collection" and page_type != "collection":
            continue

        try:
            if fn_name == "check_structured_data":
                checks = check_structured_data(soup, html)
            elif fn_name == "check_semantic_html":
                checks = check_semantic_html(soup, html)
            elif fn_name == "check_accessibility":
                checks = check_accessibility(soup, html)
            elif fn_name == "check_internal_linking":
                checks = check_internal_linking(soup, html, base_url)
            elif fn_name == "check_meta_discoverability":
                checks = check_meta_discoverability(soup, html, url)
            elif fn_name == "check_machine_readability":
                checks = check_machine_readability(soup, html, resp_headers)
            elif fn_name == "check_entity_authority":
                checks = check_entity_authority(soup, html, base_url)
            elif fn_name == "check_citability":
                checks = check_citability(soup, html)
            elif fn_name == "check_performance":
                checks = check_performance(soup, html)
            elif fn_name == "check_agent_interactivity":
                checks = check_agent_interactivity(soup, html, base_url, fetch_fn)
            elif fn_name == "check_product_page":
                checks = check_product_page(soup, html, url, cms_id)
            elif fn_name == "check_collection_page":
                checks = check_collection_page(soup, html, url, cms_id)
            elif fn_name == "check_cms_and_customer_data":
                checks = check_cms_and_customer_data(soup, html, url, cms_id, cms_confidence, robots_txt, fetch_fn)
            else:
                checks = []
        except Exception as e:
            checks = [check("Error running checks", "fail", str(e), cat_conf["name"])]

        # Calculate category score
        total = len(checks)
        passes = sum(1 for c in checks if c["status"] == "pass")
        warns = sum(1 for c in checks if c["status"] == "warn")
        fails = sum(1 for c in checks if c["status"] == "fail")
        infos = sum(1 for c in checks if c["status"] == "info")

        scorable = passes + warns + fails
        if scorable > 0:
            score = round((passes * 100 + warns * 50) / scorable)
        else:
            score = 100 if not fails else 50

        results[key] = {
            "name": cat_conf["name"],
            "icon": cat_conf["icon"],
            "checks": checks,
            "score": score,
            "passes": passes,
            "warns": warns,
            "fails": fails,
            "infos": infos,
            "total": total,
        }

    # Overall extended score
    scores = [r["score"] for r in results.values()]
    overall = round(sum(scores) / len(scores)) if scores else 0

    return {
        "categories": results,
        "overall": overall,
        "cms": {"id": cms_id, "name": CMS_PROFILES.get(cms_id, {}).get("name", "Unknown"), "confidence": cms_confidence} if cms_id else None,
        "page_type": page_type,
    }
