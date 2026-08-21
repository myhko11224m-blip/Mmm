# ============================================================
# 🤖 نبر وان v4.0 — محلل الشارت بالصور (نسخة مصححة)
# ============================================================
# التعديلات الجوهرية عن v3.0:
#
# 1) ❌ حذف "المقياس السعري الوهمي" (100 → 110) نهائياً.
#    إذا ما قدر OCR يوفر سعرين حقيقيين على الأقل من محاور الشارت،
#    النظام يرفض إعطاء إشارة تداول أو أهداف أو وقف خسارة،
#    ويرجّع رسالة خطأ واضحة بدل أرقام مفبركة.
#
# 2) 🕯️ اكتشاف شموع أكثر مرونة (نطاقات ألوان أوسع + خيار
#    fallback بالتدرج الرمادي لو الألوان ما نفعت) بدل الاعتماد
#    الكامل على ثيم ألوان واحد.
#
# 3) 🔒 تخزين النتائج Thread-safe مع سقف أقصى للحجم (بدل قائمة
#    عالمية بلا حدود وبدون قفل).
#
# 4) 🛡️ التحقق من نوع الملف عبر "التوقيع الحقيقي" للبايتات
#    (magic bytes) مش بس امتداد الاسم.
#
# 5) ⚠️ تحذير واضح ودائم في كل استجابة: هذا تحليل تقريبي
#    لأغراض تعليمية / بحثية، وليس توصية استثمارية، ولا يجوز
#    اعتماده للتداول الفعلي بدون بيانات OHLC حقيقية من مزود بيانات.
# ============================================================

import os
import re
import threading
from datetime import datetime

import cv2
import numpy as np
import pytesseract

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn


# ============================================================
# ⚙️ التطبيق
# ============================================================

app = FastAPI(
    title="نبر وان v4.0 — محلل الشارت بالصور",
    description="محلل تداول تقريبي يعتمد على صورة الشارت (لأغراض تعليمية فقط)",
    version="4.0.0",
    docs_url="/لوحة-التحكم",
    redoc_url="/تفاصيل"
)

تنويه_عام = (
    "⚠️ هذا التحليل مستخرج تقريبياً من صورة (وليس من بيانات OHLC حقيقية)، "
    "وهو لأغراض تعليمية وبحثية فقط وليس توصية استثمارية أو مالية. "
    "أي قرار تداول فعلي يجب أن يعتمد على بيانات سعرية موثوقة من مزود بيانات، "
    "وعلى مسؤوليتك الخاصة."
)


# ============================================================
# 🔒 تخزين النتائج (Thread-safe + سقف أقصى)
# ============================================================

_قفل_النتائج = threading.Lock()
_الحد_الأقصى_للنتائج = 500
النتائج: list = []


def حفظ_نتيجة(نتيجة: dict):
    with _قفل_النتائج:
        النتائج.append(نتيجة)
        if len(النتائج) > _الحد_الأقصى_للنتائج:
            del النتائج[: len(النتائج) - _الحد_الأقصى_للنتائج]


def جلب_آخر_النتائج(عدد: int = 50):
    with _قفل_النتائج:
        return list(النتائج[-عدد:]), len(النتائج)


# ============================================================
# 🛡️ التحقق من نوع الملف عبر توقيع البايتات الحقيقي
# ============================================================

_تواقيع_الصور = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # يحتاج تحقق إضافي أدناه
}


def التحقق_من_نوع_الصورة(بيانات: bytes) -> str:
    if not بيانات or len(بيانات) < 12:
        raise Exception("الملف فارغ أو صغير جداً ليكون صورة صالحة")

    if بيانات.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    if بيانات.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if بيانات[:4] == b"RIFF" and بيانات[8:12] == b"WEBP":
        return "webp"

    raise Exception(
        "نوع الملف غير مدعوم أو ملف تالف. المسموح فقط: JPEG / PNG / WEBP حقيقية "
        "(تم التحقق من محتوى الملف وليس فقط اسمه)."
    )


# ============================================================
# 🖼️ قراءة الصورة
# ============================================================

def قراءة_الصورة(بيانات_الصورة: bytes):
    التحقق_من_نوع_الصورة(بيانات_الصورة)

    try:
        مصفوفة = np.frombuffer(بيانات_الصورة, dtype=np.uint8)
        صورة = cv2.imdecode(مصفوفة, cv2.IMREAD_COLOR)

        if صورة is None:
            raise Exception("تعذر فك ترميز الصورة (الملف قد يكون تالفاً)")

        if صورة.shape[0] < 200 or صورة.shape[1] < 300:
            raise Exception("الصورة صغيرة جداً للتحليل (الحد الأدنى تقريباً 300x200)")

        # سقف أعلى معقول لمنع صور ضخمة تستهلك الذاكرة/المعالجة
        if صورة.shape[0] > 6000 or صورة.shape[1] > 6000:
            raise Exception("الصورة كبيرة جداً (الحد الأقصى 6000x6000 بكسل تقريباً)")

        return صورة

    except Exception as e:
        raise Exception(f"فشل قراءة الصورة: {str(e)}")


def تجهيز_الصورة(صورة):
    رمادي = cv2.cvtColor(صورة, cv2.COLOR_BGR2GRAY)
    رمادي = cv2.GaussianBlur(رمادي, (3, 3), 0)
    return رمادي


# ============================================================
# 🔤 استخراج النص والأسعار (OCR)
# ============================================================

def استخراج_النص_من_الصورة(صورة):
    try:
        رمادي = تجهيز_الصورة(صورة)
        ثنائي = cv2.adaptiveThreshold(
            رمادي, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )
        نص = pytesseract.image_to_string(ثنائي, lang="eng")
        return نص.strip()
    except Exception:
        return ""


def استخراج_الأسعار_من_النص(النص):
    if not النص:
        return []

    النمط = r'(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?!\d)'
    القيم = re.findall(النمط, النص)

    أسعار = []
    for قيمة in القيم:
        try:
            قيمة = قيمة.replace(",", "")
            رقم = float(قيمة)
            # فلترة أرقام غير منطقية كأسعار (مثل تواريخ أو أرقام صفحات)
            if 0 < رقم < 10_000_000:
                أسعار.append(رقم)
        except Exception:
            continue

    return أسعار


def استخراج_أسعار_المحور_العمودي(صورة, منطقة_الرسم):
    """
    محاولة أدق: قراءة النص فقط من الشريط الجانبي الأيمن (حيث توضع
    أسعار المحور العمودي عادة في أغلب منصات التداول)، بدل قراءة
    الصورة كاملة (وبالتالي تقليل التلوث من أرقام غير متعلقة بالسعر
    مثل الوقت أو حجم التداول).
    """
    الارتفاع, العرض = صورة.shape[:2]
    x1 = int(العرض * 0.90)
    شريط_الأسعار = صورة[:, x1:العرض]

    نص = استخراج_النص_من_الصورة(شريط_الأسعار)
    return استخراج_الأسعار_من_النص(نص)


# ============================================================
# 📊 اكتشاف منطقة الرسم
# ============================================================

def اكتشاف_منطقة_الشارت(صورة):
    الارتفاع, العرض = صورة.shape[:2]
    x1 = int(العرض * 0.03)
    x2 = int(العرض * 0.90)  # نستبعد شريط الأسعار الجانبي من منطقة الشموع
    y1 = int(الارتفاع * 0.08)
    y2 = int(الارتفاع * 0.78)
    return صورة[y1:y2, x1:x2]


# ============================================================
# 🕯️ اكتشاف الشموع (نطاقات أوسع + fallback رمادي)
# ============================================================

def _تنقية_وتجميع_قناع(قناع, منطقة):
    قناع = cv2.morphologyEx(قناع, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    عدد, تسميات, إحصائيات, مراكز = cv2.connectedComponentsWithStats(قناع, 8)

    عناصر = []
    for i in range(1, عدد):
        x = إحصائيات[i, cv2.CC_STAT_LEFT]
        y = إحصائيات[i, cv2.CC_STAT_TOP]
        w = إحصائيات[i, cv2.CC_STAT_WIDTH]
        h = إحصائيات[i, cv2.CC_STAT_HEIGHT]
        area = إحصائيات[i, cv2.CC_STAT_AREA]

        if area < 5 or h < 4:
            continue
        # نسبة عرض متكيفة مع حجم الصورة بدل رقم ثابت (30px) كان يكسر
        # على صور بدقة عالية أو صور مصغّرة
        if w > max(30, منطقة.shape[1] * 0.03):
            continue
        if h > منطقة.shape[0] * 0.7:
            continue

        عناصر.append({"x": x + w / 2, "y": y, "w": w, "h": h, "area": area})

    return عناصر


def اكتشاف_الشموع(منطقة):
    if منطقة is None or منطقة.size == 0:
        return []

    hsv = cv2.cvtColor(منطقة, cv2.COLOR_BGR2HSV)

    # نطاقات ألوان أوسع من v3.0 لتغطية ثيمات شارت أكثر
    # (ألوان فاتحة/غامقة لأخضر وأحمر، وإضافة أزرق/برتقالي شائعين
    # في بعض منصات التداول)
    أقنعة = [
        cv2.inRange(hsv, np.array([30, 25, 25]), np.array([100, 255, 255])),   # أخضر واسع
        cv2.inRange(hsv, np.array([0, 35, 25]), np.array([20, 255, 255])),     # أحمر واسع 1
        cv2.inRange(hsv, np.array([155, 35, 25]), np.array([179, 255, 255])),  # أحمر واسع 2
        cv2.inRange(hsv, np.array([95, 35, 40]), np.array([135, 255, 255])),   # أزرق (بعض المنصات)
    ]

    كل_الشموع = []
    for قناع in أقنعة:
        كل_الشموع.extend(_تنقية_وتجميع_قناع(قناع, منطقة))

    # Fallback: لو الألوان ما أعطت نتائج كافية، نجرب استخراج
    # الأعمدة الداكنة/الفاتحة عن الخلفية بالتدرج الرمادي
    if len(كل_الشموع) < 20:
        رمادي = cv2.cvtColor(منطقة, cv2.COLOR_BGR2GRAY)
        _, ثنائي = cv2.threshold(
            رمادي, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        عكس = cv2.bitwise_not(ثنائي)
        كل_الشموع.extend(_تنقية_وتجميع_قناع(عكس, منطقة))
        كل_الشموع.extend(_تنقية_وتجميع_قناع(ثنائي, منطقة))

    كل_الشموع.sort(key=lambda x: x["x"])

    شموع_نهائية = []
    for شمعة in كل_الشموع:
        if not شموع_نهائية:
            شموع_نهائية.append(شمعة)
            continue
        السابقة = شموع_نهائية[-1]
        if abs(شمعة["x"] - السابقة["x"]) < 4:
            if شمعة["area"] > السابقة["area"]:
                شموع_نهائية[-1] = شمعة
        else:
            شموع_نهائية.append(شمعة)

    return شموع_نهائية


# ============================================================
# 📈 تحويل الشموع إلى سلسلة سعرية — **بدون مقياس وهمي**
# ============================================================

class خطأ_مقياس_سعري(Exception):
    """يُرفع عندما لا توجد بيانات كافية لتحديد مقياس سعري حقيقي."""
    pass


def تحويل_الشموع_إلى_أسعار(الشموع, أسعار_OCR):
    """
    ⚠️ التعديل الجوهري: لم يعد هناك أي fallback لمقياس وهمي.
    إذا لم نملك سعرين حقيقيين على الأقل من OCR، نرفع استثناء صريح
    بدل اختلاق أرقام (100–110) قد تُقرأ كإشارة تداول حقيقية.
    """
    if not الشموع or len(الشموع) < 2:
        raise خطأ_مقياس_سعري("لا توجد شموع كافية لبناء سلسلة سعرية")

    if not أسعار_OCR or len(أسعار_OCR) < 2:
        raise خطأ_مقياس_سعري(
            "تعذّر قراءة سعرين حقيقيين على الأقل من محور الأسعار في الصورة. "
            "لن يتم إنشاء إشارة تداول لتفادي إعطاء أرقام وهمية. "
            "ارفع صورة أوضح تظهر فيها أرقام محور السعر (يمين الشارت) بشكل جيد."
        )

    مواضع_y = [شمعة["y"] + شمعة["h"] / 2 for شمعة in الشموع]
    أعلى_Y, أدنى_Y = max(مواضع_y), min(مواضع_y)

    if أعلى_Y == أدنى_Y:
        raise خطأ_مقياس_سعري("كل الشموع المكتشفة على نفس الارتفاع، تعذر بناء مقياس")

    سعر_أدنى, سعر_أعلى = min(أسعار_OCR), max(أسعار_OCR)

    if سعر_أعلى <= سعر_أدنى:
        raise خطأ_مقياس_سعري("الأسعار المستخرجة من OCR غير منطقية (قيمة عليا <= قيمة دنيا)")

    def تحويل(y):
        نسبة = (أعلى_Y - y) / (أعلى_Y - أدنى_Y)
        return سعر_أدنى + (نسبة * (سعر_أعلى - سعر_أدنى))

    الإغلاقات, الأعلى, الأدنى = [], [], []
    for شمعة in الشموع:
        y, h = شمعة["y"], شمعة["h"]
        مركز = y + h / 2
        close = تحويل(مركز)
        high = تحويل(y)
        low = تحويل(y + h)
        if high < low:
            high, low = low, high
        الإغلاقات.append(float(close))
        الأعلى.append(float(high))
        الأدنى.append(float(low))

    return الإغلاقات, الأعلى, الأدنى


# ============================================================
# 📐 المؤشرات الفنية (كما هي — الحسابات كانت صحيحة أصلاً)
# ============================================================

def حساب_EMA_قياسي(الإغلاقات, الفترة):
    if len(الإغلاقات) < الفترة:
        return [الإغلاقات[0]] * len(الإغلاقات)

    k = 2 / (الفترة + 1)
    القيم = []
    ema = sum(الإغلاقات[:الفترة]) / الفترة
    القيم.extend([ema] * الفترة)

    for سعر in الإغلاقات[الفترة:]:
        ema = (سعر * k) + (ema * (1 - k))
        القيم.append(ema)

    return القيم


def حساب_RSI_Wilder(الإغلاقات, الفترة=14):
    if len(الإغلاقات) < الفترة + 1:
        return 50.0

    التغيرات = [الإغلاقات[i] - الإغلاقات[i - 1] for i in range(1, len(الإغلاقات))]
    الأرباح = [max(ت, 0) for ت in التغيرات]
    الخسائر = [abs(min(ت, 0)) for ت in التغيرات]

    متوسط_ربح = sum(الأرباح[:الفترة]) / الفترة
    متوسط_خسارة = sum(الخسائر[:الفترة]) / الفترة
    α = 1 / الفترة

    for i in range(الفترة, len(التغيرات)):
        متوسط_ربح = متوسط_ربح * (1 - α) + الأرباح[i] * α
        متوسط_خسارة = متوسط_خسارة * (1 - α) + الخسائر[i] * α

    if متوسط_خسارة == 0:
        return 100.0

    rs = متوسط_ربح / متوسط_خسارة
    return round(100 - (100 / (1 + rs)), 1)


def حساب_MACD_قياسي(الإغلاقات):
    ema12 = حساب_EMA_قياسي(الإغلاقات, 12)
    ema26 = حساب_EMA_قياسي(الإغلاقات, 26)
    خط_macd = [ema12[i] - ema26[i] for i in range(len(ema12))]
    خط_الإشارة = حساب_EMA_قياسي(خط_macd, 9)
    الهيستوجرام = [خط_macd[i] - خط_الإشارة[i] for i in range(len(خط_macd))]

    return {
        "خط_MACD": خط_macd[-1],
        "خط_الإشارة": خط_الإشارة[-1],
        "الهيستوجرام": الهيستوجرام[-1],
        "اتجاه": "شراء" if خط_macd[-1] > خط_الإشارة[-1] else "بيع",
        "الزخم_متزايد": الهيستوجرام[-1] > (الهيستوجرام[-2] if len(الهيستوجرام) > 1 else 0)
    }


def حساب_ATR_Wilder(الأعلى, الأدنى, الإغلاقات, الفترة=14):
    if len(الإغلاقات) < الفترة + 1:
        return abs(الأعلى[-1] - الأدنى[-1])

    TRs = []
    for i in range(1, len(الإغلاقات)):
        tr1 = الأعلى[i] - الأدنى[i]
        tr2 = abs(الأعلى[i] - الإغلاقات[i - 1])
        tr3 = abs(الأدنى[i] - الإغلاقات[i - 1])
        TRs.append(max(tr1, tr2, tr3))

    atr = sum(TRs[:الفترة]) / الفترة
    α = 1 / الفترة
    for i in range(الفترة, len(TRs)):
        atr = atr * (1 - α) + TRs[i] * α

    return atr


def تحديد_القمم_والقيعان(الأعلى, الأدنى, نافذة=5):
    القمم, القيعان = [], []
    if len(الأعلى) < (نافذة * 2 + 1):
        return القمم, القيعان

    for i in range(نافذة, len(الأعلى) - نافذة):
        if الأعلى[i] == max(الأعلى[i - نافذة: i + نافذة + 1]):
            القمم.append(الأعلى[i])
        if الأدنى[i] == min(الأدنى[i - نافذة: i + نافذة + 1]):
            القيعان.append(الأدنى[i])

    return القمم, القيعان


def تجميع_المناطق(القيم, عتبة=0.005):
    if not القيم:
        return []

    القيم_المفرزة = sorted(القيم)
    المناطق = []
    المجموعة = [القيم_المفرزة[0]]

    for ق in القيم_المفرزة[1:]:
        متوسط = sum(المجموعة) / len(المجموعة)
        if متوسط != 0 and (abs(ق - متوسط) / متوسط < عتبة):
            المجموعة.append(ق)
        else:
            المناطق.append({"السعر": round(sum(المجموعة) / len(المجموعة), 5), "القوة": len(المجموعة)})
            المجموعة = [ق]

    المناطق.append({"السعر": round(sum(المجموعة) / len(المجموعة), 5), "القوة": len(المجموعة)})
    return المناطق


def تحليل_المستويات(الأعلى, الأدنى, سعر_الحالي):
    القمم, القيعان = تحديد_القمم_والقيعان(الأعلى, الأدنى)
    المقاومات = تجميع_المناطق(القمم)
    الدعومات = تجميع_المناطق(القيعان)

    المقاومات_أعلاه = sorted(
        [م for م in المقاومات if م["السعر"] > سعر_الحالي],
        key=lambda x: x["السعر"]
    )
    الدعومات_أدناه = sorted(
        [د for د in الدعومات if د["السعر"] < سعر_الحالي],
        key=lambda x: x["السعر"], reverse=True
    )

    return {
        "أقرب_مقاومة": المقاومات_أعلاه[0] if المقاومات_أعلاه else None,
        "أقرب_دعم": الدعومات_أدناه[0] if الدعومات_أدناه else None,
        "جميع_المقاومات": المقاومات_أعلاه,
        "جميع_الدعومات": الدعومات_أدناه
    }


def تحديد_الاتجاه(الإغلاقات):
    if len(الإغلاقات) < 30:
        return "محايد"

    ema9 = حساب_EMA_قياسي(الإغلاقات, 9)[-1]
    ema21 = حساب_EMA_قياسي(الإغلاقات, 21)[-1]
    ema50 = حساب_EMA_قياسي(الإغلاقات, 50)[-1]
    rsi = حساب_RSI_Wilder(الإغلاقات)
    macd = حساب_MACD_قياسي(الإغلاقات)

    نقاط_شراء = نقاط_بيع = 0

    if ema9 > ema21: نقاط_شراء += 2
    else: نقاط_بيع += 2

    if ema21 > ema50: نقاط_شراء += 2
    else: نقاط_بيع += 2

    if rsi >= 50: نقاط_شراء += 1
    else: نقاط_بيع += 1

    if macd["اتجاه"] == "شراء": نقاط_شراء += 2
    else: نقاط_بيع += 2

    if macd["الزخم_متزايد"] and macd["اتجاه"] == "شراء": نقاط_شراء += 1
    if macd["الزخم_متزايد"] and macd["اتجاه"] == "بيع": نقاط_بيع += 1

    if abs(نقاط_شراء - نقاط_بيع) <= 1:
        return "محايد"

    return "شراء" if نقاط_شراء > نقاط_بيع else "بيع"


def حساب_قوة_الإعداد(الإغلاقات, الأعلى, الأدنى, سعر_الحالي, atr, اتجاه):
    الدرجة = 0
    تفاصيل = {}

    ema9 = حساب_EMA_قياسي(الإغلاقات, 9)[-1]
    ema21 = حساب_EMA_قياسي(الإغلاقات, 21)[-1]
    rsi = حساب_RSI_Wilder(الإغلاقات)
    macd = حساب_MACD_قياسي(الإغلاقات)

    if اتجاه == "شراء":
        درجة_EMA = 10 if ema9 > ema21 else 0
    elif اتجاه == "بيع":
        درجة_EMA = 10 if ema9 < ema21 else 0
    else:
        درجة_EMA = 0
    الدرجة += درجة_EMA
    تفاصيل["EMA_قياسي"] = f"{درجة_EMA}/10"

    if اتجاه == "شراء":
        درجة_RSI = 8 if 45 <= rsi <= 65 else (4 if 35 <= rsi < 45 else 1)
    elif اتجاه == "بيع":
        درجة_RSI = 8 if 35 <= rsi <= 55 else (4 if 55 < rsi <= 65 else 1)
    else:
        درجة_RSI = 0
    الدرجة += درجة_RSI
    تفاصيل["RSI_Wilder"] = f"{درجة_RSI}/8"

    if اتجاه == "شراء":
        درجة_MACD = 8 if (macd["اتجاه"] == "شراء" and macd["الزخم_متزايد"]) else (4 if macd["اتجاه"] == "شراء" else 1)
    elif اتجاه == "بيع":
        درجة_MACD = 8 if (macd["اتجاه"] == "بيع" and macd["الزخم_متزايد"]) else (4 if macd["اتجاه"] == "بيع" else 1)
    else:
        درجة_MACD = 0
    الدرجة += درجة_MACD
    تفاصيل["MACD_قياسي"] = f"{درجة_MACD}/8"

    المستويات = تحليل_المستويات(الأعلى, الأدنى, سعر_الحالي)
    if المستويات["أقرب_دعم"] and المستويات["أقرب_مقاومة"]:
        درجة_البنية = 4
    elif المستويات["أقرب_دعم"] or المستويات["أقرب_مقاومة"]:
        درجة_البنية = 2
    else:
        درجة_البنية = 1
    الدرجة += درجة_البنية
    تفاصيل["وضوح_البنية"] = f"{درجة_البنية}/4"

    if len(الإغلاقات) >= 20:
        ميل = ((الإغلاقات[-1] - الإغلاقات[-20]) / الإغلاقات[-20]) * 100
    else:
        ميل = 0

    if اتجاه == "شراء":
        درجة_الميل = 6 if ميل > 0 else 0
    elif اتجاه == "بيع":
        درجة_الميل = 6 if ميل < 0 else 0
    else:
        درجة_الميل = 0
    الدرجة += درجة_الميل
    تفاصيل["ميل_الاتجاه"] = f"{درجة_الميل}/6"

    if len(الإغلاقات) >= 4:
        if اتجاه == "شراء":
            متوافقة = sum(1 for i in range(-3, 0) if الإغلاقات[i] > الإغلاقات[i - 1])
        elif اتجاه == "بيع":
            متوافقة = sum(1 for i in range(-3, 0) if الإغلاقات[i] < الإغلاقات[i - 1])
        else:
            متوافقة = 0

        درجة_الشموع = 5 if متوافقة == 3 else (3 if متوافقة >= 2 else 1)
    else:
        درجة_الشموع = 0
    الدرجة += درجة_الشموع
    تفاصيل["الشموع"] = f"{درجة_الشموع}/5"

    return {
        "الدرجة": min(round(الدرجة, 1), 90),
        "التفاصيل": تفاصيل,
        "المستويات": المستويات,
        "RSI": rsi,
        "MACD": macd,
        "ATR": atr
    }


def تحديد_الأهداف(اتجاه, سعر_الحالي, atr, المستويات):
    if not atr or atr <= 0:
        atr = abs(سعر_الحالي * 0.001)

    if اتجاه == "شراء":
        وقف_الخسارة = سعر_الحالي - 1.5 * atr
        هدف1 = سعر_الحالي + 1 * atr
        هدف2 = سعر_الحالي + 2 * atr
        هدف3 = سعر_الحالي + 3 * atr
        مقاومة = المستويات["أقرب_مقاومة"]
        if مقاومة and مقاومة["السعر"] > سعر_الحالي:
            هدف1 = min(هدف1, مقاومة["السعر"])
        return {"وقف_الخسارة": وقف_الخسارة, "هدف1": هدف1, "هدف2": هدف2, "هدف3": هدف3}

    elif اتجاه == "بيع":
        وقف_الخسارة = سعر_الحالي + 1.5 * atr
        هدف1 = سعر_الحالي - 1 * atr
        هدف2 = سعر_الحالي - 2 * atr
        هدف3 = سعر_الحالي - 3 * atr
        دعم = المستويات["أقرب_دعم"]
        if دعم and دعم["السعر"] < سعر_الحالي:
            هدف1 = max(هدف1, دعم["السعر"])
        return {"وقف_الخسارة": وقف_الخسارة, "هدف1": هدف1, "هدف2": هدف2, "هدف3": هدف3}

    return {"وقف_الخسارة": None, "هدف1": None, "هدف2": None, "هدف3": None}


def حساب_RR(سعر_الدخول, وقف_الخسارة, الهدف):
    if وقف_الخسارة is None or الهدف is None:
        return 0
    المخاطرة = abs(سعر_الدخول - وقف_الخسارة)
    العائد = abs(الهدف - سعر_الدخول)
    if المخاطرة <= 0:
        return 0
    return round(العائد / المخاطرة, 2)


# ============================================================
# 🧠 التحليل الكامل للصورة
# ============================================================

def تحليل_الصورة(صورة, الإطار_الزمني="غير معروف", الزوج="غير معروف"):
    منطقة = اكتشاف_منطقة_الشارت(صورة)
    الشموع = اكتشاف_الشموع(منطقة)

    if len(الشموع) < 20:
        raise Exception(
            "لم أستطع اكتشاف عدد كافٍ من الشموع (تم اكتشاف "
            f"{len(الشموع)} فقط، والحد الأدنى 20). "
            "ارفع صورة واضحة للشارت بدون ضغط شديد أو تشويش، وبدقة عالية."
        )

    # ⚠️ نحاول أولاً قراءة الأسعار من شريط المحور العمودي تحديداً
    # (أدق من قراءة الصورة كاملة)، ولو فشل نجرب الصورة كاملة كاحتياط
    أسعار_OCR = استخراج_أسعار_المحور_العمودي(صورة, منطقة)
    if len(أسعار_OCR) < 2:
        نص_كامل = استخراج_النص_من_الصورة(صورة)
        أسعار_OCR = استخراج_الأسعار_من_النص(نص_كامل)

    try:
        الإغلاقات, الأعلى, الأدنى = تحويل_الشموع_إلى_أسعار(الشموع, أسعار_OCR)
    except خطأ_مقياس_سعري as e:
        # نرجّع خطأ صريح بدل أي إشارة تداول وهمية
        raise Exception(str(e))

    if len(الإغلاقات) < 20:
        raise Exception("البيانات المستخرجة من الصورة غير كافية بعد المعايرة السعرية.")

    سعر_الحالي = الإغلاقات[-1]
    atr = حساب_ATR_Wilder(الأعلى, الأدنى, الإغلاقات)
    اتجاه = تحديد_الاتجاه(الإغلاقات)
    تحليل = حساب_قوة_الإعداد(الإغلاقات, الأعلى, الأدنى, سعر_الحالي, atr, اتجاه)
    الأهداف = تحديد_الأهداف(اتجاه, سعر_الحالي, atr, تحليل["المستويات"])
    rr = حساب_RR(سعر_الحالي, الأهداف["وقف_الخسارة"], الأهداف["هدف1"])

    if اتجاه == "محايد":
        الثقة = 50
    else:
        الثقة = min(95, max(50, 50 + (تحليل["الدرجة"] / 2)))

    if اتجاه == "محايد":
        الإشارة = "محايد"
    elif تحليل["الدرجة"] >= 65:
        الإشارة = اتجاه
    elif تحليل["الدرجة"] >= 50:
        الإشارة = "شراء ضعيف" if اتجاه == "شراء" else "بيع ضعيف"
    else:
        الإشارة = "محايد"

    return {
        "وقت_التحليل": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "الزوج": الزوج,
        "الإطار_الزمني": الإطار_الزمني,
        "الإشارة": الإشارة,
        "الاتجاه": اتجاه,
        "الثقة": round(الثقة, 1),
        "الدرجة": تحليل["الدرجة"],
        "سعر_الدخول": round(سعر_الحالي, 5),
        "وقف_الخسارة": round(الأهداف["وقف_الخسارة"], 5) if الأهداف["وقف_الخسارة"] else None,
        "هدف1": round(الأهداف["هدف1"], 5) if الأهداف["هدف1"] else None,
        "هدف2": round(الأهداف["هدف2"], 5) if الأهداف["هدف2"] else None,
        "هدف3": round(الأهداف["هدف3"], 5) if الأهداف["هدف3"] else None,
        "RR": rr,
        "RSI": تحليل["RSI"],
        "MACD": تحليل["MACD"],
        "ATR": round(atr, 5),
        "المستويات": تحليل["المستويات"],
        "تفاصيل_الدرجات": تحليل["التفاصيل"],
        "عدد_الشموع_المكتشفة": len(الشموع),
        "عدد_أسعار_OCR_المستخدمة": len(أسعار_OCR),
        "تنويه": تنويه_عام
    }


# ============================================================
# 📤 رفع وتحليل صورة
# ============================================================

@app.post("/تحليل-الصورة")
async def تحليل_صورة_API(
    صورة: UploadFile = File(...),
    الزوج: str = Form("غير معروف"),
    الإطار_الزمني: str = Form("غير معروف")
):
    try:
        البيانات = await صورة.read()
        صورة_مقروءة = قراءة_الصورة(البيانات)
        النتيجة = تحليل_الصورة(صورة_مقروءة, الإطار_الزمني, الزوج)
        حفظ_نتيجة(النتيجة)
        return JSONResponse(content=النتيجة)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 📋 آخر النتائج
# ============================================================

@app.get("/النتائج")
async def آخر_النتائج():
    نتائج_أخيرة, العدد_الكلي = جلب_آخر_النتائج(50)
    return {"عدد_التحاليل": العدد_الكلي, "النتائج": نتائج_أخيرة}


# ============================================================
# ❤️ فحص النظام
# ============================================================

@app.get("/حالة-النظام")
async def حالة_النظام():
    return {
        "الحالة": "يعمل",
        "الإصدار": "4.0.0",
        "النظام": "نبر وان — محلل الشارت بالصور",
        "OCR": "متاح",
        "OpenCV": "متاح",
        "ملاحظة": "نسخة مصححة: لا يتم إنتاج إشارات بدون مقياس سعري حقيقي من OCR"
    }


# ============================================================
# 🌐 الواجهة (نفس تصميم v3.0 + عرض التنويه + رسائل خطأ أوضح)
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>نبر وان v4.0 — محلل الشارت بالصور</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: radial-gradient(circle at top, #142338, #050b13 65%);
    color: #e8eef7;
    font-family: Arial, Tahoma, sans-serif;
}
.container { max-width: 1250px; margin: auto; padding: 25px; }
.header { text-align: center; margin-bottom: 20px; }
.header h1 { font-size: 30px; margin: 5px 0; }
.header p { color: #8fa2b8; }
.disclaimer {
    background: rgba(157,138,46,.12);
    border: 1px solid #9d8a2e;
    color: #e7d99a;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.7;
    margin-bottom: 20px;
    text-align: center;
}
.grid { display: grid; grid-template-columns: 360px 1fr; gap: 20px; }
.card {
    background: rgba(13, 24, 39, .95);
    border: 1px solid #24364c;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 15px 45px rgba(0,0,0,.25);
}
.upload {
    border: 2px dashed #45627f;
    border-radius: 14px;
    padding: 45px 20px;
    text-align: center;
    cursor: pointer;
    transition: .2s;
}
.upload:hover { border-color: #36d17d; background: rgba(54,209,125,.05); }
input, select {
    width: 100%; padding: 12px; margin-top: 8px; margin-bottom: 15px;
    border-radius: 9px; border: 1px solid #334a63; background: #08111d; color: white;
}
button {
    width: 100%; border: 0; border-radius: 10px; padding: 14px;
    background: linear-gradient(135deg, #1474e5, #1b9dff);
    color: white; font-weight: bold; font-size: 16px; cursor: pointer;
}
button:hover { opacity: .9; }
.preview { width: 100%; max-height: 400px; object-fit: contain; margin-top: 15px; border-radius: 10px; display: none; }
.result { display: none; }
.signal {
    border-radius: 14px; padding: 22px; text-align: center; margin-bottom: 20px;
    background: linear-gradient(135deg, #093f29, #0a251d); border: 1px solid #1b8758;
}
.signal.sell { background: linear-gradient(135deg, #4a1717, #241010); border-color: #b93a3a; }
.signal.neutral { background: linear-gradient(135deg, #3c3411, #201c0b); border-color: #9d8a2e; }
.signal-title { font-size: 28px; font-weight: bold; }
.score { font-size: 34px; margin-top: 8px; }
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.metric { background: #091523; border: 1px solid #263b52; padding: 15px; border-radius: 10px; text-align: center; }
.metric span { display: block; color: #8094aa; font-size: 13px; margin-bottom: 7px; }
.metric strong { font-size: 18px; }
.green { color: #3be486; } .red { color: #ff5f63; } .yellow { color: #e7ca52; }
.details { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.details-box { background: #08121f; border: 1px solid #24374c; padding: 16px; border-radius: 12px; }
.row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #15283a; }
.row:last-child { border-bottom: 0; }
.loading { display: none; text-align: center; padding: 30px; color: #6fc6ff; }
.errorbox {
    display: none; background: rgba(185,58,58,.12); border: 1px solid #b93a3a;
    color: #ffb3b3; padding: 16px; border-radius: 12px; margin-top: 15px; line-height: 1.8;
}
.warning { margin-top: 15px; color: #d5c477; font-size: 13px; line-height: 1.8; }
@media(max-width: 850px) {
    .grid { grid-template-columns: 1fr; }
    .metrics { grid-template-columns: repeat(2, 1fr); }
    .details { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="container">

<div class="header">
<h1>🤖 نبر وان v4.0</h1>
<p>محلل الشارت بالصور — صورة → تحليل فني → إشارة (نسخة مصححة)</p>
</div>

<div class="disclaimer">
⚠️ هذا تحليل تقريبي مستخرج من صورة وليس بيانات سعرية حقيقية، لأغراض تعليمية/بحثية فقط
وليس توصية استثمارية. النظام يرفض إعطاء إشارة إذا لم يستطع قراءة سعرين حقيقيين
على الأقل من محور الشارت، بدل اختلاق أرقام غير موثوقة.
</div>

<div class="grid">
<div class="card">
<h2>📸 صورة الشارت</h2>
<label class="upload">
<input id="image" type="file" accept=".png,.jpg,.jpeg,.webp" style="display:none">
<div style="font-size:45px">☁️</div>
<div>اضغط هنا لاختيار صورة الشارت</div>
<div style="color:#71869c;margin-top:8px">PNG / JPG / JPEG / WEBP</div>
</label>
<img id="preview" class="preview">

<label>الزوج — اختياري</label>
<input id="pair" placeholder="EUR/USD">

<label>الإطار الزمني — اختياري</label>
<select id="tf">
<option>غير معروف</option>
<option>1 دقيقة</option>
<option selected>5 دقائق</option>
<option>15 دقيقة</option>
<option>30 دقيقة</option>
<option>ساعة</option>
<option>4 ساعات</option>
<option>يومي</option>
</select>

<button onclick="analyze()">🔎 تحليل الصورة الآن</button>

<div class="warning">
⚠️ لأفضل نتيجة: ارفع صورة واضحة تظهر فيها أرقام محور السعر (يمين الشارت)
بشكل جيد وغير مقصوص، لأن النظام يرفض التحليل بدونها.
</div>
</div>

<div class="card">
<div id="loading" class="loading">⏳ جاري قراءة الصورة وتحليل الشموع والمؤشرات...</div>

<div id="empty" style="text-align:center;padding:100px 20px;color:#60758c">
<h2>📊</h2>
<p>ارفع صورة الشارت لبدء التحليل</p>
</div>

<div id="errorbox" class="errorbox"></div>

<div id="result" class="result">
<div id="signal" class="signal">
<div id="signalText" class="signal-title">—</div>
<div id="score" class="score">—</div>
</div>

<div class="metrics">
<div class="metric"><span>سعر الدخول</span><strong id="entry">—</strong></div>
<div class="metric"><span>وقف الخسارة</span><strong id="sl" class="red">—</strong></div>
<div class="metric"><span>نسبة RR</span><strong id="rr" class="green">—</strong></div>
<div class="metric"><span>هدف 1</span><strong id="tp1" class="green">—</strong></div>
<div class="metric"><span>هدف 2</span><strong id="tp2" class="green">—</strong></div>
<div class="metric"><span>هدف 3</span><strong id="tp3" class="green">—</strong></div>
</div>

<div class="details">
<div class="details-box">
<h3>📊 المؤشرات</h3>
<div class="row"><span>RSI Wilder</span><strong id="rsi">—</strong></div>
<div class="row"><span>MACD</span><strong id="macd">—</strong></div>
<div class="row"><span>ATR</span><strong id="atr">—</strong></div>
<div class="row"><span>عدد الشموع</span><strong id="candles">—</strong></div>
<div class="row"><span>أسعار OCR مستخدمة</span><strong id="ocrcount">—</strong></div>
</div>

<div class="details-box">
<h3>⭐ درجات التحليل</h3>
<div id="scores"></div>
</div>
</div>

<div class="details">
<div class="details-box">
<h3>🧱 المستويات</h3>
<div class="row"><span>أقرب مقاومة</span><strong id="resistance">—</strong></div>
<div class="row"><span>أقرب دعم</span><strong id="support">—</strong></div>
</div>

<div class="details-box">
<h3>🔍 معلومات الصورة</h3>
<div class="row"><span>الزوج</span><strong id="pairResult">—</strong></div>
<div class="row"><span>الإطار</span><strong id="tfResult">—</strong></div>
<div class="row"><span>الثقة</span><strong id="confidence">—</strong></div>
</div>
</div>

<div class="disclaimer" style="margin-top:15px" id="footerDisclaimer"></div>

</div>
</div>
</div>

<script>
const imageInput = document.getElementById("image");
const preview = document.getElementById("preview");

imageInput.addEventListener("change", function(){
    const file = this.files[0];
    if(!file) return;
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
});

async function analyze(){
    const file = imageInput.files[0];
    if(!file){ alert("اختر صورة الشارت أولاً"); return; }

    const loading = document.getElementById("loading");
    const empty = document.getElementById("empty");
    const result = document.getElementById("result");
    const errorbox = document.getElementById("errorbox");

    loading.style.display = "block";
    empty.style.display = "none";
    result.style.display = "none";
    errorbox.style.display = "none";

    const form = new FormData();
    form.append("صورة", file);
    form.append("الزوج", document.getElementById("pair").value);
    form.append("الإطار_الزمني", document.getElementById("tf").value);

    try{
        const response = await fetch("/تحليل-الصورة", { method:"POST", body:form });
        const data = await response.json();

        if(!response.ok){
            throw new Error(data.detail || "فشل التحليل");
        }

        عرض_النتيجة(data);
    }
    catch(error){
        errorbox.textContent = "❌ " + error.message;
        errorbox.style.display = "block";
        empty.style.display = "block";
    }
    finally{
        loading.style.display = "none";
    }
}

function عرض_النتيجة(data){
    const result = document.getElementById("result");
    result.style.display = "block";

    const signal = document.getElementById("signal");
    signal.className = "signal";
    if(data["الإشارة"].includes("بيع")) signal.classList.add("sell");
    else if(data["الإشارة"] === "محايد") signal.classList.add("neutral");

    document.getElementById("signalText").textContent = "الإشارة: " + data["الإشارة"];
    document.getElementById("score").textContent = data["الدرجة"] + " / 90";

    document.getElementById("entry").textContent = data["سعر_الدخول"] ?? "—";
    document.getElementById("sl").textContent = data["وقف_الخسارة"] ?? "—";
    document.getElementById("tp1").textContent = data["هدف1"] ?? "—";
    document.getElementById("tp2").textContent = data["هدف2"] ?? "—";
    document.getElementById("tp3").textContent = data["هدف3"] ?? "—";
    document.getElementById("rr").textContent = "1 : " + (data["RR"] ?? "—");

    document.getElementById("rsi").textContent = data["RSI"] ?? "—";
    document.getElementById("macd").textContent = data["MACD"]["اتجاه"] ?? "—";
    document.getElementById("atr").textContent = data["ATR"] ?? "—";
    document.getElementById("candles").textContent = data["عدد_الشموع_المكتشفة"] ?? "—";
    document.getElementById("ocrcount").textContent = data["عدد_أسعار_OCR_المستخدمة"] ?? "—";

    document.getElementById("pairResult").textContent = data["الزوج"] || "غير معروف";
    document.getElementById("tfResult").textContent = data["الإطار_الزمني"] || "غير معروف";
    document.getElementById("confidence").textContent = data["الثقة"] + "%";

    const مستويات = data["المستويات"];
    document.getElementById("resistance").textContent =
        مستويات && مستويات["أقرب_مقاومة"] ? مستويات["أقرب_مقاومة"]["السعر"] : "غير موجود";
    document.getElementById("support").textContent =
        مستويات && مستويات["أقرب_دعم"] ? مستويات["أقرب_دعم"]["السعر"] : "غير موجود";

    const scores = document.getElementById("scores");
    scores.innerHTML = "";
    const التفاصيل = data["تفاصيل_الدرجات"] || {};
    for(const [key,value] of Object.entries(التفاصيل)){
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `<span>${key}</span><strong>${value}</strong>`;
        scores.appendChild(row);
    }

    document.getElementById("footerDisclaimer").textContent = data["تنويه"] || "";
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def الرئيسية():
    return HTML


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
