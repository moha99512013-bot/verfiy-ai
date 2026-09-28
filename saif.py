import os
import io
import base64
import hashlib
from datetime import datetime

import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from openai import OpenAI


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="VerifyAI Terminal",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# OPENAI
# =========================================================

API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    try:
        API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        API_KEY = None

client = None

if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception:
        client = None


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ---------- MAIN ---------- */

    .stApp {
        background: #000000 !important;
        color: #ffffff !important;
    }

    body,
    .stApp,
    .stMarkdown,
    p,
    span,
    label,
    div,
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        color: #ffffff !important;
    }

    /* ---------- SIDEBAR ---------- */

    [data-testid="stSidebar"] {
        background: #050505 !important;
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* ---------- INPUTS ---------- */

    .stTextInput input,
    .stTextArea textarea {
        background: #050505 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #888888 !important;
    }

    /* ---------- BUTTONS ---------- */

    .stButton button {
        background: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
    }

    .stButton button:hover {
        border-color: #ffffff !important;
    }

    /* ---------- FILE UPLOADER ---------- */

    [data-testid="stFileUploader"] {
        background: #050505 !important;
        border: 1px dashed #444444 !important;
        border-radius: 12px !important;
    }

    [data-testid="stFileUploader"] * {
        color: #ffffff !important;
    }

    /* ---------- METRICS ---------- */

    [data-testid="stMetric"] {
        background: #050505 !important;
        border: 1px solid #222222 !important;
        padding: 12px !important;
        border-radius: 10px !important;
    }

    /* ---------- CHAT ---------- */

    [data-testid="stChatMessage"] {
        background: #050505 !important;
        border: 1px solid #222222 !important;
    }

    /* ---------- EXPANDERS ---------- */

    [data-testid="stExpander"] {
        background: #050505 !important;
        border: 1px solid #222222 !important;
    }

    /* ---------- ALERTS ---------- */

    [data-testid="stAlert"] * {
        color: #ffffff !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_bytes" not in st.session_state:
    st.session_state.uploaded_bytes = None

if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "ela_image" not in st.session_state:
    st.session_state.ela_image = None

if "sha256" not in st.session_state:
    st.session_state.sha256 = None

if "operations" not in st.session_state:
    st.session_state.operations = []


# =========================================================
# FUNCTIONS
# =========================================================

def add_operation(text):
    st.session_state.operations.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": text,
        },
    )


def calculate_sha256(data):
    return hashlib.sha256(data).hexdigest()


def create_ela(image, quality=90):
    """
    Error Level Analysis.
    ELA is an indicator and not conclusive proof of manipulation.
    """

    image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)

    buffer.seek(0)
    compressed = Image.open(buffer).convert("RGB")

    diff = ImageChops.difference(image, compressed)

    extrema = diff.getextrema()

    max_diff = max(
        channel_max
        for channel_min, channel_max in extrema
    )

    if max_diff == 0:
        max_diff = 1

    scale = 255 / max_diff

    ela = ImageEnhance.Brightness(diff).enhance(scale)

    return ela


def image_to_data_url(data, mime_type):
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def analyze_image_with_ai(image_bytes, mime_type):
    if not client:
        return (
            "⚠️ OpenAI API غير متصل.\n\n"
            "تأكد من إضافة OPENAI_API_KEY في "
            "Streamlit Cloud → Settings → Secrets."
        )

    image_url = image_to_data_url(
        image_bytes,
        mime_type,
    )

    instructions = """
أنت مساعد جنائي رقمي لتحليل الصور.

حلل الصورة المرفوعة بحذر وقدم تقريرًا واضحًا باللغة العربية.

ركز على:
- الأشياء والأشخاص والمحتوى الظاهر.
- أي علامات واضحة على التعديل أو التركيب.
- جودة الصورة والضغط.
- الاتساق البصري بين المناطق.
- النصوص أو الشعارات أو العناصر غير المعتادة.
- حدود ما يمكن إثباته من الصورة.

مهم:
لا تعتبر ELA أو أي مؤشر بصري دليلًا قاطعًا وحده.
إذا لم تستطع إثبات شيء، قل بوضوح إنه غير مؤكد.

استخدم العناوين:
1. الملخص
2. الملاحظات
3. مؤشرات التلاعب المحتملة
4. مستوى الثقة
5. حدود التحليل
"""

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "حلل هذه الصورة جنائيًا.",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                    ],
                }
            ],
        )

        return response.output_text

    except Exception as e:
        return (
            "حدث خطأ أثناء الاتصال بـ OpenAI.\n\n"
            f"تفاصيل الخطأ: {str(e)}"
        )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        # 🔎 VerifyAI
        ### المنصة الوطنية للاستخبارات الجنائية الرقمية
        """
    )

    st.divider()

    pages = [
        ("🏠", "الرئيسية"),
        ("📄", "تحليل المستندات"),
        ("💬", "المحادثة الذكية"),
        ("📊", "التقارير"),
        ("🪪", "التحقق من الهوية"),
        ("🔐", "التشفير والأمان"),
        ("🕘", "سجل العمليات"),
        ("⚙️", "الإعدادات"),
    ]

    for icon, page_name in pages:
        if st.button(
            f"{icon}  {page_name}",
            use_container_width=True,
            key=f"nav_{page_name}",
        ):
            st.session_state.page = page_name
            st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div style="
        padding: 10px 0 25px 0;
        border-bottom: 1px solid #222;
        margin-bottom: 25px;
    ">
        <div style="font-size: 30px; font-weight: 700;">
            🔎 VerifyAI Terminal
        </div>

        <div style="
            font-size: 15px;
            color: #aaaaaa !important;
            margin-top: 6px;
        ">
            المنصة الوطنية للاستخبارات الجنائية الرقمية
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# API STATUS
# =========================================================

if client:
    st.success("✓ OpenAI API متصل")
else:
    st.warning(
        "⚠️ OpenAI API غير متصل. "
        "تأكد من OPENAI_API_KEY في Streamlit Secrets."
    )


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.header("تحليل الأدلة الرقمية")

    st.write(
        "ارفع صورة لتحليلها باستخدام الذكاء الاصطناعي."
    )

    uploaded_file = st.file_uploader(
        "ارفع صورة",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
    )

    if uploaded_file:

        image_bytes = uploaded_file.getvalue()

        st.session_state.uploaded_bytes = image_bytes
        st.session_state.uploaded_name = uploaded_file.name
        st.session_state.sha256 = calculate_sha256(
            image_bytes
        )

        image = Image.open(
            io.BytesIO(image_bytes)
        )

        st.image(
            image,
            caption=uploaded_file.name,
            use_container_width=True,
        )

        st.write(
            f"SHA-256: `{st.session_state.sha256}`"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "🔍 تحليل الصورة بالذكاء الاصطناعي",
                use_container_width=True,
            ):

                with st.spinner(
                    "جاري تحليل الصورة..."
                ):

                    result = analyze_image_with_ai(
                        image_bytes,
                        uploaded_file.type,
                    )

                st.session_state.analysis = result

                add_operation(
                    f"تحليل الصورة: {uploaded_file.name}"
                )

        with col2:
            if st.button(
                "🧾 ورّيني الدليل",
                use_container_width=True,
            ):

                ela = create_ela(image)

                st.session_state.ela_image = ela

                add_operation(
                    f"إنشاء مؤشر ELA: {uploaded_file.name}"
                )

        if st.session_state.analysis:

            st.divider()

            st.subheader("نتيجة التحليل")

            st.write(
                st.session_state.analysis
            )

        if st.session_state.ela_image:

            st.divider()

            st.subheader(
                "المؤشر البصري ELA"
            )

            st.image(
                st.session_state.ela_image,
                caption=(
                    "ELA — مؤشر مساعد وليس دليلًا قاطعًا "
                    "على التلاعب."
                ),
                use_container_width=True,
            )


# =========================================================
# SMART CHAT
# =========================================================

elif st.session_state.page == "المحادثة الذكية":

    st.header("💬 المحادثة الذكية")

    if not client:
        st.warning(
            "OpenAI غير متصل. أضف OPENAI_API_KEY في Secrets."
        )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):
            st.markdown(
                message["content"]
            )

    prompt = st.chat_input(
        "اكتب سؤالك هنا..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        if client:

            try:

                response = client.responses.create(
                    model="gpt-5.6-luna",
                    instructions="""
أنت مساعد VerifyAI للذكاء الجنائي الرقمي.
أجب بالعربية بشكل واضح ومختصر.
لا تدّعي أن أي مؤشر بصري وحده يثبت التلاعب.
""",
                    input=prompt,
                )

                answer = response.output_text

            except Exception as e:

                answer = (
                    "حدث خطأ في OpenAI:\n"
                    + str(e)
                )

        else:

            answer = (
                "⚠️ OpenAI API غير متصل. "
                "تحقق من OPENAI_API_KEY في Secrets."
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()


# =========================================================
# REPORTS
# =========================================================

elif st.session_state.page == "التقارير":

    st.header("📊 التقارير")

    if st.session_state.analysis:

        st.subheader("آخر تحليل")

        st.write(
            st.session_state.analysis
        )

    else:

        st.info(
            "لم يتم إنشاء تقرير بعد."
        )


# =========================================================
# OPERATION LOG
# =========================================================

elif st.session_state.page == "سجل العمليات":

    st.header("🕘 سجل العمليات")

    if not st.session_state.operations:

        st.info(
            "لا توجد عمليات حتى الآن."
        )

    else:

        for operation in st.session_state.operations:

            st.write(
                f"**{operation['time']}** — "
                f"{operation['text']}"
            )


# =========================================================
# OTHER PAGES
# =========================================================

elif st.session_state.page == "تحليل المستندات":

    st.header("📄 تحليل المستندات")

    st.info(
        "قسم تحليل المستندات جاهز للإضافة."
    )


elif st.session_state.page == "التحقق من الهوية":

    st.header("🪪 التحقق من الهوية")

    st.info(
        "قسم التحقق من الهوية جاهز للإضافة."
    )


elif st.session_state.page == "التشفير والأمان":

    st.header("🔐 التشفير والأمان")

    st.info(
        "بيانات التحليل الحساسة يجب التعامل معها بأمان."
    )


elif st.session_state.page == "الإعدادات":

    st.header("⚙️ الإعدادات")

    st.write(
        "إعدادات VerifyAI Terminal"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "حالة الذكاء الاصطناعي",
        "متصل" if client else "غير متصل",
    )

with col2:
    st.metric(
        "العمليات",
        len(st.session_state.operations),
    )

with col3:
    st.metric(
        "الصورة الحالية",
        "مرفوعة"
        if st.session_state.uploaded_bytes
        else "لا توجد",
    )
