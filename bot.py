import os
import time
import math
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import requests
import yfinance as yf

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse


# ============================================================
# ⚙️ الإعدادات
# ============================================================

APP_NAME = "نبر وان TITAN v6.1 — Web + Telegram"
VERSION = "6.1.0"

# ------------------------------------------------------------
# 🔑 تم وضع التوكن مباشرة كما طلبت
# ------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "8792351652:AAGAg4g3E9PB29upyMe_lverCMtelPzvtq8"
TELEGRAM_BOT_ID = "8674500253"  # تم إضافة آي دي البوت

TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN)

TELEGRAM_API = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    if TELEGRAM_ENABLED else ""
)


# ============================================================
# 📊 الأزواج
# ============================================================

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "NZD/USD": "NZDUSD=X",
    "AUD/JPY": "AUDJPY=X",

    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "BTC/USD": "BTC-USD",
}


# ============================================================
# ⏱️ الفريمات
# ============================================================

TIMEFRAMES = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "1d": "1d",
}


HIGHER_TF = {
    "1m": "5m",
    "5m": "15m",
    "15m": "1h",
    "30m": "1h",
    "1h": "1d",
    "1d": None,
}


# ============================================================
# 💾 Cache
# ============================================================

CACHE_TTL = {
    "1m": 50,
    "5m": 200,
    "15m": 600,
    "30m": 1200,
    "1h": 2400,
    "1d": 36000,
}

cache: Dict[str, Tuple[float, List[dict]]] = {}
cache_lock = threading.Lock()


# ============================================================
# 🌐 FastAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version=VERSION
)


# ============================================================
# 🛠️ أدوات عامة
# ============================================================

def now_utc():
    return datetime.now(timezone.utc)


def clean_pair(pair: str) -> str:
    return pair.strip().upper()


def round_price(value: float, pair: str) -> float:

    if "JPY" in pair:
        return round(value, 3)

    if pair in ("XAU/USD", "XAG/USD"):
        return round(value, 2)

    if pair == "BTC/USD":
        return round(value, 2)

    return round(value, 5)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ============================================================
# 📥 جلب البيانات من Yahoo Finance
# ============================================================

def fetch_market_data(
    pair: str,
    timeframe: str,
    period: str = "3mo"
) -> List[dict]:

    pair = clean_pair(pair)

    if pair not in PAIRS:
        raise ValueError(f"الزوج غير مدعوم: {pair}")

    if timeframe not in TIMEFRAMES:
        raise ValueError(f"الفريم غير مدعوم: {timeframe}")

    symbol = PAIRS[pair]
    interval = TIMEFRAMES[timeframe]

    cache_key = f"{pair}|{timeframe}"

    ttl = CACHE_TTL.get(timeframe, 300)

    with cache_lock:

        item = cache.get(cache_key)

        if item and time.time() - item[0] < ttl:
            return item[1]

    try:

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period=period,
            interval=interval,
            auto_adjust=False
        )

        if df.empty:
            raise RuntimeError("Yahoo Finance لم يرجع بيانات")

        candles = []

        for idx, row in df.iterrows():

            try:

                volume = float(row.get("Volume", 0) or 0)

                candles.append({
                    "time": idx.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": volume,
                })

            except Exception:
                continue

        # ----------------------------------------------------
        # حذف آخر شمعة لأنها قد تكون غير مكتملة
        # ----------------------------------------------------

        if len(candles) > 1:
            candles = candles[:-1]

        if len(candles) < 60:
            raise RuntimeError(
                f"البيانات غير كافية: {len(candles)} شمعة"
            )

        with cache_lock:
            cache[cache_key] = (
                time.time(),
                candles
            )

        return candles

    except Exception as e:

        raise RuntimeError(
            f"فشل جلب البيانات: {str(e)}"
        )


# ============================================================
# 📈 EMA
# ============================================================

def ema(values, period):

    res = [None] * len(values)

    if len(values) < period:
        return res

    sma_value = sum(values[:period]) / period

    res[period - 1] = sma_value

    multiplier = 2 / (period + 1)

    prev = sma_value

    for i in range(period, len(values)):

        prev = (
            (values[i] - prev) * multiplier
            + prev
        )

        res[i] = prev

    return res


# ============================================================
# 📈 SMA
# ============================================================

def sma(values, period):

    res = [None] * len(values)

    if len(values) < period:
        return res

    for i in range(period - 1, len(values)):

        res[i] = (
            sum(values[i - period + 1:i + 1])
            / period
        )

    return res


# ============================================================
# RSI
# ============================================================

def rsi(values, period=14):

    res = [None] * len(values)

    if len(values) <= period:
        return res

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = values[i] - values[i - 1]

        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:

        res[period] = 100.0

    else:

        rs = avg_gain / avg_loss

        res[period] = (
            100 - 100 / (1 + rs)
        )

    for i in range(period + 1, len(values)):

        avg_gain = (
            avg_gain * (period - 1)
            + gains[i - 1]
        ) / period

        avg_loss = (
            avg_loss * (period - 1)
            + losses[i - 1]
        ) / period

        if avg_loss == 0:

            res[i] = 100.0

        else:

            rs = avg_gain / avg_loss

            res[i] = (
                100 - 100 / (1 + rs)
            )

    return res


# ============================================================
# ATR
# ============================================================

def atr(candles, period=14):

    res = [None] * len(candles)

    if len(candles) <= period:
        return res

    tr = [None] * len(candles)

    for i in range(1, len(candles)):

        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]

        tr[i] = max(
            h - l,
            abs(h - pc),
            abs(l - pc)
        )

    first = [
        x for x in tr[1:period + 1]
        if x is not None
    ]

    if len(first) < period:
        return res

    current = sum(first) / period

    res[period] = current

    for i in range(period + 1, len(candles)):

        current = (
            current * (period - 1)
            + tr[i]
        ) / period

        res[i] = current

    return res


# ============================================================
# ADX + DI
# ============================================================

def adx_indicator(candles, period=14):

    n = len(candles)

    adx_vals = [None] * n
    plus_vals = [None] * n
    minus_vals = [None] * n

    if n < period * 2 + 2:
        return adx_vals, plus_vals, minus_vals

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):

        h = candles[i]["high"]
        l = candles[i]["low"]

        ph = candles[i - 1]["high"]
        pl = candles[i - 1]["low"]

        up = h - ph
        down = pl - l

        plus_dm[i] = (
            up if up > down and up > 0
            else 0.0
        )

        minus_dm[i] = (
            down if down > up and down > 0
            else 0.0
        )

        tr[i] = max(
            h - l,
            abs(h - candles[i - 1]["close"]),
            abs(l - candles[i - 1]["close"])
        )

    sm_tr = sum(tr[1:period + 1])
    sm_plus = sum(plus_dm[1:period + 1])
    sm_minus = sum(minus_dm[1:period + 1])

    dx = [None] * n

    for i in range(period, n):

        if i > period:

            sm_tr = (
                sm_tr
                - sm_tr / period
                + tr[i]
            )

            sm_plus = (
                sm_plus
                - sm_plus / period
                + plus_dm[i]
            )

            sm_minus = (
                sm_minus
                - sm_minus / period
                + minus_dm[i]
            )

        if sm_tr <= 0:
            continue

        plus_di = 100 * sm_plus / sm_tr
        minus_di = 100 * sm_minus / sm_tr

        plus_vals[i] = plus_di
        minus_vals[i] = minus_di

        total = plus_di + minus_di

        if total > 0:

            dx[i] = (
                100
                * abs(plus_di - minus_di)
                / total
            )

    valid_dx = [
        x for x in dx[period:]
        if x is not None
    ]

    if len(valid_dx) < period:
        return adx_vals, plus_vals, minus_vals

    first_adx = sum(valid_dx[:period]) / period

    count = 0
    first_idx = None

    for i in range(period, n):

        if dx[i] is not None:

            count += 1

            if count == period:

                first_idx = i
                break

    if first_idx is None:
        return adx_vals, plus_vals, minus_vals

    adx_vals[first_idx] = first_adx

    current = first_adx

    for i in range(first_idx + 1, n):

        if dx[i] is None:
            continue

        current = (
            current * (period - 1)
            + dx[i]
        ) / period

        adx_vals[i] = current

    return adx_vals, plus_vals, minus_vals


# ============================================================
# MACD
# ============================================================

def macd_indicator(
    values,
    fast=12,
    slow=26,
    sig=9
):

    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)

    macd_line = [None] * len(values)

    for i in range(len(values)):

        if (
            fast_ema[i] is not None
            and slow_ema[i] is not None
        ):

            macd_line[i] = (
                fast_ema[i]
                - slow_ema[i]
            )

    valid = [
        x for x in macd_line
        if x is not None
    ]

    signal_valid = ema(valid, sig)

    signal = [None] * len(values)

    valid_start = len(values) - len(signal_valid)

    for i, value in enumerate(signal_valid):

        idx = valid_start + i

        if 0 <= idx < len(signal):
            signal[idx] = value

    histogram = [None] * len(values)

    for i in range(len(values)):

        if (
            macd_line[i] is not None
            and signal[i] is not None
        ):

            histogram[i] = (
                macd_line[i]
                - signal[i]
            )

    return macd_line, signal, histogram


# ============================================================
# Bollinger Bands
# ============================================================

def bollinger(values, period=20, mul=2.0):

    mid = sma(values, period)

    upper = [None] * len(values)
    lower = [None] * len(values)

    for i in range(period - 1, len(values)):

        window = values[
            i - period + 1:i + 1
        ]

        mean_value = sum(window) / period

        std = math.sqrt(
            sum(
                (x - mean_value) ** 2
                for x in window
            ) / period
        )

        upper[i] = (
            mean_value + mul * std
        )

        lower[i] = (
            mean_value - mul * std
        )

    return mid, upper, lower


# ============================================================
# Stochastic
# ============================================================

def stochastic(candles, kp=14, dp=3):

    kv = [None] * len(candles)
    dv = [None] * len(candles)

    for i in range(len(candles)):

        if i < kp - 1:
            continue

        window = candles[
            i - kp + 1:i + 1
        ]

        high = max(
            x["high"] for x in window
        )

        low = min(
            x["low"] for x in window
        )

        if high == low:

            kv[i] = 50.0

        else:

            kv[i] = (
                (
                    candles[i]["close"]
                    - low
                )
                / (high - low)
            ) * 100

    for i in range(len(candles)):

        if i < kp + dp - 2:
            continue

        window = kv[
            i - dp + 1:i + 1
        ]

        if all(x is not None for x in window):

            dv[i] = sum(window) / dp

    return kv, dv


# ============================================================
# CCI
# ============================================================

def cci(candles, period=20):

    typical = [
        (
            x["high"]
            + x["low"]
            + x["close"]
        ) / 3
        for x in candles
    ]

    result = [None] * len(candles)

    for i in range(period - 1, len(candles)):

        window = typical[
            i - period + 1:i + 1
        ]

        mean_value = sum(window) / period

        deviation = (
            sum(
                abs(x - mean_value)
                for x in window
            )
            / period
        )

        if deviation == 0:

            result[i] = 0

        else:

            result[i] = (
                typical[i] - mean_value
            ) / (
                0.015 * deviation
            )

    return result


# ============================================================
# Williams %R
# ============================================================

def williams_r(candles, period=14):

    result = [None] * len(candles)

    for i in range(period - 1, len(candles)):

        window = candles[
            i - period + 1:i + 1
        ]

        high = max(
            x["high"] for x in window
        )

        low = min(
            x["low"] for x in window
        )

        if high == low:

            result[i] = -50.0

        else:

            result[i] = (
                (
                    high
                    - candles[i]["close"]
                )
                / (high - low)
            ) * -100

    return result


# ============================================================
# SuperTrend
# ============================================================

def supertrend(candles, period=10, multiplier=3.0):

    n = len(candles)

    atr_values = atr(candles, period)

    result = [None] * n
    direction = [None] * n

    upper = [None] * n
    lower = [None] * n

    for i in range(n):

        if atr_values[i] is None:
            continue

        hl2 = (
            candles[i]["high"]
            + candles[i]["low"]
        ) / 2

        basic_upper = (
            hl2
            + multiplier * atr_values[i]
        )

        basic_lower = (
            hl2
            - multiplier * atr_values[i]
        )

        if i == 0:

            upper[i] = basic_upper
            lower[i] = basic_lower
            continue

        upper[i] = (
            basic_upper
            if upper[i - 1] is None
            else min(
                basic_upper,
                upper[i - 1]
            )
            if candles[i - 1]["close"] > upper[i - 1]
            else basic_upper
        )

        lower[i] = (
            basic_lower
            if lower[i - 1] is None
            else max(
                basic_lower,
                lower[i - 1]
            )
            if candles[i - 1]["close"] < lower[i - 1]
            else basic_lower
        )

        if direction[i - 1] is None:

            direction[i] = (
                1
                if candles[i]["close"] >= lower[i]
                else -1
            )

        elif direction[i - 1] == -1:

            direction[i] = (
                1
                if candles[i]["close"] > upper[i]
                else -1
            )

        else:

            direction[i] = (
                -1
                if candles[i]["close"] < lower[i]
                else 1
            )

        result[i] = (
            lower[i]
            if direction[i] == 1
            else upper[i]
        )

    return result, direction


# ============================================================
# Ichimoku
# ============================================================

def ichimoku(candles):

    n = len(candles)

    tenkan = [None] * n
    kijun = [None] * n

    for i in range(n):

        if i >= 8:

            window = candles[i - 8:i + 1]

            high = max(
                x["high"] for x in window
            )

            low = min(
                x["low"] for x in window
            )

            tenkan[i] = (
                high + low
            ) / 2

        if i >= 25:

            window = candles[i - 25:i + 1]

            high = max(
                x["high"] for x in window
            )

            low = min(
                x["low"] for x in window
            )

            kijun[i] = (
                high + low
            ) / 2

    return tenkan, kijun


# ============================================================
# 📊 جميع المؤشرات
# ============================================================

def calculate_indicators(candles):

    close = [
        x["close"] for x in candles
    ]

    e20 = ema(close, 20)
    e50 = ema(close, 50)
    e200 = ema(close, 200)

    r = rsi(close, 14)

    a = atr(candles, 14)

    adx, plus_di, minus_di = (
        adx_indicator(candles, 14)
    )

    macd, macd_signal, macd_hist = (
        macd_indicator(close)
    )

    bb_mid, bb_upper, bb_lower = (
        bollinger(close, 20, 2.0)
    )

    stoch_k, stoch_d = stochastic(candles)

    cc = cci(candles, 20)

    wr = williams_r(candles, 14)

    st_line, st_direction = supertrend(
        candles,
        period=10,
        multiplier=3.0
    )

    tenkan, kijun = ichimoku(candles)

    return {

        "price": close[-1],

        "ema20": e20[-1],
        "ema50": e50[-1],
        "ema200": e200[-1],

        "rsi": r[-1],

        "atr": a[-1],

        "adx": adx[-1],
        "plus_di": plus_di[-1],
        "minus_di": minus_di[-1],

        "macd": macd[-1],
        "macd_signal": macd_signal[-1],
        "macd_hist": macd_hist[-1],

        "bb_mid": bb_mid[-1],
        "bb_upper": bb_upper[-1],
        "bb_lower": bb_lower[-1],

        "stoch_k": stoch_k[-1],
        "stoch_d": stoch_d[-1],

        "cci": cc[-1],

        "williams_r": wr[-1],

        "supertrend_direction":
            st_direction[-1],

        "ichimoku_tenkan": tenkan[-1],
        "ichimoku_kijun": kijun[-1],
    }


# ============================================================
# ⚖️ الأوزان
# ============================================================

WEIGHTS = {

    "trend": 14,
    "ema200": 8,
    "rsi": 8,
    "macd": 10,
    "adx_di": 12,
    "stochastic": 7,
    "bollinger": 6,
    "cci": 6,
    "williams": 5,
    "supertrend": 10,
    "ichimoku": 8,
}


# ============================================================
# 🧠 نظام النقاط
# ============================================================

def score_indicator(ind):

    buy = 0.0
    sell = 0.0

    w = WEIGHTS

    # --------------------------------------------------------
    # EMA Trend
    # --------------------------------------------------------

    if (
        ind["ema20"] is not None
        and ind["ema50"] is not None
    ):

        if ind["ema20"] > ind["ema50"]:

            buy += w["trend"]

        elif ind["ema20"] < ind["ema50"]:

            sell += w["trend"]

    # --------------------------------------------------------
    # EMA200
    # --------------------------------------------------------

    if ind["ema200"] is not None:

        if ind["price"] > ind["ema200"]:

            buy += w["ema200"]

        elif ind["price"] < ind["ema200"]:

            sell += w["ema200"]

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    r = ind["rsi"]

    if r is not None:

        if 50 < r < 70:

            buy += w["rsi"]

        elif 30 < r < 50:

            sell += w["rsi"]

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        ind["macd"] is not None
        and ind["macd_signal"] is not None
    ):

        if ind["macd"] > ind["macd_signal"]:

            buy += w["macd"]

        elif ind["macd"] < ind["macd_signal"]:

            sell += w["macd"]

    # --------------------------------------------------------
    # ADX + DI
    # --------------------------------------------------------

    if (
        ind["adx"] is not None
        and ind["plus_di"] is not None
        and ind["minus_di"] is not None
    ):

        if ind["adx"] >= 20:

            if ind["plus_di"] > ind["minus_di"]:

                buy += w["adx_di"]

            elif ind["minus_di"] > ind["plus_di"]:

                sell += w["adx_di"]

    # --------------------------------------------------------
    # Stochastic
    # --------------------------------------------------------

    if (
        ind["stoch_k"] is not None
        and ind["stoch_d"] is not None
    ):

        if (
            ind["stoch_k"] > ind["stoch_d"]
            and ind["stoch_k"] < 80
        ):

            buy += w["stochastic"]

        elif (
            ind["stoch_k"] < ind["stoch_d"]
            and ind["stoch_k"] > 20
        ):

            sell += w["stochastic"]

    # --------------------------------------------------------
    # Bollinger
    # --------------------------------------------------------

    if (
        ind["bb_upper"] is not None
        and ind["bb_lower"] is not None
    ):

        price = ind["price"]

        if price > ind["bb_mid"]:

            buy += w["bollinger"]

        elif price < ind["bb_mid"]:

            sell += w["bollinger"]

    # --------------------------------------------------------
    # CCI
    # --------------------------------------------------------

    if ind["cci"] is not None:

        if ind["cci"] > 0:

            buy += w["cci"]

        elif ind["cci"] < 0:

            sell += w["cci"]

    # --------------------------------------------------------
    # Williams
    # --------------------------------------------------------

    if ind["williams_r"] is not None:

        if ind["williams_r"] > -50:

            buy += w["williams"]

        elif ind["williams_r"] < -50:

            sell += w["williams"]

    # --------------------------------------------------------
    # SuperTrend
    # --------------------------------------------------------

    if ind["supertrend_direction"] is not None:

        if ind["supertrend_direction"] == 1:

            buy += w["supertrend"]

        elif ind["supertrend_direction"] == -1:

            sell += w["supertrend"]

    # --------------------------------------------------------
    # Ichimoku
    # --------------------------------------------------------

    if (
        ind["ichimoku_tenkan"] is not None
        and ind["ichimoku_kijun"] is not None
    ):

        if (
            ind["price"] > ind["ichimoku_tenkan"]
            and ind["price"] > ind["ichimoku_kijun"]
        ):

            buy += w["ichimoku"]

        elif (
            ind["price"] < ind["ichimoku_tenkan"]
            and ind["price"] < ind["ichimoku_kijun"]
        ):

            sell += w["ichimoku"]

    # --------------------------------------------------------
    # النتيجة
    # --------------------------------------------------------

    total = sum(w.values())

    buy_score = clamp(
        buy / total * 100,
        0,
        100
    )

    sell_score = clamp(
        sell / total * 100,
        0,
        100
    )

    difference = abs(
        buy_score - sell_score
    )

    if (
        buy_score > sell_score
        and buy_score >= 55
        and difference >= 8
    ):

        signal = "شراء"
        confidence = buy_score

    elif (
        sell_score > buy_score
        and sell_score >= 55
        and difference >= 8
    ):

        signal = "بيع"
        confidence = sell_score

    else:

        signal = "انتظار"
        confidence = 50.0

    return {

        "buy": round(buy_score, 1),

        "sell": round(sell_score, 1),

        "confidence": round(
            confidence,
            1
        ),

        "signal": signal,

        "direction": (
            "صاعد"
            if signal == "شراء"
            else "هابط"
            if signal == "بيع"
            else "محايد"
        )
    }


# ============================================================
# 🔎 تحليل فريم
# ============================================================

def analyze_timeframe(pair, tf):

    candles = fetch_market_data(
        pair,
        tf
    )

    if len(candles) < 60:
        raise RuntimeError(
            "بيانات غير كافية"
        )

    indicators = calculate_indicators(
        candles
    )

    score = score_indicator(
        indicators
    )

    return {
        "candles": candles,
        "indicators": indicators,
        "score": score
    }


# ============================================================
# 🔄 MTF
# ============================================================

def mtf_confirm(
    pair,
    main_tf,
    main_signal
):

    higher = HIGHER_TF.get(main_tf)

    if not higher:

        return {
            "timeframe": None,
            "signal": "غير متاح",
            "confirmed": False
        }

    try:

        result = analyze_timeframe(
            pair,
            higher
        )

        higher_signal = (
            result["score"]["signal"]
        )

        confirmed = (
            main_signal != "انتظار"
            and higher_signal == main_signal
        )

        return {
            "timeframe": higher,
            "signal": higher_signal,
            "confirmed": confirmed
        }

    except Exception as e:

        logging.warning(
            "MTF error: %s",
            e
        )

        return {
            "timeframe": higher,
            "signal": "تعذر",
            "confirmed": False
        }


# ============================================================
# 🎯 SL / TP
# ============================================================

def calculate_levels(
    pair,
    price,
    atr_value,
    signal,
    capital,
    risk_pct
):

    if not atr_value or atr_value <= 0:

        return {
            "stop_loss": 0,
            "tp1": 0,
            "tp2": 0,
            "tp3": 0,
            "risk_amount": 0,
            "position_units": 0
        }

    risk_pct = clamp(
        risk_pct,
        0.1,
        10
    )

    risk_amount = (
        capital
        * risk_pct
        / 100
    )

    sl_distance = atr_value * 1.5

    if signal == "شراء":

        stop = price - sl_distance

        tp1 = price + atr_value * 1.5
        tp2 = price + atr_value * 3
        tp3 = price + atr_value * 4.5

    elif signal == "بيع":

        stop = price + sl_distance

        tp1 = price - atr_value * 1.5
        tp2 = price - atr_value * 3
        tp3 = price - atr_value * 4.5

    else:

        return {
            "stop_loss": 0,
            "tp1": 0,
            "tp2": 0,
            "tp3": 0,
            "risk_amount": round(
                risk_amount,
                2
            ),
            "position_units": 0
        }

    position_units = (
        risk_amount / sl_distance
        if sl_distance > 0
        else 0
    )

    return {

        "stop_loss": round_price(
            stop,
            pair
        ),

        "tp1": round_price(
            tp1,
            pair
        ),

        "tp2": round_price(
            tp2,
            pair
        ),

        "tp3": round_price(
            tp3,
            pair
        ),

        "risk_amount": round(
            risk_amount,
            2
        ),

        "position_units": round(
            position_units,
            2
        )
    }


# ============================================================
# 🧠 التحليل الكامل
# ============================================================

def full_analysis(
    pair,
    tf="1h",
    capital=1000.0,
    risk_pct=2.0
):

    pair = clean_pair(pair)

    if pair not in PAIRS:

        raise ValueError(
            f"الزوج غير موجود: {pair}"
        )

    if tf not in TIMEFRAMES:

        raise ValueError(
            f"الفريم غير موجود: {tf}"
        )

    main = analyze_timeframe(
        pair,
        tf
    )

    indicators = main["indicators"]
    score = main["score"]

    mtf = mtf_confirm(
        pair,
        tf,
        score["signal"]
    )

    final_signal = score["signal"]
    final_confidence = score["confidence"]

    if score["signal"] != "انتظار":

        if mtf["confirmed"]:

            final_confidence = clamp(
                final_confidence + 8,
                0,
                100
            )

        elif mtf["signal"] not in (
            "غير متاح",
            "تعذر"
        ):

            final_signal = "انتظار"

            final_confidence = clamp(
                final_confidence - 12,
                0,
                100
            )

    final_direction = (
        "صاعد"
        if final_signal == "شراء"
        else "هابط"
        if final_signal == "بيع"
        else "محايد"
    )

    levels = calculate_levels(
        pair,
        indicators["price"],
        indicators["atr"],
        final_signal,
        capital,
        risk_pct
    )

    trend_strength = clamp(
        (indicators["adx"] or 0) * 2,
        0,
        100
    )

    return {

        "pair": pair,

        "timeframe": tf,

        "price": round_price(
            indicators["price"],
            pair
        ),

        "signal": final_signal,

        "direction": final_direction,

        "ai_score": round(
            max(
                score["buy"],
                score["sell"]
            ),
            1
        ),

        "confidence": round(
            final_confidence,
            1
        ),

        "trend_strength": round(
            trend_strength,
            1
        ),

        "buy_score": score["buy"],

        "sell_score": score["sell"],

        "rsi": round(
            indicators["rsi"] or 0,
            2
        ),

        "adx": round(
            indicators["adx"] or 0,
            2
        ),

        "plus_di": round(
            indicators["plus_di"] or 0,
            2
        ),

        "minus_di": round(
            indicators["minus_di"] or 0,
            2
        ),

        "atr": round(
            indicators["atr"] or 0,
            6
        ),

        "ema20": round(
            indicators["ema20"] or 0,
            6
        ),

        "ema50": round(
            indicators["ema50"] or 0,
            6
        ),

        "ema200": round(
            indicators["ema200"] or 0,
            6
        ),

        "macd": round(
            indicators["macd"] or 0,
            8
        ),

        "stoch_k": round(
            indicators["stoch_k"] or 0,
            2
        ),

        "cci": round(
            indicators["cci"] or 0,
            2
        ),

        "williams_r": round(
            indicators["williams_r"] or 0,
            2
        ),

        "supertrend_direction":
            indicators[
                "supertrend_direction"
            ],

        "stop_loss":
            levels["stop_loss"],

        "tp1":
            levels["tp1"],

        "tp2":
            levels["tp2"],

        "tp3":
            levels["tp3"],

        "risk_percent":
            risk_pct,

        "risk_amount":
            levels["risk_amount"],

        "position_units":
            levels["position_units"],

        "main_signal":
            score["signal"],

        "higher_timeframe":
            mtf["timeframe"],

        "higher_signal":
            mtf["signal"],

        "mtf_confirmed":
            mtf["confirmed"],

        "updated_at":
            now_utc().strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
    }


# ============================================================
# 🌐 API
# ============================================================

@app.get("/health")
def health_check():

    return {

        "status": "ok",

        "app": APP_NAME,

        "version": VERSION,

        "pairs": len(PAIRS),

        "timeframes":
            list(TIMEFRAMES.keys()),

        "telegram":
            TELEGRAM_ENABLED,
            
        "bot_id": TELEGRAM_BOT_ID
    }


@app.get("/تحليل")
def analysis_endpoint(

    زوج: str = Query(
        "EUR/USD"
    ),

    فريم: str = Query(
        "1h"
    ),

    رأس_المال: float = Query(
        1000.0,
        ge=1
    ),

    المخاطر: float = Query(
        2.0,
        ge=0.1,
        le=10
    )
):

    try:

        return full_analysis(
            زوج,
            فريم,
            رأس_المال,
            المخاطر
        )

    except ValueError as e:

        raise HTTPException(
            400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            500,
            detail=f"خطأ: {e}"
        )


# ============================================================
# 📱 Telegram
# ============================================================

def telegram_request(
    method,
    payload=None
):

    if not TELEGRAM_ENABLED:
        return None

    try:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload or {},
            timeout=30
        )

        return response.json()

    except Exception as e:

        logging.error(
            "Telegram request error: %s",
            e
        )

        return None


def telegram_send(
    chat_id,
    text
):

    return telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
    )


def format_analysis(d):

    signal = d["signal"]

    if signal == "شراء":
        icon = "🟢"
    elif signal == "بيع":
        icon = "🔴"
    else:
        icon = "🟡"

    mtf = (
        "✅ مؤكد"
        if d["mtf_confirmed"]
        else "❌ غير مؤكد"
    )

    text = f"""
🤖 <b>نبر وان TITAN v6.1</b>

━━━━━━━━━━━━━━

📊 <b>الزوج:</b> {d["pair"]}
⏱ <b>الفريم:</b> {d["timeframe"]}

{icon} <b>الإشارة: {signal}</b>

💰 السعر: <b>{d["price"]}</b>

📈 الاتجاه: {d["direction"]}

🎯 الثقة: <b>{d["confidence"]}%</b>
📊 قوة الاتجاه: {d["trend_strength"]}%

━━━━━━━━━━━━━━

📌 <b>المؤشرات</b>

RSI: {d["rsi"]}
ADX: {d["adx"]}

+DI: {d["plus_di"]}
-DI: {d["minus_di"]}

EMA20: {d["ema20"]}
EMA50: {d["ema50"]}
EMA200: {d["ema200"]}

MACD: {d["macd"]}

Stochastic: {d["stoch_k"]}
CCI: {d["cci"]}
Williams %R: {d["williams_r"]}

━━━━━━━━━━━━━━

🔄 <b>MTF</b>

الفريم الأعلى:
{d["higher_timeframe"]}

الإشارة:
{d["higher_signal"]}

التأكيد:
{mtf}

━━━━━━━━━━━━━━
"""

    if signal != "انتظار":

        text += f"""
🎯 <b>مستويات الصفقة</b>

🛑 Stop Loss:
<b>{d["stop_loss"]}</b>

🎯 TP1:
<b>{d["tp1"]}</b>

🎯 TP2:
<b>{d["tp2"]}</b>

🎯 TP3:
<b>{d["tp3"]}</b>

━━━━━━━━━━━━━━

💵 المخاطرة:
{d["risk_percent"]}%

💰 مبلغ المخاطرة:
{d["risk_amount"]}

⚠️ حجم الوحدات:
{d["position_units"]}

"""

    text += f"""
━━━━━━━━━━━━━━

🕐 آخر تحديث:
{d["updated_at"]}

⚠️ <b>تنبيه:</b>
هذه إشارة تحليلية وليست ضمانًا للربح.
بيانات Yahoo Finance قد تختلف عن سعر وسيط التداول.
"""

    return text


# ============================================================
# 📋 Telegram Help
# ============================================================

def telegram_help():

    return """
🤖 <b>نبر وان TITAN v6.1</b>

أوامر البوت:

/start
بدء البوت

/help
عرض المساعدة

/الأزواج
عرض الأزواج

/الفريمات
عرض الفريمات

/تحليل
تحليل EUR/USD على 1h

أو:

/تحليل EUR/USD 5m

أو:

/تحليل GBP/USD 15m

━━━━━━━━━━━━━━

مثال:

<code>/تحليل EUR/USD 5m</code>

ثم انتظر نتيجة التحليل.
"""


def telegram_pairs():

    lines = [
        "📊 <b>الأزواج المتاحة</b>",
        ""
    ]

    for pair in PAIRS:

        lines.append(
            f"• {pair}"
        )

    lines.append("")
    lines.append(
        "مثال: <code>/تحليل EUR/USD 5m</code>"
    )

    return "\n".join(lines)


def telegram_timeframes():

    return """
⏱ <b>الفريمات المتاحة</b>

• 1m
• 5m
• 15m
• 30m
• 1h
• 1d

مثال:

<code>/تحليل EUR/USD 5m</code>
"""


# ============================================================
# 🧠 معالجة أوامر Telegram
# ============================================================

def handle_telegram_message(message):

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    if not chat_id:
        return

    text = (
        message.get("text", "")
        .strip()
    )

    if not text:
        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if text.startswith("/start"):

        telegram_send(
            chat_id,
            f"""
🤖 <b>مرحبًا بك في نبر وان TITAN</b>
🆔 معرف البوت: <code>{TELEGRAM_BOT_ID}</code>

نسخة Web + Telegram

━━━━━━━━━━━━━━

📊 لتحليل زوج:

<code>/تحليل EUR/USD 5m</code>

📋 الأزواج:

<code>/الأزواج</code>

⏱ الفريمات:

<code>/الفريمات</code>

❓ المساعدة:

<code>/help</code>

━━━━━━━━━━━━━━

⚠️ البوت للتحليل الفني فقط.
"""
        )

        return

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if text.startswith("/help"):

        telegram_send(
            chat_id,
            telegram_help()
        )

        return

    # --------------------------------------------------------
    # PAIRS
    # --------------------------------------------------------

    if text.startswith("/الأزواج"):

        telegram_send(
            chat_id,
            telegram_pairs()
        )

        return

    # --------------------------------------------------------
    # TIMEFRAMES
    # --------------------------------------------------------

    if text.startswith("/الفريمات"):

        telegram_send(
            chat_id,
            telegram_timeframes()
        )

        return

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    if text.startswith("/تحليل"):

        parts = text.split()

        if len(parts) < 2:

            telegram_send(
                chat_id,
                """
❌ طريقة الاستخدام:

<code>/تحليل EUR/USD 5m</code>

مثال:

<code>/تحليل GBP/USD 15m</code>
"""
            )

            return

        pair = parts[1].upper()

        tf = (
            parts[2]
            if len(parts) >= 3
            else "1h"
        )

        if pair not in PAIRS:

            telegram_send(
                chat_id,
                f"""
❌ الزوج غير موجود:

<b>{pair}</b>

استخدم:

/الأزواج
"""
            )

            return

        if tf not in TIMEFRAMES:

            telegram_send(
                chat_id,
                f"""
❌ الفريم غير صحيح:

<b>{tf}</b>

استخدم:

/الفريمات
"""
            )

            return

        telegram_send(
            chat_id,
            "⏳ جاري جلب البيانات وتحليل السوق..."
        )

        try:

            result = full_
