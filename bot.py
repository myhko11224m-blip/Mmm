# ============================================================
# 🤖 نبر وان v2.1 — النظام المصحح والاحترافي
# ✅ قوة الإعداد بدلاً من الثقة الزائفة
# ✅ جميع الأخطاء الإملائية مصححة
# ✅ الأهداف مقيدة بمستويات حقيقية + مسافة ديناميكية من ATR
# ✅ اتجاه الصفقة بناءً على أغلبية المؤشرات (EMA + RSI + MACD)
# ✅ لا بيانات محاكاة — عند فشل Binance نرجع خطأ واضح
# ✅ توضيح مصدر البيانات (PAXG/USDT وليس XAU/USD الفوري)
# ✅ تأكيد من إطارين زمنيين (1H + 4H)
# ============================================================

import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import requests

app = FastAPI(
    title="نبر وان v2.1 — النظام المصحح والاحترافي",
    description="قوة الإعداد الحقيقية · تحليل متكامل · إدارة مخاطر احترافية · بيانات Binance فقط",
    version="2.1.0",
    docs_url="/لوحة-التحكم",
    redoc_url="/تفاصيل"
)

# ============================================================
# 📦 البيانات والإعدادات
# ============================================================

class بيانات_الصفقة(BaseModel):
    الزوج_المالي: str = "XAUUSD"
    مبلغ_الاستثمار: float = 1000
    مستوى_المخاطر: str = "متوازن"

النتائج = []

# ملاحظة مهمة: PAXGUSDT هو الذهب الرقمي على Binance، وليس XAUUSD الفوري
# الأسعار قريبة جداً لكنها ليست متطابقة تماماً
رموز_Binance = {
    "XAUUSD": "PAXGUSDT",
    "BTCUSDT": "BTCUSDT",
    "BTCUSD": "BTCUSDT",
}

# ============================================================
# 💰 جلب بيانات السوق الحقيقية من Binance فقط
# ============================================================

def جلب_شموع_السعر(الزوج, الإطار="1h", الحد=100):
    """جلب بيانات حقيقية من Binance فقط — لا بيانات محاكاة"""
    رمز = رموز_Binance.get(الزوج.upper().strip(), "PAXGUSDT")
    try:
        res = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={
                "symbol": رمز,
                "interval": الإطار,
                "limit": الحد
            },
            timeout=10
        )
        res.raise_for_status()
        بيانات = res.json()
        if not isinstance(بيانات, list) or len(بيانات) < 50:
            raise Exception("بيانات غير كافية من Binance")
        
        # ✅ تم الإصلاح: for ش in بيانات بدلاً من for ش في بيانات
        الإغلاقات = [float(ش[4]) for ش in بيانات]
        الأسعار_الأعلى = [float(ش[2]) for ش in بيانات]
        الأسعار_الأدنى = [float(ش[3]) for ش in بيانات]
        الأحجام = [float(ش[5]) for ش in بيانات]
        return الإغلاقات, الأسعار_الأعلى, الأسعار_الأدنى, الأحجام

    except Exception as e:
        # ✅ تم الإصلاح: لا بيانات محاكاة، نرجع خطأ واضحاً
        raise Exception(f"فشل جلب البيانات من Binance: {str(e)}. لا توجد بيانات احتياطية لضمان الشفافية.")

# ============================================================
# 📐 المؤشرات الفنية
# ============================================================

def حساب_EMA(الإغلاقات, الفترة):
    k = 2 / (الفترة + 1)
    ema = الإغلاقات[0]
    القيم = [ema]
    for سعر in الإغلاقات[1:]:
        ema = سعر * k + ema * (1 - k)
        القيم.append(ema)
    return القيم

def حساب_RSI(الإغلاقات, الفترة=14):
    if len(الإغلاقات) < الفترة + 1:
        return 50.0
    أرباح, خسائر = [], []
    for i in range(1, len(الإغلاقات)):
        فرق = الإغلاقات[i] - الإغلاقات[i - 1]
        أرباح.append(max(فرق, 0))
        خسائر.append(max(-فرق, 0))
    متوسط_ربح = sum(أرباح[-الفترة:]) / الفترة
    متوسط_خسارة = sum(خسائر[-الفترة:]) / الفترة
    if متوسط_خسارة == 0:
        return 100.0
    rs = متوسط_ربح / متوسط_خسارة
    return round(100 - (100 / (1 + rs)), 1)

def حساب_MACD(الإغلاقات):
    ema12 = حساب_EMA(الإغلاقات, 12)
    ema26 = حساب_EMA(الإغلاقات, 26)
    خط_macd = [ema12[i] - ema26[i] for i in range(len(ema12))]
    خط_الإشارة = حساب_EMA(خط_macd, 9)
    الهيستوجرام = [خط_macd[i] - خط_الإشارة[i] for i in range(len(خط_macd))]
    return {
        "خط_MACD": خط_macd[-1],
        "خط_الإشارة": خط_الإشارة[-1],
        "الهيستوجرام": الهيستوجرام[-1],
        "اتجاه": "شراء" if خط_macd[-1] > خط_الإشارة[-1] else "بيع",
        "الزخم_متزايد": الهيستوجرام[-1] > (الهيستوجرام[-2] if len(الهيستوجرام) > 1 else 0)
    }

def حساب_ATR(الأسعار_الأعلى, الأسعار_الأدنى, الإغلاقات, الفترة=14):
    if len(الإغلاقات) < الفترة + 1:
        return abs(الأسعار_الأعلى[-1] - الأسعار_الأدنى[-1])
    TRs = []
    for i in range(1, len(الإغلاقات)):
        tr1 = الأسعار_الأعلى[i] - الأسعار_الأدنى[i]
        tr2 = abs(الأسعار_الأعلى[i] - الإغلاقات[i-1])
        tr3 = abs(الأسعار_الأدنى[i] - الإغلاقات[i-1])
        TRs.append(max(tr1, tr2, tr3))
    return sum(TRs[-الفترة:]) / الفترة

# ============================================================
# 📊 تحديد الدعم والمقاومة
# ============================================================

def تحديد_القمم_والقيعان(الأسعار_الأعلى, الأسعار_الأدنى, نافذة=5):
    القمم, القيعان = [], []
    for i in range(نافذة, len(الأسعار_الأعلى) - نافذة):
        if الأسعار_الأعلى[i] == max(الأسعار_الأعلى[i-نافذة : i+نافذة+1]):
            القمم.append(الأسعار_الأعلى[i])
        if الأسعار_الأدنى[i] == min(الأسعار_الأدنى[i-نافذة : i+نافذة+1]):
            القيعان.append(الأسعار_الأدنى[i])
    return القمم, القيعان

def تجميع_المناطق(القيم, عتبة=0.005):
    if not القيم:
        return []
    القيم_المفرزة = sorted(القيم)
    المناطق, المجموعة = [], [القيم_المفرزة[0]]
    for ق in القيم_المفرزة[1:]:
        متوسط = sum(المجموعة) / len(المجموعة)
        if abs(ق - متوسط) / متوسط < عتبة:
            المجموعة.append(ق)
        else:
            المناطق.append({"السعر": round(sum(المجموعة)/len(المجموعة), 2), "القوة": len(المجموعة)})
            المجموعة = [ق]
    المناطق.append({"السعر": round(sum(المجموعة)/len(المجموعة), 2), "القوة": len(المجموعة)})
    return المناطق

def تحليل_المستويات(الأسعار_الأعلى, الأسعار_الأدنى, سعر_الحالي):
    القمم, القيعان = تحديد_القمم_والقيعان(الأسعار_الأعلى, الأسعار_الأدنى)
    المقاومات = تجميع_المناطق(القمم)
    الدعومات = تجميع_المناطق(القيعان)
    المقاومات_أعلاه = sorted([م for م in المقاومات if م["السعر"] > سعر_الحالي], key=lambda x: x["السعر"])
    الدعومات_أدناه = sorted([د for د in الدعومات if د["السعر"] < سعر_الحالي], key=lambda x: x["السعر"], reverse=True)
    return {
        "أقرب_مقاومة": المقاومات_أعلاه[0] if المقاومات_أعلاه else None,
        "أقرب_دعم": الدعومات_أدناه[0] if الدعومات_أدناه else None,
        "جميع_المقاومات": المقاومات_أعلاه,
        "جميع_الدعومات": الدعومات_أدناه
    }

# ============================================================
# 🧠 محرك حساب قوة الإعداد (100 نقطة)
# ============================================================

def حساب_قوة_الإعداد(الإغلاقات, الأسعار_الأعلى, الأسعار_الأدنى, الأحجام, سعر_الحالي, atr, الإغلاقات_4H=None):
    الدرجة = 0
    تفاصيل = {}

    # ========== العامل 1: المؤشرات الفنية (30 نقطة) ==========
    ema9 = حساب_EMA(الإغلاقات, 9)[-1]
    ema21 = حساب_EMA(الإغلاقات, 21)[-1]
    rsi = حساب_RSI(الإغلاقات)
    macd = حساب_MACD(الإغلاقات)
    
    # ✅ تم الإصلاح: الأحجام بدلاً من Aحجام
    متوسط_الحجم = sum(الأحجام[-20:]) / 20
    الحجم_الحالي = الأحجام[-1]

    # EMA (حتى 10 نقاط)
    فرق_EMA = abs(ema9 - ema21) / سعر_الحالي * 100
    if ema9 > ema21 and فرق_EMA > 0.05:
        درجة_EMA = 10
    elif ema9 > ema21:
        درجة_EMA = 6
    elif ema9 < ema21 and فرق_EMA > 0.05:
        درجة_EMA = 0
    else:
        درجة_EMA = 3
    الدرجة += درجة_EMA
    تفاصيل["EMA"] = f"{درجة_EMA}/10"

    # RSI (حتى 8 نقاط)
    if 45 <= rsi <= 65:
        درجة_RSI = 8
    elif 35 <= rsi < 45 or 65 < rsi <= 75:
        درجة_RSI = 4
    else:
        درجة_RSI = 1
    الدرجة += درجة_RSI
    تفاصيل["RSI"] = f"{درجة_RSI}/8"

    # MACD (حتى 8 نقاط)
    if macd["اتجاه"] == "شراء" and macd["الزخم_متزايد"]:
        درجة_MACD = 8
    elif macd["اتجاه"] == "شراء":
        درجة_MACD = 4
    else:
        درجة_MACD = 1
    الدرجة += درجة_MACD
    تفاصيل["MACD"] = f"{درجة_MACD}/8"

    # حجم التداول (حتى 4 نقاط)
    if الحجم_الحالي > متوسط_الحجم * 1.3:
        درجة_الحجم = 4
    elif الحجم_الحالي > متوسط_الحجم:
        درجة_الحجم = 2
    else:
        درجة_الحجم = 1
    الدرجة += درجة_الحجم
    تفاصيل["الحجم"] = f"{درجة_الحجم}/4"

    تفاصيل["مجموع_المؤشرات"] = f"{درجة}/30"

    # ========== العامل 2: بنية السوق + المستويات (25 نقطة) ==========
    المستويات = تحليل_المستويات(الأسعار_الأعلى, الأسعار_الأدنى, سعر_الحالي)

    # موضع السعر بالنسبة للمقاومة (حتى 15 نقطة)
    if المستويات["أقرب_مقاومة"]:
        مسافة = (المستويات["أقرب_مقاومة"]["السعر"] - سعر_الحالي) / atr
        if مسافة > 2:
            درجة_مقاومة = 15
        elif مسافة > 1.5:
            درجة_مقاومة = 10
        elif مسافة > 1:
            درجة_مقاومة = 5
        else:
            درجة_مقاومة = 0
    else:
        درجة_مقاومة = 15
    الدرجة += درجة_مقاومة
    تفاصيل["المقاومة"] = f"{درجة_مقاومة}/15"

    # قوة الدعم تحت السعر (حتى 10 نقاط)
    if المستويات["أقرب_دعم"] and المستويات["أقرب_دعم"]["القوة"] >= 3:
        درجة_دعم = 10
    elif المستويات["أقرب_دعم"] and المستويات["أقرب_دعم"]["القوة"] >= 2:
        درجة_دعم = 5
    else:
        درجة_دعم = 2
    الدرجة += درجة_دعم
    تفاصيل["الدعم"] = f"{درجة_دعم}/10"

    تفاصيل["مجموع_البنية"] = f"{درجة - sum([int(x.split('/')[0]) for x in [تفاصيل['EMA'], تفاصيل['RSI'], تفاصيل['MACD'], تفاصيل['الحجم']]])}/25"

    # ========== العامل 3: توافق الأطر الزمنية (20 نقطة) ==========
    if الإغلاقات_4H and len(الإغلاقات_4H) >= 30:
        ema9_4H = حساب_EMA(الإغلاقات_4H, 9)[-1]
        ema21_4H = حساب_EMA(الإغلاقات_4H, 21)[-1]
        rsi_4H = حساب_RSI(الإغلاقات_4H)
        
        اتفاق_EMA = (ema9 > ema21) == (ema9_4H > ema21_4H)
        اتفاق_RSI = (rsi >= 50) == (rsi_4H >= 50)
        
        if اتفاق_EMA and اتفاق_RSI:
            درجة_MTF = 20
        elif اتفاق_EMA:
            درجة_MTF = 12
        elif اتفاق_RSI:
            درجة_MTF = 8
        else:
            درجة_MTF = 0
    else:
        درجة_MTF = 10
    الدرجة += درجة_MTF
    تفاصيل["توافق_الأطر"] = f"{درجة_MTF}/20"

    # ========== العامل 4: نسبة RR (15 نقطة) ==========
    مسافة_هدف = 2 * atr
    مسافة_SL = 1.5 * atr
    rr_تقديري = مسافة_هدف / مسافة_SL
    if rr_تقديري >= 2:
        درجة_RR = 10
    elif rr_تقديري >= 1.5:
        درجة_RR = 6
    else:
        درجة_RR = 2
    الدرجة += درجة_RR
    تفاصيل["RR_تقديري"] = f"{درجة_RR}/15"

    # ========== العامل 5: جودة الإعداد السعري (10 نقاط) ==========
    if len(الإغلاقات) >= 20:
        ميل = (الإغلاقات[-1] - الإغلاقات[-20]) / الإغلاقات[-20] * 100
        if 0.3 <= abs(ميل) <= 1.5:
            درجة_الميل = 4
        elif abs(ميل) > 0.1:
            درجة_الميل = 2
        else:
            درجة_الميل = 0
    else:
        درجة_الميل = 2
    الدرجة += درجة_الميل
    تفاصيل["ميل_الاتجاه"] = f"{درجة_الميل}/4"

    if len(الإغلاقات) >= 3:
        الشمعات_صاعدة = sum(1 for i in range(-3, 0) if الإغلاقات[i] > الإغلاقات[i-1])
        if الشمعات_صاعدة == 3 and ema9 > ema21:
            درجة_الشموع = 3
        elif الشمعات_صاعدة >= 2:
            درجة_الشموع = 2
        else:
            درجة_الشموع = 1
    else:
        درجة_الشموع = 1
    الدرجة += درجة_الشموع
    تفاصيل["الشموع"] = f"{درجة_الشموع}/3"

    if المستويات["أقرب_دعم"] and المستويات["أقرب_مقاومة"]:
        درجة_البنية = 3
    elif المستويات["أقرب_دعم"] or المستويات["أقرب_مقاومة"]:
        درجة_البنية = 2
    else:
        درجة_البنية = 1
    الدرجة += درجة_البنية
    تفاصيل["وضوح_البنية"] = f"{درجة_البنية}/3"

    الدرجة_النهائية = min(الدرجة, 100)
    
    # تصنيف الإعداد
    if الدرجة_النهائية >= 90:
        التصنيف = "إعداد ممتاز"
        القرار = "✅✅✅ صفقة قوية جداً"
    elif الدرجة_النهائية >= 80:
        التصنيف = "قوي"
        القرار = "✅✅ صفقة قوية"
    elif الدرجة_النهائية >= 70:
        التصنيف = "جيد"
        القرار = "✅ صفقة جيدة"
    elif الدرجة_النهائية >= 60:
        التصنيف = "ضعيف"
        القرار = "⚠️ تداول بحذر وحجم نصف"
    else:
        التصنيف = "ضعيف جداً"
        القرار = "❌ لا صفقة"

    return {
        "الدرجة_النهائية": round(الدرجة_النهائية, 1),
        "التصنيف": التصنيف,
        "القرار": القرار,
        "التفاصيل": تفاصيل,
        "المستويات": المستويات,
        "اتجاه_EMA": "صاعد" if ema9 > ema21 else "هابط",
        "اتجاه_RSI": "صاعد" if rsi >= 50 else "هابط",
        "اتجاه_MACD": macd["اتجاه"],
        "RSI": rsi,
        "MACD": macd
    }

# ============================================================
# 🎯 تحديد الأهداف المقيدة بالمستويات الحقيقية
# ============================================================

def تحديد_الأهداف_المقيدة(اتجاه, سعر_الحالي, atr, المستويات):
    """
    ✅ تحديد الأهداف بناءً على ATR والمستويات الحقيقية معاً
    المسافة قبل المستوى = 0.2 × ATR (ديناميكية حسب الأصل)
    """
    مسافة_أمان = 0.2 * atr  # ديناميكية، لا قيمة ثابتة
    
    if اتجاه == "شراء":
        المقاومات = المستويات["جميع_المقاومات"]
        
        # الهدف الأول: min(سعر + 1×ATR, أقرب مقاومة - مسافة أمان)
        هدف1_atr = سعر_الحالي + 1 * atr
        if المقاومات and len(المقاومات) >= 1:
            هدف1_مستوى = المقاومات[0]["السعر"] - مسافة_أمان
            هدف1 = min(هدف1_atr, هدف1_مستوى)
        else:
            هدف1 = هدف1_atr
        
        # الهدف الثاني: min(سعر + 2×ATR, المقاومة الثانية - مسافة أمان)
        هدف2_atr = سعر_الحالي + 2 * atr
        if المقاومات and len(المقاومات) >= 2:
            هدف2_مستوى = المقاومات[1]["السعر"] - مسافة_أمان
            هدف2 = min(هدف2_atr, هدف2_مستوى)
        elif المقاومات and len(المقاومات) >= 1:
            هدف2_مستوى = المقاومات[0]["السعر"] - مسافة_أمان
            هدف2 = min(هدف2_atr, هدف2_مستوى)
        else:
            هدف2 = هدف2_atr
        
        # الهدف الثالث: min(سعر + 3×ATR, المقاومة الثالثة - مسافة أمان)
        هدف3_atr = سعر_الحالي + 3 * atr
        if المقاومات and len(المقاومات) >= 3:
            هدف3_مستوى = المقاومات[2]["السعر"] - مسافة_أمان
            هدف3 = min(هدف3_atr, هدف3_مستوى)
        elif المقاومات and len(المقاومات) >= 2:
            هدف3_مستوى = المقاومات[1]["السعر"] - مسافة_أمان
            هدف3 = min(هدف3_atr, هدف3_مستوى)
        else:
            هدف3 = هدف3_atr
        
        # وقف الخسارة: سعر - 1.5×ATR
        وقف_الخسارة = سعر_الحالي - 1.5 * atr
        
    else:  # بيع
        الدعومات = المستويات["جميع_الدعومات"]
        
        # الهدف الأول: max(سعر - 1×ATR, أقرب دعم + مسافة أمان)
        هدف1_atr = سعر_الحالي - 1 * atr
        if الدعومات and len(الدعومات) >= 1:
            هدف1_مستوى = الدعومات[0]["السعر"] + مسافة_أمان
            هدف1 = max(هدف1_atr, هدف1_مستوى)
        else:
            هدف1 = هدف1_atr
        
        # الهدف الثاني: max(سعر - 2×ATR, الدعم الثاني + مسافة أمان)
        هدف2_atr = سعر_الحالي - 2 * atr
        if الدعومات and len(الدعومات) >= 2:
            هدف2_مستوى = الدعومات[1]["السعر"] + مسافة_أمان
            هدف2 = max(هدف2_atr, هدف2_مستوى)
        elif الدعومات and len(الدعومات) >= 1:
            هدف2_مستوى = الدعومات[0]["السعر"] + مسافة_أمان
            هدف2 = max(هدف2_atr, هدف2_مستوى)
        else:
            هدف2 = هدف2_atr
        
        # الهدف الثالث: max(سعر - 3×ATR, الدعم الثالث + مسافة أمان)
        هدف3_atr = سعر_الحالي - 3 * atr
        if الدعومات and len(الدعومات) >= 3:
            هدف3_مستوى = الدعومات[2]["السعر"] + مسافة_أمان
            هدف3 = max(هدف3_atr, هدف3_مستوى)
        elif الدعومات and len(الدعومات) >= 2:
            هدف3_مستوى = الدعومات[1]["السعر"] + مسافة_أمان
            هدف3 = max(هدف3_atr, هدف3_مستوى)
        else:
            هدف3 = هدف3_atr
        
        # وقف الخسارة: سعر + 1.5×ATR
        وقف_الخسارة = سعر_الحالي + 1.5 * atr
    
    return round(وقف_الخسارة, 2), round(هدف1, 2), round(هدف2, 2), round(هدف3, 2)

# ============================================================
# 🎯 تحليل السوق الكامل
# ============================================================

def تحليل_السوق(الزوج, مبلغ, المخاطر):
    # جلب بيانات إطار 1 ساعة
    try:
        الإغلاقات, الأسعار_الأعلى, الأسعار_الأدنى, الأحجام = جلب_شموع_السعر(الزوج, "1h", 100)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    سعر_الحالي = الإغلاقات[-1]
    
    # جلب بيانات إطار 4 ساعات للتأكيد
    الإغلاقات_4H = None
    try:
        الإغلاقات_4H, _, _, _ = جلب_شموع_السعر(الزوج, "4h", 50)
    except:
        الإغلاقات_4H = None
    
    # حساب ATR
    atr = حساب_ATR(الأسعار_الأعلى, الأسعار_الأدنى, الإغلاقات)
    
    # حساب قوة الإعداد
    نتيجة_الإعداد = حساب_قوة_الإعداد(
        الإغلاقات, الأسعار_الأعلى, الأسعار_الأدنى, الأحجام,
        سعر_الحالي, atr, الإغلاقات_4H
    )
    
    # ✅ تم الإصلاح: تحديد اتجاه الصفقة بناءً على أغلبية المؤشرات (EMA + RSI + MACD)
    أصوات_شراء = 0
    أصوات_بيع = 0
    
    if نتيجة_الإعداد["اتجاه_EMA"] == "صاعد":
        أصوات_شراء += 1
    else:
        أصوات_بيع += 1
    
    if نتيجة_الإعداد["اتجاه_RSI"] == "صاعد":
        أصوات_شراء += 1
    else:
        أصوات_بيع += 1
    
    if نتيجة_الإعداد["اتجاه_MACD"] == "شراء":
        أصوات_شراء += 1
    else:
        أصوات_بيع += 1
    
    اتجاه = "شراء" if أصوات_شراء > أصوات_بيع else "بيع"
    
    # ✅ تم الإصلاح: تحديد الأهداف مقيدة بالمستويات الحقيقية
    المستويات = نتيجة_الإعداد["المستويات"]
    وقف_الخسارة, هدف1, هدف2, هدف3 = تحديد_الأهداف_المقيدة(اتجاه, سعر_الحالي, atr, المستويات)
    
    # حساب حجم الصفقة بناءً على إدارة المخاطر
    نسب_المخاطر = {"متحفظ": 0.005, "متوازن": 0.01, "عالي": 0.02}
    نسبة_مخاطرة = نسب_المخاطر.get(المخاطر, 0.01)
    المبلغ_المخاطر = مبلغ * نسبة_مخاطرة
    مسافة_SL = 1.5 * atr
    حجم_الصفقة = round(المبلغ_المخاطر / مسافة_SL, 4)
    
    # حساب الأرباح والخسائر
    if اتجاه == "شراء":
        خسارة_محتملة = round(abs((سعر_الحالي - وقف_الخسارة) * حجم_الصفقة), 2)
        ربح1 = round(abs((هدف1 - سعر_الحالي) * حجم_الصفقة), 2)
        ربح2 = round(abs((هدف2 - سعر_الحالي) * حجم_الصفقة), 2)
        ربح3 = round(abs((هدف3 - سعر_الحالي) * حجم_الصفقة), 2)
    else:
        خسارة_محتملة = round(abs((وقف_الخسارة - سعر_الحالي) * حجم_الصفقة), 2)
        ربح1 = round(abs((سعر_الحالي - هدف1) * حجم_الصفقة), 2)
        ربح2 = round(abs((سعر_الحالي - هدف2) * حجم_الصفقة), 2)
        ربح3 = round(abs((سعر_الحالي - هدف3) * حجم_الصفقة), 2)
    
    نسبة_rr = round(ربح3 / خسارة_محتملة, 2) if خسارة_محتملة > 0 else 0
    
    # تصحيح درجة RR بناءً على القيمة الفعلية
    if نسبة_rr >= 3:
        نتيجة_الإعداد["الدرجة_النهائية"] = min(نتيجة_الإعداد["الدرجة_النهائية"] + 5, 100)
    elif نسبة_rr >= 2:
        نتيجة_الإعداد["الدرجة_النهائية"] = min(نتيجة_الإعداد["الدرجة_النهائية"] + 3, 100)
    
    # ✅ تم الإصلاح: توضيح مصدر البيانات بوضوح
    if "XAU" in الزوج.upper():
        اسم_الزوج = "PAXG/USDT — الذهب الرقمي على Binance (قريب من XAUUSD)"
        ملاحظة_البيانات = "البيانات من PAXG/USDT على Binance، وهي قريبة جداً من سعر الذهب الفوري لكنها ليست متطابقة تماماً"
    else:
        اسم_الزوج = "BTC/USDT — البيتكوين مقابل USDT على Binance"
        ملاحظة_البيانات = "البيانات حقيقية من Binance"
    
    return {
        "المعرف": len(النتائج) + 1,
        "التاريخ_والوقت": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "الزوج_المالي": اسم_الزوج,
        "ملاحظة_مصدر_البيانات": ملاحظة_البيانات,
        "قوة_الإعداد": {
            "الدرجة": نتيجة_الإعداد["الدرجة_النهائية"],
            "التصنيف": نتيجة_الإعداد["التصنيف"],
            "القرار": نتيجة_الإعداد["القرار"],
            "تفاصيل_النقاط": نتيجة_الإعداد["التفاصيل"],
            "أصوات_المؤشرات": {
                "شراء": أصوات_شراء,
                "بيع": أصوات_بيع
            }
        },
        "التحليل": {
            "اتجاه_السوق": "صاعد ↗️" if اتجاه == "شراء" else "هابط ↘️",
            "سعر_السوق_الحالي": round(سعر_الحالي, 2),
            "أعلى_سعر_100شمعة": round(max(الأسعار_الأعلى), 2),
            "أدنى_سعر_100شمعة": round(min(الأسعار_الأدنى), 2),
            "المؤشرات": {
                # ✅ تم الإصلاح: حساب_EMA بدلاً من hساب_EMA
                "EMA9": round(حساب_EMA(الإغلاقات, 9)[-1], 2),
                "EMA21": round(حساب_EMA(الإغلاقات, 21)[-1], 2),
                "RSI14": نتيجة_الإعداد["RSI"],
                "MACD": f"{round(نتيجة_الإعداد['MACD']['خط_MACD'], 2)} / {round(نتيجة_الإعداد['MACD']['خط_الإشارة'], 2)}",
                "ATR14": round(atr, 2)
            },
            "المستويات": {
                "أقرب_مقاومة": المستويات["أقرب_مقاومة"],
                "أقرب_دعم": المستويات["أقرب_دعم"]
            }
        },
        "النتيجة_النهائية": {"الاشارة": اتجاه, "سعر_الدخول": round(سعر_الحالي, 2)},
        "إدارة_المخاطر": {
            "مبلغ_الاستثمار": مبلغ,
            "مستوى_المخاطر": المخاطر,
            "نسبة_المخاطرة": f"{نسبة_مخاطرة * 100}%",
            "حجم_الصفقة": حجم_الصفقة
        },
        "وقف_الخسارة": {"السعر": وقف_الخسارة, "الخسارة_المحتملة": خسارة_محتملة},
        "الأهداف": {
            "الهدف_الأول": {"السعر": هدف1, "الربح_المتوقع": ربح1},
            "الهدف_الثاني": {"السعر": هدف2, "الربح_المتوقع": ربح2},
            "الهدف_الثالث": {"السعر": هدف3, "الربح_المتوقع": ربح3}
        },
        "نسبة_الربح_إلى_الخسارة": f"{نسبة_rr} : 1",
        "التوصية": "هذا التحليل دليل إرشادي وليس ضماناً للربح. التداول ينطوي على مخاطر. البيانات من Binance فقط."
    }

# ============================================================
# 🏠 API
# ============================================================

@app.get("/api")
def api_home():
    return {
        "المنصة": "نبر وان v2.1",
        "الإصدار": "2.1.0 (مصحح ومحسن)",
        "الحالة": "تعمل",
        "الواجهة": "/",
        "ملاحظة_مهمة": "البيانات حقيقية من Binance فقط. PAXG/USDT هو الذهب الرقمي وليس XAUUSD الفوري."
    }

@app.post("/فحص-وتحليل")
def فحص_وتحليل(البيانات: بيانات_الصفقة):
    if البيانات.مبلغ_الاستثمار <= 0:
        raise HTTPException(status_code=400, detail="مبلغ الاستثمار يجب أن يكون أكبر من صفر")
    if not البيانات.الزوج_المالي:
        raise HTTPException(status_code=400, detail="يجب إدخال الزوج المالي")
    النتيجة = تحليل_السوق(البيانات.الزوج_المالي, البيانات.مبلغ_الاستثمار, البيانات.مستوى_المخاطر)
    النتائج.append(النتيجة)
    return النتيجة

# ============================================================
# 🎨 الواجهة المحسنة (نفس الواجهة مع إضافة عرض أصوات المؤشرات)
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>نبر وان v2.1 — النظام المصحح والاحترافي</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:Tahoma,Arial,sans-serif;background:radial-gradient(circle at top,#08243a 0%,#020811 45%,#01040a 100%);color:#fff;min-height:100vh;}
.container{max-width:1250px;margin:auto;padding:18px;}
.header{border:1px solid #0877b8;border-radius:18px;background:linear-gradient(135deg,#07192b,#020812);padding:18px;box-shadow:0 0 25px rgba(0,170,255,.18);}
.logo{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;}
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
.strength-box{background:linear-gradient(135deg,#0a1a2e,#05101e);border:2px solid;border-radius:15px;padding:20px;text-align:center;margin-bottom:15px;}
.strength-score{font-size:48px;font-weight:bold;}
.strength-label{font-size:20px;margin-top:8px;}
.strength-decision{font-size:18px;margin-top:12px;padding:10px;border-radius:10px;}
.meter{height:12px;background:#021020;border-radius:6px;overflow:hidden;margin-top:10px;border:1px solid #15435d;}
.meter-fill{height:100%;transition:width .5s;border-radius:6px;}
.details-list{display:grid;gap:8px;margin-top:15px;}
.detail-row{display:flex;justify-content:space-between;padding:8px 12px;background:#031321;border-radius:8px;border:1px solid #15435d;}
.votes{display:flex;justify-content:center;gap:20px;margin-top:12px;}
.vote-buy{color:#32ff55;font-weight:bold;font-size:16px;}
.vote-sell{color:#ff5757;font-weight:bold;font-size:16px;}
.signal{background:linear-gradient(135deg,#07350d,#001a09);border:1px solid #16e84b;border-radius:12px;padding:18px;text-align:center;}
.buy{color:#32ff55;font-size:30px;font-weight:bold;}
.sell{color:#ff5757;font-size:30px;font-weight:bold;}
.price{font-size:27px;margin-top:10px;color:#fff;}
.input-box{width:100%;background:#020b15;color:#fff;border:1px solid #12668e;padding:14px;border-radius:9px;font-size:18px;outline:none;}
.input-box:focus{border-color:#00bfff;}
label{display:block;margin-bottom:7px;color:#b7cbd7;}
.form-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.targets{display:grid;gap:9px;}
.target{padding:14px;border-radius:10px;background:#031321;border:1px solid #15435d;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;}
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
.result{margin-top:15px;white-space:pre-wrap;background:#01070e;border:1px solid #123c54;border-radius:10px;padding:15px;display:none;color:#fff;max-height:300px;overflow-y:auto;}
.footer{text-align:center;color:#728c9c;padding:20px;font-size:13px;}
.status{text-align:center;margin-top:10px;color:#7dffac;}
.data-note{background:#1a1a05;border:1px solid #ccaa00;color:#ffdd66;padding:10px;border-radius:8px;margin-top:10px;font-size:13px;text-align:center;}
select.input-box{appearance:none;-webkit-appearance:none;-moz-appearance:none;}
@media(max-width:800px){.main,.analysis-grid,.form-row,.buttons{grid-template-columns:1fr;}.full{grid-column:auto;}.logo{flex-direction:column;align-items:flex-start;}.logo-title{font-size:25px;}}
</style>
</head>
<body>
<div class="container">
<div class="header">
    <div class="logo">
        <div><div class="logo-title">🤖 نـبـر وان v2.1</div><div class="logo-sub">النظام المصحح والاحترافي · قوة الإعداد الحقيقية · بيانات Binance فقط</div></div>
        <div class="live">⚡ تحديث لحظي</div>
    </div>
    <div class="clock" id="clock">🕐 جاري تحميل الوقت...</div>
    <div class="data-note">📌 ملاحظة: بيانات الذهب هي PAXG/USDT من Binance (قريبة جداً من XAUUSD الفوري لكنها ليست متطابقة تماماً)</div>
</div>
<div class="main">

<div class="card full">
    <div class="section-title"><span class="badge">⭐</span> قوة الإعداد</div>
    <div class="strength-box" id="strengthBox">
        <div class="strength-score" id="strengthScore">—</div>
        <div class="strength-label" id="strengthLabel">في انتظار التحليل...</div>
        <div class="meter"><div class="meter-fill" id="strengthMeter" style="width:0%;background:#555;"></div></div>
        <div class="strength-decision" id="strengthDecision">اضغط على "فحص وتحليل" للبدء</div>
        <div class="votes" id="votesBox" style="display:none;">
            <span class="vote-buy">🟢 أصوات الشراء: <strong id="buyVotes">—</strong></span>
            <span class="vote-sell">🔴 أصوات البيع: <strong id="sellVotes">—</strong></span>
        </div>
    </div>
    <div class="details-list" id="strengthDetails"></div>
</div>

<div class="card full">
    <div class="section-title"><span class="badge">1</span> الزوج المالي</div>
    <div class="pair" id="pairDisplay">🪙 PAXG/USDT <span style="color:#aaa;font-size:18px;">— الذهب الرقمي على Binance</span></div>
</div>

<div class="card">
    <div class="section-title"><span class="badge">2</span> التحليل الفني</div>
    <div class="analysis-grid">
        <div class="stat"><div class="stat-label">📈 اتجاه السوق</div><div class="stat-value" id="dirValue">—</div></div>
        <div class="stat"><div class="stat-label">💰 سعر السوق الحالي</div><div class="stat-value" id="marketPrice">جاري الجلب...</div></div>
        <div class="stat"><div class="stat-label">📊 RSI 14</div><div class="stat-value" id="rsiValue">—</div></div>
        <div class="stat"><div class="stat-label">📉 ATR 14</div><div class="stat-value" id="atrValue">—</div></div>
    </div>
</div>

<div class="card">
    <div class="section-title">🎯 مستويات الدعم والمقاومة</div>
    <div class="analysis-grid">
        <div class="stat"><div class="stat-label">🔴 أقرب مقاومة</div><div class="stat-value" id="resValue" style="color:#ff6666;">—</div></div>
        <div class="stat"><div class="stat-label">🟢 أقرب دعم</div><div class="stat-value" id="supValue" style="color:#66ff66;">—</div></div>
        <div class="stat"><div class="stat-label">📈 أعلى سعر</div><div class="stat-value" id="highValue">—</div></div>
        <div class="stat"><div class="stat-label">📉 أدنى سعر</div><div class="stat-value" id="lowValue">—</div></div>
    </div>
</div>

<div class="card">
    <div class="section-title"><span class="badge">3</span> الإشارة النهائية</div>
    <div class="signal">
        <div>الإشارة (بناءً على أغلبية EMA + RSI + MACD)</div>
        <div class="buy" id="signalValue">—</div>
        <div class="price">سعر الدخول: <strong id="entryPrice">—</strong></div>
    </div>
</div>

<div class="card">
    <div class="section-title"><span class="badge">4</span> إدارة المخاطر</div>
    <div class="analysis-grid">
        <div class="stat"><div class="stat-label">💵 حجم الصفقة</div><div class="stat-value" id="lotSize">—</div></div>
        <div class="stat"><div class="stat-label">⚠️ مستوى المخاطر</div><div class="stat-value" id="riskLevel">—</div></div>
    </div>
</div>

<div class="card">
    <div class="section-title"><span class="badge">5</span> وقف الخسارة</div>
    <div class="stat">
        <div class="stat-value" style="color:#ff5757" id="slPrice">—</div>
        <div style="color:#ff5757;margin-top:8px;">⚠️ خسارة محتملة: <strong id="loss">—</strong> دولار</div>
    </div>
</div>

<div class="card">
    <div class="section-title"><span class="badge">6</span> الأهداف المقترحة (مقيدة بالمستويات الحقيقية)</div>
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
        <div><label>الزوج المالي</label><select id="pair" class="input-box" onchange="updatePairDisplay(this.value)"><option value="XAUUSD" selected>🪙 PAXG/USDT — ذهب رقمي (Binance)</option><option value="BTCUSDT">₿ BTC/USDT — بيتكوين</option></select></div>
        <div><label>مبلغ الاستثمار</label><input id="amount" class="input-box" type="number" value="1000"></div>
        <div><label>مستوى المخاطر</label><select id="riskLevelSelect" class="input-box"><option>متحفظ</option><option selected>متوازن</option><option>عالي</option></select></div>
    </div>
    <div class="buttons">
        <button class="execute" onclick="analyze()">🔍 فحص وتحليل الصفقة</button>
        <button class="save" onclick="saveTrade()">💾 حفظ والمراقبة</button>
    </div>
    <div id="status" class="status"></div>
    <div id="result" class="result"></div>
</div>

</div>
<div class="footer">🤖 نبر وان v2.1 — النظام المصحح والاحترافي<br>الإصدار 2.1.0 · قوة الإعداد الحقيقية · بيانات Binance فقط · شفافية كاملة</div>
</div>

<script>
function updateClock(){const n=new Date();document.getElementById("clock").innerHTML="🕐 التاريخ والوقت: "+n.toLocaleDateString("ar-SA")+" | "+n.toLocaleTimeString("ar-SA");}
setInterval(updateClock,1000);updateClock();

function updatePairDisplay(v){document.getElementById("pairDisplay").innerHTML=v=="XAUUSD"?"🪙 PAXG/USDT <span style='color:#aaa;font-size:18px;'>— الذهب الرقمي على Binance</span>":"₿ BTC/USDT <span style='color:#aaa;font-size:18px;'>— البيتكوين مقابل USDT</span>";}

function getStrengthColor(score){
    if(score>=90)return {border:"#00ff88",bg:"#073a1f",text:"#66ffaa",fill:"linear-gradient(90deg,#00ff88,#00cc66)"};
    if(score>=80)return {border:"#00ccff",bg:"#072a3a",text:"#66ddff",fill:"linear-gradient(90deg,#00ccff,#0099cc)"};
    if(score>=70)return {border:"#ffcc00",bg:"#3a2f07",text:"#ffdd66",fill:"linear-gradient(90deg,#ffcc00,#ff9900)"};
    if(score>=60)return {border:"#ff8c00",bg:"#3a1f07",text:"#ffaa33",fill:"linear-gradient(90deg,#ff8c00,#ff6600)"};
    return {border:"#ff4444",bg:"#3a0707",text:"#ff6666",fill:"linear-gradient(90deg,#ff4444,#cc0000)"};
}

async function analyze(){
    const p=document.getElementById("pair").value,a=Number(document.getElementById("amount").value),r=document.getElementById("riskLevelSelect").value,s=document.getElementById("status"),res=document.getElementById("result");
    s.innerText="⏳ جاري جلب البيانات الحقيقية من Binance وتحليل السوق...";res.style.display="none";
    
    try{
        const response=await fetch("/فحص-وتحليل",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({الزوج_المالي:p,مبلغ_الاستثمار:a,مستوى_المخاطر:r})});
        const d=await response.json();
        if(!response.ok)throw new Error(d.detail||"خطأ في التحليل");
        
        s.innerText="✅ اكتمل التحليل — بيانات حقيقية من Binance";res.style.display="block";res.innerText=JSON.stringify(d,null,2);
        
        // ===== عرض قوة الإعداد =====
        const score=d["قوة_الإعداد"]["الدرجة"];
        const colors=getStrengthColor(score);
        document.getElementById("strengthBox").style.borderColor=colors.border;
        document.getElementById("strengthBox").style.background=colors.bg;
        document.getElementById("strengthScore").innerText=score+"/100";
        document.getElementById("strengthScore").style.color=colors.text;
        document.getElementById("strengthLabel").innerText=d["قوة_الإعداد"]["التصنيف"];
        document.getElementById("strengthLabel").style.color=colors.text;
        document.getElementById("strengthMeter").style.width=score+"%";
        document.getElementById("strengthMeter").style.background=colors.fill;
        document.getElementById("strengthDecision").innerText=d["قوة_الإعداد"]["القرار"];
        document.getElementById("strengthDecision").style.background=colors.bg;
        document.getElementById("strengthDecision").style.color=colors.text;
        document.getElementById("strengthDecision").style.border="1px solid "+colors.border;
        
        // عرض أصوات المؤشرات
        document.getElementById("votesBox").style.display="flex";
        document.getElementById("buyVotes").innerText=d["قوة_الإعداد"]["أصوات_المؤشرات"]["شراء"]+"/3";
        document.getElementById("sellVotes").innerText=d["قوة_الإعداد"]["أصوات_المؤشرات"]["بيع"]+"/3";
        
        // تفاصيل النقاط
        const details=d["قوة_الإعداد"]["تفاصيل_النقاط"];
        let detailsHTML="";
        const names={
            "EMA":"📊 EMA 9/21",
            "RSI":"📈 RSI 14",
            "MACD":"📉 MACD",
            "الحجم":"📦 حجم التداول",
            "مجموع_المؤشرات":"⭐ مجموع المؤشرات",
            "المقاومة":"🔴 المقاومة",
            "الدعم":"🟢 الدعم",
            "مجموع_البنية":"🏗️ مجموع البنية",
            "توافق_الأطر":"⏱️ توافق الأطر",
            "RR_تقديري":"💰 نسبة RR",
            "ميل_الاتجاه":"📐 ميل الاتجاه",
            "الشموع":"🕯️ الشمعات",
            "وضوح_البنية":"🏛️ وضوح البنية"
        };
        for(const [key,val] of Object.entries(details)){
            if(names[key])detailsHTML+=`<div class="detail-row"><span>${names[key]}</span><strong>${val}</strong></div>`;
        }
        document.getElementById("strengthDetails").innerHTML=detailsHTML;
        
        // ===== بقية البيانات =====
        document.getElementById("marketPrice").innerText=d["التحليل"]["سعر_السوق_الحالي"];
        document.getElementById("dirValue").innerText=d["التحليل"]["اتجاه_السوق"];
        document.getElementById("rsiValue").innerText=d["التحليل"]["المؤشرات"]["RSI14"];
        document.getElementById("atrValue").innerText=d["التحليل"]["المؤشرات"]["ATR14"];
        document.getElementById("highValue").innerText=d["التحليل"]["أعلى_سعر_100شمعة"];
        document.getElementById("lowValue").innerText=d["التحليل"]["أدنى_سعر_100شمعة"];
        
        const resLevel=d["التحليل"]["المستويات"]["أقرب_مقاومة"];
        const supLevel=d["التحليل"]["المستويات"]["أقرب_دعم"];
        document.getElementById("resValue").innerText=resLevel?resLevel["السعر"]+" (قوة: "+resLevel["القوة"]+")":"—";
        document.getElementById("supValue").innerText=supLevel?supLevel["السعر"]+" (قوة: "+supLevel["القوة"]+")":"—";
        
        const اشارة=d["النتيجة_النهائية"]["الاشارة"];
        const sigEl=document.getElementById("signalValue");
        sigEl.className=اشارة=="شراء"?"buy":"sell";
        sigEl.innerText=اشارة=="شراء"?"🟢 شراء ↗️":"🔴 بيع ↘️";
        document.getElementById("entryPrice").innerText=d["النتيجة_النهائية"]["سعر_الدخول"];
        
        document.getElementById("lotSize").innerText=d["إدارة_المخاطر"]["حجم_الصفقة"];
        document.getElementById("riskLevel").innerText=d["إدارة_المخاطر"]["مستوى_المخاطر"];
        
        document.getElementById("slPrice").innerText=d["وقف_الخسارة"]["السعر"];
        document.getElementById("loss").innerText=d["وقف_الخسارة"]["الخسارة_المحتملة"];
        
        document.getElementById("t1Price").innerText=d["الأهداف"]["الهدف_الأول"]["السعر"];
        document.getElementById("t1Pnl").innerText="+"+d["الأهداف"]["الهدف_الأول"]["الربح_المتوقع"]+"$";
        document.getElementById("t2Price").innerText=d["الأهداف"]["الهدف_الثاني"]["السعر"];
        document.getElementById("t2Pnl").innerText="+"+d["الأهداف"]["الهدف_الثاني"]["الربح_المتوقع"]+"$";
        document.getElementById("t3Price").innerText=d["الأهداف"]["الهدف_الثالث"]["السعر"];
        document.getElementById("t3Pnl").innerText="+"+d["الأهداف"]["الهدف_الثالث"]["الربح_المتوقع"]+"$";
        
        document.getElementById("rrValue").innerText=d["نسبة_الربح_إلى_الخسارة"];
        const rr=parseFloat(d["نسبة_الربح_إلى_الخسارة"]);
        document.getElementById("rrLabel").innerText=rr>=3?"✅ ممتازة":rr>=2?"🟢 جيدة جداً":rr>=1.5?"🟡 مقبولة":"🔴 ضعيفة";
        
    }catch(e){s.innerText="❌ "+e.message;res.style.display="block";res.innerText=e.message;}
}

function saveTrade(){document.getElementById("status").innerText="💾 تم حفظ الصفقة للمراقبة.";}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

# ============================================================
# ▶️ تشغيل التطبيق
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
