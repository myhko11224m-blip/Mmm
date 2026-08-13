============================================================

🤖 نبر وان v4.1 — المعيارية بالكامل

✅ MACD حقيقي (سلسلة كاملة + EMA9 Signal)

✅ ADX حقيقي (سلسلة + تنعيم Wilder كامل)

✅ MTF ثنائي الاتجاه + شمعة مغلقة

✅ عتبات دقة: فرق≥4 ، ثقة≥60% ، ADX≥20

✅ RSI منطق محسّن في الترندات القوية

✅ بيانات Binance حقيقية — 300 شمعة — EMA200 حقيقي

ملف واحد — انسخه واشغله مباشرة

============================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import requests

app = FastAPI(
title="نبر وان — منصة التحليل الفني الذكي",
description="بيانات حقيقية من Binance · مؤشرات معيارية 100%",
version="4.1.0",
docs_url="/لوحة-التحكم",
redoc_url="/تفاصيل"
)

============================================================

📦 الإعدادات والبيانات

============================================================

class بيانات_الصفقة(BaseModel):
الزوج_المالي: str = "BTCUSDT"
مبلغ_الاستثمار: float = 1000
مستوى_المخاطر: str = "متوازن"
الإطار_الزمني: str = "5د"

النتائج = []
سجل_الصفقات = []

الأطر_الزمنية = {
"1د":  {"interval": "1m",  "label": "1 دقيقة",  "limit": 300},
"5د":  {"interval": "5m",  "label": "5 دقائق", "limit": 300},
"15د": {"interval": "15m", "label": "15 دقيقة", "limit": 300},
"30د": {"interval": "30m", "label": "30 دقيقة", "limit": 300},
"1ساعة": {"interval": "1h", "label": "ساعة",     "limit": 300},
}

الأزواج_المالية = {
"BTCUSDT":  "₿ BTCUSDT — بيتكوين",
"ETHUSDT":  "Ξ ETHUSDT — إيثيريوم",
"BNBUSDT":  "◈ BNBUSDT — بينانس كوين",
"SOLUSDT":  "◎ SOLUSDT — سولانا",
"XRPUSDT":  "✕ XRPUSDT — ريبل",
"ADAUSDT":  "₳ ADAUSDT — كاردانو",
"DOGEUSDT": "🐶 DOGEUSDT — دوجكوين",
"DOTUSDT":  "● DOTUSDT — بولكادوت",
"MATICUSDT":"⬡ MATICUSDT — ماتيك",
"LINKUSDT": "🔗 LINKUSDT — تشين لينك",
"AVAXUSDT": "🔺 AVAXUSDT — أفالانش",
"ATOMUSDT": "⚛️ ATOMUSDT — كوزموس",
"LTCUSDT":  "Ł LTCUSDT — لايتكوين",
"UNIUSDT":  "🦄 UNIUSDT — يونيسواب",
"PAXGUSDT": "🪙 PAXGUSDT — ذهب (مرتبط)",
}

رموز_Binance = list(الأزواج_المالية.keys())

============================================================

📡 جلب البيانات من Binance

============================================================

def جلب_شموع_السعر(الزوج, إطار_زمني):
فترة = الأطر_الزمنية[إطار_زمني]["interval"]
try:
res = requests.get(
"https://api.binance.com/api/v3/klines",
params={"symbol": الزوج, "interval": فترة, "limit": 300},
timeout=15
)
res.raise_for_status()
بيانات = res.json()
if not بيانات or len(بيانات) < 250:
return None
الإغلاقات = [float(s[4]) for s in بيانات]
عالي = [float(s[2]) for s in بيانات]
منخفض = [float(s[3]) for s in بيانات]
حجم_الشموع = [float(s[5]) for s in بيانات]
أعلى_سعر = max(عالي)
أدنى_سعر = min(منخفض)
السعر_الحالي = الإغلاقات[-1]
حجم_التداول = sum(حجم_الشموع[-20:])
# ✅ آخر شمعة مغلقة (ليست الحالية غير المكتملة)
سعر_إغلاق_سابق = الإغلاقات[-2] if len(الإغلاقات) >= 2 else السعر_الحالي
return الإغلاقات, السعر_الحالي, أعلى_سعر, أدنى_سعر, حجم_التداول, عالي, منخفض, حجم_الشموع, سعر_إغلاق_سابق
except Exception as e:
print(f"خطأ جلب البيانات: {e}")
return None

============================================================

📐 المؤشرات — معيارية 100%

============================================================

def حساب_EMA(الإغلاقات, الفترة):
k = 2 / (الفترة + 1)
ema = الإغلاقات[0]
for سعر in الإغلاقات[1:]:
ema = سعر * k + ema * (1 - k)
return ema

def حساب_EMA_لسلسلة(القيم, الفترة):
"""حساب EMA لسلسلة كاملة من القيم"""
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
for i in range(فترة, len(أرباح)):
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
"""✅ ADX حقيقي بالكامل — سلسلة كاملة + تنعيم Wilder"""
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
"""✅ MACD حقيقي — سلسلة كاملة → EMA9 → Signal + Histogram"""
# حساب سلسلة EMA السريعة والبطيئة
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
  
# سلسلة خط MACD كاملة  
macd_series = [ema_s[i] - ema_l[i] for i in range(len(ema_s))]  
  
# ✅ حساب خط Signal = EMA9 لسلسلة MACD — حقيقي 100%  
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

============================================================

🔍 فلتر MTF — ثنائي الاتجاه + شمعة مغلقة

============================================================

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
# ✅ نستخدم آخر شمعة مغلقة وليس السعر الحالي غير المكتمل
سعر_إغلاق_آخر = إغلاقات[-2] if len(إغلاقات) >= 2 else إغلاقات[-1]

if سعر_إغلاق_آخر > ema50 and ema50 > ema200:  
    اتجاه = "صاعد"  
elif سعر_إغلاق_آخر < ema50 and ema50 < ema200:  
    اتجاه = "هابط"  
else:  
    اتجاه = "محايد"  
  
return {"إطار": إطار_أعلى, "اتجاه": اتجاه, "سعر_إغلاق": سعر_إغلاق_آخر, "EMA50": ema50, "EMA200": ema200}

============================================================

🧠 منطق الإشارة — مع عتبات دقة صارمة

============================================================

def تحليل_السوق(الزوج, إطار_زمني, مبلغ, المخاطر):
بيانات_السوق = جلب_شموع_السعر(الزوج, إطار_زمني)
if not بيانات_السوق:
return None, None, None, "فشل جلب البيانات من Binance"

الإغلاقات, سعر_الدخول, أعلى_سعر, أدنى_سعر, حجم_التداول, عالي, منخفض, حجم_الشموع, سعر_إغلاق_سابق = بيانات_السوق  

# حساب المؤشرات  
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

# فلتر MTF ثنائي الاتجاه  
بيانات_إطار_أعلى = جلب_إطار_أعلى_مصحح(الزوج, إطار_زمني)  
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

# 1. المتوسطات  
if ema9 > ema21 > ema50 > ema200:  
    شراء_نقاط += 4  
    التفاصيل.append("ترند قوي صاعد: EMA9>EMA21>EMA50>EMA200")  
elif ema9 < ema21 < ema50 < ema200:  
    بيع_نقاط += 4  
    التفاصيل.append("ترند قوي هابط: EMA9<EMA21<EMA50<EMA200")  
elif ema9 > ema21:  
    شراء_نقاط += 1  
    التفاصيل.append("EMA9 فوق EMA21")  
else:  
    بيع_نقاط += 1  
    التفاصيل.append("EMA9 تحت EMA21")  

# 2. EMA200  
if سعر_الدخول > ema200:  
    شراء_نقاط += 2  
    التفاصيل.append(f"السعر فوق EMA200 ({ema200:.2f})")  
else:  
    بيع_نقاط += 2  
    التفاصيل.append(f"السعر تحت EMA200 ({ema200:.2f})")  

# ✅ RSI منطق محسّن — لا يعاكس الترند القوي  
ترند_قوي_صاعد = (ema9 > ema21 > ema50) and adx >= 25  
ترند_قوي_هابط = (ema9 < ema21 < ema50) and adx >= 25  
  
if rsi < 30:  
    شراء_نقاط += 3  
    التفاصيل.append(f"RSI {rsi} — تشبع بيع")  
elif 30 <= rsi < 50:  
    شراء_نقاط += 1  
    التفاصيل.append(f"RSI {rsi} — تحت المنتصف")  
elif 50 < rsi <= 70:  
    if ترند_قوي_صاعد:  
        شراء_نقاط += 1  # في ترند صاعد، RSI 50-70 قوة وليست إشارة بيع!  
        التفاصيل.append(f"RSI {rsi} — قوة شرائية في ترند صاعد")  
    else:  
        بيع_نقاط += 1  
        التفاصيل.append(f"RSI {rsi} — فوق المنتصف")  
elif rsi > 70:  
    if ترند_قوي_هابط:  
        بيع_نقاط += 1  
        التفاصيل.append(f"RSI {rsi} — قوة بيعية في ترند هابط")  
    else:  
        بيع_نقاط += 3  
        التفاصيل.append(f"RSI {rsi} — تشبع شراء")  

# ✅ MACD حقيقي  
if macd_line > macd_signal and macd_hist > 0:  
    شراء_نقاط += 3  
    التفاصيل.append(f"MACD إيجابي وتصاعدي: {macd_line:.4f} > {macd_signal:.4f}")  
elif macd_line < macd_signal and macd_hist < 0:  
    بيع_نقاط += 3  
    التفاصيل.append(f"MACD سلبي وتنازلي: {macd_line:.4f} < {macd_signal:.4f}")  
elif macd_line > 0:  
    شراء_نقاط += 1  
    التفاصيل.append("MACD فوق الصفر")  
else:  
    بيع_نقاط += 1  
    التفاصيل.append("MACD تحت الصفر")  

# 4. Bollinger  
if سعر_الدخول <= bb_l * 1.005:  
    شراء_نقاط += 2  
    التفاصيل.append("عند الحد السفلي لبولينجر")  
elif سعر_الدخول >= bb_u * 0.995:  
    بيع_نقاط += 2  
    التفاصيل.append("عند الحد العلوي لبولينجر")  

# 5. Stochastic  
if stoch < 20:  
    شراء_نقاط += 2  
    التفاصيل.append(f"ستوكاستيك {stoch} — تشبع بيع")  
elif stoch > 80:  
    بيع_نقاط += 2  
    التفاصيل.append(f"ستوكاستيك {stoch} — تشبع شراء")  

# 6. ADX  
if adx >= 25:  
    if شراء_نقاط > بيع_نقاط:  
        شراء_نقاط += 2  
        التفاصيل.append(f"ADX {adx} — ترند قوي صاعد")  
    else:  
        بيع_نقاط += 2  
        التفاصيل.append(f"ADX {adx} — ترند قوي هابط")  
elif adx < 15:  
    التفاصيل.append(f"ADX {adx} — سوق عرضي")  

# ✅ تطبيق فلتر MTF ثنائي الاتجاه  
شراء_نقاط += تعزيز_شراء  
بيع_نقاط += تعزيز_بيع  
if بيانات_إطار_أعلى:  
    التفاصيل.append(f"فلتر MTF ({بيانات_إطار_أعلى['إطار']}): {بيانات_إطار_أعلى['اتجاه']}")  

# ✅ عتبات الدقة — لا إشارة إلا بفرق كافٍ وثقة عالية  
فرق_النقاط = abs(شراء_نقاط - بيع_نقاط)  
إجمالي = شراء_نقاط + بيع_نقاط  
if إجمالي == 0:  
    return None, None, None, "لا توجد إشارة — حاول لاحقاً"  
  
الثقة = round((max(شراء_نقاط, بيع_نقاط) / إجمالي) * 100, 1)  
  
# 🚫 رفض الإشارات الضعيفة  
if فرق_النقاط < 4 or الثقة < 60 or adx < 20:  
    سبب_الرفض = []  
    if فرق_النقاط < 4: سبب_الرفض.append(f"فرق نقاط ضعيف ({فرق_النقاط})")  
    if الثقة < 60: سبب_الرفض.append(f"ثقة منخفضة ({الثقة}%)")  
    if adx < 20: سبب_الرفض.append(f"ترند ضعيف (ADX {adx})")  
    return None, None, None, "⚠️ لا إشارة — " + " | ".join(سبب_الرفض)  

# ✅ إشارة مقبولة  
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

النتيجة = {  
    "المعرف": len(النتائج) + 1,  
    "التاريخ_والوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  
    "الزوج_المالي": الأزواج_المالية.get(الزوج, الزوج),  
    "الإطار_الزمني": الأطر_الزمنية[إطار_زمني]["label"],  
    "التحليل": {  
        "اتجاه_السوق": "صاعد ↗️" if الإشارة == "شراء" else "هابط ↘️",  
        "قوة_الترند_ADX": f"{adx}%",  
        "نسبة_إجماع_المؤشرات": f"{الثقة}%",  
        "فرق_النقاط": فرق_النقاط,  
        "سعر_السوق_الحالي": round(سعر_الدخول, 5),  
        "ATR": round(atr, 6),  
        "فلتر_MTF": بيانات_إطار_أعلى["اتجاه"] if بيانات_إطار_أعلى else "غير متاح",  
        "المؤشرات": {  
            "EMA9": round(ema9, 5), "EMA21": round(ema21, 5), "EMA50": round(ema50, 5), "EMA200": round(ema200, 5),  
            "RSI14": rsi, "MACD_Line": macd_line, "MACD_Signal": macd_signal, "MACD_Hist": macd_hist,  
            "ADX14": adx, "Stochastic": stoch, "BB_Upper": bb_u, "BB_Lower": bb_l,  
        }  
    },  
    "الإشارة": الإشارة, "سعر_الدخول": round(سعر_الدخول, 5),  
    "مبلغ_الاستثمار": مبلغ,  
    "وقف_الخسارة": {"السعر": وقف_خسارة, "الخسارة_المحتملة": round(خسارة_محتملة, 2)},  
    "الأهداف": {  
        "الهدف_الأول": {"السعر": هدف1, "الربح": round(ربح1, 2)},  
        "الهدف_الثاني": {"السعر": هدف2, "الربح": round(ربح2, 2)},  
        "الهدف_الثالث": {"السعر": هدف3, "الربح": round(ربح3, 2)},  
    },  
    "نسبة_RR": f"{نسبة_RR} : 1",  
    "التفاصيل": " | ".join(التفاصيل),  
    "التوصية": "⚠️ أداة تحليل — ليست توصية استثمارية. إدارة المخاطر ضرورية. يُنصح بـ Backtest."  
}  
return الإشارة, الثقة, النتيجة, None

============================================================

🏠 API

============================================================

@app.post("/فحص-وتحليل")
def فحص_وتحليل(البيانات: بيانات_الصفقة):
if البيانات.مبلغ_الاستثمار <= 0:
raise HTTPException(status_code=400, detail="مبلغ الاستثمار يجب أن يكون أكبر من صفر")
if البيانات.الزوج_المالي not in رموز_Binance:
raise HTTPException(status_code=400, detail="الزوج المالي غير مدعوم")

الإشارة, الثقة, النتيجة, خطأ = تحليل_السوق(  
    البيانات.الزوج_المالي,  
    البيانات.الإطار_الزمني,  
    البيانات.مبلغ_الاستثمار,  
    البيانات.مستوى_المخاطر  
)  
  
if خطأ:  
    raise HTTPException(status_code=400, detail=خطأ)  
  
النتائج.append(النتيجة)  
return النتيجة

@app.post("/حفظ-صفقة")
def حفظ_صفقة(البيانات: بيانات_الصفقة):
النتيجة = فحص_وتحليل(البيانات)
سجل_الصفقات.append(النتيجة)
return {"رسالة": "✅ تم الحفظ", "الصفقة": النتيجة, "العدد": len(سجل_الصفقات)}

@app.get("/سجل-الصفقات")
def عرض_السجل():
return {"عدد": len(سجل_الصفقات), "الصفقات": سجل_الصفقات}

============================================================

🎨 الواجهة

============================================================

HTML = r"""

<!DOCTYPE html>  <html lang="ar" dir="rtl">  
<head>  
<meta charset="UTF-8">  
<meta name="viewport" content="width=device-width, initial-scale=1.0">  
<title>نبر وان v4.1 — معيارية بالكامل</title>  
<style>  
*{box-sizing:border-box;}  
body{margin:0;font-family:Tahoma,Arial,sans-serif;background:radial-gradient(circle at top,#08243a 0%,#020811 45%,#01040a 100%);color:#fff;min-height:100vh;}  
.container{max-width:1250px;margin:auto;padding:18px;}  
.header{border:1px solid #0877b8;border-radius:18px;background:linear-gradient(135deg,#07192b,#020812);padding:18px;box-shadow:0 0 25px rgba(0,170,255,.18);}  
.logo{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;}  
.logo-title{font-size:28px;font-weight:bold;}  
.live{background:#062f1c;border:1px solid #00ff6a;color:#35ff86;padding:10px 18px;border-radius:10px;font-weight:bold;}  
.clock{margin-top:15px;border:1px solid #12618e;padding:12px;border-radius:10px;text-align:center;}  
.timeframe-bar{margin-top:15px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;}  
.tf-btn{padding:8px 14px;border-radius:8px;border:1px solid #12668e;background:#031321;color:#8fa8b9;cursor:pointer;transition:.2s;}  
.tf-btn:hover{border-color:#00bfff;color:#fff;}  
.tf-btn.active{background:linear-gradient(135deg,#00a83b,#007d2b);border-color:#00ff6a;color:#fff;font-weight:bold;}  
.main{margin-top:15px;display:grid;grid-template-columns:1fr 1fr;gap:15px;}  
.card{background:linear-gradient(145deg,rgba(7,28,46,.96),rgba(2,10,19,.98));border:1px solid #096d9f;border-radius:15px;padding:18px;}  
.full{grid-column:1 / -1;}  
.section-title{font-size:20px;font-weight:bold;margin-bottom:12px;}  
.badge{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:50%;background:#123b7b;margin-left:6px;}  
.pair{font-size:22px;color:#ffd633;font-weight:bold;}  
.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}  
.stat{border:1px solid #15435d;background:#031321;border-radius:10px;padding:15px;}  
.stat-label{color:#bdcfda;font-size:14px;}  
.stat-value{margin-top:6px;color:#32ff66;font-size:20px;font-weight:bold;}  
.signal{background:linear-gradient(135deg,#07350d,#001a09);border:1px solid #16e84b;border-radius:12px;padding:18px;text-align:center;}  
.buy{color:#32ff55;font-size:28px;font-weight:bold;}  
.sell{color:#ff5757;font-size:28px;font-weight:bold;}  
.input-box{width:100%;background:#020b15;color:#fff;border:1px solid #12668e;padding:12px;border-radius:9px;font-size:16px;outline:none;}  
.input-box:focus{border-color:#00bfff;}  
label{display:block;margin-bottom:6px;color:#b7cbd7;}  
.form-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}  
.targets{display:grid;gap:8px;}  
.target{padding:12px;border-radius:10px;background:#031321;border:1px solid #15435d;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}  
.t1{color:#ffd52e;}.t2{color:#31ff70;}.t3{color:#ff6a2e;}  
.risk{text-align:center;border-top:1px solid #12384e;margin-top:15px;padding-top:15px;}  
.rr{color:#34ff64;font-size:28px;font-weight:bold;}  
.buttons{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px;}  
button{border:none;border-radius:10px;padding:14px;font-size:17px;font-weight:bold;cursor:pointer;transition:.2s;}  
button:hover{transform:translateY(-2px);}  
.execute{background:linear-gradient(135deg,#00a83b,#007d2b);color:#fff;}  
.save{background:linear-gradient(135deg,#154f9e,#0a326b);color:#fff;}  
.result{margin-top:15px;background:#01070e;border:1px solid #123c54;border-radius:10px;padding:15px;display:none;max-height:400px;overflow:auto;font-size:13px;line-height:1.6;}  
.footer{text-align:center;color:#728c9c;padding:20px;font-size:13px;line-height:1.8;}  
.status{text-align:center;margin-top:10px;color:#7dffac;}  
select.input-box{appearance:none;-webkit-appearance:none;}  
.note{background:rgba(50,200,255,.08);border:1px solid #32c8ff;border-radius:8px;padding:10px;margin-top:10px;color:#99ddff;font-size:13px;}  
.warning{background:rgba(255,70,70,.1);border:1px solid #ff4646;border-radius:8px;padding:10px;margin-top:10px;color:#ff8888;font-size:13px;}  
@media(max-width:800px){.main,.analysis-grid,.form-row,.buttons{grid-template-columns:1fr;}.full{grid-column:auto;}.logo{flex-direction:column;align-items:flex-start;}}  
</style>  
</head>  
<body>  
<div class="container">  
<div class="header">  
    <div class="logo">  
        <div><div class="logo-title">🤖 نـبـر وان v4.1 — معيارية بالكامل</div><div style="color:#8fa8b9;font-size:13px;">MACD حقيقي · ADX كامل · MTF ثنائي · عتبات دقة صارمة</div></div>  
        <div class="live">⚡ تحديث لحظي</div>  
    </div>  
    <div class="clock" id="clock">🕐 جاري تحميل الوقت...</div>  
    <div class="timeframe-bar">  
        <button class="tf-btn" data-tf="1د" onclick="selectTF(this)">1 دقيقة</button>  
        <button class="tf-btn active" data-tf="5د" onclick="selectTF(this)">5 دقائق</button>  
        <button class="tf-btn" data-tf="15د" onclick="selectTF(this)">15 دقيقة</button>  
        <button class="tf-btn" data-tf="30د" onclick="selectTF(this)">30 دقيقة</button>  
        <button class="tf-btn" data-tf="1ساعة" onclick="selectTF(this)">ساعة</button>  
    </div>  
    <div class="note">✅ عتبات الإشارة: فرق نقاط ≥ 4 | ثقة ≥ 60% | ADX ≥ 20 — لا إشارات ضعيفة بعد اليوم!</div>  
    <div class="warning">⚠️ أداة تحليل — ليست توصية استثمارية. التداول يحمل مخاطر خسارة الأموال.</div>  
</div>  
<div class="main">  
<div class="card full">  
    <div class="section-title"><span class="badge">1</span> الزوج المالي</div>  
    <div class="pair" id="pairDisplay">₿ BTCUSDT — بيتكوين</div>  
</div>  
<div class="card">  
    <div class="section-title"><span class="badge">2</span> التحليل <span id="currentTF" style="color:#00bfff;font-size:14px;">| 5 دقائق</span></div>  
    <div class="analysis-grid">  
        <div class="stat"><div class="stat-label">📈 اتجاه السوق</div><div class="stat-value" id="dirValue">—</div></div>  
        <div class="stat"><div class="stat-label">💪 قوة الترند (ADX)</div><div class="stat-value" id="trendValue">—</div></div>  
        <div class="stat"><div class="stat-label">🧠 إجماع المؤشرات</div><div class="stat-value" id="confValue">—</div></div>  
        <div class="stat"><div class="stat-label">💰 السعر الحقيقي</div><div class="stat-value" id="marketPrice">جاري الجلب...</div></div>  
    </div>  
    <div class="stat" style="margin-top:10px;">  
        <div class="stat-label">🔍 فلتر MTF</div>  
        <div class="stat-value" style="color:#aaa;font-size:16px;" id="mtfFilter">—</div>  
    </div>  
</div>  
<div class="card">  
    <div class="section-title"><span class="badge">3</span> الإشارة النهائية</div>  
    <div class="signal">  
        <div>الإشارة</div>  
        <div class="buy" id="signalValue">—</div>  
        <div class="price">سعر الدخول: <strong id="entryPrice">—</strong></div>  
    </div>  
</div>  
<div class="card">  
    <div class="section-title"><span class="badge">4</span> مبلغ الاستثمار</div>  
    <input id="investment" class="input-box" type="number" value="1000" min="1">  
    <div style="margin-top:6px;color:#8ca4b2;">💵 دولار أمريكي</div>  
</div>  
<div class="card">  
    <div class="section-title"><span class="badge">5</span> وقف الخسارة (ATR ديناميكي)</div>  
    <div class="stat">  
        <div class="stat-value" style="color:#ff5757" id="slPrice">—</div>  
        <div style="color:#ff5757;margin-top:6px;">⚠️ خسارة محتملة: <strong id="loss">—</strong> $</div>  
    </div>  
</div>  
<div class="card">  
    <div class="section-title"><span class="badge">6</span> الأهداف الديناميكية</div>  
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
    </div>  
</div>  
<div class="card full">  
    <div class="section-title">⚙️ إعداد التحليل</div>  
    <div class="form-row">  
        <div><label>الزوج المالي</label>  
            <select id="pair" class="input-box" onchange="updatePairDisplay(this.value)">  
                <option value="BTCUSDT" selected>₿ BTCUSDT — بيتكوين</option>  
                <option value="ETHUSDT">Ξ ETHUSDT — إيثيريوم</option>  
                <option value="BNBUSDT">◈ BNBUSDT — بينانس كوين</option>  
                <option value="SOLUSDT">◎ SOLUSDT — سولانا</option>  
                <option value="XRPUSDT">✕ XRPUSDT — ريبل</option>  
                <option value="ADAUSDT">₳ ADAUSDT — كاردانو</option>  
                <option value="DOGEUSDT">🐶 DOGEUSDT — دوجكوين</option>  
                <option value="DOTUSDT">● DOTUSDT — بولكادوت</option>  
                <option value="MATICUSDT">⬡ MATICUSDT — ماتيك</option>  
                <option value="LINKUSDT">🔗 LINKUSDT — تشين لينك</option>  
                <option value="AVAXUSDT">🔺 AVAXUSDT — أفالانش</option>  
                <option value="ATOMUSDT">⚛️ ATOMUSDT — كوزموس</option>  
                <option value="LTCUSDT">Ł LTCUSDT — لايتكوين</option>  
                <option value="UNIUSDT">🦄 UNIUSDT — يونيسواب</option>  
                <option value="PAXGUSDT">🪙 PAXGUSDT — ذهب (مرتبط)</option>  
            </select>  
        </div>  
        <div><label>مبلغ الاستثمار ($)</label><input id="amount" class="input-box" type="number" value="1000"></div>  
        <div><label>مستوى المخاطر</label><select id="riskLevel" class="input-box"><option>متحفظ</option><option selected>متوازن</option><option>عالي</option></select></div>  
    </div>  
    <div class="buttons">  
        <button class="execute" onclick="analyze()">🔍 فحص وتحليل الصفقة</button>  
        <button class="save" onclick="saveTrade()">💾 حفظ للمراقبة</button>  
    </div>  
    <div id="status" class="status"></div>  
    <div id="result" class="result"></div>  
</div>  
</div>  
<div class="footer">  
🤖 نبر وان v4  
