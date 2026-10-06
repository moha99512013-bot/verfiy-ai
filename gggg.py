import os
import io
import base64
import streamlit as st
from PIL import Image
from openai import OpenAI

# =========================================================
# VerifyAI Access
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide"
)

# =========================================================
# OpenAI
# =========================================================

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

client = OpenAI(api_key=api_key) if api_key else None

MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
)

# =========================================================
# Session State
# =========================================================

if "result" not in st.session_state:
    st.session_state.result = None

if "score" not in st.session_state:
    st.session_state.score = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# Design
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #ffffff;
        color: #172033;
    }

    header {
        visibility: hidden;
    }

    .block-container {
        max-width: 1150px;
        padding-top: 25px;
        padding-bottom: 70px;
    }

    /* Header */

    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 5px 25px 5px;
    }

    .logo {
        font-size: 25px;
        font-weight: 900;
        color: #172033;
    }

    .logo span {
        color: #6c63ff;
    }

    .status {
        background: #eefbf4;
        color: #20a464;
        border-radius: 30px;
        padding: 8px 15px;
        font-size: 13px;
        font-weight: 700;
    }

    /* Hero */

    .hero {
        text-align: center;
        padding: 65px 20px 45px;
    }

    .hero h1 {
        font-size: 52px;
        line-height: 1.15;
        font-weight: 900;
        color: #172033;
        margin-bottom: 18px;
    }

    .hero h1 .purple {
        color: #6c63ff;
    }

    .hero h1 .blue {
        color: #20aee8;
    }

    .hero p {
        color: #667085 !important;
        font-size: 18px;
        line-height: 1.8;
        max-width: 720px;
        margin: auto;
    }

    /* Feature Cards */

    .feature-row {
        display: flex;
        gap: 14px;
        margin: 15px 0 30px;
    }

    .feature {
        flex: 1;
        padding: 20px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 15px;
    }

    .feature p {
        margin: 7px 0 0;
        font-weight: 500;
        font-size: 13px;
    }

    .purple-card {
        background: #f1efff;
        color: #665ce6;
    }

    .blue-card {
        background: #eaf8ff;
        color: #1699d0;
    }

    .green-card {
        background: #eafaf1;
        color: #20a464;
    }

    .orange-card {
        background: #fff5e8;
        color: #ed921c;
    }

    /* Main Card */

    .main-card {
        background: #ffffff;
        border: 1px solid #e9edf4;
        box-shadow: 0 12px 40px rgba(39, 52, 77, 0.08);
        border-radius: 25px;
        padding: 30px;
        margin-top: 20px;
    }

    .section-title {
        font-size: 21px;
        font-weight: 850;
        color: #172033;
        margin-bottom: 5px;
    }

    .section-subtitle {
        color: #7a8495;
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* Upload */

    [data-testid="stFileUploader"] {
        background: #f8faff;
        border: 2px dashed #cdd5e1;
        border-radius: 20px;
        padding: 12px;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #6c63ff;
        background: #faf9ff;
    }

    /* Buttons */

    .stButton > button {
        width: 100%;
        height: 54px;
        border-radius: 15px;
        border: none;
        background: linear-gradient(
            90deg,
            #6c63ff,
            #20aee8
        );
        color: white;
        font-size: 16px;
        font-weight: 800;
        box-shadow: 0 8px 20px rgba(
            108,
            99,
            255,
            0.22
        );
    }

    .stButton > button:hover {
        color: white;
    }

    /* Results */

    .result-card {
        background: #f8faff;
        border: 1px solid #e7ebf3;
        border-radius: 22px;
        padding: 25px;
        margin-top: 18px;
    }

    .problem-card {
        background: #fff7f5;
        border-left: 5px solid #ff6b6b;
        border-radius: 16px;
        padding: 18px;
        margin-top: 12px;
    }

    .solution-card {
        background: #effbf5;
        border-left: 5px solid #25b874;
        border-radius: 16px;
        padding: 18px;
        margin-top: 12px;
    }

    .ai-card {
        background: #f1efff;
        border-left: 5px solid #6c63ff;
        border-radius: 16px;
        padding: 18px;
        margin-top: 12px;
    }

    /* Score */

    .score-box {
        text-align: center;
        background: linear-gradient(
            145deg,
            #f1efff,
            #eaf8ff
        );
        border-radius: 22px;
        padding: 25px;
    }

    .score-number {
        font-size: 58px;
        font-weight: 900;
        color: #6c63ff;
    }

    .score-label {
        color: #687386;
        font-size: 13px;
    }

    /* Chat */

    .chat-title {
        font-size: 25px;
        font-weight: 900;
        color: #172033;
        margin-top: 45px;
    }

    /* Images */

    img {
        border-radius: 18px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# Header
# =========================================================

st.markdown(
    """
    <div class="topbar">

        <div class="logo">
            VerifyAI <span>Access</span>
        </div>

        <div class="status">
            ● AI جاهز للتحليل
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# Hero
# =========================================================

st.markdown(
    """
    <div class="hero">

        <h1>
            اكتشف ما يحتاجه المكان<br>
            <span class="purple">ليصبح أسهل</span>
            <span class="blue">للجميع</span>
        </h1>

        <p>
            ارفع صورة لأي مكان، ودع الذكاء الاصطناعي
            يكتشف بنفسه المشاكل والعوائق وما الذي يحتاجه
            المكان ليصبح أكثر إتاحة وسهولة واستقلالية للجميع.
        </p>

    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# Features
# =========================================================

st.markdown(
    """
    <div class="feature-row">

        <div class="feature purple-card">
            🔎 يكتشف المشكلة
            <p>
                يحلل المكان ويحدد العوائق الظاهرة.
            </p>
        </div>

        <div class="feature blue-card">
            💡 يعرف الاحتياج
            <p>
                يحدد ما الذي يحتاجه المكان.
            </p>
        </div>

        <div class="feature green-card">
            ✓ يقترح الحل
            <p>
                يعطي حلولاً عملية وقابلة للتطبيق.
            </p>
        </div>

        <div class="feature orange-card">
            🤖 يستخدم AI
            <p>
                ذكاء اصطناعي لتحليل التجربة.
            </p>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# Upload Section
# =========================================================

st.markdown(
    """
    <div class="main-card">

        <div class="section-title">
            📷 ارفع صورة المكان
        </div>

        <div class="section-subtitle">
            مدخل، مدرسة، شارع، متجر، محطة، ملعب،
            مبنى أو أي مكان آخر.
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

uploaded = st.file_uploader(
    "اختر صورة",
    type=[
        "png",
        "jpg",
        "jpeg",
        "webp"
    ],
    label_visibility="collapsed"
)

# =========================================================
# Image Analysis
# =========================================================

if uploaded:

    try:

        image = Image.open(
            uploaded
        ).convert("RGB")

    except Exception:

        st.error(
            "الصورة غير صالحة."
        )

        st.stop()

    st.write("")

    st.image(
        image,
        use_container_width=True
    )

    st.write("")

    analyze = st.button(
        "✨ اكتشف ما يحتاجه هذا المكان بالذكاء الاصطناعي"
    )

    if analyze:

        if not client:

            st.error(
                "OPENAI_API_KEY غير موجود. "
                "أضفه في Secrets ثم أعد تشغيل الموقع."
            )

        else:

            with st.spinner(
                "الذكاء الاصطناعي يفحص المكان..."
            ):

                try:

                    # Resize image
                    image.thumbnail(
                        (1600, 1600),
                        Image.Resampling.LANCZOS
                    )

                    # Convert image to JPEG
                    buffer = io.BytesIO()

                    image.save(
                        buffer,
                        format="JPEG",
                        quality=85
                    )

                    # Encode image
                    encoded = base64.b64encode(
                        buffer.getvalue()
                    ).decode("utf-8")

                    # AI instructions
                    prompt = """
أنت VerifyAI Access، خبير في التصميم الشامل
وإمكانية الوصول.

حلل الصورة المرفقة بنفسك.

مهم جداً:

لا أريد من المستخدم اختيار نوع الإعاقة.

أنت الذي تحدد من الصورة:
1. ما هي المشكلة أو العائق؟
2. من الأشخاص الذين قد يتأثرون؟
3. ما الذي يحتاجه المكان؟
4. كيف يمكن تحسينه؟
5. كيف يمكن استخدام الذكاء الاصطناعي؟

لا تخترع أشياء غير موجودة في الصورة.

إذا كان شيء غير واضح في الصورة،
اذكر أنه غير واضح.

أجب باللغة العربية.

استخدم هذا الشكل:

SCORE:
رقم من 0 إلى 100 يوضح مستوى الإتاحة الظاهر في الصورة.

WHAT_IS_THE_PROBLEM:
ما المشكلة أو العائق الذي تراه؟

WHO_MAY_NEED_HELP:
من الأشخاص الذين قد يحتاجون مساعدة بسبب هذا العائق؟

WHAT_IS_NEEDED:
ما الشيء الذي يحتاجه المكان ليصبح أكثر إتاحة؟

SOLUTIONS:
حلول عملية وواضحة لتحسين المكان.

AI_SOLUTION:
فكرة تستخدم الذكاء الاصطناعي لجعل التجربة
أسهل وأكثر استقلالية.

SUMMARY:
ملخص قصير جداً للنتيجة.

ركز فقط على الأشياء التي يمكن رؤيتها
أو استنتاجها بشكل منطقي من الصورة.
"""

                    # OpenAI request
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
                                        "image_url": (
                                            "data:image/jpeg;base64,"
                                            + encoded
                                        )
                                    }
                                ]
                            }
                        ]
                    )

                    result = response.output_text

                    # Extract score
                    score = None

                    for line in result.splitlines():

                        if line.strip().upper().startswith(
                            "SCORE:"
                        ):

                            try:

                                score = int(
                                    line.split(
                                        ":",
                                        1
                                    )[1].strip()
                                )

                            except Exception:

                                score = None

                            break

                    # Save result
                    st.session_state.result = result
                    st.session_state.score = score

                except Exception as e:

                    st.error(
                        "حدث خطأ أثناء التحليل:\n\n"
                        + str(e)
                    )

# =========================================================
# Results
# =========================================================

if st.session_state.result:

    st.markdown(
        """
        <div class="chat-title">
            📊 نتيجة التحليل
        </div>
        """,
        unsafe_allow_html=True
    )

    score = st.session_state.score

    if score is not None:

        col1, col2 = st.columns(
            [1, 2.8]
        )

        with col1:

            st.markdown(
                f"""
                <div class="score-box">

                    <div class="score-label">
                        مستوى الإتاحة
                    </div>

                    <div class="score-number">
                        {score}
                    </div>

                    <div class="score-label">
                        من 100
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:

            st.markdown(
                """
                <div class="result-card">
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                st.session_state.result
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

    else:

        st.markdown(
            """
            <div class="result-card">
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            st.session_state.result
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

# =========================================================
# AI Chat
# =========================================================

st.markdown(
    """
    <div class="chat-title">
        💬 اسأل VerifyAI Access
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="section-subtitle">
        اسأل الذكاء الاصطناعي عن أي تجربة أو مكان
        وكيف يمكن جعله أكثر إتاحة.
    </div>
    """,
    unsafe_allow_html=True
)

# Show previous messages

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )

# Chat input

question = st.chat_input(
    "مثلاً: كيف نجعل المدرسة أسهل للجميع؟"
)

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(
            question
        )

    if not client:

        answer = (
            "الذكاء الاصطناعي غير متصل. "
            "تأكد من إضافة OPENAI_API_KEY."
        )

    else:

        try:

            response = client.responses.create(
                model=MODEL,
                instructions="""
أنت VerifyAI Access.

أنت متخصص في التصميم الشامل
وإمكانية الوصول.

ساعد المستخدم على اكتشاف:

- المشكلة
- من قد يحتاج مساعدة
- ما الذي يحتاجه المكان
- الحلول الممكنة
- أفكار تستخدم الذكاء الاصطناعي

لا تفترض معلومات غير معروفة.

اجعل الإجابات واضحة وعملية ومختصرة.

أجب باللغة العربية.
""",
                input=question
            )

            answer = response.output_text

        except Exception as e:

            answer = (
                "حدث خطأ:\n\n"
                + str(e)
            )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    with st.chat_message("assistant"):

        st.markdown(
            answer
        )
