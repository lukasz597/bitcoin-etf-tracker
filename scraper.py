import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


START_URL = "https://www.justetf.com/en/how-to/invest-in-bitcoin.html"


def extract_isins(html):
    soup = BeautifulSoup(html, "html.parser")
    isins = set()

    for a in soup.find_all("a", href=True):
        if "etf-profile.html?isin=" in a["href"]:
            match = re.search(r"isin=([A-Z0-9]+)", a["href"])
            if match:
                isins.add(match.group(1))

    return list(isins)


def parse_number(s):
    s = s.strip()

    # przypadek EU / US mieszany
    # 1,069.23 → 1069.23
    # 1.069,23 → 1069.23

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # EU format: 1.069,23
            s = s.replace(".", "").replace(",", ".")
        else:
            # US format: 1,069.23
            s = s.replace(",", "")
    else:
        # tylko przecinki → tysiące
        if "," in s:
            s = s.replace(",", "")
        # tylko kropki → mogą być tysiące lub decimal
        # heurystyka: jeśli 3 cyfry po kropce → tysiące
        if "." in s:
            parts = s.split(".")
            if len(parts) > 2 or len(parts[-1]) == 3:
                s = s.replace(".", "")

    return float(s)


def extract_aum(page):
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    for text in soup.stripped_strings:
        t = text.lower()

        if ("bn" in t or "m" in t) and any(c.isdigit() for c in t):

            match = re.search(r'([\d.,]+)\s*(bn|m)', t, re.I)
            if match:
                number = parse_number(match.group(1))
                unit = match.group(2).lower()

                # konwersja do mln EUR
                return number * 1000 if unit == "bn" else number

    return None


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.set_default_timeout(60000)

    # 1. start
    page.goto(START_URL, wait_until="domcontentloaded")

    html = page.content()
    isins = extract_isins(html)

    # print(f"Znaleziono ISIN: {len(isins)}")

    results = []

    # 2. ETF profile
    for isin in isins:
        url = f"https://www.justetf.com/en/etf-profile.html?isin={isin}"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            print(f"Timeout: {isin}")
            continue

        name = page.title()
        aum = extract_aum(page)

        if aum:
            results.append({
                "isin": isin,
                "name": name,
                "aum_million": aum
            })

    browser.close()


# 3. sortowanie
results = [r for r in results if r["aum_million"] is not None]
results.sort(key=lambda x: x["aum_million"], reverse=True)

# if results:
#     top2 = results[:2]

#     print("\n🔥 2 NAJWIĘKSZE BITCOIN ETF/ETN:\n")

#     for i, etf in enumerate(top2, start=1):
#         print(f"{i}. {etf['name']}")
#         print(f"   ISIN: {etf['isin']}")
#         print(f"   AUM (mln EUR): {etf['aum_million']:.2f}")
#         print()
# else:
#     print("Brak danych")

if results:
    top2 = results[:2]

    html = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>2 największe Bitcoin ETF/ETN</title>
</head>
<body>
    <h1>🔥 2 największe Bitcoin ETF/ETN</h1>
"""

    for i, etf in enumerate(top2, start=1):
        html += f"""
    <h2>{i}. {etf['name']}</h2>
    <ul>
        <li><strong>ISIN:</strong> {etf['isin']}</li>
        <li><strong>AUM (mln EUR):</strong> {etf['aum_million']:.2f}</li>
    </ul>
"""

    html += """
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Zapisano plik index.html")
else:
    print("Brak danych")