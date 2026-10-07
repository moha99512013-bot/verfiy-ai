import os
import math
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "VerifyAI-Access/1.0 accessibility-navigation"
}

# =========================
# CSS
# =========================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap');

* {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 10% 10%, rgba(125, 92, 255, 0.10), transparent 25%),
        radial-gradient(circle at 90% 20%, rgba(0, 210, 190, 0.10), transparent 25%),
        #f7f8fc;
    color: #151526;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

/* =========================
   TOP BAR
========================= */

.topbar {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    background: rgba(255,255,255,0.90);
    border: 1px solid rgba(20,20,40,0.07);
    border-radius: 22px;
    box-shadow: 0 10px 35px rgba(30,25,70,0.06);
    margin-bottom: 28px;
}

.brand {
    font-size: 25px;
    font-weight: 900;
    letter-spacing: -0.7px;
}

.brand span {
    color: #7657ff;
}

.status {
    display: flex;
    align-items: center;
    gap: 9px;
    background: #f0efff;
    color: #6650db;
    padding: 9px 15px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
}

.status-dot {
    width: 9px;
    height: 9px;
    background: #35c98a;
    border-radius: 50%;
    box-shadow: 0 0 0 5px rgba(53,201,138,0.12);
}

/* =========================
   HERO
========================= */

.hero {
    position: relative;
    overflow: hidden;
    border-radius: 30px;
    padding: 48px;
    margin-bottom: 25px;
    background:
        radial-gradient(circle at 85% 20%, rgba(119,87,255,0.18), transparent 30%),
        radial-gradient(circle at 10% 90%, rgba(0,207,190,0.12), transparent 30%),
        white;
    border: 1px solid rgba(30,30,60,0.07);
    box-shadow: 0 20px 60px rgba(35,25,90,0.08);
}

.hero-content {
    max-width: 780px;
}

.hero-tag {
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: #f0edff;
    color: #6b51e6;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 17px;
}

.hero h1 {
    font-size: clamp(38px, 5vw, 68px);
    line-height: 1.08;
    margin: 0 0 18px 0;
    font-weight: 900;
    letter-spacing: -2px;
}

.hero h1 span {
    color: #7657ff;
}

.hero p {
    max-width: 760px;
    color: #646579;
    font-size: 17px;
    line-height: 2;
    margin: 0;
}

/* =========================
   SEARCH CARD
========================= */

.search-card {
    background: white;
    border: 1px solid rgba(30,30,60,0.07);
    border-radius: 25px;
    padding: 25px;
    box-shadow: 0 15px 45px rgba(30,25,70,0.06);
    margin-bottom: 25px;
}

.search-title {
    font-size: 20px;
    font-weight: 900;
    margin-bottom: 4px;
}

.search-subtitle {
    color: #77798b;
    font-size: 13px;
    margin-bottom: 18px;
}

/* =========================
   MAP
========================= */

.map-card {
    background: white;
    padding: 12px;
    border-radius: 27px;
    border: 1px solid rgba(30,30,60,0.07);
    box-shadow: 0 18px 55px rgba(30,25,70,0.07);
    margin-bottom: 25px;
}

.map-title {
    padding: 15px 18px 8px;
    font-size: 20px;
    font-weight: 900;
}

.map-subtitle {
    padding: 0 18px 15px;
    color: #77798b;
    font-size: 13px;
}

/* =========================
   STATS
========================= */

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 25px;
}

.stat {
    background: white;
    border: 1px solid rgba(30,30,60,0.07);
    border-radius: 22px;
    padding: 22px;
    text-align: center;
    box-shadow: 0 12px 35px rgba(30,25,70,0.05);
}

.stat-icon {
    font-size: 27px;
    margin-bottom: 7px;
}

.stat-number {
    font-size: 25px;
    font-weight: 900;
    color: #7657ff;
}

.stat-label {
    font-size: 12px;
    color: #77798b;
    margin-top: 3px;
    font-weight: 600;
}

/* =========================
   INFORMATION CARDS
========================= */

.info-card {
    background: white;
    border: 1px solid rgba(30,30,60,0.07);
    border-radius: 25px;
    padding: 25px;
    box-shadow: 0 15px 45px rgba(30,25,70,0.05);
    height: 100%;
}

.card-title {
    font-size: 20px;
    font-weight: 900;
    margin-bottom: 5px;
}

.card-subtitle {
    color: #77798b;
    font-size: 13px;
    margin-bottom: 20px;
}

/* =========================
   LEGEND
========================= */

.legend {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 13px;
    background: #f8f8fc;
    border-radius: 14px;
    color: #39394b;
    font-size: 13px;
    font-weight: 600;
}

.legend-icon {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    background: white;
    font-size: 17px;
}

/* =========================
   ROUTE ANALYSIS
========================= */

.route-analysis {
    padding: 18px;
    border-radius: 17px;
    background: #f6f5ff;
    border: 1px solid #e8e4ff;
}

.route-status {
    font-size: 17px;
    font-weight: 900;
    color: #5f49d4;
    margin-bottom: 8px;
}

.route-text {
    color: #68697a;
    line-height: 1.9;
    font-size: 13px;
}

/* =========================
   FOOTER
========================= */

.footer {
    text-align: center;
    color: #9697a5;
    font-size: 12px;
    padding: 25px 0 10px;
}

/* =========================
   BUTTONS
========================= */

.stButton > button {
    border-radius: 14px !important;
    border: 0 !important;
    background: #7657ff !important;
    color: white !important;
    font-weight: 800 !important;
    min-height: 45px !important;
    box-shadow: 0 8px 22px rgba(118,87,255,0.22);
}

.stButton > button:hover {
    background: #6749ed !important;
}

/* =========================
   INPUTS
========================= */

.stTextInput input {
    border-radius: 14px !important;
    border: 1px solid #e5e4ed !important;
    min-height: 45px !important;
}

.stTextInput input:focus {
    border-color: #7657ff !important;
    box-shadow: 0 0 0 2px rgba(118,87,255,0.10) !important;
}

/* =========================
   MOBILE
========================= */

@media (max-width: 800px) {

    .hero {
        padding: 30px 22px;
    }

    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .legend {
        grid-template-columns: 1fr;
    }

    .topbar {
        padding: 15px;
    }

    .brand {
        font-size: 21px;
    }

}

</style>
""", unsafe_allow_html=True)


# =========================
# SESSION
# =========================

if "route_result" not in st.session_state:
    st.session_state.route_result = None

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = None

if "start_text" not in st.session_state:
    st.session_state.start_text = ""

if "destination_text" not in st.session_state:
    st.session_state.destination_text = ""


# =========================
# HELPERS
# =========================

def geocode(place):
    try:
        params = {
            "q": place,
            "format": "json",
            "limit": 1
        }

        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=HEADERS,
            timeout=15
        )

        data = response.json()

        if not data:
            return None

        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "name": data[0].get("display_name", place)
        }

    except Exception:
        return None


def distance_meters(lat1, lon1, lat2, lon2):

    radius = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return radius * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def get_accessibility_data(lat, lon, radius=1800):

    query = f"""
    [out:json][timeout:25];

    (
      node["highway"="steps"](around:{radius},{lat},{lon});
      way["highway"="steps"](around:{radius},{lat},{lon});

      node["highway"="elevator"](around:{radius},{lat},{lon});
      node["elevator"="yes"](around:{radius},{lat},{lon});

      node["ramp"="yes"](around:{radius},{lat},{lon});
      way["ramp"="yes"](around:{radius},{lat},{lon});

      node["wheelchair"](around:{radius},{lat},{lon});
      way["wheelchair"](around:{radius},{lat},{lon});

      node["amenity"="toilets"]["wheelchair"="yes"](around:{radius},{lat},{lon});
      node["amenity"="parking"]["wheelchair"="yes"](around:{radius},{lat},{lon});

      node["entrance"]["wheelchair"="yes"](around:{radius},{lat},{lon});
      way["entrance"]["wheelchair"="yes"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=35
        )

        data = response.json()

        return data.get("elements", [])

    except Exception:

        return []


def get_route(start, destination):

    url = (
        "https://router.project-osrm.org/"
        "route/v1/foot/"
        f"{start['lon']},{start['lat']};"
        f"{destination['lon']},{destination['lat']}"
    )

    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=25
        )

        data = response.json()

        return data.get("routes", [])

    except Exception:

        return []


def classify_accessibility(elements):

    result = {
        "stairs": [],
        "elevators": [],
        "ramps": [],
        "wheelchair_yes": [],
        "wheelchair_limited": [],
        "wheelchair_no": [],
        "toilets": [],
        "parking": [],
        "entrances": []
    }

    for element in elements:

        tags = element.get("tags", {})

        if "lat" in element:
            lat = element["lat"]
            lon = element["lon"]

        elif "center" in element:
            lat = element["center"]["lat"]
            lon = element["center"]["lon"]

        else:
            continue

        point = {
            "lat": lat,
            "lon": lon,
            "tags": tags
        }

        if tags.get("highway") == "steps":
            result["stairs"].append(point)

        if tags.get("highway") == "elevator" or tags.get("elevator") == "yes":
            result["elevators"].append(point)

        if tags.get("ramp") == "yes":
            result["ramps"].append(point)

        wheelchair = tags.get("wheelchair")

        if wheelchair == "yes":
            result["wheelchair_yes"].append(point)

        elif wheelchair == "limited":
            result["wheelchair_limited"].append(point)

        elif wheelchair == "no":
            result["wheelchair_no"].append(point)

        if (
            tags.get("amenity") == "toilets"
            and tags.get("wheelchair") == "yes"
        ):
            result["toilets"].append(point)

        if (
            tags.get("amenity") == "parking"
            and tags.get("wheelchair") == "yes"
        ):
            result["parking"].append(point)

        if (
            tags.get("entrance")
            and tags.get("wheelchair") == "yes"
        ):
            result["entrances"].append(point)

    return result


def score_route(route, accessibility):

    score = 100

    geometry = route["geometry"]["coordinates"]

    # Check nearby accessibility data
    for lat, lon in [
        (p[1], p[0])
        for p in geometry[::max(1, len(geometry)//80)]
    ]:

        for stair in accessibility["stairs"]:

            d = distance_meters(
                lat,
                lon,
                stair["lat"],
                stair["lon"]
            )

            if d < 80:
                score -= 18

        for bad in accessibility["wheelchair_no"]:

            d = distance_meters(
                lat,
                lon,
                bad["lat"],
                bad["lon"]
            )

            if d < 80:
                score -= 20

        for good in (
            accessibility["wheelchair_yes"]
            + accessibility["ramps"]
            + accessibility["elevators"]
        ):

            d = distance_meters(
                lat,
                lon,
                good["lat"],
                good["lon"]
            )

            if d < 100:
                score += 3

    score = max(0, min(100, score))

    return score


# =========================
# TOP BAR
# =========================

st.markdown("""
<div class="topbar">

    <div class="brand">
        VerifyAI <span>Access</span>
    </div>

    <div class="status">
        <span class="status-dot"></span>
        Wheelchair Navigation
    </div>

</div>
""", unsafe_allow_html=True)


# =========================
# HERO
# =========================

st.markdown("""
<div class="hero">

    <div class="hero-content">

        <div class="hero-tag">
            ♿ AI-POWERED ACCESSIBILITY
        </div>

        <h1>
            تحرك بحرية.<br>
            <span>الوصول للجميع.</span>
        </h1>

        <p>
            خريطة ذكية مصممة أولاً لمستخدمي الكراسي المتحركة.
            ابحث عن وجهتك واحصل على مسار يعطي الأولوية
            للطرق المناسبة، مع إظهار المصاعد والمنحدرات
            والعوائق ونقاط الوصول المهيأة المسجلة على الخريطة.
        </p>

    </div>

</div>
""", unsafe_allow_html=True)


# =========================
# SEARCH
# =========================

st.markdown("""
<div class="search-card">

    <div class="search-title">
        🧭 أين تريد الذهاب؟
    </div>

    <div class="search-subtitle">
        أدخل نقطة البداية والوجهة للحصول على المسار المقترح.
    </div>

</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 0.32])

with col1:

    start = st.text_input(
        "نقطة البداية",
        placeholder="مثال: جامعة الملك عبدالعزيز",
        key="start_input"
    )

with col2:

    destination = st.text_input(
        "الوجهة",
        placeholder="مثال: مستشفى الملك فهد",
        key="destination_input"
    )

with col3:

    st.write("")

    search = st.button(
        "اعثر على المسار",
        use_container_width=True
    )


# =========================
# ROUTE SEARCH
# =========================

if search:

    if not start or not destination:

        st.warning("يرجى إدخال نقطة البداية والوجهة.")

    else:

        with st.spinner("جاري البحث عن أفضل مسار..."):

            start_location = geocode(start)
            destination_location = geocode(destination)

            if not start_location or not destination_location:

                st.error(
                    "لم نتمكن من العثور على إحدى النقطتين. "
                    "جرّب كتابة اسم المكان بشكل أوضح."
                )

            else:

                routes = get_route(
                    start_location,
                    destination_location
                )

                if not routes:

                    st.error(
                        "تعذر العثور على مسار حاليًا. "
                        "حاول مرة أخرى."
                    )

                else:

                    accessibility_elements = get_accessibility_data(
                        destination_location["lat"],
                        destination_location["lon"]
                    )

                    accessibility = classify_accessibility(
                        accessibility_elements
                    )

                    scored_routes = []

                    for route in routes:

                        route_score = score_route(
                            route,
                            accessibility
                        )

                        scored_routes.append(
                            (
                                route_score,
                                route
                            )
                        )

                    scored_routes.sort(
                        key=lambda x: x[0],
                        reverse=True
                    )

                    best_score, best_route = scored_routes[0]

                    st.session_state.route_result = {
                        "start": start_location,
                        "destination": destination_location,
                        "route": best_route,
                        "score": best_score,
                        "accessibility": accessibility
                    }

                    st.session_state.ai_answer = None


# =========================
# DISPLAY RESULT
# =========================

result = st.session_state.route_result

if result:

    start_location = result["start"]
    destination_location = result["destination"]
    route = result["route"]
    score = result["score"]
    accessibility = result["accessibility"]

    # =========================
    # STATS
    # =========================

    distance_km = route["distance"] / 1000

    duration_min = max(
        1,
        round(route["duration"] / 60)
    )

    elevator_count = len(
        accessibility["elevators"]
    )

    st.markdown(f"""
    <div class="stats-grid">

        <div class="stat">

            <div class="stat-icon">
                ♿
            </div>

            <div class="stat-number">
                {score}%
            </div>

            <div class="stat-label">
                مؤشر الإتاحة
            </div>

        </div>

        <div class="stat">

            <div class="stat-icon">
                🛣️
            </div>

            <div class="stat-number">
                {distance_km:.1f} كم
            </div>

            <div class="stat-label">
                المسافة
            </div>

        </div>

        <div class="stat">

            <div class="stat-icon">
                ⏱️
            </div>

            <div class="stat-number">
                {duration_min} دقيقة
            </div>

            <div class="stat-label">
                الوقت التقريبي
            </div>

        </div>

        <div class="stat">

            <div class="stat-icon">
                🛗
            </div>

            <div class="stat-number">
                {elevator_count}
            </div>

            <div class="stat-label">
                مصاعد مسجلة
            </div>

        </div>

    </div>
    """, unsafe_allow_html=True)


    # =========================
    # MAP
    # =========================

    center_lat = (
        start_location["lat"]
        + destination_location["lat"]
    ) / 2

    center_lon = (
        start_location["lon"]
        + destination_location["lon"]
    ) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles="OpenStreetMap"
    )

    # Start
    folium.Marker(
        [
            start_location["lat"],
            start_location["lon"]
        ],
        tooltip="نقطة البداية",
        popup=f"البداية<br>{start_location['name']}",
        icon=folium.Icon(
            color="green",
            icon="play",
            prefix="fa"
        )
    ).add_to(m)

    # Destination
    folium.Marker(
        [
            destination_location["lat"],
            destination_location["lon"]
        ],
        tooltip="الوجهة",
        popup=f"الوجهة<br>{destination_location['name']}",
        icon=folium.Icon(
            color="red",
            icon="flag",
            prefix="fa"
        )
    ).add_to(m)

    # Route
    route_points = [
        [point[1], point[0]]
        for point in route["geometry"]["coordinates"]
    ]

    folium.PolyLine(
        route_points,
        color="#7657ff",
        weight=7,
        opacity=0.85,
        tooltip="المسار المفضل"
    ).add_to(m)

    # Elevators
    for point in accessibility["elevators"]:

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🛗 مصعد",
            popup="مصعد مسجل على الخريطة",
            icon=folium.Icon(
                color="blue",
                icon="arrow-up",
                prefix="fa"
            )
        ).add_to(m)

    # Ramps
    for point in accessibility["ramps"]:

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🛝 منحدر",
            popup="منحدر مسجل للوصول",
            icon=folium.Icon(
                color="green",
                icon="road",
                prefix="fa"
            )
        ).add_to(m)

    # Wheelchair yes
    for point in accessibility["wheelchair_yes"]:

        folium.CircleMarker(
            [
                point["lat"],
                point["lon"]
            ],
            radius=7,
            color="#00a884",
            fill=True,
            fill_opacity=0.85,
            tooltip="♿ وصول مهيأ",
            popup="المكان مسجل كمتاح للكراسي المتحركة"
        ).add_to(m)

    # Stairs
    for point in accessibility["stairs"]:

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🚫 درج",
            popup="يوجد درج مسجل هنا",
            icon=folium.Icon(
                color="red",
                icon="warning-sign",
                prefix="glyphicon"
            )
        ).add_to(m)

    # Wheelchair no
    for point in accessibility["wheelchair_no"]:

        folium.CircleMarker(
            [
                point["lat"],
                point["lon"]
            ],
            radius=8,
            color="#e5484d",
            fill=True,
            fill_opacity=0.85,
            tooltip="⚠️ غير مهيأ",
            popup="المكان مسجل كغير مناسب للكراسي المتحركة"
        ).add_to(m)

    # Toilets
    for point in accessibility["toilets"]:

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🚻 دورة مياه مهيأة",
            popup="دورة مياه مهيأة مسجلة",
            icon=folium.Icon(
                color="purple",
                icon="home",
                prefix="glyphicon"
            )
        ).add_to(m)

    # Parking
    for point in accessibility["parking"]:

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🅿️ موقف مهيأ",
            popup="موقف مهيأ مسجل",
            icon=folium.Icon(
                color="orange",
                icon="parking",
                prefix="fa"
            )
        ).add_to(m)

    # =========================
    # MAP CARD
    # =========================

    st.markdown("""
    <div class="map-card">

        <div class="map-title">
            🗺️ خريطة الوصول
        </div>

        <div class="map-subtitle">
            العلامات على الخريطة توضح نقاط الوصول والعوائق
            المسجلة في بيانات OpenStreetMap.
        </div>

    </div>
    """, unsafe_allow_html=True)

    st_folium(
        m,
        width=None,
        height=620,
        returned_objects=[]
    )


    # =========================
    # LEGEND + ANALYSIS
    # =========================

    col1, col2 = st.columns([1.15, 0.85])

    with col1:

        st.markdown("""
        <div class="info-card">

            <div class="card-title">
                🗺️ دليل العلامات
            </div>

            <div class="card-subtitle">
                معنى كل علامة تظهر على الخريطة
            </div>

            <div class="legend">

                <div class="legend-item">
                    <span class="legend-icon">🟣</span>
                    <span>
                        <b>المسار المفضل</b><br>
                        الطريق الذي يقترحه النظام
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">🛗</span>
                    <span>
                        <b>مصعد</b><br>
                        مصعد مسجل على الخريطة
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">🛝</span>
                    <span>
                        <b>منحدر</b><br>
                        منحدر مسجل للوصول
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">♿</span>
                    <span>
                        <b>وصول مهيأ</b><br>
                        موقع مسجل كمتاح للكراسي المتحركة
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">🚫</span>
                    <span>
                        <b>درج</b><br>
                        وجود درج مسجل في المنطقة
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">⚠️</span>
                    <span>
                        <b>غير مهيأ</b><br>
                        موقع مسجل كغير مناسب
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">🚻</span>
                    <span>
                        <b>دورة مياه</b><br>
                        دورة مياه مهيأة مسجلة
                    </span>
                </div>

                <div class="legend-item">
                    <span class="legend-icon">🅿️</span>
                    <span>
                        <b>موقف مهيأ</b><br>
                        موقف مخصص أو مهيأ مسجل
                    </span>
                </div>

            </div>

        </div>
        """, unsafe_allow_html=True)


    with col2:

        if len(accessibility["stairs"]) == 0 and score >= 80:

            status_title = "♿ المسار يبدو مناسبًا بدرجة جيدة."

            status_text = (
                "لم يتم العثور على درجات قريبة من المسار "
                "ضمن بيانات الخريطة المتاحة، مع وجود مؤشرات "
                "وصول مهيأة."
            )

        elif len(accessibility["stairs"]) > 0:

            status_title = "⚠️ انتبه: توجد عوائق مسجلة."

            status_text = (
                f"تم العثور على {len(accessibility['stairs'])} "
                "نقطة مرتبطة بالدرجات ضمن المنطقة التي تم فحصها. "
                "تحقق من العلامات على الخريطة قبل بدء الرحلة."
            )

        else:

            status_title = "ℹ️ بيانات الوصول محدودة."

            status_text = (
                "لم يتم العثور على معلومات كافية لتأكيد "
                "جميع عناصر الإتاحة حول المسار. "
                "هذا لا يعني بالضرورة أن المكان غير مهيأ."
            )

        st.markdown(f"""
        <div class="info-card">

            <div class="card-title">
                ♿ تحليل المسار
            </div>

            <div class="card-subtitle">
                تقييم مبني على بيانات الوصول المتاحة
            </div>

            <div class="route-analysis">

                <div class="route-status">
                    {status_title}
                </div>

                <div class="route-text">
                    {status_text}
                </div>

            </div>

        </div>
        """, unsafe_allow_html=True)


    # =========================
    # AI ANALYSIS
    # =========================

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">

        <div class="card-title">
            ✨ المساعد الذكي للمسار
        </div>

        <div class="card-subtitle">
            اسأل VerifyAI عن المسار والعلامات الظاهرة على الخريطة.
        </div>

    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "✨ تحليل المسار بالذكاء الاصطناعي",
        use_container_width=True
    ):

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:

            try:
                api_key = st.secrets["OPENAI_API_KEY"]
            except Exception:
                api_key = None

        if not api_key:

            st.warning(
                "مفتاح OpenAI غير متصل. "
                "يمكن استخدام الخريطة بدون الذكاء الاصطناعي."
            )

        else:

            try:

                from openai import OpenAI

                client = OpenAI(
                    api_key=api_key
                )

                prompt = f"""
أنت مساعد متخصص في الوصول الشامل والتنقل لمستخدمي الكراسي المتحركة.

حلل المعلومات التالية فقط:

مؤشر الإتاحة: {score}/100

عدد المصاعد:
{len(accessibility["elevators"])}

عدد المنحدرات:
{len(accessibility["ramps"])}

عدد الدرج:
{len(accessibility["stairs"])}

عدد نقاط الوصول المهيأة:
{len(accessibility["wheelchair_yes"])}

عدد النقاط غير المهيأة:
{len(accessibility["wheelchair_no"])}

عدد دورات المياه المهيأة:
{len(accessibility["toilets"])}

عدد المواقف المهيأة:
{len(accessibility["parking"])}

قواعد مهمة:
- لا تقل إن المسار مضمون 100%.
- لا تخترع أي معلومة غير موجودة.
- وضح أن البيانات تعتمد على المعلومات المسجلة في الخريطة.
- اشرح للمستخدم معنى أهم العلامات.
- أعطِ خلاصة قصيرة وواضحة باللغة العربية.
"""

                response = client.responses.create(
                    model=MODEL,
                    input=prompt
                )

                st.session_state.ai_answer = response.output_text

            except Exception as e:

                st.error(
                    f"حدث خطأ أثناء تشغيل الذكاء الاصطناعي: {e}"
                )

    if st.session_state.ai_answer:

        st.markdown(
            f"""
            <div class="route-analysis">
                <div class="route-text">
                    {st.session_state.ai_answer}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================
# FOOTER
# =========================

st.markdown("""
<div class="footer">
    VerifyAI Access — Smart Accessibility Navigation
    <br>
    صُمم لجعل الوصول أكثر وضوحًا واستقلالية للجميع.
</div>
""", unsafe_allow_html=True)
