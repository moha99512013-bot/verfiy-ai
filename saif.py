import os
import io
import base64
import hashlib

import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from openai import OpenAI

st.set_page_config(
    page_title="VerifyAI Terminal",
    page_icon="🔎",
    layout="wide"
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

client = OpenAI(api_key=api_key) if api_key else None

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"

if "image" not in st.session_state:
    st.session_state.image = None

if "image_name" not in st.session_state:
    st.session_state.image_name = None

if "sha" not in st.session_state:
    st.session_state.sha = None

if "ela" not in st.session_state:
    st.session_state.ela = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ai_calls" not in st.session_state:
    st.session_state.ai_calls = 0


st.markdown("""
<style>
.stApp {
    background: #070b12;
    color: #eef3f8;
}

section[data-testid="stSidebar"] {
    background: #090e16;
}

.title {
    font-size: 28px;
    font-weight: 800;
}

.sub {
    color: #7f8b9b;
    font-size: 13px;
    margin-bottom: 20px;
}

.card {
    background: #0d141e;
    border: 1px solid #1c2735;
    border-radius: 15px;
    padding: 18px;
}

.stButton > button {
    background: #0d141e;
    color: #dbe4ed;
    border: 1px solid #253243;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


def make_ela(data):
    original = Image.open(io.BytesIO(data)).convert("RGB")

    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=90)

    compressed = Image.open(
        io.BytesIO(buffer.getvalue())
    ).convert("RGB")

    diff = ImageChops.difference(
        original,
        compressed
    )

    maximum = max(
        value for _, value in diff.getextrema()
    ) or 1

    result = ImageEnhance.Brightness(
        diff
    ).enhance(255 / maximum)

    output = io.BytesIO()
    result.save(output, "PNG")

    return output.getvalue()


def save_image(uploaded):
    data = uploaded.getvalue()

    st.session_state.image = data
    st.session_state.image_name = uploaded.name

    st.session_state.sha = hashlib.sha256(
        data
    ).hexdigest()

    try:
        st.session_state.ela = make_ela(data)
    except Exception:
        st.session_state.ela = None

    st.session_state.analysis = None


def analyze_image(question):
    if client is None:
        return "⚠️ OpenAI API غير متصل. تأكد من OPENAI_API_KEY."

    if st.session_state.image is None:
        return "ارفع صورة أولاً."

    if st.session_state.ai_calls >= 15:
        return "تم الوصول إلى حد 15 طلب AI في هذه الجلسة."

    image = Image.open(
        io.BytesIO(st.session_state.image)
    ).convert("RGB")

    image.thumbnail((1600, 1600))

    buffer = io.BytesIO()

    image.save(
        buffer,
        "JPEG",
        quality=85,
        optimize=True
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode()

    data_url = (
        "data:image/jpeg;base64,"
        + encoded
    )

    instructions = """
أنت مساعد للتحليل الجنائي الرقمي للصور.

حلل الصورة باللغة العربية.

صف ما يظهر في الصورة.
اذكر المؤشرات البصرية التي تستحق الفحص.
لا تحدد هوية الأشخاص.
لا تقل إن الصورة مزورة بشكل قطعي.
ELA مؤشر مساعد وليس دليلاً قاطعاً.
لا تخترع معلومات غير موجودة في الصورة.
"""

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": question
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url
                        }
                    ]
                }
            ]
        )

        st.session_state.ai_calls += 1

        result = response.output_text.strip()

        st.session_state.analysis = result

        return result

    except Exception as error:
        return "حدث خطأ في OpenAI:\n" + str(error)


with st.sidebar:

    st.markdown(
        "## 🔎 VerifyAI Terminal"
    )

    st.caption(
        "المنصة الوطنية للاستخبارات الجنائية الرقمية"
    )

    pages = [
        ("⌂", "الرئيسية"),
        ("◉", "تحليل المستندات"),
        ("✦", "المحادثة الذكية"),
        ("▤", "التقارير"),
        ("◌", "التحقق من الهوية"),
        ("◇", "التشفير والأمان"),
        ("◷", "سجل العمليات"),
        ("⚙", "الإعدادات")
    ]

    for icon, name in pages:

        if st.button(
            icon + "  " + name,
            key="nav_" + name,
            use_container_width=True
        ):
            st.session_state.page = name
            st.rerun()


st.markdown(
    '<div class="title">VerifyAI Terminal</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub">المنصة الوطنية للاستخبارات الجنائية الرقمية</div>',
    unsafe_allow_html=True
)


if st.session_state.page == "الرئيسية":

    left, right = st.columns(
        [1.55, 1],
        gap="large"
    )

    with left:

        st.subheader(
            "تحليل الأدلة الرقمية"
        )

        uploaded = st.file_uploader(
            "ارفع أي صورة",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp"
            ],
            key="home_upload"
        )

        if uploaded is not None:
            save_image(uploaded)

        if st.session_state.image is not None:

            st.image(
                st.session_state.image,
                use_container_width=True
            )

            st.caption(
                st.session_state.image_name
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "🔎 تحليل الصورة بالـAI",
                    use_container_width=True
                ):

                    analyze_image(
                        "حلل هذه الصورة جنائياً رقمياً."
                    )

                    st.rerun()

            with c2:

                if st.button(
                    "🧾 وريني الدليل",
                    use_container_width=True
                ):

                    st.markdown(
                        "### الدليل المرئي"
                    )

                    st.image(
                        st.session_state.image,
                        use_container_width=True
                    )

                    if st.session_state.ela is not None:

                        st.image(
                            st.session_state.ela,
                            use_container_width=True
                        )

                        st.caption(
                            "ELA مؤشر مساعد فقط، وليس إثباتاً قاطعاً."
                        )

            if st.session_state.analysis:

                st.markdown(
                    "### نتيجة تحليل الـAI"
                )

                st.markdown(
                    '<div class="card">'
                    + st.session_state.analysis.replace(
                        "\n",
                        "<br>"
                    )
                    + "</div>",
                    unsafe_allow_html=True
                )

        else:

            st.info(
                "ارفع صورة للبدء."
            )

    with right:

        st.subheader(
            "المساعد الجنائي الذكي"
        )

        for message in st.session_state.messages:

            with st.chat_message(
                message["role"]
            ):
                st.markdown(
                    message["content"]
                )

        prompt = st.chat_input(
            "اكتب طلبك هنا..."
        )

        if prompt:

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": prompt
                }
            )

            if (
                "وريني الدليل" in prompt
                or "أرني الدليل" in prompt
                or "show evidence" in prompt.lower()
            ):

                if st.session_state.image is not None:

                    answer = (
                        "هذا هو الدليل المرئي "
                        "من الصورة التي رفعتها."
                    )

                else:

                    answer = "ارفع صورة أولاً."

            elif st.session_state.image is not None:

                answer = analyze_image(
                    prompt
                )

            else:

                answer = "ارفع صورة أولاً."

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            st.rerun()


elif st.session_state.page == "تحليل المستندات":

    st.subheader(
        "تحليل المستندات والصور"
    )

    uploaded = st.file_uploader(
        "ارفع صورة",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp"
        ],
        key="documents_upload"
    )

    if uploaded is not None:
        save_image(uploaded)

    if st.session_state.image is not None:

        a, b = st.columns(2)

        with a:

            st.image(
                st.session_state.image,
                use_container_width=True
            )

        with b:

            if st.session_state.ela is not None:

                st.image(
                    st.session_state.ela,
                    use_container_width=True
                )

        if st.button(
            "🔎 تحليل بالذكاء الاصطناعي",
            use_container_width=True
        ):

            analyze_image(
                "حلل الصورة كدليل رقمي."
            )

            st.rerun()

        if st.session_state.analysis:
            st.write(
                st.session_state.analysis
            )

        st.markdown(
            "### SHA-256"
        )

        st.code(
            st.session_state.sha
        )


elif st.session_state.page == "المحادثة الذكية":

    st.subheader(
        "المحادثة الذكية"
    )

    if st.session_state.image is not None:

        st.image(
            st.session_state.image,
            width=400
        )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):
            st.markdown(
                message["content"]
            )

    prompt = st.chat_input(
        "اسأل عن الصورة..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        if st.session_state.image is not None:

            answer = analyze_image(
                prompt
            )

        else:

            answer = "ارفع صورة أولاً."

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        st.rerun()


elif st.session_state.page == "التقارير":

    st.subheader(
        "التقارير"
    )

    if st.session_state.analysis:

        report = (
            "VerifyAI Terminal\n\n"
            "الملف: "
            + str(st.session_state.image_name)
            + "\n\n"
            "SHA-256: "
            + str(st.session_state.sha)
            + "\n\n"
            "نتيجة التحليل:\n"
            + st.session_state.analysis
        )

        st.text_area(
            "التقرير",
            report,
            height=350
        )

        st.download_button(
            "⬇️ تحميل التقرير",
            report,
            "verifyai_report.txt",
            "text/plain"
        )

    else:

        st.info(
            "لا يوجد تحليل حتى الآن."
        )


elif st.session_state.page == "التشفير والأمان":

    st.subheader(
        "التشفير والأمان"
    )

    if st.session_state.sha:

        st.write(
            "SHA-256"
        )

        st.code(
            st.session_state.sha
        )

    else:

        st.info(
            "ارفع صورة أولاً."
        )


elif st.session_state.page == "الإعدادات":

    st.subheader(
        "الإعدادات"
    )

    st.write(
        "Model:",
        MODEL
    )

    st.write(
        "OpenAI API:",
        "متصل" if client else "غير متصل"
    )

    st.write(
        "طلبات AI:",
        str(st.session_state.ai_calls)
        + " / 15"
    )


st.markdown("---")

a, b, c = st.columns(3)

a.metric(
    "طلبات AI",
    st.session_state.ai_calls
)

b.metric(
    "صورة مرفوعة",
    "نعم" if st.session_state.image else "لا"
)

c.metric(
    "API",
    "متصل" if client else "غير متصل"
)
