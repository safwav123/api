from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import mediapipe as mp
import json
import uvicorn
from typing import Optional

app = FastAPI(title="نظام تحديد شكل الجسم")

# إعدادات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تعريف توصيات أنواع الجسم
BODY_TYPE_RECOMMENDATIONS = {
    "hourglass": [
        {"id": 1, "style": "فساتين مخصصة عند الخصر", "description": "تسليط الضوء على تناسق الخصر مع الصدر والأوراك"},
        {"id": 2, "style": "أحزمة وسط", "description": "إبراز منطقة الخصر باستخدام أحزمة زينة"}
    ],
    "pear": [
        {"id": 3, "style": "تأكيد على الجزء العلوي", "description": "استخدام تفاصيل جذابة في أعلى الجسم"},
        {"id": 4, "style": "A-line", "description": "تصميم يتسع تدريجياً ليوازن الجزء السفلي"}
    ],
    "inverted_triangle": [
        {"id": 5, "style": "تصاميم متسعة من الأسفل", "description": "إضافة حجم للجزء السفلي لتحقيق التوازن"},
        {"id": 6, "style": "تفاصيل أسفل الجسم", "description": "تركيز الزخارف في الجزء السفلي"}
    ],
    "rectangle": [
        {"id": 7, "style": "طبقات وتفاصيل", "description": "خلق إيحاء بالمنحنيات باستخدام طبقات القماش"},
        {"id": 8, "style": "أحزمة عريضة", "description": "إبراز الخصر باستخدام أحزمة واضحة"}
    ],
    "apple": [
        {"id": 9, "style": "خط الإمبراطورة", "description": "تصميم يبدأ تحت الصدر مباشرة لإطالة المظهر"},
        {"id": 10, "style": "تفاصيل أعلى الجسم", "description": "جذب الانتباه لأعلى بعيداً عن المنطقة الوسطى"}
    ]
}

# تهيئة نموذج MediaPipe لتحليل الجسم
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    min_detection_confidence=0.7,
    model_complexity=2
)

def calculate_body_ratios(measurements):
    """حساب النسب الأساسية لتحديد شكل الجسم"""
    ratios = {
        "waist_to_bust": measurements["waist"] / measurements["bust"],
        "waist_to_hip": measurements["waist"] / measurements["hips"],
        "shoulder_to_hip": measurements["shoulder_width"] / measurements["hips"]
    }
    return ratios

def determine_body_type(measurements):
    """تحديد نوع الجسم بناء على القياسات والنسب"""
    ratios = calculate_body_ratios(measurements)
    
    # تحليل النسب
    is_defined_waist = ratios["waist_to_hip"] < 0.8
    balanced_upper_lower = 0.9 < ratios["shoulder_to_hip"] < 1.1
    
    if ratios["waist_to_hip"] < 0.75 and ratios["waist_to_bust"] < 0.75 and balanced_upper_lower:
        return "hourglass"
    elif ratios["waist_to_hip"] < 0.8 and ratios["shoulder_to_hip"] < 0.9:
        return "pear"
    elif ratios["shoulder_to_hip"] > 1.15 and ratios["waist_to_bust"] < 0.85:
        return "inverted_triangle"
    elif ratios["waist_to_bust"] > 0.85 and ratios["waist_to_hip"] > 0.85:
        return "apple"
    else:
        return "rectangle"

def analyze_image_content(image_data, user_height_cm=0):
    """تحليل الصورة لاستخراج القياسات"""
    img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("لا يمكن قراءة الصورة")
    
    # تحويل الصورة وتحليلها
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)
    
    if not results.pose_landmarks:
        raise ValueError("لم يتم اكتشاف وضعية الجسم في الصورة")
    
    landmarks = results.pose_landmarks.landmark
    img_height, img_width = img.shape[:2]
    
    # استخراج النقاط الرئيسية
    def get_coords(landmark):
        return landmark.x * img_width, landmark.y * img_height
    
    # حساب القياسات (بالبكسل)
    shoulder_width = abs(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x - 
                        landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x) * img_width
    bust = shoulder_width * 1.6  # تقدير محيط الصدر
    waist = abs(landmarks[mp_pose.PoseLandmark.LEFT_HIP].x - 
               landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x) * img_width * 1.3
    hips = waist * 1.3  # تقدير محيط الأوراك
    
    # التحويل إلى سنتيمترات
    if user_height_cm > 0:
        body_height_px = abs(landmarks[mp_pose.PoseLandmark.NOSE].y - 
                         landmarks[mp_pose.PoseLandmark.LEFT_HEEL].y) * img_height
        scale = user_height_cm / body_height_px
    else:
        scale = 0.0265  # افتراضي إذا لم يتم تقديم الطول
    
    measurements = {
        "shoulder_width": round(shoulder_width * scale, 2),
        "bust": round(bust * scale, 2),
        "waist": round(waist * scale, 2),
        "hips": round(hips * scale, 2),
        "height": user_height_cm if user_height_cm > 0 else round(body_height_px * scale, 2)
    }
    
    return measurements

@app.post("/analyze-body")
async def analyze_body(
    image: Optional[UploadFile] = File(None),
    manual_measurements: Optional[str] = Form(None),
    user_height_cm: float = Form(0)
):
    try:
        if image:
            # تحليل الصورة
            image_data = await image.read()
            measurements = analyze_image_content(image_data, user_height_cm)
            source = "image_analysis"
        elif manual_measurements:
            # تحليل القياسات اليدوية
            measurements = json.loads(manual_measurements)
            required = ["bust", "waist", "hips", "shoulder_width"]
            if not all(k in measurements for k in required):
                missing = [k for k in required if k not in measurements]
                raise HTTPException(400, f"القياسات المطلوبة: {', '.join(missing)}")
            source = "manual_input"
        else:
            raise HTTPException(400, "يجب تقديم صورة أو قياسات يدوية")
        
        # تحديد نوع الجسم
        body_type = determine_body_type(measurements)
        
        # إعداد النتائج
        response = {
            "source": source,
            "measurements": measurements,
            "body_type": body_type,
            "characteristics": get_body_characteristics(body_type),
            "recommendations": BODY_TYPE_RECOMMENDATIONS.get(body_type, [])
        }
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(400, "تنسيق JSON غير صحيح للقياسات اليدوية")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"خطأ في المعالجة: {str(e)}")

def get_body_characteristics(body_type):
    """وصف خصائص كل نوع جسم"""
    characteristics = {
        "hourglass": "تناسق بين الصدر والأوراك مع خصر محدد بوضوح",
        "pear": "أوراك عريضة مقارنة بالكتفين مع خصر متوسط",
        "inverted_triangle": "كتفان عريضان مقارنة بالأوراك مع خصر غير محدد",
        "rectangle": "تناسق بين الكتفين والصدر والأوراك مع خصر غير واضح",
        "apple": "منطقة وسطية عريضة مع صدر وأوراك متقاربة في العرض"
    }
    return characteristics.get(body_type, "")

@app.get("/body-types-info")
async def get_body_types_info():
    """الحصول على معلومات عن جميع أنواع الأجسام"""
    return {
        "types": {
            "hourglass": {"description": "الصدر والأوراك متساويان تقريباً مع خصر ضيق", "common": 20},
            "pear": {"description": "الأوراك أوسع من الكتفين مع خصر متوسط", "common": 35},
            "inverted_triangle": {"description": "الكتفان أوسع من الأوراك مع خصر غير محدد", "common": 15},
            "rectangle": {"description": "القياسات متقاربة مع خصر غير واضح", "common": 25},
            "apple": {"description": "المنطقة الوسطى هي الأوسع مع صدر وأوراك متقاربة", "common": 5}
        }
    }

if _name_ == "_main_":
    uvicorn.run(app, host="0.0.0.0", port=8000)
