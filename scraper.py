import yfinance as yf
import pandas as pd
from datetime import datetime

TICKER = "WBTC.PA"


def get_data():
    data = yf.download(
        TICKER,
        start="2026-01-08",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    # zabezpieczenie MultiIndex (czasem yfinance to robi)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    return data


def add_sma(data):
    data = data.copy()
    
    # tylko zamkniecia
    close = data["Close"]

    # min_periods=1 pozwala na liczenie SMA z dostepnych dni, jesli jest ich mniej niz 20 lub 200
    data["SMA20"] = close.rolling(20, min_periods=1).mean()
    data["SMA200"] = close.rolling(200, min_periods=1).mean()

    return data


def generate_signal(close, sma20, sma200):
    
    if close < sma20 and close < sma200:
        return "BUY"
    elif close > sma20 and close > sma200:
        return "SELL"
    else:
        return "BUY/SELL"
    

def save_html(date, close, sma20, sma200, signal):
    html = f"""
    <html>
    <head>
        <title>WBTC Signal</title>
        <style>
            body {{ font-family: Arial; margin: 20px; }}
            .box {{ padding: 20px; border: 1px solid #ccc; width: 300px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>WBTC (GB00BJYDH287)</h2>

            <p><b>Last CLOSED session:</b> {date}</p>
            <p><b>Close:</b> {close:.2f} EUR</p>
            <p><b>SMA20:</b> {sma20:.2f}</p>
            <p><b>SMA200:</b> {sma200:.2f}</p>

            <h3>Signal: {signal}</h3>

            <p><i>Generated: {datetime.now()}</i></p>
        </div>
    </body>
    </html>
    """

    with open("signal.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    data = get_data()
    
    if data.empty:
        print("Błąd: Brak danych z yfinance.")
        return

    # KLUCZ: usuwamy dzisiejszy dzien (niezamknieta swieca)
    today = pd.Timestamp.today().normalize()
    data = data[data.index < today]

    if data.empty:
        print("Błąd: Brak danych po odrzuceniu dzisiejszej sesji.")
        return

    data = add_sma(data)

    # pd.set_option("display.max_rows", None)
    # pd.set_option("display.max_columns", None)
    # pd.set_option("display.width", None)
    # pd.set_option("display.max_colwidth", None)
    # data = data.dropna()
    # last_200 = data["Close"].tail(200)

    # print(last_200)

    last = data.iloc[-1]

    date = last.name.date()
    close = float(last["Close"])
    sma20 = float(last["SMA20"])
    sma200 = float(last["SMA200"])

    signal = generate_signal(close, sma20, sma200)

    save_html(date, close, sma20, sma200, signal)

    print(f"OK -> signal.html (REAL closed: {date})")


if __name__ == "__main__":
    main()
