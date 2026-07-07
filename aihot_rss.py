#!/usr/bin/env python3
"""
三合一 RSS：AI热榜 + 加密货币 + 沪金沪银期货
"""
import json, sys, os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0")
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "docs/aihot.xml"
NOW_RFC = format_datetime(datetime.now(timezone.utc))


def fetch_aihot(hours=24, take=30):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://aihot.virxact.com/api/public/items?{urlencode({'mode':'selected', 'since':since, 'take':take})}"
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        data = json.load(r)
    return data.get("items", data) if isinstance(data, dict) else data


def fetch_crypto():
    url = ("https://api.coingecko.com/api/v3/coins/markets"
           "?vs_currency=cny&ids=bitcoin,ethereum,binancecoin,solana,dogecoin"
           "&order=market_cap_desc&per_page=5&page=1&sparkline=false"
           "&price_change_percentage=24h")
    with urlopen(url, timeout=20) as r:
        return json.load(r)


def fetch_precious_metals():
    url = ("https://push2.eastmoney.com/api/qt/ulist.np/get"
           "?fltt=2&secids=113.aum,113.agm&fields=f2,f3,f4,f6,f12,f14,f58")
    with urlopen(url, timeout=20) as r:
        return json.load(r)


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
            title=f"{coin['name']} ({coin['symbol'].upper()}) ¥{coin['current_price']:,.2f} {format_pct(coin['price_change_percentage_24h'])}",
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
            title=f"{name} ¥{price:.2f} {format_pct(pct)}",
            link=f"https://quote.eastmoney.com/qihuo/{code}.html",
            description=desc,
        ))
    return items


def build_aihot_items(data):
    items = []
    for it in data:
        t = it.get("title") or it.get("name") or "(无标题)"
        u = it.get("url") or it.get("link") or "https://aihot.virxact.com/"
        s = escape(it.get("summary") or it.get("description") or it.get("excerpt") or t)
        pub = it.get("published_at") or it.get("created_at")
        try:
            dt = datetime.fromisoformat(pub.replace("Z","+00:00")) if pub else None
            rfc = format_datetime(dt) if dt else NOW_RFC
        except:
            rfc = NOW_RFC
        items.append(item_xml(t, u, s, pub_date=rfc))
    return items


def main():
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        '<title>综合热榜（AI热榜 + 加密货币 + 贵金属）</title>',
        '<link>https://github.com/yuhao0406/aihot-rss</link>',
        '<description>AI精选、BTC/ETH/BNB/SOL/DOGE行情、沪金沪银期货，每小时更新</description>',
        f'<lastBuildDate>{NOW_RFC}</lastBuildDate>',
    ]

    errors = []

    try:
        parts.extend(build_aihot_items(fetch_aihot()))
    except Exception as e:
        errors.append(f"AI热榜: {e}")

    try:
        parts.extend(build_crypto_items(fetch_crypto()))
    except Exception as e:
        errors.append(f"加密货币: {e}")

    try:
        parts.extend(build_metal_items(fetch_precious_metals()))
    except Exception as e:
        errors.append(f"贵金属: {e}")

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
