#!/usr/bin/env python3
"""
AIHot RSS + Smart Money Radar

功能：

AI热点
加密行情
贵金属
少数派
Elon Musk
Naval

新增：

机构资金雷达
- SEC
- MicroStrategy
- Michael Saylor
- BlackRock
- Bitcoin ETF
- Fed
- CoinDesk
- The Block

"""

import json
import sys
import os
import time
import re

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

import xml.etree.ElementTree as ET



# =========================
# 基础配置
# =========================


UA = (
    "Mozilla/5.0 "
    "(Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 "
    "Chrome/124 Safari/537.36 "
    "aihot-smartmoney/1.0"
)


OUTPUT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "docs/aihot.xml"
)


NOW_RFC = format_datetime(
    datetime.now(timezone.utc)
)



# =========================
# 网络请求
# =========================


def http_get(url, timeout=30):

    req = Request(
        url,
        headers={
            "User-Agent": UA
        }
    )


    with urlopen(
        req,
        timeout=timeout
    ) as r:

        return r.read()



# =========================
# AI热点
# =========================


def fetch_aihot(
        hours=24,
        take=30):


    since = (
        datetime.now(timezone.utc)
        -
        timedelta(hours=hours)
    ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


    url = (
        "https://aihot.virxact.com/api/public/items?"
        +
        urlencode(
            {
                "mode":"selected",
                "since":since,
                "take":take
            }
        )
    )


    for i in range(3):

        try:

            data = json.loads(
                http_get(url,45)
            )


            if isinstance(data,dict):

                return data.get(
                    "items",
                    []
                )

            return data


        except Exception as e:

            if i==2:
                raise e


            time.sleep(10)



# =========================
# 加密行情
# =========================


def fetch_crypto():


    url = (
        "https://api.coingecko.com/api/v3/"
        "coins/markets?"
        "vs_currency=cny&"
        "ids=bitcoin,ethereum,"
        "binancecoin,solana,dogecoin&"
        "order=market_cap_desc&"
        "per_page=5&page=1&"
        "sparkline=false&"
        "price_change_percentage=24h"
    )


    return json.loads(
        http_get(url,30)
    )



# =========================
# 贵金属
# =========================


def fetch_precious_metals():


    url = (
        "https://push2.eastmoney.com/api/"
        "qt/ulist.np/get?"
        "fltt=2&"
        "secids=113.aum,113.agm&"
        "fields=f2,f3,f4,f6,f12,f14,f58"
    )


    return json.loads(
        http_get(url,20)
    )



# =========================
# 通用RSS抓取
# =========================


def fetch_rss(url):


    raw = http_get(
        url,
        30
    ).decode(
        "utf-8",
        errors="replace"
    )


    raw = re.sub(
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',
        '',
        raw
    )


    root = ET.fromstring(raw)


    ns={
        "atom":
        "http://www.w3.org/2005/Atom"
    }


    items=[]


    atom = (
        root.tag.endswith("feed")
    )


    title=""


    if atom:


        title = (
            root.findtext(
                "atom:title",
                "",
                ns
            )
            or ""
        )


        entries = (
            root.findall(
                "atom:entry",
                ns
            )
        )


        for e in entries:


            t = (
                e.findtext(
                    "atom:title",
                    "",
                    ns
                )
            )


            link=""


            le=e.find(
                "atom:link",
                ns
            )


            if le is not None:

                link=le.get(
                    "href",
                    ""
                )


            s=(
                e.findtext(
                    "atom:summary",
                    "",
                    ns
                )
            )


            u=(
                e.findtext(
                    "atom:updated",
                    "",
                    ns
                )
            )


            items.append(
                {
                    "title":t,
                    "link":link,
                    "summary":s,
                    "updated":u
                }
            )


    else:


        title=root.findtext(
            "channel/title",
            ""
        )


        for e in root.findall(
            "channel/item"
        ):


            items.append(
                {
                    "title":
                    e.findtext(
                        "title",
                        ""
                    ),

                    "link":
                    e.findtext(
                        "link",
                        ""
                    ),

                    "summary":
                    e.findtext(
                        "description",
                        ""
                    ),

                    "updated":
                    e.findtext(
                        "pubDate",
                        ""
                    )
                }
            )


    return title,items



# ===== Part 1结束 =====
# =====================================================
# Smart Money 资金雷达模块
# =====================================================


SMART_KEYWORDS = {


    # ===== 机构 =====

    "MicroStrategy":10,
    "Michael Saylor":10,
    "MSTR":10,

    "BlackRock":9,
    "iShares":9,
    "IBIT":10,

    "Berkshire Hathaway":8,
    "Warren Buffett":8,
    "Buffett":8,


    # ===== ETF =====

    "Bitcoin ETF":10,
    "BTC ETF":10,
    "ETF inflow":9,
    "ETF outflow":-9,


    # ===== BTC资金 =====

    "Bitcoin":5,
    "BTC":5,

    "whale":8,
    "accumulation":8,

    "exchange inflow":-8,
    "exchange outflow":8,


    # ===== 宏观 =====

    "Federal Reserve":10,
    "FOMC":10,
    "Jerome Powell":9,

    "interest rate":7,
    "liquidity":8,

    "quantitative easing":10,
    "QT":-8,


    # ===== SEC =====

    "13F":8,
    "8-K":8,
    "SEC filing":8,

}



SMART_SOURCES = [


    {
        "name":"SEC",
        "label":"机构文件",

        "url":
        "https://www.sec.gov/cgi-bin/"
        "browse-edgar?"
        "action=getcurrent&"
        "output=atom"
    },


    {
        "name":"CoinDesk",
        "label":"机构加密",

        "url":
        "https://www.coindesk.com/"
        "arc/outboundfeeds/rss/"
    },


    {
        "name":"TheBlock",
        "label":"机构加密",

        "url":
        "https://www.theblock.co/rss.xml"
    },


    {
        "name":"Fed",
        "label":"宏观流动性",

        "url":
        "https://www.federalreserve.gov/"
        "feeds/press_all.xml"
    },

]



def smart_score(text):


    score=0


    lower=text.lower()


    for key,value in SMART_KEYWORDS.items():

        if key.lower() in lower:

            score += value


    return score




def fetch_smart_money():


    results=[]


    for source in SMART_SOURCES:


        try:


            _,items = fetch_rss(
                source["url"]
            )


            for item in items[:20]:


                text = (
                    item["title"]
                    +
                    item["summary"]
                )


                score = smart_score(
                    text
                )


                # 没有资金价值过滤

                if score <= 0:

                    continue



                results.append(
                    {

                    "source":
                    source["label"],


                    "title":
                    item["title"],


                    "link":
                    item["link"],


                    "summary":
                    item["summary"],


                    "updated":
                    item["updated"],


                    "score":
                    score

                    }
                )



        except Exception as e:


            print(
                "[SmartMoney错误]",
                source["name"],
                e
            )



    # 高分优先

    results.sort(
        key=lambda x:x["score"],
        reverse=True
    )


    return results




# =====================================================
# RSS XML生成
# =====================================================



def item_xml(
        title,
        link,
        description,
        pub_date=None):


    pub = (
        pub_date
        or
        NOW_RFC
    )


    return (

        "<item>"

        f"<title>{escape(title)}</title>"

        f"<link>{escape(link)}</link>"

        f"<description>{escape(description)}</description>"

        f"<pubDate>{pub}</pubDate>"

        f"<guid isPermaLink=\"false\">"
        f"{escape(title)}"
        "</guid>"

        "</item>"

    )





def format_pct(v):


    sign="+" if v>=0 else ""


    return (
        f"{sign}{v:.2f}%"
    )





def build_crypto_items(data):

    items = []

    for coin in data:

        pct = coin.get(
            "price_change_percentage_24h",
            0
        )

        price = coin.get(
            "current_price",
            0
        )

        name = coin.get(
            "name",
            ""
        )

        symbol = coin.get(
            "symbol",
            ""
        ).upper()


        desc = (
            name
            + " ("
            + symbol
            + ") "
            + "价格:"
            + str(price)
            + " "
            + "24h:"
            + format_pct(pct)
        )


        items.append(

            item_xml(

                "[币] "
                + name,

                "https://www.coingecko.com/",

                desc

            )

        )


    return items


        items.append(

            item_xml(

                "[币]"
                +
                coin["name"],

                "https://www.coingecko.com/",

                desc

            )

        )


    return items





def build_smart_money_items(data):


    items=[]


    for item in data:


        desc=(

            "资金来源:"
            +
            item["source"]

            +

            "\n\n评分:"
            +
            str(item["score"])

            +

            "\n\n"

            +

            item["summary"]

        )


        title=(

            "[资金+"

            +
            str(item["score"])

            +

            "] "

            +

            item["title"]

        )


        items.append(

            item_xml(

                title,

                item["link"],

                desc,

                item["updated"]

            )

        )


    return items



# ===== Part 2结束 =====
# =====================================================
# 其它RSS内容构建
# =====================================================


def build_aihot_items(data):

    items=[]


    for it in data:


        title = (
            it.get("title")
            or
            it.get("name")
            or
            "(无标题)"
        )


        link = (
            it.get("url")
            or
            it.get("link")
            or
            "https://aihot.virxact.com/"
        )


        summary = (
            it.get("summary")
            or
            it.get("description")
            or
            title
        )


        pub = (
            it.get("published_at")
            or
            it.get("created_at")
        )


        try:

            if pub:

                dt=datetime.fromisoformat(
                    pub.replace(
                        "Z",
                        "+00:00"
                    )
                )

                rfc=format_datetime(dt)

            else:

                rfc=NOW_RFC


        except:

            rfc=NOW_RFC



        items.append(

            item_xml(

                "[AI] "
                +
                title,

                link,

                summary,

                rfc

            )

        )


    return items





def build_rss_items(
        raw_items,
        label,
        default_link):


    items=[]


    for item in raw_items[:10]:


        title=item.get(
            "title",
            "(无标题)"
        )


        summary=item.get(
            "summary",
            ""
        )


        summary=re.sub(
            "<[^>]+>",
            "",
            summary
        )


        summary=summary[:300]


        link=item.get(
            "link",
            default_link
        )


        pub=item.get(
            "updated",
            NOW_RFC
        )



        items.append(

            item_xml(

                "["+label+"] "
                +
                title,

                link,

                summary,

                pub

            )

        )


    return items




def build_metal_items(data):


    items=[]


    try:


        metals=data.get(
            "data",
            {}
        ).get(
            "diff",
            []
        )


        for m in metals:


            name=m.get(
                "f14",
                ""
            )


            price=m.get(
                "f2",
                0
            )


            pct=m.get(
                "f3",
                0
            )


            items.append(

                item_xml(

                    "[贵金属] "
                    +
                    name,

                    "https://quote.eastmoney.com/",

                    f"{name} "
                    f"价格:{price} "
                    f"涨跌:{pct}%"

                )

            )


    except Exception:

        pass


    return items





# =====================================================
# 主程序
# =====================================================


def main():


    parts=[

        '<?xml version="1.0" encoding="UTF-8"?>',

        '<rss version="2.0">',

        '<channel>',


        '<title>'
        'AIHot Smart Money资金雷达'
        '</title>',


        '<link>'
        'https://github.com/yuhao0406/aihot-rss'
        '</link>',


        '<description>'
        'AI热点 + 加密行情 + '
        '机构资金流 + 美联储 + ETF'
        '</description>',


        f'<lastBuildDate>{NOW_RFC}</lastBuildDate>'

    ]



    errors=[]



    # ------------------
    # AI热点
    # ------------------

    try:


        ai = fetch_aihot()


        parts.extend(

            build_aihot_items(
                ai
            )

        )


    except Exception as e:


        errors.append(
            "AI热点:"+str(e)
        )




    # ------------------
    # 加密行情
    # ------------------

    try:


        crypto=fetch_crypto()


        parts.extend(

            build_crypto_items(
                crypto
            )

        )


    except Exception as e:


        errors.append(
            "币价:"+str(e)
        )





    # ------------------
    # 贵金属
    # ------------------

    try:


        metals=fetch_precious_metals()


        parts.extend(

            build_metal_items(
                metals
            )

        )


    except Exception as e:


        errors.append(
            "贵金属:"+str(e)
        )






    # ------------------
    # 少数派
    # ------------------

    try:


        _,sspai=fetch_rss(

            "https://sspai.com/feed"

        )


        parts.extend(

            build_rss_items(

                sspai,

                "少数派",

                "https://sspai.com"

            )

        )


    except Exception as e:


        errors.append(
            "少数派:"+str(e)
        )





    # ------------------
    # Elon Musk
    # ------------------

    try:


        _,elon=fetch_rss(

            "https://rss.941009.xyz/twitter/user/elonmusk"

        )


        parts.extend(

            build_rss_items(

                elon,

                "Elon Musk",

                "https://x.com/elonmusk"

            )

        )


    except Exception as e:


        errors.append(
            "Elon:"+str(e)
        )





    # ------------------
    # Naval
    # ------------------

    try:


        _,naval=fetch_rss(

            "https://rss.941009.xyz/twitter/user/naval"

        )


        parts.extend(

            build_rss_items(

                naval,

                "Naval",

                "https://x.com/naval"

            )

        )


    except Exception as e:


        errors.append(
            "Naval:"+str(e)
        )






    # =================================================
    # Smart Money资金雷达
    # =================================================


    try:


        smart=fetch_smart_money()



        parts.extend(

            build_smart_money_items(

                smart[:50]

            )

        )



    except Exception as e:


        errors.append(

            "SmartMoney:"
            +
            str(e)

        )






    parts.append(

        "</channel></rss>"

    )



    os.makedirs(

        os.path.dirname(
            OUTPUT
        )
        or
        ".",

        exist_ok=True

    )



    with open(

        OUTPUT,

        "w",

        encoding="utf-8"

    ) as f:


        f.write(

            "\n".join(parts)

        )





    print(
        "DONE:",
        OUTPUT
    )



    if errors:


        print(
            "\n错误:"
        )


        for e in errors:

            print(
                "-",
                e
            )





if __name__=="__main__":


    main()
