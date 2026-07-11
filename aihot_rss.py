#!/usr/bin/env python3
"""
多合一 RSS：AI热榜 + 加密货币 + 贵金属 + 少数派 + Elon Musk + Naval
"""
import json, sys, os, time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0")
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "docs/aihot.xml"
NOW_RFC = format_datetime(datetime.now(timezone.utc))

# ──────────────────── 数据采集 ────────────────────

def fetch_aihot(hours=24, take=30):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://aihot.virxact.com/api/public/items?{urlencode({'mode':'selected', 'since':since, 'take':take})}"
    req = Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45) as r:
                data = json.load(r)
            return data.get("items", data) if isinstance(data, dict) else data
        except Exception as e:
            if attempt == 2:
                raise e
            print(f"[aihot] 第{attempt+1}次失败，10秒后重试: {e}")
            time.sleep(10)

def fetch_crypto():
    url = ("https://api.coingecko.com/api/v3/coins/markets"
           "?vs_currency=cny&ids=bitcoin,ethereum,binancecoin,solana,dogecoin"
           "&order=market_cap_desc&per_page=5&page=1&sparkline=false"
           "&price_change_percentage=24h")
    with urlopen(url, timeout=30) as r:
        return json.load(r)

def fetch_precious_metals():
    url = ("https://push2.eastmoney.com/api/qt/ulist.np/get"
           "?fltt=2&secids=113.aum,113.agm&fields=f2,f3,f4,f6,f12,f14,f58")
    with urlopen(url, timeout=20) as r:
        return json.load(r)

def fetch_rss(url):
    """通用 RSS/Atom 抓取"""
    headers = {"User-Agent": UA}
    if "bing.com" in url:
        headers["Referer"] = "https://www.bing.com/news/"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as r:
        raw_bytes = r.read()
    # 自动检测编码
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        raw = raw_bytes[3:].decode('utf-8', errors='replace')
    else:
        try:
            raw = raw_bytes.decode('utf-8', errors='replace')
        except:
            raw = raw_bytes.decode('latin-1', errors='replace')
    import re
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    root = ET.fromstring(raw)

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    is_atom = root.tag == "{http://www.w3.org/2005/Atom}feed" or root.tag == "feed"

    channel_title = ""
    items = []

    if is_atom:
        channel_title = root.findtext("atom:title", default="", namespaces=ns) or root.findtext("title", default="")
        for entry in root.findall("atom:entry", ns) or root.findall("entry"):
            title = entry.findtext("atom:title", default="", namespaces=ns) or entry.findtext("title", default="(无标题)")
            link_elem = entry.find("atom:link", ns) or entry.find("link")
            link = ""
            if link_elem is not None:
                link = link_elem.get("href", link_elem.text or "")
            summary = entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("summary", default="")
            updated = entry.findtext("atom:updated", default="", namespaces=ns) or entry.findtext("updated", default="")
            items.append({"title": title.strip(), "link": link.strip(), "summary": summary.strip(), "updated": updated.strip()})
    else:
        channel_title = root.findtext("channel/title", default="")
        for item in root.findall("channel/item"):
            title = item.findtext("title", default="(无标题)")
            link = item.findtext("link", default="")
            desc = item.findtext("description", default="")
            pub = item.findtext("pubDate", default="")
            items.append({"title": title.strip(), "link": link.strip(), "summary": desc.strip(), "updated": pub.strip()})

    return channel_title, items


# ──────────────────── RSS 构建 ────────────────────

def item_xml(title, link, description, pub_date=None):
    pub = pub_date or NOW_RFC
    return (f"<item>"
            f"<title>{escape(title)}</title>"
            f"<link>{escape(link)}</link>"
            f"<description>{escape(description)}</description>"
            f"<pubDate>{pub}</pubDate>"
            f'<guid isPermaLink="false">{escape(title)}</guid>'
            f"</item>")

def format_pct(val):
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"

def build_crypto_items(data):
    items = []
    for coin in data:
        desc = (f"{coin['name']}（{coin['symbol'].upper()}）: "
                f"¥{coin['current_price']:,.2f} | "
                f"24h: {format_pct(coin['price_change_percentage_24h'])} | "
                f"高 ¥{coin.get('high_24h', 0):,.2f} / 低 ¥{coin.get('low_24h', 0):,.2f}")
        items.append(item_xml(
            title=f"[币] {coin['name']} ({coin['symbol'].upper()}) ¥{coin['current_price']:,.2f} {format_pct(coin['price_change_percentage_24h'])}",
            link=f"https://www.coingecko.com/en/coins/{coin['id']}",
            description=desc,
        ))
    return items

def build_metal_items(data):
    items = []
    for m in data.get("data", {}).get("diff", []):
        name = m.get("f14", "")
        code = m.get("f12", "")
        price = m.get("f2", 0)
        pct = m.get("f3", 0)
        val = m.get("f4", 0)
        vol = m.get("f6", 0)
        desc = (f"{name}（{code}）: ¥{price:.2f} | "
                f"涨跌: {val:.2f} ({format_pct(pct)}) | "
                f"成交额: ¥{vol:,.0f}")
        items.append(item_xml(
            title=f"[期货] {name} ¥{price:.2f} {format_pct(pct)}",
            link=f"https://quote.eastmoney.com/qihuo/{code}.html",
            description=desc,
        ))
    return items

def build_aihot_items(data):
    items = []
    for it in data:
        t = it.get("title") or it.get("name") or "(无标题)"
        u = it.get("url") or it.get("link") or "https://aihot.virxact.com/"
        s = it.get("summary") or it.get("description") or it.get("excerpt") or t
        pub = it.get("published_at") or it.get("created_at")
        try:
            dt = datetime.fromisoformat(pub.replace("Z","+00:00")) if pub else None
            rfc = format_datetime(dt) if dt else NOW_RFC
        except:
            rfc = NOW_RFC
        items.append(item_xml(f"[AI] {t}", u, s, pub_date=rfc))
    return items

def build_rss_items(raw_items, source_label, source_name, default_link):
    """将通用 RSS item 转为标准 XML 条目，推文摘要截短"""
    items = []
    for ri in raw_items:
        t = ri["title"].encode('utf-8', errors='replace').decode('utf-8')

        # Twitter 推文通常内容很长，摘要只取前200字符
        s = ri["summary"]
        # 去掉 HTML 标签
        import re
        s = re.sub(r'<[^>]+>', '', s)
        s = s.encode('utf-8', errors='replace').decode('utf-8')  # 新增

        s = s[:300].strip()
        if len(s) >= 300:
            s += "..."

        u = ri["link"] or default_link
        pub = ri["updated"]
        try:
            dt = None
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    dt = datetime.strptime(pub, fmt) if pub else None
                    break
                except:
                    continue
            rfc = format_datetime(dt) if dt else NOW_RFC
        except:
            rfc = NOW_RFC
        items.append(item_xml(f"[{source_label}] {t}", u, s, pub_date=rfc))
    return items

# ──────────────────── 主流程 ────────────────────

def main():
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        '<title>综合热榜（AI + 币价 + 期货 + 少数派 + Elon + Naval + 化工塑料）</title>',
        '<link>https://github.com/yuhao0406/aihot-rss</link>',
        '<description>AI精选、加密行情、贵金属期货、少数派数码、Elon Musk &amp; Naval 推文、化工塑料新闻，每小时更新</description>',

        f'<lastBuildDate>{NOW_RFC}</lastBuildDate>',
    ]

    errors = []

    # 1. AI热榜
    try:
        parts.extend(build_aihot_items(fetch_aihot()))
    except Exception as e:
        errors.append(f"AI热榜: {e}")

    # 2. 加密货币
    try:
        parts.extend(build_crypto_items(fetch_crypto()))
    except Exception as e:
        errors.append(f"加密货币: {e}")

    # 3. 贵金属期货
    try:
        parts.extend(build_metal_items(fetch_precious_metals()))
    except Exception as e:
        errors.append(f"贵金属: {e}")

    # 4. 少数派
    try:
        _, sspai_items = fetch_rss("https://sspai.com/feed")
        parts.extend(build_rss_items(sspai_items[:10], "少数派", "少数派", "https://sspai.com"))
    except Exception as e:
        errors.append(f"少数派: {e}")

    # 5. Elon Musk 推文
    try:
        _, elon_items = fetch_rss("https://rss.941009.xyz/twitter/user/elonmusk")
        parts.extend(build_rss_items(elon_items[:10], "Elon Musk", "Elon Musk", "https://x.com/elonmusk"))
    except Exception as e:
        errors.append(f"Elon Musk: {e}")

    # 6. Naval 推文
    try:
        _, naval_items = fetch_rss("https://rss.941009.xyz/twitter/user/naval")
        parts.extend(build_rss_items(naval_items[:10], "Naval", "Naval", "https://x.com/naval"))
    except Exception as e:
        errors.append(f"Naval: {e}")

    # 7. Bing 化工塑料系列
    bing_queries = [
        ("化工+塑料", "化工塑料", "https://www.bing.com/news/search?q=塑料+化工&format=rss&cc=US"),
        ("PP+聚丙烯", "PP聚丙烯", "https://www.bing.com/news/search?q=pp+聚丙烯&format=rss&cc=US"),
        ("尼龙+PA", "尼龙PA", "https://www.bing.com/news/search?q=尼龙+PA&format=rss&cc=US"),
        ("塑料价格", "塑料价格", "https://www.bing.com/news/search?q=塑料价格&format=rss&cc=US"),
        ("塑料原料市场", "塑料原料", "https://www.bing.com/news/search?q=塑料原料市场&format=rss&cc=US"),
    ]
    for label, tag, q_url in bing_queries:
        try:
            _, bing_items = fetch_rss(q_url)
            parts.extend(build_rss_items(bing_items[:5], tag, label, q_url))
        except Exception as e:
            errors.append(f"Bing-{label}: {e}")



    parts.append("</channel></rss>")

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    if errors:
        print("!!! 以下数据源获取失败，其余正常:")
        for e in errors:
            print("  -", e)
    print(f"DONE {OUTPUT}")


if __name__ == "__main__":
    main()
