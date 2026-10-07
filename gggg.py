import os
import math
import html
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/2.0 accessibility-navigation"
}


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: "Cairo", sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 8% 5%,
            rgba(118, 87, 255, 0.10),
            transparent 25%
        ),
        radial-gradient(
            circle at 92% 10%,
            rgba(0, 196, 180, 0.10),
            transparent 25%
        ),
        #f7f8fc;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}


/* TOP */

.topbar {
    background: rgba(255,255,255,.94);
    border: 1px solid #e8e7ef;
    border-radius: 22px;
    padding: 17px 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    box-shadow: 0 12px 35px rgba(35,25,80,.06);
}

.brand {
    font-size: 25px;
    font-weight: 900;
}

.brand-access {
    color: #7657ff;
}

.status {
    background: #f0eeff;
    color: #624bd5;
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}

.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #36c98a;
    border-radius: 50%;
    margin-left: 6px;
}


/* HERO */

.hero {
    background:
        radial-gradient(
            circle at 85% 15%,
            rgba(118,87,255,.14),
            transparent 32%
        ),
        radial-gradient(
            circle at 15% 100%,
            rgba(0,196,180,.11),
            transparent 30%
        ),
        white;

    border: 1px solid #e9e8f0;
    border-radius: 30px;
    padding: 45px;
    margin-bottom: 24px;
    box-shadow: 0 20px 60px rgba(40,30,90,.07);
}

.hero-tag {
    display: inline-block;
    background: #f0edff;
    color: #674ee0;
    padding: 7px 13px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 900;
    margin-bottom: 16px;
}

.hero h1 {
    font-size: clamp(38px, 5vw, 67px);
    line-height: 1.08;
    letter-spacing: -2px;
    margin: 0 0 17px 0;
    font-weight: 900;
}

.hero h1 span {
    color: #7657ff;
}

.hero p {
    max-width: 800px;
    color: #696a7c;
    font-size: 16px;
    line-height: 2;
}


/* SEARCH */

.search-card {
    background: white;
    border: 1px solid #e7e6ee;
    border-radius: 25px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 12px 40px rgba(35,25,80,.05);
}

.section-title {
    font-size: 20px;
    font-weight: 900;
}

.section-description {
    color: #7b7c8c;
    font-size: 13px;
    margin-top: 3px;
    margin-bottom: 18px;
}


/* MAP */

.map-container {
    background: white;
    border-radius: 27px;
    border: 1px solid #e7e6ee;
    padding: 10px;
    box-shadow: 0 16px 50px rgba(35,25,80,.06);
}

.map-heading {
    padding: 12px 15px;
}

.map-heading-title {
    font-size: 20px;
    font-weight: 900;
}

.map-heading-text {
    color: #77788a;
    font-size: 12px;
}


/* STATS */

.stat-card {
    background: white;
    border: 1px solid #e8e7ef;
    border-radius: 20px;
    padding: 19px;
    text-align: center;
    box-shadow: 0 10px 32px rgba(35,25,80,.045);
}

.stat-icon {
    font-size: 25px;
}

.stat-value {
    color: #7657ff;
    font-size: 24px;
    font-weight: 900;
}

.stat-label {
    color: #77788a;
    font-size: 11px;
    font-weight: 700;
}


/* CARDS */

.info-card {
    background: white;
    border: 1px solid #e7e6ee;
    border-radius: 24px;
    padding: 23px;
    box-shadow: 0 12px 38px rgba(35,25,80,.05);
}

.info-title {
    font-size: 19px;
    font-weight: 900;
}

.info-subtitle {
    color: #7a7b8b;
    font-size: 12px;
    margin-bottom: 16px;
}


/* ACCESS ITEMS */

.access-item {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 11px 13px;
    border-radius: 14px;
    background: #f8f8fc;
    margin-bottom: 8px;
}

.access-icon {
    font-size: 20px;
    width: 30px;
    text-align: center;
}

.access-name {
    font-weight: 800;
    font-size: 13px;
}

.access-description {
    color: #77788a;
    font-size: 11px;
}


/* ROUTE */

.route-good {
    background: #effbf6;
    border: 1px solid #d3f2e3;
    color: #187852;
    padding: 17px;
    border-radius: 16px;
}

.route-warning {
    background: #fff8ea;
    border: 1px solid #f7dfac;
    color: #986b18;
    padding: 17px;
    border-radius: 16px;
}

.route-title {
    font-size: 16px;
    font-weight: 900;
    margin-bottom: 6px;
}

.route-description {
    font-size: 12px;
    line-height: 1.9;
}


/* INDOOR */

.indoor-box {
    background:
        linear-gradient(
            135deg,
            #f5f2ff,
            #f1fffc
        );
    border: 1px solid #e5e0ff;
    border-radius: 18px;
    padding: 18px;
}

.indoor-title {
    font-weight: 900;
    font-size: 17px;
}

.indoor-text {
    color: #666779;
    font-size: 12px;
    line-height: 1.9;
}


/* BUTTON */

.stButton > button {
    border-radius: 14px !important;
    border: 0 !important;
    min-height: 45px !important;
    background: #7657ff !important;
    color: white !important;
    font-weight: 800 !important;
    box-shadow: 0 8px 22px rgba(118,87,255,.22);
}

.stButton > button:hover {
    background: #6549e8 !important;
}


/* INPUT */

.stTextInput input {
    border-radius: 14px !important;
    min-height: 45px !important;
    border: 1px solid #e2e1ea !important;
}


/* FOOTER */

.footer {
    text-align: center;
    color: #999aa8;
    font-size: 11px;
    padding: 30px 0 5px;
}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# SESSION
# =========================================================

if "route_result" not in st.session_state:
    st.session_state.route_result = None

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = None


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def geocode(place):

    try:

        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": place,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            },
            headers=HEADERS,
            timeout=15
        )

        data = response.json()

        if not data:
            return None

        item = data[0]

        return {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "name": item.get("display_name", place)
        }

    except Exception:
        return None


def distance_meters(lat1, lon1, lat2, lon2):

    earth = 6371000

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

    return earth * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


# =========================================================
# OUTDOOR ACCESSIBILITY DATA
# =========================================================

def get_accessibility_data(lat, lon, radius=1800):

    query = f"""
    [out:json][timeout:30];

    (
        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        way["highway"="elevator"](around:{radius},{lat},{lon});

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
            timeout=40
        )

        return response.json().get("elements", [])

    except Exception:
        return []


# =========================================================
# INDOOR DATA
# =========================================================

def get_indoor_data(lat, lon, radius=250):

    """
    يبحث عن عناصر Indoor Mapping حول الوجهة.

    ندعم:
    - building
    - entrance
    - indoor
    - room
    - corridor
    - elevator
    - stairs
    - level
    - wheelchair
    """

    query = f"""
    [out:json][timeout:35];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});

        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});
        relation["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["highway"="steps"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        node["amenity"="parking"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=45
        )

        return response.json().get("elements", [])

    except Exception:
        return []


def parse_indoor_data(elements, destination_lat, destination_lon):

    result = {
        "buildings": [],
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "ramps": [],
        "rooms": [],
        "corridors": [],
        "toilets": [],
        "parking": [],
        "levels": set(),
        "wheelchair_yes": [],
        "wheelchair_no": [],
        "all": []
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

        result["all"].append(point)

        # Levels
        level = tags.get("level")

        if level:
            for value in str(level).split(";"):
                result["levels"].add(value.strip())

        # Buildings
        if "building" in tags:
            result["buildings"].append(point)

        # Entrances
        if "entrance" in tags:
            result["entrances"].append(point)

        # Elevators
        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
            or tags.get("indoor") == "elevator"
        ):
            result["elevators"].append(point)

        # Stairs
        if (
            tags.get("highway") == "steps"
            or tags.get("indoor") == "stairs"
        ):
            result["stairs"].append(point)

        # Ramps
        if tags.get("ramp") == "yes":
            result["ramps"].append(point)

        # Rooms
        if (
            "room" in tags
            or tags.get("indoor") == "room"
        ):
            result["rooms"].append(point)

        # Corridors
        if (
            tags.get("indoor") == "corridor"
            or tags.get("highway") == "corridor"
        ):
            result["corridors"].append(point)

        # Toilets
        if tags.get("amenity") == "toilets":
            result["toilets"].append(point)

        # Parking
        if tags.get("amenity") == "parking":
            result["parking"].append(point)

        wheelchair = tags.get("wheelchair")

        if wheelchair == "yes":
            result["wheelchair_yes"].append(point)

        elif wheelchair == "no":
            result["wheelchair_no"].append(point)

    result["levels"] = sorted(
        list(result["levels"]),
        key=lambda x: float(x) if x.replace(".", "", 1).isdigit() else 999
    )

    return result


# =========================================================
# ROUTING
# =========================================================

def get_routes(start, destination):

    url = (
        f"{OSRM_URL}/"
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
            timeout=30
        )

        return response.json().get("routes", [])

    except Exception:
        return []


def score_route(route, accessibility):

    score = 100

    coordinates = route["geometry"]["coordinates"]

    sample_step = max(
        1,
        len(coordinates) // 80
    )

    sampled = coordinates[::sample_step]

    for lon, lat in sampled:

        for stair in accessibility["stairs"]:

            if distance_meters(
                lat,
                lon,
                stair["lat"],
                stair["lon"]
            ) < 80:

                score -= 15

        for bad in accessibility["wheelchair_no"]:

            if distance_meters(
                lat,
                lon,
                bad["lat"],
                bad["lon"]
            ) < 80:

                score -= 20

        for good in (
            accessibility["wheelchair_yes"]
            + accessibility["ramps"]
            + accessibility["elevators"]
        ):

            if distance_meters(
                lat,
                lon,
                good["lat"],
                good["lon"]
            ) < 100:

                score += 2

    return max(0, min(100, round(score)))


# =========================================================
# TOP BAR
# =========================================================

st.markdown(
    """
<div class="topbar">

    <div class="brand">
        VerifyAI <span class="brand-access">Access</span>
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

    <div class="hero-tag">
        ♿ AI-POWERED ACCESSIBILITY
    </div>

    <h1>
        تحرك بحرية.<br>
        <span>الوصول للجميع.</span>
    </h1>

    <p>
        خريطة ذكية تساعد مستخدمي الكراسي المتحركة
        على العثور على مسارات أكثر ملاءمة، مع إظهار
        المصاعد والمنحدرات والمداخل والعوائق.
        وعندما تتوفر بيانات داخلية للمبنى، يعرض النظام
        الطوابق والأماكن الداخلية المسجلة أيضًا.
    </p>

</div>
""",
    unsafe_allow_html=True
)


# =========================================================
# SEARCH
# =========================================================

st.markdown(
    """
<div class="search-card">

    <div class="section-title">
        🧭 ابحث عن طريقك
    </div>

    <div class="section-description">
        اكتب نقطة البداية والوجهة. ويمكنك كتابة اسم مبنى أو جامعة أو مستشفى.
    </div>

</div>
""",
    unsafe_allow_html=True
)

c1, c2 = st.columns(2)

with c1:

    start_text = st.text_input(
        "نقطة البداية",
        placeholder="مثال: جامعة الملك عبدالعزيز"
    )

with c2:

    destination_text = st.text_input(
        "الوجهة",
        placeholder="مثال: مستشفى الملك فهد"
    )

search_button = st.button(
    "🔎 البحث عن أفضل مسار",
    use_container_width=True
)


# =========================================================
# SEARCH ACTION
# =========================================================

if search_button:

    if not start_text.strip() or not destination_text.strip():

        st.warning(
            "أدخل نقطة البداية والوجهة أولًا."
        )

    else:

        with st.spinner("جاري تحليل المكان والمسارات..."):

            start = geocode(start_text)
            destination = geocode(destination_text)

            if not start or not destination:

                st.error(
                    "لم أتمكن من تحديد أحد المكانين. "
                    "جرّب اسمًا أكثر تحديدًا."
                )

            else:

                routes = get_routes(
                    start,
                    destination
                )

                outdoor_raw = get_accessibility_data(
                    destination["lat"],
                    destination["lon"]
                )

                outdoor = {
                    "stairs": [],
                    "elevators": [],
                    "ramps": [],
                    "wheelchair_yes": [],
                    "wheelchair_no": [],
                    "toilets": [],
                    "parking": [],
                    "entrances": []
                }

                for item in outdoor_raw:

                    tags = item.get("tags", {})

                    if "lat" in item:
                        lat = item["lat"]
                        lon = item["lon"]

                    elif "center" in item:
                        lat = item["center"]["lat"]
                        lon = item["center"]["lon"]

                    else:
                        continue

                    point = {
                        "lat": lat,
                        "lon": lon,
                        "tags": tags
                    }

                    if tags.get("highway") == "steps":
                        outdoor["stairs"].append(point)

                    if (
                        tags.get("highway") == "elevator"
                        or tags.get("elevator") == "yes"
                    ):
                        outdoor["elevators"].append(point)

                    if tags.get("ramp") == "yes":
                        outdoor["ramps"].append(point)

                    wheelchair = tags.get("wheelchair")

                    if wheelchair == "yes":
                        outdoor["wheelchair_yes"].append(point)

                    elif wheelchair == "no":
                        outdoor["wheelchair_no"].append(point)

                    if (
                        tags.get("amenity") == "toilets"
                        and tags.get("wheelchair") == "yes"
                    ):
                        outdoor["toilets"].append(point)

                    if (
                        tags.get("amenity") == "parking"
                        and tags.get("wheelchair") == "yes"
                    ):
                        outdoor["parking"].append(point)

                    if (
                        tags.get("entrance")
                        and tags.get("wheelchair") == "yes"
                    ):
                        outdoor["entrances"].append(point)

                indoor_raw = get_indoor_data(
                    destination["lat"],
                    destination["lon"]
                )

                indoor = parse_indoor_data(
                    indoor_raw,
                    destination["lat"],
                    destination["lon"]
                )

                if routes:

                    scored = []

                    for route in routes:

                        score = score_route(
                            route,
                            outdoor
                        )

                        scored.append(
                            (score, route)
                        )

                    scored.sort(
                        key=lambda x: x[0],
                        reverse=True
                    )

                    best_score, best_route = scored[0]

                else:

                    best_score = 0
                    best_route = None

                st.session_state.route_result = {
                    "start": start,
                    "destination": destination,
                    "route": best_route,
                    "score": best_score,
                    "outdoor": outdoor,
                    "indoor": indoor
                }

                st.session_state.ai_answer = None


# =========================================================
# RESULT
# =========================================================

result = st.session_state.route_result

if result:

    start = result["start"]
    destination = result["destination"]
    route = result["route"]
    score = result["score"]
    outdoor = result["outdoor"]
    indoor = result["indoor"]

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    if route:

        distance_km = route["distance"] / 1000
        minutes = max(
            1,
            round(route["duration"] / 60)
        )

    else:

        distance_km = 0
        minutes = 0

    cols = st.columns(4)

    stats = [
        ("♿", f"{score}%", "مؤشر الإتاحة"),
        ("🛣️", f"{distance_km:.1f} كم", "المسافة"),
        ("⏱️", f"{minutes} دقيقة", "الوقت التقريبي"),
        ("🏢", str(len(indoor["buildings"])), "مبانٍ مكتشفة")
    ]

    for col, data in zip(cols, stats):

        with col:

            st.markdown(
                f"""
<div class="stat-card">

    <div class="stat-icon">
        {data[0]}
    </div>

    <div class="stat-value">
        {data[1]}
    </div>

    <div class="stat-label">
        {data[2]}
    </div>

</div>
""",
                unsafe_allow_html=True
            )


    st.write("")


    # -----------------------------------------------------
    # MAP
    # -----------------------------------------------------

    map_center = [
        (
            start["lat"]
            + destination["lat"]
        ) / 2,

        (
            start["lon"]
            + destination["lon"]
        ) / 2
    ]

    m = folium.Map(
        location=map_center,
        zoom_start=16,
        tiles="OpenStreetMap"
    )

    # START
    folium.Marker(
        [start["lat"], start["lon"]],
        tooltip="نقطة البداية",
        popup=folium.Popup(
            "<b>نقطة البداية</b><br>"
            + html.escape(start["name"]),
            max_width=300
        ),
        icon=folium.Icon(
            color="green",
            icon="play",
            prefix="fa"
        )
    ).add_to(m)

    # DESTINATION
    folium.Marker(
        [destination["lat"], destination["lon"]],
        tooltip="الوجهة",
        popup=folium.Popup(
            "<b>الوجهة</b><br>"
            + html.escape(destination["name"]),
            max_width=300
        ),
        icon=folium.Icon(
            color="red",
            icon="flag",
            prefix="fa"
        )
    ).add_to(m)


    # ROUTE
    if route:

        points = [
            [p[1], p[0]]
            for p in route["geometry"]["coordinates"]
        ]

        folium.PolyLine(
            points,
            color="#7657ff",
            weight=7,
            opacity=.88,
            tooltip="المسار المقترح"
        ).add_to(m)


    # -----------------------------------------------------
    # OUTDOOR MARKERS
    # -----------------------------------------------------

    for p in outdoor["elevators"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛗 مصعد",
            popup=folium.Popup(
                "<b>🛗 مصعد</b><br>"
                "مصعد مسجل في بيانات الخريطة.",
                max_width=280
            ),
            icon=folium.Icon(
                color="blue",
                icon="arrow-up",
                prefix="fa"
            )
        ).add_to(m)


    for p in outdoor["ramps"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛝 منحدر",
            popup=folium.Popup(
                "<b>🛝 منحدر</b><br>"
                "منحدر مسجل في بيانات الخريطة.",
                max_width=280
            ),
            icon=folium.Icon(
                color="green",
                icon="road",
                prefix="fa"
            )
        ).add_to(m)


    for p in outdoor["stairs"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🚫 درج",
            popup=folium.Popup(
                "<b>🚫 درج</b><br>"
                "يوجد درج مسجل في هذه المنطقة.",
                max_width=280
            ),
            icon=folium.Icon(
                color="red",
                icon="warning-sign",
                prefix="glyphicon"
            )
        ).add_to(m)


    for p in outdoor["wheelchair_yes"]:

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=7,
            color="#00a884",
            fill=True,
            fill_opacity=.9,
            tooltip="♿ وصول مهيأ",
            popup=folium.Popup(
                "<b>♿ وصول مهيأ</b><br>"
                "المكان مسجل كمتاح للكراسي المتحركة.",
                max_width=280
            )
        ).add_to(m)


    for p in outdoor["wheelchair_no"]:

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=8,
            color="#e5484d",
            fill=True,
            fill_opacity=.9,
            tooltip="⚠️ غير مهيأ",
            popup=folium.Popup(
                "<b>⚠️ غير مهيأ</b><br>"
                "المكان مسجل كغير مناسب للكراسي المتحركة.",
                max_width=280
            )
        ).add_to(m)


    for p in outdoor["toilets"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🚻 دورة مياه مهيأة",
            popup=folium.Popup(
                "<b>🚻 دورة مياه مهيأة</b><br>"
                "دورة مياه مسجلة كمتاحة للكراسي المتحركة.",
                max_width=300
            ),
            icon=folium.Icon(
                color="purple",
                icon="home",
                prefix="glyphicon"
            )
        ).add_to(m)


    for p in outdoor["parking"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🅿️ موقف مهيأ",
            popup=folium.Popup(
                "<b>🅿️ موقف مهيأ</b><br>"
                "موقف مسجل كمتاح للكراسي المتحركة.",
                max_width=300
            ),
            icon=folium.Icon(
                color="orange",
                icon="parking",
                prefix="fa"
            )
        ).add_to(m)


    # -----------------------------------------------------
    # INDOOR MARKERS
    # -----------------------------------------------------

    # Entrances
    for p in indoor["entrances"]:

        tags = p["tags"]

        wheelchair = tags.get("wheelchair")

        if wheelchair == "yes":
            title = "🚪 مدخل مهيأ"
            description = "مدخل مسجل كمتاح للكراسي المتحركة."
            color = "green"

        else:
            title = "🚪 مدخل"
            description = "مدخل مسجل للمبنى."
            color = "cadetblue"

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip=title,
            popup=folium.Popup(
                f"<b>{title}</b><br>{description}",
                max_width=300
            ),
            icon=folium.Icon(
                color=color,
                icon="sign-in",
                prefix="fa"
            )
        ).add_to(m)


    # Indoor elevators
    for p in indoor["elevators"]:

        level = p["tags"].get("level", "غير محدد")

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛗 مصعد داخلي",
            popup=folium.Popup(
                "<b>🛗 مصعد داخلي</b><br>"
                f"الطابق المسجل: {html.escape(str(level))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="blue",
                icon="arrow-up",
                prefix="fa"
            )
        ).add_to(m)


    # Indoor stairs
    for p in indoor["stairs"]:

        level = p["tags"].get("level", "غير محدد")

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🪜 درج داخلي",
            popup=folium.Popup(
                "<b>🪜 درج داخلي</b><br>"
                f"الطابق المسجل: {html.escape(str(level))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="red",
                icon="warning-sign",
                prefix="glyphicon"
            )
        ).add_to(m)


    # Rooms
    for p in indoor["rooms"]:

        tags = p["tags"]

        name = (
            tags.get("name")
            or tags.get("ref")
            or "مكان داخلي"
        )

        level = tags.get(
            "level",
            "غير محدد"
        )

        wheelchair = tags.get(
            "wheelchair",
            "غير محدد"
        )

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=6,
            color="#7657ff",
            fill=True,
            fill_opacity=.85,
            tooltip=f"📍 {name}",
            popup=folium.Popup(
                "<b>📍 مكان داخلي</b><br>"
                f"<b>الاسم:</b> {html.escape(str(name))}<br>"
                f"<b>الطابق:</b> {html.escape(str(level))}<br>"
                f"<b>الوصول:</b> {html.escape(str(wheelchair))}",
                max_width=320
            )
        ).add_to(m)


    # Indoor toilets
    for p in indoor["toilets"]:

        level = p["tags"].get(
            "level",
            "غير محدد"
        )

        wheelchair = p["tags"].get(
            "wheelchair",
            "غير محدد"
        )

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🚻 دورة مياه داخلية",
            popup=folium.Popup(
                "<b>🚻 دورة مياه</b><br>"
                f"<b>الطابق:</b> {html.escape(str(level))}<br>"
                f"<b>الوصول:</b> {html.escape(str(wheelchair))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="purple",
                icon="home",
                prefix="glyphicon"
            )
        ).add_to(m)


    # -----------------------------------------------------
    # MAP DISPLAY
    # -----------------------------------------------------

    st.markdown(
        """
<div class="map-container">

    <div class="map-heading">

        <div class="map-heading-title">
            🗺️ خريطة الوصول الذكية
        </div>

        <div class="map-heading-text">
            اضغط على أي علامة لمعرفة معناها والمعلومات المسجلة عنها.
        </div>

    </div>

</div>
""",
        unsafe_allow_html=True
    )

    st_folium(
        m,
        width=None,
        height=650,
        returned_objects=[]
    )


    # =====================================================
    # INDOOR SECTION
    # =====================================================

    st.write("")

    st.markdown(
        """
<div class="info-card">

    <div class="info-title">
        🏢 الوصول داخل المبنى
    </div>

    <div class="info-subtitle">
        معلومات داخلية من بيانات الخرائط المتوفرة للمكان.
    </div>

</div>
""",
        unsafe_allow_html=True
    )


    indoor_available = (
        len(indoor["buildings"]) > 0
        or len(indoor["rooms"]) > 0
        or len(indoor["elevators"]) > 0
        or len(indoor["corridors"]) > 0
        or len(indoor["levels"]) > 0
    )


    if indoor_available:

        st.markdown(
            """
<div class="indoor-box">

    <div class="indoor-title">
        🟢 توجد بيانات داخلية لهذا المكان
    </div>

    <div class="indoor-text">
        تم العثور على عناصر داخلية مسجلة في الخريطة.
        يمكنك رؤية المداخل والمصاعد والغرف والطوابق
        المتوفرة على الخريطة.
    </div>

</div>
""",
            unsafe_allow_html=True
        )

        st.write("")


        indoor_cols = st.columns(4)

        indoor_stats = [
            (
                "🚪",
                len(indoor["entrances"]),
                "مداخل"
            ),
            (
                "🛗",
                len(indoor["elevators"]),
                "مصاعد"
            ),
            (
                "📍",
                len(indoor["rooms"]),
                "أماكن داخلية"
            ),
            (
                "🪜",
                len(indoor["stairs"]),
                "سلالم"
            )
        ]

        for col, stat in zip(
            indoor_cols,
            indoor_stats
        ):

            with col:

                st.markdown(
                    f"""
<div class="stat-card">

    <div class="stat-icon">
        {stat[0]}
    </div>

    <div class="stat-value">
        {stat[1]}
    </div>

    <div class="stat-label">
        {stat[2]}
    </div>

</div>
""",
                    unsafe_allow_html=True
                )


        # Floors
        if indoor["levels"]:

            st.write("")

            st.markdown(
                "### 🏷️ الطوابق المسجلة"
            )

            st.write(
                " • ".join(
                    [f"الطابق {x}" for x in indoor["levels"]]
                )
            )

        # Indoor details
        st.write("")

        detail_cols = st.columns(2)

        with detail_cols[0]:

            st.markdown(
                """
<div class="info-card">

    <div class="info-title">
        🚪 نقاط الدخول
    </div>

                """,
                unsafe_allow_html=True
            )

            if indoor["entrances"]:

                for p in indoor["entrances"][:10]:

                    tags = p["tags"]

                    entrance_type = tags.get(
                        "entrance",
                        "مدخل"
                    )

                    wheelchair = tags.get(
                        "wheelchair",
                        "غير محدد"
                    )

                    level = tags.get(
                        "level",
                        "غير محدد"
                    )

                    st.write(
                        f"🚪 {entrance_type} — "
                        f"الوصول: {wheelchair} — "
                        f"الطابق: {level}"
                    )

            else:

                st.caption(
                    "لا توجد مداخل داخلية مفصلة مسجلة."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


        with detail_cols[1]:

            st.markdown(
                """
<div class="info-card">

    <div class="info-title">
        📍 الأماكن الداخلية
    </div>

                """,
                unsafe_allow_html=True
            )

            if indoor["rooms"]:

                for p in indoor["rooms"][:12]:

                    tags = p["tags"]

                    name = (
                        tags.get("name")
                        or tags.get("ref")
                        or "مكان داخلي"
                    )

                    level = tags.get(
                        "level",
                        "غير محدد"
                    )

                    st.write(
                        f"📍 {name} — "
                        f"الطابق: {level}"
                    )

            else:

                st.caption(
                    "لا توجد غرف أو أماكن داخلية مفصلة مسجلة."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

    else:

        st.markdown(
            """
<div class="indoor-box">

    <div class="indoor-title">
        ⚪ لا توجد بيانات داخلية كافية
    </div>

    <div class="indoor-text">
        لم يتم العثور على خريطة داخلية مفصلة لهذا المكان.
        لذلك لن يخترع VerifyAI Access مواقع الغرف أو المصاعد
        أو الطوابق. يمكنك الاعتماد فقط على العلامات المسجلة
        حاليًا على الخريطة.
    </div>

</div>
""",
            unsafe_allow_html=True
        )


    # =====================================================
    # ROUTE ANALYSIS
    # =====================================================

    st.write("")

    st.markdown(
        """
<div class="info-card">

    <div class="info-title">
        ♿ تقييم المسار
    </div>

    <div class="info-subtitle">
        التقييم يعتمد على بيانات الوصول المسجلة، وليس ضمانًا ميدانيًا.
    </div>

</div>
""",
        unsafe_allow_html=True
    )


    if score >= 80 and len(outdoor["stairs"]) == 0:

        st.success(
            "المسار يبدو مناسبًا بدرجة جيدة. "
            "لم يتم العثور على درجات قريبة من المسار "
            "ضمن البيانات المتاحة."
        )

    elif len(outdoor["stairs"]) > 0:

        st.warning(
            f"تم العثور على {len(outdoor['stairs'])} "
            "نقطة مرتبطة بالدرجات ضمن منطقة المسار. "
            "تحقق من العلامات على الخريطة قبل الرحلة."
        )

    else:

        st.info(
            "بيانات الوصول محدودة. "
            "عدم وجود علامة لا يعني بالضرورة أن المكان مهيأ."
        )


    # =====================================================
    # ACCESSIBILITY SUMMARY
    # =====================================================

    st.write("")

    summary_cols = st.columns(2)

    with summary_cols[0]:

        st.markdown(
            """
<div class="info-card">

    <div class="info-title">
        🧭 عناصر الوصول الخارجية
    </div>

            """,
            unsafe_allow_html=True
        )

        items = [
            (
                "🛗",
                "مصاعد",
                len(outdoor["elevators"])
            ),
            (
                "🛝",
                "منحدرات",
                len(outdoor["ramps"])
            ),
            (
                "♿",
                "وصول مهيأ",
                len(outdoor["wheelchair_yes"])
            ),
            (
                "🚫",
                "درجات",
                len(outdoor["stairs"])
            ),
            (
                "⚠️",
                "غير مهيأ",
                len(outdoor["wheelchair_no"])
            ),
            (
                "🚻",
                "دورات مياه",
                len(outdoor["toilets"])
            ),
            (
                "🅿️",
                "مواقف مهيأة",
                len(outdoor["parking"])
            )
        ]

        for icon, name, count in items:

            st.write(
                f"{icon} **{name}:** {count}"
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


    with summary_cols[1]:

        st.markdown(
            """
<div class="info-card">

    <div class="info-title">
        🏢 عناصر الوصول الداخلية
    </div>

            """,
            unsafe_allow_html=True
        )

        indoor_items = [
            (
                "🚪",
                "مداخل",
                len(indoor["entrances"])
            ),
            (
                "🛗",
                "مصاعد داخلية",
                len(indoor["elevators"])
            ),
            (
                "📍",
                "أماكن داخلية",
                len(indoor["rooms"])
            ),
            (
                "🪜",
                "سلالم داخلية",
                len(indoor["stairs"])
            ),
            (
                "🚻",
                "دورات مياه داخلية",
                len(indoor["toilets"])
            ),
            (
                "🛣️",
                "ممرات داخلية",
                len(indoor["corridors"])
            )
        ]

        for icon, name, count in indoor_items:

            st.write(
                f"{icon} **{name}:** {count}"
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


    # =====================================================
    # AI
    # =====================================================

    st.write("")

    st.markdown(
        """
<div class="info-card">

    <div class="info-title">
        ✨ تحليل VerifyAI
    </div>

    <div class="info-subtitle">
        اسأل الذكاء الاصطناعي عن المسار والبيانات الموجودة.
    </div>

</div>
""",
        unsafe_allow_html=True
    )


    if st.button(
        "✨ تحليل المكان والمسار",
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
                "الخريطة والبحث يعملان بدون الذكاء الاصطناعي."
            )

        else:

            try:

                from openai import OpenAI

                client = OpenAI(
                    api_key=api_key
                )

                prompt = f"""
أنت VerifyAI Access، مساعد متخصص في الوصول الشامل.

حلل البيانات التالية فقط:

المسار:
مؤشر الإتاحة = {score}/100

البيانات الخارجية:
مصاعد = {len(outdoor["elevators"])}
منحدرات = {len(outdoor["ramps"])}
درجات = {len(outdoor["stairs"])}
وصول مهيأ = {len(outdoor["wheelchair_yes"])}
غير مهيأ = {len(outdoor["wheelchair_no"])}
دورات مياه = {len(outdoor["toilets"])}
مواقف مهيأة = {len(outdoor["parking"])}

البيانات الداخلية:
مبانٍ = {len(indoor["buildings"])}
مداخل = {len(indoor["entrances"])}
مصاعد = {len(indoor["elevators"])}
أماكن داخلية = {len(indoor["rooms"])}
سلالم = {len(indoor["stairs"])}
ممرات = {len(indoor["corridors"])}
دورات مياه = {len(indoor["toilets"])}
الطوابق المسجلة = {", ".join(indoor["levels"]) if indoor["levels"] else "لا توجد"}

القواعد:
1. لا تقل إن المكان مضمون أو مناسب 100%.
2. لا تخترع غرفة أو طابق أو مصعد.
3. إذا لم توجد بيانات داخلية، قل ذلك بوضوح.
4. اشرح معنى العلامات المهمة للمستخدم.
5. اذكر أن البيانات تعتمد على OpenStreetMap وقد تكون ناقصة أو قديمة.
6. أعطِ إجابة عربية قصيرة وواضحة.
"""

                response = client.responses.create(
                    model=MODEL,
                    input=prompt
                )

                st.session_state.ai_answer = response.output_text

            except Exception as error:

                st.error(
                    f"حدث خطأ أثناء تشغيل الذكاء الاصطناعي: {error}"
                )


    if st.session_state.ai_answer:

        st.info(
            st.session_state.ai_answer
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
<div class="footer">
    VerifyAI Access — Smart Accessibility Navigation
    <br>
    الوصول للجميع، بوضوح واستقلالية.
</div>
""",
    unsafe_allow_html=True
)
