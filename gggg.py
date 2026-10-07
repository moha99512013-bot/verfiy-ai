import os
import math
import html
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# =========================================================
# SETTINGS
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/3.0"
}


# =========================================================
# STYLE
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
        radial-gradient(circle at 10% 5%, rgba(118,87,255,.10), transparent 25%),
        radial-gradient(circle at 90% 10%, rgba(0,190,180,.08), transparent 25%),
        #f7f8fc;
}

.block-container {
    max-width: 1450px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    letter-spacing: -0.5px;
}

.stButton > button {
    border-radius: 14px !important;
    border: 0 !important;
    background: #7657ff !important;
    color: white !important;
    font-weight: 800 !important;
    min-height: 45px !important;
}

.stButton > button:hover {
    background: #6549e8 !important;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e8e7ef;
    padding: 14px;
    border-radius: 18px;
    box-shadow: 0 8px 25px rgba(35,25,80,.04);
}

.footer {
    text-align: center;
    color: #999aa8;
    font-size: 11px;
    padding: 30px 0 10px;
}
</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = None

if "start_point" not in st.session_state:
    st.session_state.start_point = None

if "destination_point" not in st.session_state:
    st.session_state.destination_point = None

if "route_result" not in st.session_state:
    st.session_state.route_result = None

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = None

if "map_version" not in st.session_state:
    st.session_state.map_version = 0


# =========================================================
# GEOGRAPHY
# =========================================================

def reverse_geocode(lat, lon):
    try:
        response = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 18,
                "addressdetails": 1
            },
            headers=HEADERS,
            timeout=15
        )

        data = response.json()

        return data.get("display_name", "الموقع المحدد")

    except Exception:
        return "الموقع المحدد"


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
# OUTDOOR ACCESSIBILITY
# =========================================================

def get_accessibility_data(lat, lon, radius=1500):

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


def parse_outdoor_data(elements):

    result = {
        "stairs": [],
        "elevators": [],
        "ramps": [],
        "wheelchair_yes": [],
        "wheelchair_no": [],
        "toilets": [],
        "parking": [],
        "entrances": []
    }

    for item in elements:

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
            result["stairs"].append(point)

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
        ):
            result["elevators"].append(point)

        if tags.get("ramp") == "yes":
            result["ramps"].append(point)

        wheelchair = tags.get("wheelchair")

        if wheelchair == "yes":
            result["wheelchair_yes"].append(point)

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


# =========================================================
# INDOOR DATA
# =========================================================

def get_indoor_data(lat, lon, radius=300):

    query = f"""
    [out:json][timeout:35];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});

        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["highway"="steps"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        way["amenity"="toilets"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});
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


def parse_indoor_data(elements):

    result = {
        "buildings": [],
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "rooms": [],
        "toilets": [],
        "corridors": [],
        "levels": set()
    }

    for item in elements:

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

        if "building" in tags:
            result["buildings"].append(point)

        if "entrance" in tags:
            result["entrances"].append(point)

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
            or tags.get("indoor") == "elevator"
        ):
            result["elevators"].append(point)

        if (
            tags.get("highway") == "steps"
            or tags.get("indoor") == "stairs"
        ):
            result["stairs"].append(point)

        if (
            tags.get("room")
            or tags.get("indoor") == "room"
        ):
            result["rooms"].append(point)

        if tags.get("amenity") == "toilets":
            result["toilets"].append(point)

        if (
            tags.get("indoor") == "corridor"
            or tags.get("highway") == "corridor"
        ):
            result["corridors"].append(point)

        if tags.get("level"):
            for value in str(tags["level"]).split(";"):
                result["levels"].add(value.strip())

    result["levels"] = sorted(
        list(result["levels"]),
        key=lambda x: float(x)
        if x.replace(".", "", 1).replace("-", "", 1).isdigit()
        else 999
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

    step = max(
        1,
        len(coordinates) // 80
    )

    for lon, lat in coordinates[::step]:

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

    return max(
        0,
        min(
            100,
            round(score)
        )
    )


# =========================================================
# HEADER
# =========================================================

header1, header2 = st.columns([4, 1])

with header1:
    st.title("VerifyAI Access")

with header2:
    st.success("♿ Wheelchair Navigation")


st.caption(
    "خريطة وصول ذكية — اختر الأماكن بالضغط على الخريطة مباشرة."
)


# =========================================================
# SELECT LOCATION
# =========================================================

st.subheader("📍 اختر المواقع")

st.write(
    "حدد نقطة البداية أو الوجهة بالضغط على الخريطة. "
    "لن تحتاج إلى كتابة اسم المكان."
)

b1, b2, b3 = st.columns([1, 1, 1])

with b1:
    if st.button(
        "🟢 تحديد نقطة البداية",
        use_container_width=True
    ):
        st.session_state.selection_mode = "start"
        st.session_state.map_version += 1

with b2:
    if st.button(
        "🔴 تحديد الوجهة",
        use_container_width=True
    ):
        st.session_state.selection_mode = "destination"
        st.session_state.map_version += 1

with b3:
    if st.button(
        "🗑️ مسح الاختيارات",
        use_container_width=True
    ):
        st.session_state.start_point = None
        st.session_state.destination_point = None
        st.session_state.route_result = None
        st.session_state.ai_answer = None
        st.session_state.selection_mode = None
        st.session_state.map_version += 1


if st.session_state.selection_mode == "start":
    st.info(
        "🟢 وضع تحديد البداية فعال — اضغط الآن على الخريطة."
    )

elif st.session_state.selection_mode == "destination":
    st.info(
        "🔴 وضع تحديد الوجهة فعال — اضغط الآن على الخريطة."
    )

else:
    st.info(
        "اضغط أولًا على «تحديد نقطة البداية» أو «تحديد الوجهة»."
    )


# =========================================================
# MAP FOR PICKING
# =========================================================

if st.session_state.start_point:
    map_center = [
        st.session_state.start_point["lat"],
        st.session_state.start_point["lon"]
    ]
elif st.session_state.destination_point:
    map_center = [
        st.session_state.destination_point["lat"],
        st.session_state.destination_point["lon"]
    ]
else:
    # Saudi Arabia default view
    map_center = [24.7136, 46.6753]


selection_map = folium.Map(
    location=map_center,
    zoom_start=6,
    tiles="OpenStreetMap"
)


if st.session_state.start_point:

    folium.Marker(
        [
            st.session_state.start_point["lat"],
            st.session_state.start_point["lon"]
        ],
        tooltip="🟢 البداية",
        popup="نقطة البداية",
        icon=folium.Icon(
            color="green",
            icon="play",
            prefix="fa"
        )
    ).add_to(selection_map)


if st.session_state.destination_point:

    folium.Marker(
        [
            st.session_state.destination_point["lat"],
            st.session_state.destination_point["lon"]
        ],
        tooltip="🔴 الوجهة",
        popup="الوجهة",
        icon=folium.Icon(
            color="red",
            icon="flag",
            prefix="fa"
        )
    ).add_to(selection_map)


map_data = st_folium(
    selection_map,
    width=None,
    height=580,
    returned_objects=["last_clicked"],
    key=f"selection_map_{st.session_state.map_version}"
)


# =========================================================
# HANDLE MAP CLICK
# =========================================================

clicked = map_data.get("last_clicked")

if clicked and st.session_state.selection_mode:

    lat = float(clicked["lat"])
    lon = float(clicked["lng"])

    place_name = reverse_geocode(
        lat,
        lon
    )

    point = {
        "lat": lat,
        "lon": lon,
        "name": place_name
    }

    if st.session_state.selection_mode == "start":

        st.session_state.start_point = point

        st.session_state.selection_mode = None

        st.session_state.route_result = None
        st.session_state.ai_answer = None

        st.session_state.map_version += 1

        st.rerun()

    elif st.session_state.selection_mode == "destination":

        st.session_state.destination_point = point

        st.session_state.selection_mode = None

        st.session_state.route_result = None
        st.session_state.ai_answer = None

        st.session_state.map_version += 1

        st.rerun()


# =========================================================
# SELECTED LOCATIONS
# =========================================================

st.subheader("📌 المواقع المحددة")

location1, location2 = st.columns(2)

with location1:

    if st.session_state.start_point:

        st.success(
            "🟢 البداية\n\n"
            + st.session_state.start_point["name"]
        )

    else:

        st.warning(
            "🟢 لم يتم اختيار نقطة البداية."
        )


with location2:

    if st.session_state.destination_point:

        st.error(
            "🔴 الوجهة\n\n"
            + st.session_state.destination_point["name"]
        )

    else:

        st.warning(
            "🔴 لم يتم اختيار الوجهة."
        )


# =========================================================
# ROUTE BUTTON
# =========================================================

ready = (
    st.session_state.start_point is not None
    and st.session_state.destination_point is not None
)

if ready:

    if st.button(
        "🚀 احسب أفضل مسار",
        use_container_width=True
    ):

        with st.spinner(
            "جاري تحليل المسارات وبيانات الوصول..."
        ):

            start = st.session_state.start_point
            destination = st.session_state.destination_point

            routes = get_routes(
                start,
                destination
            )

            outdoor_raw = get_accessibility_data(
                destination["lat"],
                destination["lon"]
            )

            outdoor = parse_outdoor_data(
                outdoor_raw
            )

            indoor_raw = get_indoor_data(
                destination["lat"],
                destination["lon"]
            )

            indoor = parse_indoor_data(
                indoor_raw
            )

            if routes:

                scored_routes = []

                for route in routes:

                    score = score_route(
                        route,
                        outdoor
                    )

                    scored_routes.append(
                        (
                            score,
                            route
                        )
                    )

                scored_routes.sort(
                    key=lambda x: x[0],
                    reverse=True
                )

                best_score, best_route = scored_routes[0]

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

            st.rerun()


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

    st.divider()

    st.header("🗺️ المسار")

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

    a, b, c, d = st.columns(4)

    a.metric(
        "♿ مؤشر الإتاحة",
        f"{score}%"
    )

    b.metric(
        "🛣️ المسافة",
        f"{distance_km:.1f} كم"
    )

    c.metric(
        "⏱️ الوقت التقريبي",
        f"{minutes} دقيقة"
    )

    d.metric(
        "🛗 المصاعد",
        len(outdoor["elevators"])
    )


    # -----------------------------------------------------
    # RESULT MAP
    # -----------------------------------------------------

    center = [
        (
            start["lat"]
            + destination["lat"]
        ) / 2,

        (
            start["lon"]
            + destination["lon"]
        ) / 2
    ]

    result_map = folium.Map(
        location=center,
        zoom_start=15,
        tiles="OpenStreetMap"
    )


    # START

    folium.Marker(
        [
            start["lat"],
            start["lon"]
        ],
        tooltip="🟢 نقطة البداية",
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
    ).add_to(result_map)


    # DESTINATION

    folium.Marker(
        [
            destination["lat"],
            destination["lon"]
        ],
        tooltip="🔴 الوجهة",
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
    ).add_to(result_map)


    # ROUTE

    if route:

        route_points = [
            [
                point[1],
                point[0]
            ]
            for point in route["geometry"]["coordinates"]
        ]

        folium.PolyLine(
            route_points,
            color="#7657ff",
            weight=7,
            opacity=0.9,
            tooltip="🟣 المسار المقترح"
        ).add_to(result_map)


    # -----------------------------------------------------
    # OUTDOOR MARKERS
    # -----------------------------------------------------

    for p in outdoor["elevators"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛗 مصعد",
            popup="🛗 مصعد مسجل على الخريطة.",
            icon=folium.Icon(
                color="blue",
                icon="arrow-up",
                prefix="fa"
            )
        ).add_to(result_map)


    for p in outdoor["ramps"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛝 منحدر",
            popup="🛝 منحدر مسجل للوصول.",
            icon=folium.Icon(
                color="green",
                icon="road",
                prefix="fa"
            )
        ).add_to(result_map)


    for p in outdoor["stairs"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🚫 درج",
            popup="🚫 يوجد درج مسجل في هذه المنطقة.",
            icon=folium.Icon(
                color="red",
                icon="warning-sign",
                prefix="glyphicon"
            )
        ).add_to(result_map)


    for p in outdoor["wheelchair_yes"]:

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=7,
            color="#00a884",
            fill=True,
            fill_opacity=0.9,
            tooltip="♿ وصول مهيأ",
            popup="♿ المكان مسجل كمتاح للكراسي المتحركة."
        ).add_to(result_map)


    for p in outdoor["wheelchair_no"]:

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=8,
            color="#e5484d",
            fill=True,
            fill_opacity=0.9,
            tooltip="⚠️ غير مهيأ",
            popup="⚠️ المكان مسجل كغير مناسب للكراسي المتحركة."
        ).add_to(result_map)


    for p in outdoor["toilets"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🚻 دورة مياه مهيأة",
            popup="🚻 دورة مياه مهيأة مسجلة.",
            icon=folium.Icon(
                color="purple",
                icon="home",
                prefix="glyphicon"
            )
        ).add_to(result_map)


    for p in outdoor["parking"]:

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🅿️ موقف مهيأ",
            popup="🅿️ موقف مهيأ مسجل.",
            icon=folium.Icon(
                color="orange",
                icon="parking",
                prefix="fa"
            )
        ).add_to(result_map)


    # -----------------------------------------------------
    # INDOOR MARKERS
    # -----------------------------------------------------

    for p in indoor["entrances"]:

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
            tooltip="🚪 مدخل",
            popup=folium.Popup(
                "<b>🚪 مدخل</b><br>"
                f"الطابق: {html.escape(str(level))}<br>"
                f"الوصول: {html.escape(str(wheelchair))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="cadetblue",
                icon="sign-in",
                prefix="fa"
            )
        ).add_to(result_map)


    for p in indoor["elevators"]:

        level = p["tags"].get(
            "level",
            "غير محدد"
        )

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🛗 مصعد داخلي",
            popup=folium.Popup(
                "<b>🛗 مصعد داخلي</b><br>"
                f"الطابق: {html.escape(str(level))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="blue",
                icon="arrow-up",
                prefix="fa"
            )
        ).add_to(result_map)


    for p in indoor["stairs"]:

        level = p["tags"].get(
            "level",
            "غير محدد"
        )

        folium.Marker(
            [p["lat"], p["lon"]],
            tooltip="🪜 درج داخلي",
            popup=folium.Popup(
                "<b>🪜 درج داخلي</b><br>"
                f"الطابق: {html.escape(str(level))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="red",
                icon="warning-sign",
                prefix="glyphicon"
            )
        ).add_to(result_map)


    for p in indoor["rooms"]:

        name = (
            p["tags"].get("name")
            or p["tags"].get("ref")
            or "مكان داخلي"
        )

        level = p["tags"].get(
            "level",
            "غير محدد"
        )

        folium.CircleMarker(
            [p["lat"], p["lon"]],
            radius=6,
            color="#7657ff",
            fill=True,
            fill_opacity=0.9,
            tooltip=f"📍 {name}",
            popup=folium.Popup(
                "<b>📍 مكان داخلي</b><br>"
                f"الاسم: {html.escape(str(name))}<br>"
                f"الطابق: {html.escape(str(level))}",
                max_width=320
            )
        ).add_to(result_map)


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
            tooltip="🚻 دورة مياه",
            popup=folium.Popup(
                "<b>🚻 دورة مياه</b><br>"
                f"الطابق: {html.escape(str(level))}<br>"
                f"الوصول: {html.escape(str(wheelchair))}",
                max_width=300
            ),
            icon=folium.Icon(
                color="purple",
                icon="home",
                prefix="glyphicon"
            )
        ).add_to(result_map)


    st_folium(
        result_map,
        width=None,
        height=650,
        returned_objects=[]
    )


    # =====================================================
    # MARKER EXPLANATION
    # =====================================================

    with st.expander(
        "📍 اضغط هنا لمعرفة معنى العلامات"
    ):

        st.write("🟣 **المسار المقترح** — المسار الذي اختاره النظام.")

        st.write("🟢 **البداية** — المكان الذي حددته كنقطة انطلاق.")

        st.write("🔴 **الوجهة** — المكان الذي حددته كنهاية.")

        st.write("🛗 **مصعد** — مصعد مسجل في بيانات الخريطة.")

        st.write("🛝 **منحدر** — منحدر مسجل للوصول.")

        st.write("♿ **وصول مهيأ** — موقع مسجل كمتاح للكراسي المتحركة.")

        st.write("🚫 **درج** — درج مسجل في هذه المنطقة.")

        st.write("⚠️ **غير مهيأ** — مكان مسجل كغير مناسب للكراسي المتحركة.")

        st.write("🚻 **دورة مياه** — دورة مياه مسجلة.")

        st.write("🅿️ **موقف مهيأ** — موقف مهيأ مسجل.")

        st.write("🚪 **مدخل** — مدخل للمبنى.")

        st.write("📍 **مكان داخلي** — غرفة أو مساحة داخلية مسجلة.")


    # =====================================================
    # ROUTE STATUS
    # =====================================================

    st.subheader("♿ تحليل المسار")

    if route is None:

        st.error(
            "لم يتم العثور على طريق للمشاة بين النقطتين."
        )

    elif score >= 80 and len(outdoor["stairs"]) == 0:

        st.success(
            "المسار يبدو مناسبًا بدرجة جيدة حسب البيانات المتاحة."
        )

    elif len(outdoor["stairs"]) > 0:

        st.warning(
            f"تم العثور على {len(outdoor['stairs'])} "
            "نقطة درج ضمن منطقة المسار. "
            "راجع العلامات على الخريطة."
        )

    else:

        st.info(
            "بيانات الإتاحة محدودة، لذلك لا يمكن تأكيد "
            "ملاءمة المسار بالكامل."
        )


    # =====================================================
    # INDOOR BUILDING
    # =====================================================

    st.subheader("🏢 المعلومات داخل المبنى")

    indoor_found = (
        len(indoor["buildings"]) > 0
        or len(indoor["entrances"]) > 0
        or len(indoor["rooms"]) > 0
        or len(indoor["elevators"]) > 0
        or len(indoor["levels"]) > 0
    )

    if indoor_found:

        st.success(
            "تم العثور على بيانات داخلية للمكان."
        )

        x1, x2, x3, x4 = st.columns(4)

        x1.metric(
            "🚪 المداخل",
            len(indoor["entrances"])
        )

        x2.metric(
            "🛗 المصاعد",
            len(indoor["elevators"])
        )

        x3.metric(
            "📍 الأماكن الداخلية",
            len(indoor["rooms"])
        )

        x4.metric(
            "🪜 السلالم",
            len(indoor["stairs"])
        )

        if indoor["levels"]:

            st.write(
                "**الطوابق المسجلة:** "
                + "، ".join(
                    f"الطابق {level}"
                    for level in indoor["levels"]
                )
            )

    else:

        st.info(
            "لا توجد بيانات داخلية كافية لهذا المبنى في الخريطة حاليًا. "
            "لن يخمن النظام مواقع الغرف أو المصاعد غير المسجلة."
        )


    # =====================================================
    # AI
    # =====================================================

    st.subheader("✨ تحليل VerifyAI")

    if st.button(
        "✨ تحليل المسار والوجهة بالذكاء الاصطناعي",
        use_container_width=True
    ):

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
                "مفتاح OpenAI غير متصل."
            )

        else:

            try:

                from openai import OpenAI

                client = OpenAI(
                    api_key=api_key
                )

                prompt = f"""
أنت مساعد VerifyAI Access للوصول الشامل.

حلل المعلومات التالية فقط:

مؤشر الإتاحة: {score}/100

المسار:
المسافة: {distance_km:.1f} كم
الوقت: {minutes} دقيقة

الخارج:
المصاعد: {len(outdoor["elevators"])}
المنحدرات: {len(outdoor["ramps"])}
الدرجات: {len(outdoor["stairs"])}
الوصول المهيأ: {len(outdoor["wheelchair_yes"])}
غير المهيأ: {len(outdoor["wheelchair_no"])}
دورات المياه: {len(outdoor["toilets"])}
المواقف: {len(outdoor["parking"])}

الداخل:
المداخل: {len(indoor["entrances"])}
المصاعد: {len(indoor["elevators"])}
الأماكن الداخلية: {len(indoor["rooms"])}
السلالم: {len(indoor["stairs"])}
الطوابق: {", ".join(indoor["levels"]) if indoor["levels"] else "غير متوفرة"}

القواعد:
- لا تقل إن المكان مضمون 100%.
- لا تخترع أي غرفة أو طابق أو مصعد.
- إذا كانت البيانات الداخلية غير موجودة، قل ذلك.
- وضح معنى العلامات المهمة.
- اذكر أن بيانات OpenStreetMap قد تكون ناقصة أو قديمة.
- أجب بالعربية بشكل واضح ومختصر.
"""

                response = client.responses.create(
                    model=MODEL,
                    input=prompt
                )

                st.session_state.ai_answer = (
                    response.output_text
                )

            except Exception as error:

                st.error(
                    f"حدث خطأ في الذكاء الاصطناعي: {error}"
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
الوصول للجميع.
</div>
""",
    unsafe_allow_html=True
)
