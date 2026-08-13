from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import requests
import threading
import logging
import time

app = FastAPI(
    title="نبر وان — منصة التداول بالذكاء الاصطناعي",
    description="بيانات حقيقية · تحليل فني معياري كامل · تليجرام بوت · تحديث مباشر",
    version="4.1.0-Telegram",
    docs_url="/لوحة-التحكم",
    redoc_url="/تفاصيل"
)

# ============================================================
# 🤖 إعدادات تليجرام
# ============================================================
TELEGRAM_BOT_TOKEN = "8829397342:AAFvJVy9rElo8gk1Wb76TtpjCJlGDjaDDY0"
TELEGRAM_BOT_ID = "8674500253"
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN)
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_ENABLED else ""

def telegram_request(method, payload=None):
    if not TELEGRAM_ENABLED:
        return None
    try:
        resp = requests.post(f"{TELEGRAM_API}/{method}", json=payload or {}, timeout=30)
        return resp.json()
    except Exception as e:
        logging.error("Telegram error: %s", e)
        return None

def telegram_send(chat_id, text):
    return telegram_request("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def telegram_polling():
    if not TELEGRAM_ENABLED:
        return
    logging.info("Telegram bot started...")
    offset = 0
    while True:
        try:
            upd = telegram_request("getUpdates", {"offset": offset, "timeout": 25})
            if not upd or not upd.get("ok"):
                time.sleep(3)
                continue
            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message")
                if not msg or "text" not in msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = msg["text"].strip()
                if text == "/start":
                    telegram_send(chat_id, f"""
🤖 <b>مرحباً بك في نبر وان TITAN v4.1</b>
🆔 معرف البوت: <code>{TELEGRAM_BOT_ID}</code>

أوامر البوت:
/تحليل — تحليل السوق الحالي (XAUUSD افتراضي)
/تحليل BTCUSDT — تحليل بيتكوين
/تحليل XAUUSD — تحليل الذهب
/help — عرض المساعدة
                    """)
                elif text == "/help":
                    telegram_send(chat_id, """
أوامر البوت المتاحة:
/start — بدء استخدام البوت
/تحليل [الزوج] — جلب بيانات السوق وتحليلها بمؤشرات كاملة
/help — عرض هذه المساعدة
                    """)
                elif text.startswith("/تحليل"):
                    try:
                        parts = text.split()
                        symbol = parts[1].upper() if len(parts) > 1 else "XAUUSD"
                        if symbol not in رموز_Binance:
                            symbol = "XAUUSD"
                        result = تحليل_السوق(symbol, 1000, "متوازن")
                        if not result:
                            telegram_send(chat_id, "❌ فشل جلب البيانات أو لا توجد إشارة واضحة حالياً.")
                            continue
                        msg_text = f"""
📊 <b>تحليل السوق — {result['الزوج_المالي']}</b>
⏰ التاريخ: {result['التاريخ_والوقت']}

💰 السعر الحالي: {result['التحليل']['سعر_السوق_الحالي']}
📈 الاتجاه: {result['التحليل']['اتجاه_السوق']}
💪 قوة الترند (ADX): {result['التحليل']['قوة_الترند_ADX']}
🧠 ثقة التحليل: {result['التحليل']['نسبة_إجماع_المؤشرات']}

🎯 الإشارة النهائية: <b>{result['الإشارة']}</b>
💰 سعر الدخول: {result['سعر_الدخول']}
🔒 وقف الخسارة: {result['وقف_الخسارة']['السعر']} (خسارة محتملة: {result['وقف_الخسارة']['الخسارة_المحتملة']}$)
🎯 الهدف الأول: {result['الأهداف']['الهدف_الأول']['السعر']} (ربح: {result['الأهداف']['الهدف_الأول']['الربح']}$)
🎯 الهدف الثاني: {result['الأهداف']['الهدف_الثاني']['السعر']} (ربح: {result['الأهداف']['الهدف_الثاني']['الربح']}$)
🎯 الهدف الثالث: {result['الأهداف']['الهدف_الثالث']['السعر']} (ربح: {result['الأهداف']['الهدف_الثالث']['الربح']}$)

📊 نسبة الربح/الخسارة: {result['نسبة_RR']}
📋 التفاصيل: {result['التفاصيل']}
                        """
                        telegram_send(chat_id, msg_text)
                    except Exception as e:
                        telegram_send(chat_id, f"❌ خطأ أثناء التحليل: {str(e)}")
                else:
                    telegram_send(chat_id, "❓ أمر غير معروف. استخدم /help لعرض الأوامر المتاحة.")
        except Exception as e:
            logging.error("Polling error: %s", e)
            time.sleep(5)

def start_telegram_bot():
    if TELEGRAM_ENABLED:
        telegram_request("deleteWebhook")
        t = threading.Thread(target=telegram_polling, daemon=True)
        t.start()

# ============================================================
# 📦 البيانات والإعدادات
# ============================================================
class بيانات_الصفقة(BaseModel):
    الزوج_المالي: str = "XAUUSD"
    مبلغ_الاستثمار: float = 1000
    مستوى_المخاطر: str = "متوازن"
    الإطار_الزمني: str = "5د"

النتائج = []

رموز_Binance = {
    "XAUUSD": "PAXGUSDT",
    "BTCUSDT": "BTCUSDT",
    "BTCUSD": "BTCUSDT",
    "ETHUSDT": "ETHUSDT",
    "BNBUSDT": "BNBUSDT",
    "SOLUSDT": "SOLUSDT",
    "PAXGUSDT": "PAXGUSDT",
}

الأطر_الزمنية = {
    "1د":  {"interval": "1m",  "label": "1 دقيقة",  "limit": 300},
    "5د":  {"interval": "5m",  "label": "5 دقائق", "limit": 300},
    "15د": {"interval": "15m", "label": "15 دقيقة", "limit": 300},
    "30د": {"interval": "30m", "label": "30 دقيقة", "limit": 300},
    "1ساعة": {"interval": "1h", "label": "ساعة",     "limit": 300},
}

# ============================================================
# 📡 جلب البيانات من Binance
# ============================================================
def جلب_شموع_السعر(الزوج, إطار_زمني="5د"):
    رمز = رموز_Binance.get(الزوج.upper().strip(), "PAXGUSDT")
    فترة = الأطر_الزمنية[إطار_زمني]["interval"]
    try:
        res = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": رمز, "interval": فترة, "limit": 300},
            timeout=15
        )
        res.raise_for_status()
        بيانات = res.json()
        if not بيانات or len(بيانات) < 250:
            return None
        الإغلاقات = [float(شمعة[4]) for شمعة in بيانات]
        عالي = [float(شمعة[2]) for شمعة in بيانات]
        منخفض = [float(شمعة[3]) for شمعة in بيانات]
        حجم_الشموع = [float(شمعة[5]) for شمعة in بيانات]
        أعلى_سعر = max(عالي)
        أدنى_سعر = min(منخفض)
        السعر_الحالي = الإغلاقات[-1]
        حجم_التداول = sum(حجم_الشموع[-20:])
        سعر_إغلاق_سابق = الإغلاقات[-2] if len(الإغلاقات) >= 2 else السعر_الحالي
        return الإغلاقات, السعر_الحالي, أعلى_سعر, أدنى_سعر, حجم_التداول, عالي, منخفض, حجم_الشموع, سعر_إغلاق_سابق
    except Exception as e:
        logging.error("Error fetching data: %s", e)
        return None

# ============================================================
# 📐 المؤشرات الفنية
# ============================================================
def حساب_EMA(الإغلاقات, الفترة):
    k = 2 / (الفترة + 1)
    ema = الإغلاقات[0]
    for سعر in الإغلاقات[1:]:
        ema = سعر * k + ema * (1 - k)
    return ema

def حساب_EMA_لسلسلة(القيم, الفترة):
    if not القيم:
        return 0
    k = 2 / (الفترة + 1)
    ema = القيم[0]
    for v in القيم[1:]:
        ema = v * k + ema * (1 - k)
    return ema

def حساب_RSI_Wilder(الإغلاقات, فترة=14):
    if len(الإغلاقات) < فترة + 1:
        return 50.0
    أرباح, خسائر = [], []
    for i in range(1, len(الإغلاقات)):
        فرق = الإغلاقات[i] - الإغلاقات[i-1]
        أرباح.append(max(فرق, 0.0))
        خسائر.append(max(-فرق, 0.0))
    متوسط_ربح = sum(أرباح[:فترة]) / فترة
    متوسط_خسارة = sum(خسائر[:فترة]) / فترة
    for i in range(fترة, len(أرباح)):
        متوسط_ربح = (متوسط_ربح * (فترة - 1) + أرباح[i]) / فترة
        متوسط_خسارة = (متوسط_خسارة * (فترة - 1) + خسائر[i]) / فترة
    if متوسط_خسارة == 0:
        return 100.0 if متوسط_ربح > 0 else 50.0
    rs = متوسط_ربح / متوسط_خسارة
    return round(100 - (100 / (1 + rs)), 1)

def حساب_ATR(عالي, منخفض, إغلاق, فترة=14):
    tr_values = []
    for i in range(1, len(إغلاق)):
        hl = عالي[i] - منخفض[i]
        hc = abs(عالي[i] - إغلاق[i-1])
        lc = abs(منخفض[i] - إغلاق[i-1])
        tr_values.append(max(hl, hc, lc))
    if len(tr_values) < فترة:
        return sum(tr_values) / len(tr_values) if tr_values else 0
    atr = sum(tr_values[:فترة]) / فترة
    for tr in tr_values[فترة:]:
        atr = (atr * (فترة - 1) + tr) / فترة
    return atr

def حساب_ADX_كامل(عالي, منخفض, إغلاق, فترة=14):
    if len(عالي) < فترة * 2:
        return 25.0
    up = [عالي[i] - عالي[i-1] for i in range(1, len(عالي))]
    down = [منخفض[i-1] - منخفض[i] for i in range(1, len(منخفض))]
    pdm = [up[i] if up[i] > down[i] and up[i] > 0 else 0 for i in range(len(up))]
    ndm = [down[i] if down[i] > up[i] and down[i] > 0 else 0 for i in range(len(down))]
    tr = [max(عالي[i]-منخفض[i], abs(عالي[i]-إغلاق[i-1]), abs(منخفض[i]-إغلاق[i-1])) for i in range(1, len(عالي))]
    def wilder_smooth_series(arr, p):
        smoothed = [0.0] * len(arr)
        smoothed[0] = sum(arr[:p]) / p
        for i in range(1, len(arr)):
            smoothed[i] = (smoothed[i-1] * (p - 1) + arr[i-1]) / p
        return smoothed
    atr_series = wilder_smooth_series(tr, فترة)
    pdi_series = [100 * wilder_smooth_series(pdm, فترة)[i] / atr_series[i] if atr_series[i] > 0 else 0 for i in range(len(atr_series))]
    ndi_series = [100 * wilder_smooth_series(ndm, فترة)[i] / atr_series[i] if atr_series[i] > 0 else 0 for i in range(len(atr_series))]
    dx_series = [100 * abs(pdi_series[i] - ndi_series[i]) / (pdi_series[i] + ndi_series[i]) if (pdi_series[i] + ndi_series[i]) > 0 else 0 for i in range(len(pdi_series))]
    adx_series = wilder_smooth_series(dx_series, فترة)
    return round(adx_series[-1], 1)

def حساب_MACD_كامل_حقيقي(الإغلاقات, سريع=12, بطيء=26, سيجنال=9):
    ema_s = []
    k_s = 2 / (سريع + 1)
    e = الإغلاقات[0]
    for سعر in الإغلاقات:
        e = سعر * k_s + e * (1 - k_s)
        ema_s.append(e)
    ema_l = []
    k_l = 2 / (بطيء + 1)
    e = الإغلاقات[0]
    for سعر in الإغلاقات:
        e = سعر * k_l + e * (1 - k_l)
        ema_l.append(e)
    macd_series = [ema_s[i] - ema_l[i] for i in range(len(ema_s))]
    signal_line = حساب_EMA_لسلسلة(macd_series, سيجنال)
    macd_line = macd_series[-1]
    histogram = macd_line - signal_line
    return round(macd_line, 5), round(signal_line, 5), round(histogram, 5)

def حساب_Bollinger(الإغلاقات, فترة=20, انحراف=2):
    وسط = sum(الإغلاقات[-فترة:]) / فترة
    تباين = sum((x - وسط)**2 for x in الإغلاقات[-فترة:]) / فترة
    انحراف_معياري = تباين ** 0.5
    return round(وسط + انحراف * انحراف_معياري, 5), round(وسط, 5), round(وسط - انحراف * انحراف_معياري, 5)

def حساب_Stochastic(عالي, منخفض, إغلاق, فترة=14):
    if len(إغلاق) < فترة:
        return 50.0
    ll = min(منخفض[-فترة:])
    hh = max(عالي[-فترة:])
    if hh == ll:
        return 50.0
    return round(100 * (إغلاق[-1] - ll) / (hh - ll), 1)

# ============================================================
# 🔍 فلتر MTF
# ============================================================
def جلب_إطار_أعلى_مصحح(الزوج, الإطار_الحالي):
    ترتيب = ["1د", "5د", "15د", "30د", "1ساعة"]
    if الإطار_الحالي == "1ساعة":
        return None
    idx = ترتيب.index(الإطار_الحالي) + 1
    إطار_أعلى = ترتيب[idx] if idx < len(ترتيب) else "1ساعة"
    بيانات = جلب_شموع_السعر(الزوج, إطار_أعلى)
    if not بيانات:
        return None
    إغلاقات = بيانات[0]
    ema50 = حساب_EMA(إغلاقات, 50)
    ema200 = حساب_EMA(إغلاقات, 200)
    سعر_إغلاق_آخر = إغلاقات[-2] if len(إغلاقات) >= 2 else إغلاقات[-1]
    if سعر_إغلاق_آخر > ema50 and ema50 > ema200:
        اتجاه = "صاعد"
    elif سعر_إغلاق_آخر < ema50 and ema50 < ema200:
        اتجاه = "هابط"
    else:
        اتجاه = "محايد"
    return {"إطار": إطار_أعلى, "اتجاه": اتجاه, "سعر_إغلاق": سعر_إغلاق_آخر, "EMA50": ema50, "EMA200": ema200}

# ============================================================
# 🧠 تحليل السوق
# ============================================================
def تحليل_السوق(الزوج, مبلغ, المخاطر, الإطار_الزمني="5د"):
    بيانات_السوق = جلب_شموع_السعر(الزوج, الإطار_الزمني)
    if not بيانات_السوق:
        return None
    الإغلاقات, سعر_الدخول, أعلى_سعر, أدنى_سعر, حجم_التداول, عالي, منخفض, حجم_الشموع, سعر_إغلاق_سابق = بيانات_السوق

    ema9 = حساب_EMA(الإغلاقات, 9)
    ema21 = حساب_EMA(الإغلاقات, 21)
    ema50 = حساب_EMA(الإغلاقات, 50)
    ema200 = حساب_EMA(الإغلاقات, 200)
    rsi = حساب_RSI_Wilder(الإغلاقات, 14)
    macd_line, macd_signal, macd_hist = حساب_MACD_كامل_حقيقي(الإغلاقات)
    atr = حساب_ATR(عالي, منخفض, الإغلاقات, 14)
    adx = حساب_ADX_كامل(عالي, منخفض, الإغلاقات, 14)
    bb_u, bb_m, bb_l = حساب_Bollinger(الإغلاقات, 20, 2)
    stoch = حساب_Stochastic(عالي, منخفض, الإغلاقات, 14)

    بيانات_إطار_أعلى = جلب_إطار_أعلى_مصحح(الزوج, الإطار_الزمني)
    تعزيز_شراء = 0
    تعزيز_بيع = 0
    if بيانات_إطار_أعلى:
        if بيانات_إطار_أعلى["اتجاه"] == "صاعد":
            تعزيز_شراء = 3
        elif بيانات_إطار_أعلى["اتجاه"] == "هابط":
            تعزيز_بيع = 3

    شراء_نقاط = 0
    بيع_نقاط = 0
    التفاصيل = []

    if ema9 > ema21 > ema50 > ema200:
        شراء_نقاط += 4
        التفاصيل.append("✅ ترند قوي صاعد: EMA9>EMA21>EMA50>EMA200")
    elif ema9 < ema21 < ema50 < ema200:
        بيع_نقاط += 4
        التفاصيل.append("✅ ترند قوي هابط: EMA9<EMA21<EMA50<EMA200")
    elif ema9 > ema21:
        شراء_نقاط += 1
        التفاصيل.append("✅ EMA9 فوق EMA21")
    else:
        بيع_نقاط += 1
        التفاصيل.append("✅ EMA9 تحت EMA21")

    if سعر_الدخول > ema200:
        شراء_نقاط += 2
        التفاصيل.append(f"✅ السعر فوق EMA200 ({ema200:.2f})")
    else:
        بيع_نقاط += 2
        التفاصيل.append(f"✅ السعر تحت EMA200 ({ema200:.2f})")

    ترند_قوي_صاعد = (ema9 > ema21 > ema50) and adx >= 25
    ترند_قوي_هابط = (ema9 < ema21 < ema50) and adx >= 25
    if rsi < 30:
        شراء_نقاط += 3
        التفاصيل.append(f"✅ RSI {rsi} — تشبع بيع")
    elif 30 <= rsi < 50:
        شراء_نقاط += 1
        التفاصيل.append(f"✅ RSI {rsi} — تحت المنتصف")
    elif 50 < rsi <= 70:
        if ترند_قوي_صاعد:
            شراء_نقاط += 1
            التفاصيل.append(f"✅ RSI {rsi} — قوة شرائية في ترند صاعد")
        else:
            بيع_نقاط += 1
            التفاصيل.append(f"✅ RSI {rsi} — فوق المنتصف")
    elif rsi > 70:
        if ترند_قوي_هابط:
            بيع_نقاط += 1
            التفاصيل.append(f"✅ RSI {rsi} — قوة بيعية في ترند هابط")
        else:
            بيع_نقاط += 3
            التفاصيل.append(f"✅ RSI {rsi} — تشبع شراء")

    if macd_line > macd_signal and macd_hist > 0:
        شراء_نقاط += 3
        التفاصيل.append(f"✅ MACD إيجابي: {macd_line:.4f} > {macd_signal:.4f}")
    elif macd_line < macd_signal and macd_hist < 0:
        بيع_نقاط += 3
        التفاصيل.append(f"✅ MACD سلبي: {macd_line:.4f} < {macd_signal:.4f}")
    elif macd_line > 0:
        شراء_نقاط += 1
        التفاصيل.append("✅ MACD فوق الصفر")
    else:
        بيع_نقاط += 1
        التفاصيل.append("✅ MACD تحت الصفر")

    if سعر_الدخول <= bb_l * 1.005:
        شراء_نقاط += 2
        التفاصيل.append("✅ السعر عند الحد السفلي لبولينجر")
    elif سعر_الدخول >= bb_u * 0.995:
        بيع_نقاط += 2
        التفاصيل.append("✅ السعر عند الحد العلوي لبولينجر")

    if stoch < 20:
        شراء_نقاط += 2
        التفاصيل.append(f"✅ ستوكاستيك {stoch} — تشبع بيع")
    elif stoch > 80:
        بيع_نقاط += 2
        التفاصيل.append(f"✅ ستوكاستيك {stoch} — تشبع شراء")

    if adx >= 25:
        if شراء_نقاط > بيع_نقاط:
            شراء_نقاط += 2
            التفاصيل.append(f"✅ ADX {adx} — ترند قوي صاعد")
        else:
            بيع_نقاط += 2
            التفاصيل.append(f"✅ ADX {adx} — ترند قوي هابط")
    elif adx < 15:
        التفاصيل.append(f"✅ ADX {adx} — سوق عرضي")

    شراء_نقاط += تعزيز_شراء
    بيع_نقاط += تعزيز_بيع
    if بيانات_إطار_أعلى:
        التفاصيل.append(f"✅ فلتر MTF ({بيانات_إطار_أعلى['إطار']}): {بيانات_إطار_أعلى['اتجاه']}")

    فرق_النقاط = abs(شراء_نقاط - بيع_نقاط)
    إجمالي = شراء_نقاط + بيع_نقاط
    if إجمالي == 0:
        return None
    الثقة = round((max(شراء_نقاط, بيع_نقاط) / إجمالي) * 100, 1)
    if فرق_النقاط < 4 or الثقة < 60 or adx < 20:
        return None

    if شراء_نقاط > بيع_نقاط:
        الإشارة = "شراء"
        مضاعف_SL = 1.5 if المخاطر == "متحفظ" else (2.0 if المخاطر == "متوازن" else 2.5)
        مضاعف_TP = 3.0 if المخاطر == "متحفظ" else (4.0 if المخاطر == "متوازن" else 5.0)
        وقف_خسارة = round(سعر_الدخول - مضاعف_SL * atr, 5)
        هدف1 = round(سعر_الدخول + 1.5 * atr, 5)
        هدف2 = round(سعر_الدخول + 2.5 * atr, 5)
        هدف3 = round(سعر_الدخول + مضاعف_TP * atr, 5)
    else:
        الإشارة = "بيع"
        مضاعف_SL = 1.5 if المخاطر == "متحفظ" else (2.0 if المخاطر == "متوازن" else 2.5)
        مضاعف_TP = 3.0 if المخاطر == "متحفظ" else (4.0 if المخاطر == "متوازن" else 5.0)
        وقف_خسارة = round(سعر_الدخول + مضاعف_SL * atr, 5)
        هدف1 = round(سعر_الدخول - 1.5 * atr, 5)
        هدف2 = round(سعر_الدخول - 2.5 * atr, 5)
        هدف3 = round(سعر_الدخول - مضاعف_TP * atr, 5)

    كمية = مبلغ / سعر_الدخول if سعر_الدخول > 0 else 0
    if الإشارة == "شراء":
        خسارة_محتملة = abs((سعر_الدخول - وقف_خسارة) * كمية)
        ربح1 = abs((هدف1 - سعر_الدخول) * كمية)
        ربح2 = abs((هدف2 - سعر_الدخول) * كمية)
        ربح3 = abs((هدف3 - سعر_الدخول) * كمية)
    else:
        خسارة_محتملة = abs((وقف_خسارة - سعر_الدخول) * كمية)
        ربح1 = abs((سعر_الدخول - هدف1) * كمية)
        ربح2 = abs((سعر_الدخول - هدف2) * كمية)
        ربح3 = abs((سعر_الدخول - هدف3) * كمية)

    نسبة_RR = round(ربح3 / خسارة_محتملة, 2) if خسارة_محتملة > 0 else 0

    اسم_الزوج = {
        "XAUUSD": "XAUUSD — الذهب مقابل الدولار",
        "BTCUSDT": "BTCUSDT — البيتكوين مقابل الدولار",
        "ETHUSDT": "ETHUSDT — الإيثيريوم مقابل الدولار",
        "PAXGUSDT": "PAXGUSDT — الذهب (مرتبط بـ Binance)",
    }.get(الزوج.upper(), الزوج.upper())

    return {
        "المعرف": len(النتائج) + 1,
        "التاريخ_والوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "الزوج_المالي": اسم_الزوج,
        "الإطار_الزمني": الأطر_الزمنية[الإطار_الزمني]["label"],
        "التحليل": {
            "اتجاه_السوق": "صاعد ↗️" if الإشارة == "شراء" else "هابط ↘️",
            "قوة_الترند_ADX": f"{adx}%",
            "نسبة_إجماع_المؤشرات": f"{الثقة}%",
            "سعر_السوق_الحالي": round(سعر_الدخول, 2),
            "أعلى_سعر_24ساعة": round(أعلى_سعر, 2),
            "أدنى_سعر_24ساعة": round(أدنى_سعر, 2),
            "ATR": round(atr, 6),
            "فلتر_MTF": بيانات_إطار_أعلى["اتجاه"] if بيانات_إطار_أعلى else "غير متاح",
            "المؤشرات": {
                "EMA9": round(ema9, 5), "EMA21": round(ema21, 5), "EMA50": round(ema50, 5), "EMA200": round(ema200, 5),
                "RSI14": rsi, "MACD_Line": macd_line, "MACD_Signal": macd_signal, "MACD_Hist": macd_hist,
                "ADX14": adx, "Stochastic": stoch, "BB_Upper": bb_u, "BB_Lower": bb_l,
            }
        },
        "الإشارة": الإشارة,
        "سعر_الدخول": round(سعر_الدخول, 2),
        "مبلغ_الاستثمار": مبلغ,
        "وقف_الخسارة": {"السعر": وقف_خسارة, "الخسارة_المحتملة": round(خسارة_محتملة, 2)},
        "الأهداف": {
            "الهدف_الأول": {"السعر": هدف1, "الربح": round(ربح1, 2)},
            "الهدف_الثاني": {"السعر": هدف2, "الربح": round(ربح2, 2)},
            "الهدف_الثالث": {"السعر": هدف3, "الربح": round(ربح3, 2)},
        },
        "نسبة_RR": f"{نسبة_RR} : 1",
        "التفاصيل": " | ".join(التفاصيل),
        "التوصية": "⚠️ أداة تحليل — ليست توصية استثمارية. إدارة المخاطر ضرورية."
    }

# ============================================================
# 🏠 API
# ============================================================
@app.get("/api")
def api_home():
    return {"المنصة": "نبر وان", "الإصدار": "4.1.0-Telegram", "الحالة": "تعمل", "الواجهة": "/"}

@app.post("/فحص-وتحليل")
def فحص_وتحليل(البيانات: بيانات_الصفقة):
    if البيانات.مبلغ_الاستثمار <= 0:
        raise HTTPException(status_code=400, detail="مبلغ الاستثمار يجب أن يكون أكبر من صفر")
    if البيانات.الزوج_المالي.upper() not in رموز_Binance:
        raise HTTPException(status_code=400, detail="الزوج المالي غير مدعوم")
    النتيجة = تحليل_السوق(البيانات.الزوج_المالي.upper(), البيانات.مبلغ_الاستثمار, البيانات.مستوى_المخاطر, البيانات.الإطار_الزمني)
    if not النتيجة:
        raise HTTPException(status_code=400, detail="❌ لا توجد إشارة قوية بما يكفي حالياً — حاول لاحقاً أو غيّر الزوج/الإطار الزمني.")
    النتائج.append(النتيجة)
    return النتيجة

# ============================================================
# 🎨 الواجهة — مكتملة بالكامل الآن!
# ============================================================
HTML = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>نبر وان — منصة التداول بالذكاء الاصطناعي</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:Tahoma,Arial,sans-serif;background:radial-gradient(circle at top,#08243a 0%,#020811 45%,#01040a 100%);color:#fff;min-height:100vh;}
.container{max-width:1250px;margin:auto;padding:18px;}
.header{border:1px solid #0877b8;border-radius:18px;background:linear-gradient(135deg,#07192b,#020812);padding:18px;box-shadow:0 0 25px rgba(0,170,255,.18);}
.logo{display:flex;align-items:center;justify-content:space-between;gap:15px;}
.logo-title{font-size:30px;font-weight:bold;}
.logo-sub{color:#8fa8b9;font-size:14px;margin-top:4px;}
.live{background:#062f1c;border:1px solid #00ff6a;color:#35ff86;padding:10px 18px;border-radius:10px;font-weight:bold;}
.clock{margin-top:15px;border:1px solid #12618e;padding:12px;border-radius:10px;text-align:center;color:#d8e9f3;}
.main{margin-top:15px;display:grid;grid-template-columns:1fr 1fr;gap:15px;}
.card{background:linear-gradient(145deg,rgba(7,28,46,.96),rgba(2,10,19,.98));border:1px solid #096d9f;border-radius:15px;padding:18px;box-shadow:inset 0 0 25px rgba(0,140,255,.04),0 0 18px rgba(0,130,255,.08);}
.full{grid-column:1 / -1;}
.section-title{font-size:21px;font-weight:bold;margin-bottom:15px;color:#fff;}
.badge{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:50%;background:#123b7b;margin-left:6px;}
.pair{font-size:27px;color:#ffd633;font-weight:bold;}
.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.stat{border:1px solid #15435d;background:#031321;border-radius:10px;padding:15px;}
.stat-label{color:#bdcfda;font-size:15px;}
.stat-value{margin-top:8px;color:#32ff66;font-size:22px;font-weight:bold;}
.chart{height:170px;border:1px solid #123d56;border-radius:10px;position:relative;overflow:hidden;background:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:25px 25px;}
.chart svg{width:100%;height:100%;}
.signal{background:linear-gradient(135deg,#07350d,#001a09);border:1px solid #16e84b;border-radius:12px;padding:18px;text-align:center;}
.buy{color:#32ff55;font-size:30px;font-weight:bold;}
.sell{color:#ff5757;font-size:30px;font-weight:bold;}
.price{font-size:27px;margin-top:10px;color:#fff;}
.input-box{width:100%;background:#020b15;color:#fff;border:1px solid #12668e;padding:14px;border-radius:9px;font-size:18px;outline:none;}
.input-box:focus{border-color:#00bfff;}
label{display:block;margin-bottom:7px;color:#b7cbd7;}
.form-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.targets{display:grid;gap:9px;}
.target{padding:14px;border-radius:10px;background:#031321;border:1px solid #15435d;display:flex;justify-content:space-between;align-items:center;}
.t1{color:#ffd52e;}
.t2{color:#31ff70;}
.t3{color:#ff6a2e;}
.risk{text-align:center;border-top:1px solid #12384e;margin-top:15px;padding-top:15px;}
.rr{color:#34ff64;font-size:30px;font-weight:bold;}
.buttons{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px;}
button{border:none;border-radius:10px;padding:16px;font-size:18px;font-weight:bold;cursor:pointer;transition:.2s;}
button:hover{transform:translateY(-2px);}
.execute{background:linear-gradient(135deg,#00a83b,#007d2b);color:#fff;}
.save{background:linear-gradient(135deg,#154f9e,#0a326b);color:#fff;}
.result{margin-top:15px;white-space:pre-wrap;background:#01070e;border:1px solid #123c54;border-radius:10px;padding:15px;display:none;}
.footer{text-align:center;color:#728c9c;padding:20px;font-size:13px;}
.status{text-align:center;margin-top:10px;color:#7dffac;}
select.input-box{appearance:none;-webkit-appearance:none;-moz-appearance:none;}
@media(max-width:800px){.main,.analysis-grid,.form-row,.buttons{grid-template-columns:1fr;}.full{grid-column:auto;}.logo{flex-direction:column;align-items:flex-start;}.logo-title{font-size:25px;}}
</style>
</head>
<body>
<div class="container">
<div class="header">
    <div class="logo">
        <div><div class="logo-title">🤖 نـبـر وان</div><div class="logo-sub">منصة التداول بالذكاء الاصطناعي — بيانات حقيقية من Binance + بوت تليجرام</div></div>
        <div class="live">⚡ تحديث لحظي</div>
    </div>
    <div class="clock" id="clock">🕐 جاري تحميل الوقت...</div>
</div>
<div class="main">
<div class="card full">
    <div class="section-title"><span class="badge">1</span> الزوج المالي</div>
    <div class="pair" id="pairDisplay">🪙 XAUUSD <span style="color:#aaa;font-size:18px;">— الذهب مقابل الدولار</span></div>
</div>
<div class="card">
    <div class="section-title"><span class="badge">2</span> التحليل</div>
    <div class="analysis-grid">
        <div class="stat"><div class="stat-label">📈 اتجاه السوق</div><div class="stat-value" id="dirValue">—</div></div>
        <div class="stat"><div class="stat-label">💪 قوة الترند</div><div class="stat-value" id="trendValue">—</div></div>
        <div class="stat"><div class="stat-label">🧠 ثقة الذكاء الاصطناعي</div><div class="stat-value" id="confValue">—</div></div>
        <div class="stat"><div class="stat-label">💰 سعر السوق (حقيقي)</div><div class="stat-value" id="marketPrice">جاري الجلب...</div></div>
    </div>
</div>
<div class="card">
    <div class="section-title"><span class="badge">3</span> النتيجة النهائية</div>
    <div class="signal">
        <div>الإشارة</div>
        <div class="buy" id="signalValue">—</div>
        <div class="price">سعر الدخول: <strong id="entryPrice">—</strong></div>
    </div>
</div>
<div class="card">
    <div class="section-title"><span class="badge">4</span> مبلغ الاستثمار</div>
    <input id="investment" class="input-box" type="number" value="1000" min="1">
    <div style="margin-top:8px;color:#8ca4b2;">💵 الدولار الأمريكي</div>
</div>
<div class="card">
    <div class="section-title"><span class="badge">5</span> وقف الخسارة</div>
    <div class="stat">
        <div class="stat-value" style="color:#ff5757" id="slPrice">—</div>
        <div style="color:#ff5757;margin-top:8px;">⚠️ خسارة محتملة: <strong id="loss">—</strong> دولار</div>
    </div>
</div>
<div class="card">
    <div class="section-title"><span class="badge">6</span> الأهداف المقترحة</div>
    <div class="targets">
        <div class="target"><span class="t1">🎯 الهدف الأول</span><strong id="t1Price">—</strong><span class="t1" id="t1Pnl">—</span></div>
        <div class="target"><span class="t2">🎯 الهدف الثاني</span><strong id="t2Price">—</strong><span class="t2" id="t2Pnl">—</span></div>
        <div class="target"><span class="t3">🎯 الهدف الثالث</span><strong id="t3Price">—</strong><span class="t3" id="t3Pnl">—</span></div>
    </div>
</div>
<div class="card full">
    <div class="risk">
        📊 نسبة الربح إلى الخسارة
        <div class="rr" id="rrValue">—</div>
        <div style="color:#32ff66;" id="rrLabel">—</div>
    </div>
</div>
<div class="card full">
    <div class="section-title">⚙️ إعداد التحليل</div>
    <div class="form-row">
        <div><label>الزوج المالي</label><select id="pair" class="input-box" onchange="updatePairDisplay(this.value)"><option value="XAUUSD" selected>🪙 XAUUSD — ذهب</option><option value="BTCUSDT">₿ BTCUSDT — بيتكوين</option><option value="ETHUSDT">Ξ ETHUSDT — إيثيريوم</option><option value="PAXGUSDT">🪙 PAXGUSDT — ذهب (Binance)</option></select></div>
        <div><label>مبلغ الاستثمار</label><input id="amount" class="input-box" type="number" value="1000"></div>
        <div><label>مستوى المخاطر</label><select id="riskLevel" class="input-box"><option>متحفظ</option><option selected>متوازن</option><option>عالي</option></select></div>
    </div>
    <div class="buttons">
        <button class="execute" onclick="analyze()">🔍 فحص وتحليل الصفقة</button>
        <button class="save" onclick="saveTrade()">💾 حفظ والمراقبة</button>
    </div>
    <div id="status" class="status"></div>
    <div id="result" class="result"></div>
</div>
</div>
<div class="footer">🤖 نبر وان — منصة التداول بالذكاء الاصطناعي<br>الإصدار 4.1.0-Telegram — بيانات حقيقية من Binance · تحليل فني معياري كامل · بوت تليجرام نشط</div>
</div>
<script>
function updateClock(){const n=new Date();document.getElementById("clock").innerHTML="🕐 التاريخ والوقت: "+n.toLocaleDateString("ar-SA")+" | "+n.toLocaleTimeString("ar-SA");}
setInterval(updateClock,1000);updateClock();
function updatePairDisplay(v){
    if(v=="XAUUSD")document.getElementById("pairDisplay").innerHTML="🪙 XAUUSD <span style='color:#aaa;font-size:18px;'>— الذهب مقابل الدولار</span>";
    else if(v=="BTCUSDT")document.getElementById("pairDisplay").innerHTML="₿ BTCUSDT <span style='color:#aaa;font-size:18px;'>— البيتكوين مقابل الدولار</span>";
    else if(v=="ETHUSDT")document.getElementById("pairDisplay").innerHTML="Ξ ETHUSDT <span style='color:#aaa;font-size:18px;'>— الإيثيريوم مقابل الدولار</span>";
    else document.getElementById("pairDisplay").innerHTML=v;
}
async function analyze(){
    const pair=document.getElementById("pair").value;
    const amount=Number(document.getElementById("amount").value);
    const risk=document.getElementById("riskLevel").value;
    const status=document.getElementById("status");
    const resultDiv=document.getElementById("result");
    status.innerText="⏳ جاري جلب البيانات وتحليل السوق...";
    resultDiv.style.display="none";
    try{
        const res=await fetch("/فحص-وتحليل",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({الزوج_المالي:pair,مبلغ_الاستثمار:amount,مستوى_المخاطر:risk,الإطار_الزمني:"5د"})
        });
        const data=await res.json();
