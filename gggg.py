```python
import os
import io
import base64

import streamlit as st
from PIL import Image
from openai import OpenAI


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CONFIG
# =========================================================

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


def get_api_key():
    """Get OpenAI API key from environment or Streamlit secrets."""
    key = os.getenv("OPENAI_API_KEY")

    if key:
        return key

    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None


API_KEY = get_api_key()

client = OpenAI(api_key=API_KEY) if API_KEY else None


# =========================================================
# SESSION STATE
# =========================================================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_score" not in st.session_state:
    st.session_state.analysis_score = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #070b12;
        color: white;
    }

    header {
        visibility: hidden;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    section[data-testid="stSidebar"] {
        background: #090e16;
        border-right: 1px solid #202936;
    }

    h1, h2, h3, h4, p, label, span {
        color: white !important;
    }

    .main-title {
        font-size: 40px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .subtitle {
        color: #9ca8b8 !important;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .card {
        background: #0d131d;
        border: 1px solid #202936;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 18px;
    }

    .score {
        font-size: 50px;
        font-weight: 800;
        text-align: center;
        padding: 10px;
    }

    .score-good {
        color: #4ade80 !important;
    }

    .score-medium {
        color: #facc15 !important;
    }

    .score-bad {
        color: #f87171 !important;
    }

    .small-text {
        color: #9ca8b8 !important;
        font-size: 14px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        min-height: 44px;
        background: #111a27;
        color: white;
        border: 1px solid #2a3747;
    }

    .stButton > button:hover {
        border-color: #60748c;
    }

    [data-testid="stFileUploader"] {
        background: #0d131d;
        border: 1px dashed #344355;
        border-radius: 16px;
        padding: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="font-size:24px;font-weight:700;">
            ♿ VerifyAI Access
        </div>

        <div class="small-text">
            التصميم الشامل بالذكاء الاصطناعي
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    page = st.radio(
        "التنقل",
        [
            "الرئيسية",
            "تحليل الإتاحة",
            "المحادثة الذكية",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    if client:
        st.success("● AI متصل")
    else:
        st.error("● API غير متصل")


# =========================================================
# HOME
# =========================================================

if page == "الرئيسية":

    st.markdown(
        '<div class="main-title">VerifyAI Access</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtitle">
        منصة تستخدم الذكاء الاصطناعي لتحليل إمكانية الوصول
        وتصميم تجارب أكثر شمولاً واستقلالية.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            <div class="card">

            <h3>المشكلة</h3>

            <p>
            قد يدخل الشخص ذو الإعاقة إلى مكان أو يستخدم خدمة
            دون معرفة مدى ملاءمتها لاحتياجه.
            </p>

            <p>
            وقد يواجه درجًا، عائقًا، معلومات غير واضحة،
            أو طريقة وصول غير مناسبة.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        st.markdown(
            """
            <div class="card">

            <h3>الحل</h3>

            <p>
            يتيح VerifyAI Access رفع صورة للمكان أو الخدمة،
            ثم يستخدم الذكاء الاصطناعي لتحليلها.
            </p>

            <p>
            يكتشف العوائق ويقترح طرقًا لجعل التجربة
            أكثر إتاحة واستقلالية.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="card">

        <h3>كيف يعمل؟</h3>

        <p>
        ① رفع صورة
        </p>

        <p>
        ② تحديد نوع الاحتياج
        </p>

        <p>
        ③ تحليل الصورة بالذكاء الاصطناعي
        </p>

        <p>
        ④ الحصول على درجة الإتاحة
        </p>

        <p>
        ⑤ الحصول على المشاكل والحلول المقترحة
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# ACCESSIBILITY ANALYSIS
# =========================================================

elif page == "تحليل الإتاحة":

    st.markdown(
        '<div class="main-title">تحليل الإتاحة</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtitle">
        ارفع صورة للمكان أو الخدمة وسيقوم AI بتحليل إمكانية الوصول.
        </div>
        """,
        unsafe_allow_html=True,
    )

    need = st.selectbox(
        "نوع الاحتياج",
        [
            "تجربة شاملة",
            "إعاقة بصرية",
            "إعاقة سمعية",
            "إعاقة حركية",
            "صعوبة في فهم المعلومات",
        ],
    )

    uploaded_file = st.file_uploader(
        "ارفع صورة المكان أو الخدمة",
        type=["png", "jpg", "jpeg", "webp"],
    )

    if uploaded_file:

        try:
            image = Image.open(uploaded_file).convert("RGB")
        except Exception:
            st.error("تعذر قراءة الصورة.")
            st.stop()

        col1, col2 = st.columns([1, 1])

        with col1:

            st.image(
                image,
                caption="الصورة المرفوعة",
                use_container_width=True,
            )

        with col2:

            st.markdown(
                """
                <div class="card">

                <h3>جاهز للتحليل</h3>

                <p>
                سيحلل AI الصورة بحثًا عن العوائق
                والعناصر التي تؤثر على سهولة الوصول.
                </p>

                </div>
                """,
                unsafe_allow_html=True,
            )

            analyze_button = st.button(
                "تحليل الصورة بالذكاء الاصطناعي",
                type="primary",
            )

        if analyze_button:

            if not client:
                st.error(
                    "OPENAI_API_KEY غير موجود. أضف المفتاح ثم أعد تشغيل التطبيق."
                )
                st.stop()

            with st.spinner("AI يحلل الصورة..."):

                try:

                    # -----------------------------------------
                    # Resize image to reduce request size
                    # -----------------------------------------

                    max_size = 1600

                    image.thumbnail(
                        (max_size, max_size),
                        Image.Resampling.LANCZOS,
                    )

                    buffer = io.BytesIO()

                    image.save(
                        buffer,
                        format="JPEG",
                        quality=85,
                        optimize=True,
                    )

                    image_bytes = buffer.getvalue()

                    encoded_image = base64.b64encode(
                        image_bytes
                    ).decode("utf-8")

                    # -----------------------------------------
                    # AI PROMPT
                    # -----------------------------------------

                    prompt = f"""
أنت خبير في التصميم الشامل وإمكانية الوصول للأشخاص ذوي الإعاقة.

نوع الاحتياج الذي يريد المستخدم تحليله:
{need}

حلل الصورة المرفقة.

مهم جدًا:
- لا تخترع أي شيء غير ظاهر في الصورة.
- إذا كان شيء غير واضح، قل إنه غير واضح.
- لا تعتبر الصورة وحدها دليلًا مؤكدًا على أن المكان غير مهيأ.
- قدم ملاحظات عملية وقابلة للتطبيق.
- أجب باللغة العربية.

أريد النتيجة بهذا الترتيب:

SCORE: رقم من 0 إلى 100

SUMMARY:
ملخص قصير جدًا.

POSITIVE:
- الأشياء الجيدة الموجودة في الصورة.
- الأشياء التي تساعد على الوصول.

PROBLEMS:
- العوائق أو المشاكل الظاهرة.
- اذكر فقط الأشياء التي يمكن ملاحظتها أو استنتاجها بحذر.

SOLUTIONS:
- حلول عملية لتحسين الإتاحة.
- اجعل الحلول قابلة للتطبيق.

AI_IDEA:
اشرح كيف يمكن استخدام الذكاء الاصطناعي لجعل هذه التجربة
أكثر شمولاً واستقلالية.
"""

                    # -----------------------------------------
                    # OPENAI REQUEST
                    # -----------------------------------------

                    response = client.responses.create(
                        model=MODEL,
                        input=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": prompt,
                                    },
                                    {
                                        "type": "input_image",
                                        "image_url": (
                                            "data:image/jpeg;base64,"
                                            + encoded_image
                                        ),
                                    },
                                ],
                            }
                        ],
                    )

                    result = response.output_text

                    # -----------------------------------------
                    # Extract score
                    # -----------------------------------------

                    score = None

                    for line in result.splitlines():

                        clean_line = line.strip()

                        if clean_line.upper().startswith("SCORE:"):

                            value = clean_line.split(
                                ":",
                                1,
                            )[1].strip()

                            try:
                                score = int(value)
                            except ValueError:
                                score = None

                            break

                    st.session_state.analysis_result = result
                    st.session_state.analysis_score = score

                except Exception as error:

                    st.error(
                        f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي:\n\n{error}"
                    )

        # =====================================================
        # RESULT
        # =====================================================

        if st.session_state.analysis_result:

            st.divider()

            st.markdown(
                '<div class="main-title" style="font-size:30px;">نتيجة التحليل</div>',
                unsafe_allow_html=True,
            )

            score = st.session_state.analysis_score

            if score is not None:

                if score >= 75:
                    score_class = "score-good"
                elif score >= 50:
                    score_class = "score-medium"
                else:
                    score_class = "score-bad"

                score_col, result_col = st.columns(
                    [1, 3]
                )

                with score_col:

                    st.markdown(
                        f"""
                        <div class="card">

                        <div class="small-text">
                        درجة الإتاحة
                        </div>

                        <div class="score {score_class}">
                        {score}/100
                        </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with result_col:

                    st.markdown(
                        '<div class="card">',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        st.session_state.analysis_result
                    )

                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True,
                    )

            else:

                st.markdown(
                    '<div class="card">',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    st.session_state.analysis_result
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True,
                )


# =========================================================
# AI CHAT
# =========================================================

elif page == "المحادثة الذكية":

    st.markdown(
        '<div class="main-title">المحادثة الذكية</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtitle">
        اسأل AI عن كيفية جعل أي تجربة يومية أكثر إتاحة.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------
    # Display old messages
    # -----------------------------------------

    for message in st.session_state.chat_messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # -----------------------------------------
    # New message
    # -----------------------------------------

    user_message = st.chat_input(
        "اكتب سؤالك هنا..."
    )

    if user_message:

        # Add user message
        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_message)

        if not client:

            answer = (
                "لم يتم الاتصال بالذكاء الاصطناعي. "
                "تأكد من وجود OPENAI_API_KEY."
            )

        else:

            try:

                system_prompt = """
أنت مساعد متخصص في التصميم الشامل وإمكانية الوصول.

مهمتك مساعدة المستخدم على إعادة تصميم
التجارب اليومية للأشخاص ذوي الإعاقة.

ركز على:

- الاستقلالية
- سهولة الوصول
- التصميم الشامل
- الحلول الواقعية
- استخدام الذكاء الاصطناعي بشكل حقيقي
- إمكانية التطبيق

لا تخترع معلومات.
أجب باللغة العربية.
اجعل الإجابات واضحة ومباشرة.
"""

                response = client.responses.create(
                    model=MODEL,
                    instructions=system_prompt,
                    input=user_message,
                )

                answer = response.output_text

            except Exception as error:

                answer = (
                    "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي:\n\n"
                    f"{error}"
                )

        # Add AI response
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        with st.chat_message("assistant"):
            st.markdown(answer)
```
