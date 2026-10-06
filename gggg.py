import os
import io
import base64
import streamlit as st
from PIL import Image
from openai import OpenAI

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide"
)

# ---------- OpenAI ----------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

client = OpenAI(api_key=api_key) if api_key else None
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

# ---------- State ----------
if "result" not in st.session_state:
    st.session_state.result = None

if "score" not in st.session_state:
    st.session_state.score = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Design ----------
st.markdown("""
<style>
.stApp {
    background: #05070b;
    color: white;
}

header {
    visibility: hidden;
}

.block-container {
    max-width: 1050px;
    padding-top: 25px;
}

.logo {
    font-size: 25px;
    font-weight: 800;
}

.logo span {
    color: #8b9cff;
}

.hero {
    text-align: center;
    padding: 70px 20px 35px;
}

.hero h1 {
    font-size: 48px;
    margin-bottom: 12px;
}

.hero h1 span {
    color: #8b9cff;
}

.hero p {
    color: #9ca8b8 !important;
    font-size: 17px;
    line-height: 1.7;
    max-width: 650px;
    margin: auto;
}

.box {
    background: #0b0f17;
    border: 1px solid #202938;
    border-radius: 18px;
    padding: 25px;
    margin-top: 20px;
}

.title {
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 5px;
}

.description {
    color: #8f9aaa !important;
    font-size: 14px;
}

.score {
    font-size: 55px;
    font-weight: 800;
    text-align: center;
}

.good {
    color: #55d98a !important;
}

.medium {
    color: #f0c75e !important;
}

.bad {
    color: #ff6b6b !important;
}

.stButton > button {
    width: 100%;
    height: 48px;
    border-radius: 12px;
    background: #121927;
    color: white;
    border: 1px solid #303b4c;
    font-weight: 600;
}

.stButton > button:hover {
    border-color: #8b9cff;
}

[data-testid="stFileUploader"] {
    background: transparent;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;">
    <div class="logo">
        VerifyAI <span>Access</span>
    </div>

    <div style="color:#8f9aaa;font-size:13px;">
        ● AI Accessibility Assistant
    </div>
</div>
""", unsafe_allow_html=True)

# ---------- Hero ----------
st.markdown("""
<div class="hero">

<h1>
اجعل العالم <span>أسهل وصولاً</span>
</h1>

<p>
ارفع صورة لمكان أو خدمة، وسيستخدم الذكاء الاصطناعي
لاكتشاف مشاكل الإتاحة واقتراح حلول تجعل التجربة
أكثر شمولاً واستقلالية.
</p>

</div>
""", unsafe_allow_html=True)

# ---------- Upload ----------
st.markdown("""
<div class="box">

<div class="title">1. ارفع صورة</div>

<div class="description">
صورة لمدخل مبنى، مدرسة، شارع، متجر، محطة أو أي مكان تريد تحليله.
</div>

</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "اختر صورة",
    type=["png", "jpg", "jpeg", "webp"],
    label_visibility="collapsed"
)

if uploaded:

    try:
        image = Image.open(uploaded).convert("RGB")
    except Exception:
        st.error("الصورة غير صالحة.")
        st.stop()

    st.image(
        image,
        use_container_width=True
    )

    st.markdown("""
    <div class="box">

    <div class="title">2. لمن تريد تحسين التجربة؟</div>

    </div>
    """, unsafe_allow_html=True)

    need = st.selectbox(
        "نوع الاحتياج",
        [
            "تجربة شاملة للجميع",
            "الأشخاص ذوو الإعاقة البصرية",
            "الأشخاص ذوو الإعاقة السمعية",
            "الأشخاص ذوو الإعاقة الحركية",
            "الأشخاص الذين يحتاجون معلومات مبسطة"
        ],
        label_visibility="collapsed"
    )

    st.write("")

    analyze = st.button(
        "✦ تحليل الصورة بالذكاء الاصطناعي",
        type="primary"
    )

    # ---------- Analyze ----------
    if analyze:

        if not client:
            st.error(
                "OPENAI_API_KEY غير موجود. أضفه في Secrets ثم أعد تشغيل الموقع."
            )
        else:

            with st.spinner("جاري تحليل الصورة..."):

                try:

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

                    encoded = base64.b64encode(
                        buffer.getvalue()
                    ).decode("utf-8")

                    prompt = f"""
أنت خبير في التصميم الشامل وإمكانية الوصول.

حلل الصورة المرفقة.

نوع الاحتياج:
{need}

لا تخترع أي شيء غير ظاهر في الصورة.
إذا كان شيء غير واضح، اذكر أنه غير واضح.

أجب باللغة العربية.

اكتب النتيجة بهذا الشكل:

SCORE:
رقم من 0 إلى 100.

SUMMARY:
ملخص قصير.

WHAT_IS_GOOD:
الأشياء الجيدة الظاهرة.

PROBLEMS:
العوائق أو المشاكل المحتملة.

SOLUTIONS:
حلول عملية لتحسين الإتاحة.

AI_SOLUTION:
كيف يمكن استخدام الذكاء الاصطناعي لجعل
هذه التجربة أكثر شمولاً واستقلالية.

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

                            try:
                                score = int(
                                    line.split(":", 1)[1].strip()
                                )
                            except:
                                score = None

                            break

                    st.session_state.result = result
                    st.session_state.score = score

                except Exception as e:

                    st.error(
                        f"حدث خطأ أثناء التحليل:\n\n{e}"
                    )

# ---------- Result ----------
if st.session_state.result:

    st.markdown("---")

    st.markdown(
        '<div class="title">نتيجة تحليل AI</div>',
        unsafe_allow_html=True
    )

    score = st.session_state.score

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
                <div class="box">

                <div style="text-align:center;color:#8f9aaa;">
                Accessibility Score
                </div>

                <div class="score {score_class}">
                {score}
                </div>

                <div style="text-align:center;color:#8f9aaa;">
                من 100
                </div>

                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:

            st.markdown(
                '<div class="box">',
                unsafe_allow_html=True
            )

            st.markdown(st.session_state.result)

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )

    else:

        st.markdown(
            '<div class="box">',
            unsafe_allow_html=True
        )

        st.markdown(st.session_state.result)

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

# ---------- Chat ----------
st.markdown("---")

st.markdown(
    '<div class="title">اسأل VerifyAI Access</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="description">اسأل عن أي طريقة لجعل تجربة يومية أكثر إتاحة.</div>',
    unsafe_allow_html=True
)

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input(
    "مثلاً: كيف أجعل مدخل المدرسة أكثر إتاحة؟"
)

if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    if not client:

        answer = "الذكاء الاصطناعي غير متصل. تأكد من OPENAI_API_KEY."

    else:

        try:

            response = client.responses.create(
                model=MODEL,
                instructions="""
أنت VerifyAI Access، مساعد متخصص في التصميم الشامل.

ساعد المستخدم على جعل التجارب اليومية أكثر إتاحة
واستقلالية للأشخاص ذوي الإعاقة.

اقترح حلولاً عملية تستخدم الذكاء الاصطناعي بشكل حقيقي.
أجب باللغة العربية وبوضوح.
""",
                input=question
            )

            answer = response.output_text

        except Exception as e:

            answer = f"حدث خطأ:\n\n{e}"

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    with st.chat_message("assistant"):
        st.markdown(answer)
