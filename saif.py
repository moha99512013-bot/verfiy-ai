```python
import streamlit as st
from openai import OpenAI
from PIL import Image
import base64
import io
import os
import json

# =========================
# إعداد الصفحة
# =========================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CSS
# =========================

st.markdown("""
<style>

.stApp {
    background: #070b12;
    color: white;
}

header {
    visibility: hidden;
}

.block-container {
    padding-top: 2rem;
    max-width: 1400px;
}

section[data-testid="stSidebar"] {
    background: #090e16;
    border-right: 1px solid #1c2633;
}

h1, h2, h3, p, label, span {
    color: white !important;
}

.card {
    background: #0d131d;
    border: 1px solid #202b38;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 18px;
}

.title {
    font-size: 38px;
    font-weight: 700;
    margin-bottom: 5px;
}

.subtitle {
    color: #9ca8b8 !important;
    font-size: 16px;
}

.score {
    font-size: 52px;
    font-weight: 800;
    text-align: center;
    padding: 15px;
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

.small {
    color: #9ca8b8 !important;
    font-size: 14px;
}

.stButton > button {
    width: 100%;
    border-radius: 10px;
    border: 1px solid #263445;
    background: #111a27;
    color: white;
    padding: 10px;
}

.stButton > button:hover {
    border-color: #4b6078;
}

[data-testid="stFileUploader"] {
    background: #0d131d;
    border: 1px dashed #344355;
    border-radius: 16px;
    padding: 10px;
}

</style>
""", unsafe_allow_html=True)

# =========================
# OpenAI
# =========================

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

client = OpenAI(api_key=api_key) if api_key else None

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

# =========================
# Sidebar
# =========================

with st.sidebar:

    st.markdown("""
    <div style="font-size:24px;font-weight:700;">
    ♿ VerifyAI Access
    </div>
    <div class="small">
    التصميم الشامل بالذكاء الاصطناعي
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "التنقل",
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

# =========================
# الصفحة الرئيسية
# =========================

if page == "الرئيسية":

    st.markdown(
        '<div class="title">VerifyAI Access</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">منصة ذكاء اصطناعي لتحليل إمكانية الوصول وتصميم تجربة أكثر شمولاً</div>',
        unsafe_allow_html=True
    )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("""
        <div class="card">

        ### المشكلة

        كثير من الأماكن والخدمات لا توفر معلومات واضحة حول مدى ملاءمتها
        للأشخاص ذوي الإعاقة.

        قد يصل الشخص إلى المكان ثم يكتشف وجود درج،
        أو عدم وجود مصعد، أو عدم وضوح الإرشادات.

        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown("""
        <div class="card">

        ### الحل

        يتيح VerifyAI Access للمستخدم رفع صورة للمكان أو الخدمة،
        ثم يستخدم الذكاء الاصطناعي لتحليلها واكتشاف
        العوائق واقتراح تحسينات تجعل التجربة أكثر إتاحة واستقلالية.

        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card">

    ### كيف يعمل؟

    **1.** ارفع صورة أو لقطة شاشة  
    **2.** حدد نوع الاحتياج  
    **3.** يحلل AI الصورة  
    **4.** تحصل على درجة للإتاحة  
    **5.** يعرض المشاكل والحلول المقترحة

    </div>
    """, unsafe_allow_html=True)

# =========================
# تحليل الإتاحة
# =========================

elif page == "تحليل الإتاحة":

    st.markdown(
        '<div class="title">تحليل الإتاحة</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">ارفع صورة للمكان أو الخدمة ودع الذكاء الاصطناعي يحلل تجربة الوصول إليها.</div>',
        unsafe_allow_html=True
    )

    st.write("")

    need = st.selectbox(
        "نوع الاحتياج",
        [
            "تجربة شاملة",
            "إعاقة بصرية",
            "إعاقة سمعية",
            "إعاقة حركية",
            "صعوبة في فهم المعلومات"
        ]
    )

    uploaded = st.file_uploader(
        "ارفع صورة المكان أو الخدمة",
        type=["png", "jpg", "jpeg", "webp"]
    )

    if uploaded:

        image = Image.open(uploaded)

        col1, col2 = st.columns([1, 1])

        with col1:

            st.image(
                image,
                caption="الصورة المرفوعة",
                use_container_width=True
            )

        with col2:

            st.markdown("""
            <div class="card">

            ### جاهز للتحليل

            سيقوم الذكاء الاصطناعي بفحص الصورة بحثًا عن
            العوائق والمعلومات التي قد تؤثر على سهولة الوصول.

            </div>
            """, unsafe_allow_html=True)

            analyze = st.button(
                "تحليل الصورة بالذكاء الاصطناعي",
                type="primary"
            )

        if analyze:

            if not client:

                st.error(
                    "لم يتم العثور على OPENAI_API_KEY."
                )

            else:

                with st.spinner("يقوم AI بتحليل الصورة..."):

                    try:

                        # تحويل الصورة إلى Base64
                        buffer = io.BytesIO()
                        image.save(buffer, format="JPEG")
                        image_bytes = buffer.getvalue()

                        base64_image = base64.b64encode(
                            image_bytes
                        ).decode("utf-8")

                        prompt = f"""
أنت خبير في التصميم الشامل وإمكانية الوصول للأشخاص ذوي الإعاقة.

نوع الاحتياج المحدد:
{need}

حلل الصورة المرفقة بعناية.

لا تفترض وجود شيء غير ظاهر في الصورة.
إذا لم تستطع التأكد من شيء، اذكر أنه غير واضح.

أريد إجابة باللغة العربية.

حلل:

1. درجة الإتاحة من 0 إلى 100.
2. الأشياء التي تجعل المكان أو الخدمة سهلة الوصول.
3. العوائق أو المشاكل المحتملة.
4. كيف يمكن تحسين التجربة.
5. اقتراحات عملية قابلة للتطبيق باستخدام الذكاء الاصطناعي.
6. شرح مختصر لكيف يمكن جعل التجربة أكثر استقلالية للمستخدم.

أرجع النتيجة بهذا الشكل:

SCORE: رقم فقط

SUMMARY:
ملخص قصير

POSITIVE:
- نقطة
- نقطة

PROBLEMS:
- مشكلة
- مشكلة

SOLUTIONS:
- حل
- حل

AI_IDEA:
فكرة توضح كيف يمكن للذكاء الاصطناعي تحسين التجربة.
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
                                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    ]
                                }
                            ]
                        )

                        result = response.output_text

                        st.session_state["last_analysis"] = result

                    except Exception as e:

                        st.error(
                            f"حدث خطأ أثناء التحليل: {e}"
                        )

        # =========================
        # عرض النتيجة
        # =========================

        if "last_analysis" in st.session_state:

            result = st.session_state["last_analysis"]

            st.divider()

            st.markdown(
                '<div class="title" style="font-size:28px;">نتيجة تحليل AI</div>',
                unsafe_allow_html=True
            )

            # استخراج الدرجة
            score = 0

            try:

                for line in result.splitlines():

                    if line.strip().startswith("SCORE:"):

                        score = int(
                            line.split(":")[1].strip()
                        )

                        break

            except:
                score = 0

            score_class = "good"

            if score < 50:
                score_class = "bad"
            elif score < 75:
                score_class = "medium"

            col1, col2 = st.columns([1, 3])

            with col1:

                st.markdown(
                    f"""
                    <div class="card">

                    <div class="small">
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

                st.markdown(result)

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

# =========================
# المحادثة الذكية
# =========================

elif page == "المحادثة الذكية":

    st.markdown(
        '<div class="title">المحادثة الذكية</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">اسأل AI عن كيفية جعل تجربة معينة أكثر إتاحة.</div>',
        unsafe_allow_html=True
    )

    if "messages" not in st.session_state:

        st.session_state.messages = []

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

    user_message = st.chat_input(
        "اكتب سؤالك..."
    )

    if user_message:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        if not client:

            answer = "لم يتم الاتصال بالذكاء الاصطناعي. تأكد من OPENAI_API_KEY."

        else:

            try:

                system_prompt = """
أنت مساعد متخصص في التصميم الشامل وإمكانية الوصول.

ساعد المستخدم على إعادة تصميم التجارب اليومية
للأشخاص ذوي الإعاقة باستخدام الذكاء الاصطناعي.

ركز على:
- الاستقلالية
- سهولة الوصول
- التصميم الشامل
- حلول واقعية
- إمكانية التطبيق

لا تقدم ادعاءات غير مؤكدة.
أجب باللغة العربية بوضوح.
"""

                response = client.responses.create(
                    model=MODEL,
                    instructions=system_prompt,
                    input=user_message
                )

                answer = response.output_text

            except Exception as e:

                answer = f"حدث خطأ: {e}"

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        st.rerun()
```
