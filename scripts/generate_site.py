from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import requests


TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
REPORTS_DIR = SITE_DIR / "reports"
ASSETS_DIR = SITE_DIR / "assets"

TOPICS: list[tuple[str, str]] = [
    ("Claude", '"Claude Code" OR Anthropic coding OR "Claude Code voice"'),
    ("Cursor", 'Cursor AI coding OR "Cursor Automations" OR Bugbot'),
    ("OpenClaw", 'OpenClaw OR "Peter Steinberger" "personal agents"'),
    ("Agent", '"AI agent" OR "personal agent" OR "always-on agent"'),
    ("Skill", '"Agent Skills" OR SKILL.md OR "AI skills"'),
]


@dataclass
class NewsItem:
    topic: str
    title: str
    summary: str
    source: str
    link: str
    published: datetime


def ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def google_news_rss_url(query: str) -> str:
    encoded = quote_plus(query)
    return (
        "https://news.google.com/rss/search"
        f"?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_title(title: str) -> str:
    title = strip_html(title)
    title = title.replace("&#39;", "'")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def clean_summary(summary: str, title: str) -> str:
    text = strip_html(summary)
    if not text:
        return f"这条动态和 {title} 相关，值得关注后续进展。"
    text = text.replace(title, "").strip(" -:：")
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    return text or f"这条动态和 {title} 相关，值得关注后续进展。"


def parse_published(entry: feedparser.FeedParserDict) -> datetime:
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TZ)
                return dt.astimezone(TZ)
            except (TypeError, ValueError):
                pass
    return datetime.now(TZ)


def parse_feed(topic: str, query: str) -> list[NewsItem]:
    response = requests.get(
        google_news_rss_url(query),
        headers={"User-Agent": "Mozilla/5.0 AI-Kuaibao-Bot"},
        timeout=20,
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    items: list[NewsItem] = []
    for entry in feed.entries[:8]:
        title = normalize_title(entry.get("title", ""))
        if not title:
            continue
        source = "未知来源"
        raw_source = entry.get("source")
        if isinstance(raw_source, dict):
            source = raw_source.get("title") or source
        elif hasattr(raw_source, "get"):
            source = raw_source.get("title") or source
        summary = clean_summary(entry.get("summary", ""), title)
        link = entry.get("link", "").strip()
        if not link:
            continue
        items.append(
            NewsItem(
                topic=topic,
                title=title,
                summary=summary,
                source=source,
                link=link,
                published=parse_published(entry),
            )
        )
    return items


def collect_items() -> list[NewsItem]:
    seen: set[str] = set()
    items: list[NewsItem] = []
    for topic, query in TOPICS:
        for item in parse_feed(topic, query):
            dedupe_key = re.sub(r"[^a-z0-9]+", "", item.title.lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append(item)
    items.sort(key=lambda item: item.published, reverse=True)
    return items[:10]


def render_signal_lines(items: Iterable[NewsItem]) -> list[str]:
    topics = [item.topic for item in items]
    unique_topics = sorted(set(topics))
    signals = [
        "AI 编程工具的关注点，正在从“会生成”继续转向“会协作、会审查、会自动运行”。",
        "个人代理和组织级 agent 都在升温，说明 agent 已经从概念阶段进入更具体的产品落地阶段。",
        "skills、工作流封装和自动化调度正在一起成熟，未来竞争点会越来越偏工程体系而不只是模型本身。",
    ]
    if "OpenClaw" in unique_topics:
        signals[1] = "OpenClaw 和 personal agent 相关话题仍然有热度，说明开源代理生态还在持续外溢。"
    return signals


def report_filename(now: datetime) -> str:
    return now.strftime("%Y-%m-%d_%H-%M-%S") + ".html"


def page_title(now: datetime) -> str:
    return f"AI 快报 | {now.strftime('%Y-%m-%d')}"


def render_report_html(now: datetime, items: list[NewsItem]) -> str:
    signals = render_signal_lines(items)
    item_html = []
    for idx, item in enumerate(items, start=1):
        item_html.append(
            f"""
      <article class="item">
        <div class="pill">{html.escape(item.topic)}</div>
        <h2>{idx}. {html.escape(item.title)}</h2>
        <p>{html.escape(item.summary)}</p>
        <div class="meta">{html.escape(item.source)} · {item.published.strftime('%m-%d %H:%M')}</div>
        <a href="{html.escape(item.link)}" target="_blank" rel="noreferrer">查看原文</a>
      </article>
"""
        )

    signal_html = "\n".join(
        f"<li>{html.escape(signal)}</li>" for signal in signals
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(page_title(now))}</title>
  <link rel="stylesheet" href="../assets/styles.css" />
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="eyebrow">AI 快报</div>
      <h1>{html.escape(page_title(now))}</h1>
      <p class="sub">时间：{now.strftime('%Y-%m-%d %H:%M:%S')} · 每天自动更新的 AI 动态精选</p>
      <p class="lead">今天值得看的 10 条 AI 动态，重点聚焦 <code>Claude</code>、<code>Cursor</code>、<code>OpenClaw</code>、<code>agent</code> 和 <code>skill</code> 这几个方向。</p>
      <p><a class="home-link" href="../index.html">返回首页</a></p>
    </section>

    <section class="grid">
      {''.join(item_html)}
    </section>

    <section class="signals">
      <h2>今天的几个信号</h2>
      <ul>
        {signal_html}
      </ul>
      <p class="note">这版快报基于公开可访问的新闻和官方内容聚合生成，适合作为每日浏览入口。</p>
    </section>
  </main>
</body>
</html>
"""


def render_index_html(now: datetime, latest_name: str, items: list[NewsItem]) -> str:
    report_links = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
    archive_items = []
    for path in report_links[:30]:
        archive_items.append(
            f'<li><a href="reports/{html.escape(path.name)}">{html.escape(path.stem)}</a></li>'
        )

    preview = []
    for item in items[:5]:
        preview.append(
            f"""
      <li>
        <span>{html.escape(item.topic)}</span>
        <a href="{html.escape(item.link)}" target="_blank" rel="noreferrer">{html.escape(item.title)}</a>
      </li>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI 快报</title>
  <link rel="stylesheet" href="assets/styles.css" />
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="eyebrow">AI 快报网站</div>
      <h1>每天上午 10 点更新</h1>
      <p class="sub">Asia/Shanghai 定时生成 · HTML 静态站点 · 适合 GitHub Pages</p>
      <p class="lead">这里会持续生成每日 AI 快报页面，只保留 HTML 产物，适合直接发布到 GitHub Pages。</p>
      <div class="hero-actions">
        <a class="button" href="reports/{html.escape(latest_name)}">查看最新快报</a>
      </div>
    </section>

    <section class="panel">
      <h2>本期预览</h2>
      <ul class="preview-list">
        {''.join(preview)}
      </ul>
    </section>

    <section class="panel">
      <h2>归档</h2>
      <ul class="archive-list">
        {''.join(archive_items)}
      </ul>
      <p class="note">最近更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    ensure_dirs()
    now = datetime.now(TZ)
    items = collect_items()
    if not items:
        raise SystemExit("No items were collected from feeds.")

    latest_name = report_filename(now)
    report_path = REPORTS_DIR / latest_name
    report_path.write_text(render_report_html(now, items), encoding="utf-8")
    (SITE_DIR / "index.html").write_text(
        render_index_html(now, latest_name, items),
        encoding="utf-8",
    )
    print(f"Generated report: {report_path}")
    print(f"Updated index: {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
