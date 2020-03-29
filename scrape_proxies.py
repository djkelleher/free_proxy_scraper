from pyppeteer_spider.spider import PyppeteerSpider
from typing import Optional, List
import asyncio
import random
import requests
import re

addr_re = r'\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3}'
addr_port_re = addr_re + r':\d{2,5}'


def proxy_ok(proxy):
    test_url = 'https://newhaven.craigslist.org/'
    response = requests.head(test_url, proxies={'http': proxy}, timeout=1.5)
    return response.status_code == 200


async def scrape_free_proxy_list_net(spider: PyppeteerSpider):
    page = await spider.get('https://free-proxy-list.net')
    proxies = set()
    while True:
        await asyncio.sleep(random.uniform(2, 3))
        col_names = [
            await page.evaluate('(ele) => ele.innerText.toLowerCase()', ele)
            for ele in await page.xpath(
                '//*[@id="proxylisttable"]/thead/*[@role="row"]//*[@aria-label]'
            )
        ]
        for row in await page.xpath(
                '//*[@id="proxylisttable"]/tbody/*[@role="row"]'):
            col_values = [
                await page.evaluate('(ele) => ele.innerText', ele)
                for ele in await row.xpath('./td')
            ]
            row_data = dict(zip(col_names, col_values))
            proxies.add(row_data["ip address"] + ":" + row_data["port"])
        next_button_ele = await page.xpath(
            '//*[@class="fg-button ui-button ui-state-default next"]')
        if next_button_ele:
            await next_button_ele[0].click()
        else:
            await spider.set_idle(page)
            print(
                f"Extracted {len(proxies)} total proxies from free-proxy-list.net"
            )
            return proxies


async def scrape_spys_one(spider: PyppeteerSpider,
                          protocols: List[str] = ['http', 'socks4', 'socks5'],
                          countries: Optional[List[str]] = None):
    if countries is None:
        page = await spider.get('http://spys.one/proxys')
        countries = [
            await page.evaluate('(ele) => ele.innerText', ele) for ele in await
            page.xpath('//a[@href]//*[@class="spy6"]//*[@class="spy4"]')
        ]
        await spider.set_idle(page)
    proxies = set()
    for country in countries:
        print(f"Extracting proxies from Spys {country}.")
        page = await spider.get(f'http://spys.one/proxys/{country}',
                                waitUntil=['load', 'networkidle2'])
        table_rows = [
            await page.evaluate('(ele) => ele.innerText', ele)
            for ele in await page.xpath('//*[contains(@class,"spy1x")]')
        ]
        proxy_matches = [
            re.search(
                r'(?i)(' + addr_port_re +
                r')\s{0,2}(http|https|socks4|socks5)', row)
            for row in table_rows
        ]
        proxy_matches = [m for m in proxy_matches if m is not None]
        for protocol in protocols:
            proxies.update([
                match.group(1) for match in proxy_matches
                if protocol.lower() in match.group(2).lower()
            ])
        await spider.set_idle(page)
        await asyncio.sleep(random.uniform(2, 3))
    print(f"Extracted {len(proxies)} total proxies from Spys One.")
    return proxies


def scrape_proxyscrape_proxies(
    protocols: List[str] = ['http', 'socks4', 'socks5']):
    protocols = [p.lower() for p in protocols]
    endpoints = []
    if 'http' in protocols:
        endpoints.append(
            "https://api.proxyscrape.com/?request=getproxies&amp;proxytype=http&amp;timeout=10000&amp;country=all&amp;ssl=all&amp;anonymity=all"
        )
    if 'socks4' in protocols:
        endpoints.append(
            "https://api.proxyscrape.com?request=getproxies&amp;proxytype=socks4&amp;timeout=10000&amp;country=all"
        )
    if 'socks5' in protocols:
        endpoints.append(
            "https://api.proxyscrape.com?request=getproxies&amp;proxytype=socks4&amp;timeout=10000&amp;country=all"
        )
    proxies = set()
    for url in endpoints:
        resp = requests.get(url, verify=False)
        proxies.update(re.findall(addr_port_re, resp.text))
    print(f"Extracted {len(proxies)} total proxies from api.proxyscrape.com")
    return proxies


async def scrape_proxy_list_org(spider: PyppeteerSpider):
    proxies = set()
    page_url = 'https://proxy-list.org/english/index.php'
    while True:
        page = await spider.get(page_url, waitUntil=['load', 'networkidle2'])
        await asyncio.sleep(random.uniform(1, 2))
        proxies.update([
            await page.evaluate('(ele) => ele.innerText', ele) for ele in await
            page.xpath('//*[@class="table"]//*[@class="proxy"]')
        ])
        next_page_ele = await page.xpath('//*[@class="next"]')
        if next_page_ele:
            page_url = await page.evaluate("(ele) => ele.getAttribute('href')",
                                           next_page_ele[0])
            page_url = 'https://proxy-list.org/english' + page_url.lstrip(".")
        else:
            print(
                f"Extracted {len(proxies)} total proxies from proxy-list.org")
            await spider.set_idle(page)
            return proxies


async def scrape_proxy_daily(
    spider: PyppeteerSpider,
    protocols: List[str] = ['http', 'socks4', 'socks5']):
    page = await spider.get('https://proxy-daily.com/',
                            waitUntil=['load', 'networkidle2'])
    titles_tables = zip([
        await page.evaluate('(ele) => ele.innerText', ele)
        for ele in await page.xpath('//*[@class="centeredProxyList"]')
    ], [
        await page.evaluate('(ele) => ele.innerText', ele) for ele in await
        page.xpath('//*[@class="centeredProxyList freeProxyStyle"]')
    ])
    await spider.set_idle(page)
    proxies = set()
    for protocol in protocols:
        for title, table in titles_tables:
            if protocol.lower() in title.lower():
                proxies.update(re.findall(addr_port_re, table))
    print(f"Extracted {len(proxies)} total proxies from proxy-daily.com")
    return proxies


async def scrape_gatherproxy_com(spider: PyppeteerSpider):
    page = await spider.get('http://www.gatherproxy.com/',
                            waitUntil=['load', 'networkidle2'])
    proxies = set()
    for row_ele in await page.xpath('//*[contains(@class,"proxy ")]'):
        table_row = await page.evaluate('(ele) => ele.innerText', row_ele)
        match = re.search("(" + addr_re + r")\t(\d{2,5})", table_row)
        if match:
            proxies.add(match.group(1) + ":" + match.group(2))
    await spider.set_idle(page)
    print(f"Extracted {len(proxies)} total proxies from gatherproxy.com")
    return proxies
