import os
import math
import requests
import streamlit as st
import folium

from streamlit_folium import st_folium


# =========================================================
# VERIFYAI ACCESS
# Wheelchair-first accessibility navigation
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "VerifyAI-Access/1.0 accessibility-navigation"
}

WHEELCHAIR_PROFILE = "♿ Wheelchair"


# =========================================================
# SESSION STATE
# =========================================================

if "route_result" not in st.session_state:
    st.session_state.route_result = None

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = None

if "start_text" not in st.session_state:
    st.session_state.start_text = ""

if "destination_text" not in st.session_state:
    st.session_state.destination_text = ""


# =========================================================
# PAGE STYLE
# =========================================================

st.markdown(
    """
    <style>

    /* ==============================
       GLOBAL
    ============================== */

    .stApp {
        background:
            radial-gradient(
                circle at 0% 0%,
                rgba(104, 92, 255, 0.12),
                transparent 27%
            ),
            radial-gradient(
                circle at 100% 0%,
                rgba(25, 190, 170, 0.11),
                transparent 27%
            ),
            #f7f9fc;

        color: #172033;
    }

    header {
        visibility: hidden;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 18px;
        padding-bottom: 70px;
    }

    /* ==============================
       BRAND
    ============================== */

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
    }

    .brand {
        font-size: 29px;
        font-weight: 950;
        letter-spacing: -1.3px;
        color: #151a2b;
    }

    .brand span {
        color: #675cf5;
    }

    .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #e9faf2;
        color: #16885b;
        padding: 9px 15px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 850;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #20bf79;
    }

    /* ==============================
       HERO
    ============================== */

    .hero {
        position: relative;
        overflow: hidden;
        padding: 65px 58px;
        border-radius: 36px;

        background:
            linear-gradient(
                120deg,
                #ffffff 0%,
                #f2efff 50%,
                #e9fbff 100%
            );

        border: 1px solid #e5e9f1;

        box-shadow:
            0 30px 80px rgba(
                45,
                55,
                90,
                0.10
            );
    }

    .hero:before {
        content: "";
        position: absolute;
        width: 330px;
        height: 330px;
        right: -120px;
        top: -130px;
        border-radius: 50%;
        background: rgba(
            103,
            92,
            245,
            0.10
        );
    }

    .hero:after {
        content: "";
        position: absolute;
        width: 180px;
        height: 180px;
        right: 170px;
        bottom: -110px;
        border-radius: 50%;
        background: rgba(
            28,
            190,
            170,
            0.09
        );
    }

    .hero-content {
        position: relative;
        z-index: 2;
    }

    .hero-tag {
        display: inline-block;
        padding: 8px 13px;
        border-radius: 50px;
        background: rgba(
            103,
            92,
            245,
            0.09
        );
        color: #5b50df;
        font-size: 12px;
        font-weight: 900;
        margin-bottom: 18px;
    }

    .hero h1 {
        margin: 0;
        font-size: 61px;
        line-height: 1.02;
        letter-spacing: -2.7px;
        font-weight: 950;
        color: #151a2b;
    }

    .hero h1 span {
        background:
            linear-gradient(
                90deg,
                #665cf5,
                #18aee7,
                #20b878
            );

        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero p {
        max-width: 760px;
        margin-top: 20px;
        color: #697386 !important;
        font-size: 17px;
        line-height: 1.85;
    }

    /* ==============================
       SEARCH PANEL
    ============================== */

    .search-panel {
        position: relative;
        z-index: 10;
        margin-top: -30px;
        padding: 25px;
        border-radius: 27px;
        background: #ffffff;
        border: 1px solid #e5e9f1;
        box-shadow:
            0 22px 60px rgba(
                35,
                45,
                75,
                0.12
            );
    }

    .search-heading {
        font-size: 22px;
        font-weight: 950;
        color: #171c2c;
    }

    .search-subheading {
        margin-top: 4px;
        margin-bottom: 18px;
        color: #7a8495;
        font-size: 13px;
    }

    .stTextInput input {
        height: 52px !important;
        border-radius: 15px !important;
        border: 1px solid #dfe4ee !important;
        background: #fbfcff !important;
        font-size: 14px !important;
    }

    .stTextInput input:focus {
        border-color: #6b60f5 !important;
        box-shadow:
            0 0 0 3px rgba(
                107,
                96,
                245,
                0.10
            ) !important;
    }

    .stButton > button {
        height: 52px;
        border: 0;
        border-radius: 15px;

        color: #ffffff;

        font-size: 15px;
        font-weight: 900;

        background:
            linear-gradient(
                100deg,
                #675cf5,
                #20aee8
            );

        box-shadow:
            0 11px 28px rgba(
                103,
                92,
                245,
                0.24
            );

        transition:
            transform 0.2s ease,
            box-shadow 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);

        box-shadow:
            0 16px 34px rgba(
                103,
                92,
                245,
                0.30
            );
    }

    /* ==============================
       MAP HEADER
    ============================== */

    .section-title {
        margin-top: 35px;
        font-size: 28px;
        font-weight: 950;
        letter-spacing: -0.7px;
        color: #171c2c;
    }

    .section-subtitle {
        margin-top: 4px;
        margin-bottom: 15px;
        color: #7b8495;
        font-size: 14px;
    }

    /* ==============================
       STATS
    ============================== */

    .stats {
        display: grid;
        grid-template-columns:
            repeat(4, 1fr);

        gap: 14px;

        margin-top: 18px;
    }

    .stat {
        padding: 20px;
        border-radius: 21px;
        background: #ffffff;
        border: 1px solid #e7eaf1;

        box-shadow:
            0 10px 28px rgba(
                35,
                45,
                75,
                0.06
            );
    }

    .stat-icon {
        font-size: 25px;
    }

    .stat-number {
        margin-top: 7px;
        font-size: 25px;
        font-weight: 950;
        color: #171c2c;
    }

    .stat-label {
        margin-top: 2px;
        color: #7c8595;
        font-size: 12px;
    }

    /* ==============================
       AI PANEL
    ============================== */

    .ai-panel {
        margin-top: 25px;
        padding: 28px;
        border-radius: 27px;

        background:
            linear-gradient(
                135deg,
                #f1efff,
                #edfbff
            );

        border: 1px solid #ddd9ff;
    }

    .ai-title {
        font-size: 22px;
        font-weight: 950;
        color: #554ad9;
    }

    .ai-subtitle {
        margin-top: 5px;
        color: #687386;
        font-size: 14px;
    }

    /* ==============================
       WARNING
    ============================== */

    .warning-box {
        margin-top: 18px;
        padding: 18px 20px;
        border-radius: 17px;
        background: #fff9eb;
        border: 1px solid #f3dfac;
        color: #725c20;
        font-size: 13px;
        line-height: 1.7;
    }

    .success-box {
        margin-top: 18px;
        padding: 18px 20px;
        border-radius: 17px;
        background: #edf9f3;
        border: 1px solid #cbeedb;
        color: #176b4b;
        font-size: 13px;
        line-height: 1.7;
    }

    /* ==============================
       LEGEND
    ============================== */

    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
        margin-top: 14px;
    }

    .legend-item {
        background: #ffffff;
        border: 1px solid #e4e8ef;
        padding: 9px 13px;
        border-radius: 13px;
        font-size: 12px;
        font-weight: 750;
    }

    /* ==============================
       FOOTER
    ============================== */

    .footer {
        margin-top: 60px;
        text-align: center;
        color: #a0a8b6;
        font-size: 12px;
    }

    /* ==============================
       MOBILE
    ============================== */

    @media (max-width: 800px) {

        .hero {
            padding: 40px 25px;
        }

        .hero h1 {
            font-size: 42px;
        }

        .stats {
            grid-template-columns:
                repeat(2, 1fr);
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="topbar">

        <div class="brand">
            VerifyAI <span>Access</span>
        </div>

        <div class="status">
            <span class="status-dot"></span>
            Wheelchair Navigation
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
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
                خريطة ذكية مصممة أولاً للكراسي المتحركة.
                ابحث عن وجهتك واحصل على مسار يعطي
                الأولوية للطرق المناسبة، مع إظهار
                المصاعد والمنحدرات والعوائق المسجلة.
            </p>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SEARCH PANEL
# =========================================================

st.markdown(
    """
    <div class="search-panel">

        <div class="search-heading">
            🧭 خطط رحلتك
        </div>

        <div class="search-subheading">
            اختر نقطة البداية والوجهة، وسيتم تقييم
            المسار من منظور مستخدم الكرسي المتحرك.
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col1:

    start = st.text_input(
        "نقطة البداية",
        placeholder="مثلاً: جامعة الملك عبدالعزيز، جدة",
        key="start_text"
    )

with col2:

    destination = st.text_input(
        "الوجهة",
        placeholder="مثلاً: مستشفى الملك فهد",
        key="destination_text"
    )


st.caption(
    "♿ الوضع الحالي: أفضل مسار متاح للكراسي المتحركة"
)


search_button = st.button(
    "✨ ابحث عن مسار مهيأ",
    use_container_width=True
)


# =========================================================
# GEOCODING
# =========================================================

def geocode(place):

    try:

        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": place,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            },
            headers=HEADERS,
            timeout=20,
        )

        response.raise_for_status()

        results = response.json()

        if not results:
            return None

        result = results[0]

        return {
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "name": result.get(
                "display_name",
                place
            )
        }

    except Exception:
        return None


# =========================================================
# HAVERSINE
# =========================================================

def distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dp / 2) ** 2
        +
        math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return (
        2
        * earth
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )


# =========================================================
# ACCESSIBILITY DATA
# =========================================================

def get_accessibility_data(
    lat,
    lon,
    radius=1800
):

    query = f"""
    [out:json][timeout:35];

    (
        nwr(
            around:{radius},
            {lat},
            {lon}
        )["highway"="steps"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["highway"="elevator"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["ramp"="yes"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["wheelchair"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["amenity"="toilets"]["wheelchair"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["amenity"="parking"]["wheelchair"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["entrance"="main"]["wheelchair"];

        nwr(
            around:{radius},
            {lat},
            {lon}
        )["entrance"="yes"]["wheelchair"];
    );

    out center tags;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=45,
        )

        response.raise_for_status()

        return response.json().get(
            "elements",
            []
        )

    except Exception:
        return []


# =========================================================
# NORMAL WALKING ROUTE
# =========================================================

def get_route(
    start_lat,
    start_lon,
    end_lat,
    end_lon
):

    url = (
        "https://router.project-osrm.org/"
        "route/v1/foot/"
        f"{start_lon},{start_lat};"
        f"{end_lon},{end_lat}"
    )

    try:

        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
                "alternatives": "true",
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("code") != "Ok":
            return []

        return data.get(
            "routes",
            []
        )

    except Exception:
        return []


# =========================================================
# POINT EXTRACTION
# =========================================================

def get_element_position(element):

    lat = element.get("lat")
    lon = element.get("lon")

    if lat is not None and lon is not None:
        return lat, lon

    center = element.get(
        "center",
        {}
    )

    lat = center.get("lat")
    lon = center.get("lon")

    if lat is None or lon is None:
        return None

    return lat, lon


# =========================================================
# CLASSIFY ACCESSIBILITY
# =========================================================

def classify_accessibility(
    elements
):

    data = {
        "stairs": [],
        "elevators": [],
        "ramps": [],
        "wheelchair_yes": [],
        "wheelchair_limited": [],
        "wheelchair_no": [],
        "toilets": [],
        "parking": [],
        "entrances": [],
    }

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        position = get_element_position(
            element
        )

        if position is None:
            continue

        lat, lon = position

        item = {
            "lat": lat,
            "lon": lon,
            "tags": tags
        }

        highway = tags.get(
            "highway",
            ""
        )

        wheelchair = tags.get(
            "wheelchair",
            ""
        ).lower()

        amenity = tags.get(
            "amenity",
            ""
        )

        entrance = tags.get(
            "entrance",
            ""
        )

        ramp = tags.get(
            "ramp",
            ""
        ).lower()

        if highway == "steps":
            data["stairs"].append(item)

        if (
            highway == "elevator"
            or tags.get("elevator") == "yes"
        ):
            data["elevators"].append(item)

        if ramp == "yes":
            data["ramps"].append(item)

        if wheelchair == "yes":
            data["wheelchair_yes"].append(item)

        elif wheelchair == "limited":
            data["wheelchair_limited"].append(item)

        elif wheelchair == "no":
            data["wheelchair_no"].append(item)

        if (
            amenity == "toilets"
            and wheelchair in [
                "yes",
                "limited"
            ]
        ):
            data["toilets"].append(item)

        if (
            amenity == "parking"
            and wheelchair in [
                "yes",
                "designated",
                "limited"
            ]
        ):
            data["parking"].append(item)

        if (
            entrance
            and wheelchair in [
                "yes",
                "limited"
            ]
        ):
            data["entrances"].append(item)

    return data


# =========================================================
# ROUTE ACCESSIBILITY SCORE
# =========================================================

def score_route(
    route,
    accessibility
):

    coordinates = route[
        "geometry"
    ]["coordinates"]

    score = 100

    nearby_stairs = 0
    nearby_good_points = 0
    nearby_bad_points = 0

    # ---------------------------------------------
    # Check route against accessibility features
    # ---------------------------------------------

    route_points = []

    # Sample route so we don't calculate thousands
    # of points.

    step = max(
        1,
        len(coordinates) // 80
    )

    for point in coordinates[::step]:

        lon, lat = point

        route_points.append(
            (lat, lon)
        )

    # ---------------------------------------------
    # Stairs
    # ---------------------------------------------

    for item in accessibility["stairs"]:

        for lat, lon in route_points:

            d = distance_meters(
                lat,
                lon,
                item["lat"],
                item["lon"]
            )

            if d <= 45:

                nearby_stairs += 1
                break

    # ---------------------------------------------
    # Wheelchair-friendly points
    # ---------------------------------------------

    good_items = (
        accessibility["wheelchair_yes"]
        +
        accessibility["ramps"]
        +
        accessibility["elevators"]
        +
        accessibility["entrances"]
    )

    for item in good_items:

        for lat, lon in route_points:

            d = distance_meters(
                lat,
                lon,
                item["lat"],
                item["lon"]
            )

            if d <= 80:

                nearby_good_points += 1
                break

    # ---------------------------------------------
    # Wheelchair=no
    # ---------------------------------------------

    for item in accessibility[
        "wheelchair_no"
    ]:

        for lat, lon in route_points:

            d = distance_meters(
                lat,
                lon,
                item["lat"],
                item["lon"]
            )

            if d <= 60:

                nearby_bad_points += 1
                break

    # ---------------------------------------------
    # Score
    # ---------------------------------------------

    score -= nearby_stairs * 18
    score += nearby_good_points * 5
    score -= nearby_bad_points * 20

    score = max(
        0,
        min(100, score)
    )

    return {
        "score": score,
        "stairs": nearby_stairs,
        "good": nearby_good_points,
        "bad": nearby_bad_points
    }


# =========================================================
# SEARCH
# =========================================================

if search_button:

    if not start.strip():

        st.error(
            "اكتب نقطة البداية أولاً."
        )

    elif not destination.strip():

        st.error(
            "اكتب الوجهة أولاً."
        )

    else:

        st.session_state.ai_answer = None

        with st.spinner(
            "♿ جاري البحث عن أفضل مسار للكراسي المتحركة..."
        ):

            start_data = geocode(
                start
            )

            destination_data = geocode(
                destination
            )

            if not start_data:

                st.error(
                    "لم أستطع العثور على نقطة البداية. جرّب اسمًا أكثر تحديدًا."
                )

            elif not destination_data:

                st.error(
                    "لم أستطع العثور على الوجهة. جرّب اسمًا أكثر تحديدًا."
                )

            else:

                routes = get_route(
                    start_data["lat"],
                    start_data["lon"],
                    destination_data["lat"],
                    destination_data["lon"]
                )

                if not routes:

                    st.error(
                        "لم يتم العثور على مسار للمشي بين الموقعين."
                    )

                else:

                    accessibility = (
                        get_accessibility_data(
                            destination_data["lat"],
                            destination_data["lon"]
                        )
                    )

                    classified = classify_accessibility(
                        accessibility
                    )

                    # ---------------------------------
                    # Evaluate available alternatives
                    # ---------------------------------

                    evaluated = []

                    for route in routes:

                        evaluation = score_route(
                            route,
                            classified
                        )

                        evaluated.append(
                            (
                                evaluation["score"],
                                route,
                                evaluation
                            )
                        )

                    # Highest accessibility score
                    evaluated.sort(
                        key=lambda x: (
                            x[0],
                            -x[1]["distance"]
                        ),
                        reverse=True
                    )

                    best_score, best_route, best_evaluation = (
                        evaluated[0]
                    )

                    st.session_state.route_result = {
                        "start": start_data,
                        "destination": destination_data,
                        "route": best_route,
                        "evaluation": best_evaluation,
                        "accessibility": classified,
                        "routes_checked": len(routes),
                    }


# =========================================================
# DISPLAY RESULT
# =========================================================

if st.session_state.route_result:

    result = st.session_state.route_result

    start_data = result["start"]
    destination_data = result["destination"]

    route = result["route"]
    evaluation = result["evaluation"]
    accessibility = result["accessibility"]

    distance_km = (
        route["distance"] / 1000
    )

    minutes = (
        route["duration"] / 60
    )

    score = evaluation["score"]

    # =====================================================
    # MAP
    # =====================================================

    st.markdown(
        """
        <div class="section-title">
            🗺️ مسارك المهيأ
        </div>

        <div class="section-subtitle">
            تم تقييم المسارات المتاحة مع إعطاء الأولوية
            لمؤشرات الإتاحة الخاصة بالكراسي المتحركة.
        </div>
        """,
        unsafe_allow_html=True
    )

    center_lat = (
        start_data["lat"]
        +
        destination_data["lat"]
    ) / 2

    center_lon = (
        start_data["lon"]
        +
        destination_data["lon"]
    ) / 2

    map_object = folium.Map(
        location=[
            center_lat,
            center_lon
        ],
        zoom_start=14,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    folium.Marker(
        [
            start_data["lat"],
            start_data["lon"]
        ],
        tooltip="📍 البداية",
        popup=folium.Popup(
            start_data["name"],
            max_width=350
        ),
        icon=folium.Icon(
            color="blue",
            icon="play"
        )
    ).add_to(map_object)

    # -----------------------------------------------------
    # DESTINATION
    # -----------------------------------------------------

    folium.Marker(
        [
            destination_data["lat"],
            destination_data["lon"]
        ],
        tooltip="🎯 الوجهة",
        popup=folium.Popup(
            destination_data["name"],
            max_width=350
        ),
        icon=folium.Icon(
            color="red",
            icon="flag"
        )
    ).add_to(map_object)

    # -----------------------------------------------------
    # ROUTE
    # -----------------------------------------------------

    route_points = []

    for lon, lat in route[
        "geometry"
    ]["coordinates"]:

        route_points.append(
            [lat, lon]
        )

    folium.PolyLine(
        route_points,
        color="#675CF5",
        weight=9,
        opacity=0.88,
        tooltip=(
            "♿ المسار المفضل للكراسي المتحركة"
        )
    ).add_to(map_object)

    # =====================================================
    # ACCESSIBILITY MARKERS
    # =====================================================

    # -----------------------------------------------------
    # ELEVATORS
    # -----------------------------------------------------

    for item in accessibility[
        "elevators"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🛗 مصعد",
            popup=(
                "🛗 مصعد مسجل في بيانات الخريطة"
            ),
            icon=folium.Icon(
                color="green",
                icon="arrow-up"
            )
        ).add_to(map_object)

    # -----------------------------------------------------
    # RAMPS
    # -----------------------------------------------------

    for item in accessibility[
        "ramps"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🛝 منحدر",
            popup=(
                "🛝 منحدر مسجل في بيانات الخريطة"
            ),
            icon=folium.Icon(
                color="green",
                icon="road"
            )
        ).add_to(map_object)

    # -----------------------------------------------------
    # WHEELCHAIR YES
    # -----------------------------------------------------

    for item in accessibility[
        "wheelchair_yes"
    ]:

        folium.CircleMarker(
            [
                item["lat"],
                item["lon"]
            ],
            radius=7,
            tooltip="♿ وصول مهيأ",
            popup=(
                "♿ موقع مسجل كـ wheelchair=yes"
            ),
            color="#20B878",
            fill=True,
            fill_opacity=0.9
        ).add_to(map_object)

    # -----------------------------------------------------
    # STAIRS
    # -----------------------------------------------------

    for item in accessibility[
        "stairs"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🚫 درج",
            popup=(
                "🚫 درج مسجل في بيانات الخريطة"
            ),
            icon=folium.Icon(
                color="red",
                icon="warning-sign"
            )
        ).add_to(map_object)

    # -----------------------------------------------------
    # WHEELCHAIR NO
    # -----------------------------------------------------

    for item in accessibility[
        "wheelchair_no"
    ]:

        folium.CircleMarker(
            [
                item["lat"],
                item["lon"]
            ],
            radius=7,
            tooltip="⚠️ غير مهيأ",
            popup=(
                "⚠️ الموقع مسجل كـ wheelchair=no"
            ),
            color="#E26D5A",
            fill=True,
            fill_opacity=0.85
        ).add_to(map_object)

    # -----------------------------------------------------
    # ACCESSIBLE TOILETS
    # -----------------------------------------------------

    for item in accessibility[
        "toilets"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🚻 دورة مياه مهيأة",
            popup=(
                "🚻 دورة مياه مهيأة مسجلة"
            ),
            icon=folium.Icon(
                color="purple",
                icon="user"
            )
        ).add_to(map_object)

    # -----------------------------------------------------
    # ACCESSIBLE PARKING
    # -----------------------------------------------------

    for item in accessibility[
        "parking"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🅿️ موقف مهيأ",
            popup=(
                "🅿️ موقف مهيأ مسجل"
            ),
            icon=folium.Icon(
                color="blue",
                icon="road"
            )
        ).add_to(map_object)

    # -----------------------------------------------------
    # ACCESSIBLE ENTRANCES
    # -----------------------------------------------------

    for item in accessibility[
        "entrances"
    ]:

        folium.Marker(
            [
                item["lat"],
                item["lon"]
            ],
            tooltip="🚪 مدخل مهيأ",
            popup=(
                "🚪 مدخل مسجل كمدخل مهيأ"
            ),
            icon=folium.Icon(
                color="green",
                icon="log-in"
            )
        ).add_to(map_object)

    st_folium(
        map_object,
        width=None,
        height=650,
        returned_objects=[]
    )

    # =====================================================
    # LEGEND
    # =====================================================

    st.markdown(
        """
        <div class="legend">

            <div class="legend-item">
                🟣 المسار المفضل
            </div>

            <div class="legend-item">
                🛗 مصعد
            </div>

            <div class="legend-item">
                🛝 منحدر
            </div>

            <div class="legend-item">
                ♿ وصول مهيأ
            </div>

            <div class="legend-item">
                🚫 درج
            </div>

            <div class="legend-item">
                ⚠️ غير مهيأ
            </div>

            <div class="legend-item">
                🚻 دورة مياه
            </div>

            <div class="legend-item">
                🅿️ موقف مهيأ
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # STATS
    # =====================================================

    elevator_count = len(
        accessibility["elevators"]
    )

    ramp_count = len(
        accessibility["ramps"]
    )

    wheelchair_count = len(
        accessibility["wheelchair_yes"]
    )

    stairs_count = len(
        accessibility["stairs"]
    )

    st.markdown(
        f"""
        <div class="stats">

            <div class="stat">

                <div class="stat-icon">
                    ♿
                </div>

                <div class="stat-number">
                    {score:.0f}%
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
                    {round(minutes)} دقيقة
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
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # ROUTE STATUS
    # =====================================================

    if stairs_count == 0 and score >= 80:

        st.markdown(
            """
            <div class="success-box">
                <strong>♿ المسار يبدو مناسبًا بدرجة جيدة.</strong><br>
                لم يتم العثور على درجات قريبة من المسار
                ضمن بيانات الخريطة المتاحة، مع وجود
                مؤشرات وصول مهيأة.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif stairs_count > 0:

        st.markdown(
            f"""
            <div class="warning-box">
                <strong>⚠️ انتبه قبل استخدام المسار.</strong><br>
                توجد {stairs_count} نقطة درج قريبة من
                المسار وفق بيانات OpenStreetMap.
                يجب التحقق ميدانيًا من إمكانية تجاوزها.
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="warning-box">
                <strong>ℹ️ البيانات غير مكتملة.</strong><br>
                لم نجد معلومات كافية للتأكد من أن
                جميع أجزاء الرحلة مهيأة للكراسي المتحركة.
                المسار المقترح ليس ضمانًا ميدانيًا.
            </div>
            """,
            unsafe_allow_html=True
        )

    # =====================================================
    # AI
    # =====================================================

    st.markdown(
        """
        <div class="ai-panel">

            <div class="ai-title">
                ✨ VerifyAI Route Intelligence
            </div>

            <div class="ai-subtitle">
                تحليل ذكي للمسار بناءً على بيانات الإتاحة
                الموجودة، بدون اختراع معلومات غير مؤكدة.
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    ai_button = st.button(
        "🤖 حلّل المسار باستخدام VerifyAI",
        use_container_width=True
    )

    if ai_button:

        api_key = os.getenv(
            "OPENAI_API_KEY"
        )

        if not api_key:

            try:
                api_key = st.secrets[
                    "OPENAI_API_KEY"
                ]
            except Exception:
                api_key = None

        if not api_key:

            st.warning(
                "أضف OPENAI_API_KEY لتفعيل التحليل الذكي."
            )

        else:

            try:

                from openai import OpenAI

                ai_client = OpenAI(
                    api_key=api_key
                )

                prompt = f"""
أنت VerifyAI Access، نظام ذكاء اصطناعي
متخصص في مسارات الوصول للكراسي المتحركة.

حلل الرحلة التالية:

البداية:
{start_data["name"]}

الوجهة:
{destination_data["name"]}

المسافة:
{distance_km:.2f} كم

الوقت:
{minutes:.0f} دقيقة

مؤشر الإتاحة:
{score:.0f}/100

عدد المسارات التي تمت مقارنتها:
{result["routes_checked"]}

درج قريب من المسار:
{stairs_count}

مصاعد مسجلة:
{elevator_count}

منحدرات مسجلة:
{ramp_count}

نقاط wheelchair=yes:
{wheelchair_count}

نقاط wheelchair=no:
{len(accessibility["wheelchair_no"])}

اكتب باللغة العربية.

أعطني:

1. تقييمًا مختصرًا للمسار.
2. لماذا تم اختيار هذا المسار.
3. أهم الأشياء التي يجب الانتباه لها.
4. أماكن الإتاحة التي تم العثور عليها.
5. ما الذي لا يمكن للنظام التأكد منه.

قواعد مهمة:
- لا تقل إن الطريق مهيأ 100%.
- لا تخترع وجود مصعد أو منحدر.
- لا تعتبر عدم وجود بيانات دليلًا على عدم وجود المرفق.
- وضح أن بيانات الخريطة قد تكون غير مكتملة.
- اجعل الإجابة واضحة وقصيرة.
"""

                response = ai_client.responses.create(
                    model=MODEL,
                    input=prompt
                )

                st.session_state.ai_answer = (
                    response.output_text
                )

            except Exception as error:

                st.error(
                    "تعذر تشغيل تحليل AI."
                )

                st.caption(
                    str(error)
                )

    if st.session_state.ai_answer:

        st.markdown(
            """
            <div class="ai-panel">
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            st.session_state.ai_answer
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        VerifyAI Access · Wheelchair-first AI navigation
    </div>
    """,
    unsafe_allow_html=True
)
