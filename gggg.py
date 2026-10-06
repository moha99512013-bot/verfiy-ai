import os
import io
import base64

import streamlit as st
from PIL import Image
from openai import OpenAI


# ==============================
# إعداد الصفحة
# ==============================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================
# إعداد OpenAI
# ==============================

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


def get_api_key():
    key = os.getenv("OPENAI_API_KEY")

    if key:
        return key

    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None


API_KEY = get_api_key()

if API_KEY:
    client = OpenAI(api_key=API_KEY)
else:
    client = None


# ==============================
# Session State
# ==============================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_score" not in st.session_state:
    st.session_state.analysis_score = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ==============================
# التصميم
# ==============================

st.markdown("""
<style>

.stApp {
    background-color: #070b12;
    color: white;
}

header {
    visibility: hidden;
}

.block-container {
    max-width: 1400px;
    padding-top: 30px;
}

section[data-testid="stSidebar"] {
    background-color: #090e16;
    border-right: 1px solid #202936;
}

h1, h2, h3, h4, p, label {
    color: white !important;
}

.main-title {
    font-size: 40px;
    font-weight: 700;
}

.subtitle {
    color: #9ca8b8 !important;
    font-size: 16px;
    margin-bottom: 25px;
}

.card {
    background-color: #0d131d;
    border: 1px solid #202936;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
}

.score {
    font-size: 50px;
    font-weight: 800;
    text-align: center;
}

.good {
    color: #4ade80 !important;
}

.medium {
    color: #facc15 !important;
}

.bad {
    color: #f87171 !important;
}

.stButton > button {
    width: 100%;
    min-height: 45px;
    border-radius: 10px;
    background-color: #111a27;
    color: white;
    border: 1px solid #2a3747;
}

.stButton > button:hover {
    border-color: #66788c;
}

[data-testid="stFileUploader"] {
    background-color: #0d131d;
    border: 1px dashed #344355;
    border-radius: 16px;
}

</style>
""", unsafe_allow_html=True)


# ==============================
# القائمة الجانبية
# ==============================

with st.sidebar:

    st.markdown("""
    <div style="font-size:25px;font-weight:700;">
        ♿ VerifyAI Access
    </div>

    <div style="color:#9ca8b8;">
        التصميم الشامل بالذكاء الاصطناعي
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "الصفحات",
        [
            "الرئيسية",
            "تحليل الإتاحة",
            "المحادثة الذكية"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    if client:
        st.success("● AI متصل")
    else:
        st.error("● API غير متصل")


# ==============================
# الرئيسية
# ==============================

if page == "الرئيسية":

    st.markdown(
        '<div class="main-title">VerifyAI Access</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
        الذكاء الاصطناعي لإعادة تصميم التجارب اليومية
        لتصبح أكثر إتاحة واستقلالية.
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("""
        <div class="card">

        <h3>المشكلة</h3>

        <p>
        بعض الأماكن والخدمات اليومية لا توفر تجربة مناسبة
        لجميع الأشخاص ذوي الإعاقة.
        </p>

        <p>
        وقد لا يعرف الشخص مسبقًا إذا كان المكان يحتوي
        على عوائق أو وسائل وصول مناسبة.
        </p>

        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown("""
        <div class="card">

        <h3>الحل</h3>

        <p>
        يتيح VerifyAI Access للمستخدم رفع صورة للمكان
        ثم يقوم الذكاء الاصطناعي بتحليل إمكانية الوصول.
        </p>

        <p>
        ويقدم درجة للإتاحة، ويحدد المشاكل،
        ويقترح حلولًا عملية.
        </p>

        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card">

    <h3>كيف يعمل النظام؟</h3>

    <p>① يرفع المستخدم صورة للمكان</p>
    <p>② يحدد نوع الاحتياج</p>
    <p>③ AI يحلل الصورة</p>
    <p>④ النظام يحدد العوائق</p>
    <p>⑤ AI يقترح تحسينات</p>

    </div>
    """, unsafe_allow_html=True)


# ==============================
# تحليل الإتاحة
# ==============================

elif page == "تحليل الإتاحة":

    st.markdown(
        '<div class="main-title">تحليل الإتاحة</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
        ارفع صورة للمكان ودع الذكاء الاصطناعي يحلل مدى سهولة الوصول إليه.
        </div>
        """,
        unsafe_allow_html=True
    )

    need = st.selectbox(
        "ما نوع الاحتياج الذي تريد تحليله؟",
        [
            "تجربة شاملة",
            "إعاقة بصرية",
            "إعاقة سمعية",
            "إعاقة حركية",
            "صعوبة في فهم المعلومات"
        ]
    )

    uploaded_file = st.file_uploader(
        "ارفع صورة للمكان",
        type=["png", "jpg", "jpeg", "webp"]
    )

    if uploaded_file:

        try:
            image = Image.open(uploaded_file).convert("RGB")
        except Exception:
            st.error("لم نتمكن من قراءة الصورة.")
            st.stop()

        col1, col2 = st.columns(2)

        with col1:

            st.image(
                image,
                caption="الصورة المرفوعة",
                use_container_width=True
            )

        with col2:

            st.markdown("""
            <div class="card">

            <h3>الصورة جاهزة</h3>

            <p>
            سيقوم AI بتحليل العناصر الظاهرة في الصورة
            وتحديد مشاكل الإتاحة المحتملة.
            </p>

            </div>
            """, unsafe_allow_html=True)

            analyze = st.button(
                "تحليل الصورة بالذكاء الاصطناعي",
                type="primary"
            )

        if analyze:

            if not client:

                st.error(
                    "OPENAI_API_KEY غير موجود. أضف المفتاح في Secrets أو Environment Variables."
                )

            else:

                with st.spinner("AI يحلل الصورة..."):

                    try:

                        # تصغير الصورة لتقليل حجم الطلب

                        image.thumbnail(
                            (1600, 1600),
                            Image.Resampling.LANCZOS
                        )

                        buffer = io.BytesIO()

                        image.save(
                            buffer,
                            format="JPEG",
                            quality=85
                        )

                        image_data = buffer.getvalue()

                        encoded = base64.b64encode(
                            image_data
                        ).decode("utf-8")

                        prompt = f"""
أنت خبير في التصميم الشامل وإمكانية الوصول.

نوع الاحتياج:
{need}

حلل الصورة المرفقة بعناية.

لا تخترع معلومات غير موجودة في الصورة.
إذا كان شيء غير واضح، اذكر أنه غير واضح.

أجب باللغة العربية.

أعطني:

SCORE:
درجة من 0 إلى 100.

SUMMARY:
ملخص مختصر.

POSITIVE:
ما الأشياء الموجودة التي تساعد على سهولة الوصول؟

PROBLEMS:
ما العوائق أو المشاكل الظاهرة؟

SOLUTIONS:
ما الحلول التي يمكن تطبيقها؟

AI_IDEA:
كيف يمكن استخدام الذكاء الاصطناعي لجعل التجربة
أكثر شمولاً واستقلالية؟

ركز على حلول واقعية وقابلة للتطبيق.
"""

                        response = client.responses.create(
                            model=MODEL,
                            input=[
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": prompt
                                        },
                                        {
                                            "type": "input_image",
                                            "image_url":
                                                f"data:image/jpeg;base64,{encoded}"
                                        }
                                    ]
                                }
                            ]
                        )

                        result = response.output_text

                        score = None

                        for line in result.splitlines():

                            if line.strip().upper().startswith("SCORE:"):

                                value = line.split(
                                    ":",
                                    1
                                )[1].strip()

                                try:
                                    score = int(value)
                                except:
                                    score = None

                                break

                        st.session_state.analysis_result = result
                        st.session_state.analysis_score = score

                    except Exception as e:

                        st.error(
                            f"حدث خطأ أثناء تحليل الصورة:\n\n{e}"
                        )

        # عرض النتيجة

        if st.session_state.analysis_result:

            st.divider()

            st.markdown(
                '<div class="main-title" style="font-size:30px;">نتيجة التحليل</div>',
                unsafe_allow_html=True
            )

            score = st.session_state.analysis_score

            if score is not None:

                if score >= 75:
                    score_class = "good"
                elif score >= 50:
                    score_class = "medium"
                else:
                    score_class = "bad"

                col1, col2 = st.columns([1, 3])

                with col1:

                    st.markdown(
                        f"""
                        <div class="card">

                        <div style="text-align:center;color:#9ca8b8;">
                        درجة الإتاحة
                        </div>

                        <div class="score {score_class}">
                        {score}/100
                        </div>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col2:

                    st.markdown(
                        '<div class="card">',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        st.session_state.analysis_result
                    )

                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True
                    )

            else:

                st.markdown(
                    '<div class="card">',
                    unsafe_allow_html=True
                )

                st.markdown(
                    st.session_state.analysis_result
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )


# ==============================
# المحادثة الذكية
# ==============================

elif page == "المحادثة الذكية":

    st.markdown(
        '<div class="main-title">المحادثة الذكية</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
        اسأل AI عن كيفية جعل تجربة معينة أكثر شمولاً.
        </div>
        """,
        unsafe_allow_html=True
    )

    for message in st.session_state.chat_messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_message = st.chat_input(
        "اكتب سؤالك..."
    )

    if user_message:

        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        with st.chat_message("user"):
            st.markdown(user_message)

        if not client:

            answer = (
                "الذكاء الاصطناعي غير متصل. "
                "تأكد من إضافة OPENAI_API_KEY."
            )

        else:

            try:

                instructions = """
أنت مساعد متخصص في التصميم الشامل وإمكانية الوصول.

ساعد المستخدم في تصميم تجارب يومية أفضل
للأشخاص ذوي الإعاقة.

استخدم الذكاء الاصطناعي بشكل حقيقي في الحلول.

ركز على:
- الاستقلالية
- سهولة الوصول
- التصميم الشامل
- قابلية التطبيق
- الإبداع

أجب باللغة العربية وبطريقة واضحة.
"""

                response = client.responses.create(
                    model=MODEL,
                    instructions=instructions,
                    input=user_message
                )

                answer = response.output_text

            except Exception as e:

                answer = f"حدث خطأ:\n\n{e}"

        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        with st.chat_message("assistant"):
            st.markdown(answer)
