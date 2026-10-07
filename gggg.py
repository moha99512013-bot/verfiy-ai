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

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/7.0"
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
        radial-gradient(
            circle at 10% 5%,
            rgba(118,87,255,.10),
            transparent 25%
        ),
        radial-gradient(
            circle at 90% 10%,
            rgba(0,190,180,.08),
            transparent 25%
        ),
        #f7f8fc;
}

.block-container {
    max-width: 1450px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}

.stButton > button {
    border-radius: 14px !important;
    border: 0 !important;
    background: #7657ff !important;
    color: white !important;
    font-weight: 800 !important;
    min-height: 45px !important;
    box-shadow: 0 8px 22px rgba(118,87,255,.20);
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

.building-card {
    background: white;
    border: 1px solid #e8e7ef;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 12px;
    box-shadow: 0 8px 25px rgba(35,25,80,.04);
}

.search-result {
    background: white;
    border: 1px solid #e8e7ef;
    border-radius: 14px;
    padding: 12px;
    margin-bottom: 8px;
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

defaults = {
    "page": "الخريطة",

    "selection_mode": None,

    "start_point": None,
    "destination_point": None,

    "selected_building": None,
    "selected_floor": "كل الطوابق",

    "indoor_mode": False,
    "indoor_destination": None,

    "route_result": None,
    "ai_answer": None,

    "search_results": [],
    "search_query": "",
    "search_center": None,

    "building_search": "",
    "building_radius": 5000,

    "map_key": 0,
    "building_page_key": 0,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPERS
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

        return response.json().get(
            "display_name",
            "الموقع المحدد"
        )

    except Exception:

        return "الموقع المحدد"


def search_places(query, limit=8):

    if not query.strip():
        return []

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": limit,
                "countrycodes": "sa"
            },
            headers=HEADERS,
            timeout=20
        )

        return response.json()

    except Exception:

        return []


def distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

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


def has_indoor_information(indoor):

    return (
        len(indoor.get("levels", [])) > 0
        or len(indoor.get("rooms", [])) > 0
        or len(indoor.get("entrances", [])) > 0
        or len(indoor.get("elevators", [])) > 0
        or len(indoor.get("stairs", [])) > 0
        or len(indoor.get("toilets", [])) > 0
        or len(indoor.get("corridors", [])) > 0
    )


def floor_visible(point, selected_floor):

    if selected_floor == "كل الطوابق":
        return True

    tags = point.get("tags", {})

    point_level = tags.get("level")

    if not point_level:
        return True

    levels = [
        str(x).strip()
        for x in str(point_level).split(";")
    ]

    return str(selected_floor) in levels


def draw_polygon(
    map_object,
    geometry,
    **kwargs
):

    points = [
        [
            point["lat"],
            point["lon"]
        ]
        for point in geometry
        if "lat" in point and "lon" in point
    ]

    if len(points) >= 3:

        folium.Polygon(
            points,
            **kwargs
        ).add_to(map_object)


def get_building_name(building):

    tags = building.get("tags", {})

    return (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("building")
        or "مبنى بدون اسم"
    )


# =========================================================
# BUILDINGS
# =========================================================

def get_openable_buildings(
    lat,
    lon,
    radius=5000
):

    query = f"""
    [out:json][timeout:90];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});
        relation["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});

        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        way["amenity"="toilets"](around:{radius},{lat},{lon});
    );

    out center geom;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=100
        )

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        return []


    buildings = []
    indoor_points = []


    # -----------------------------------------------------
    # BUILDINGS
    # -----------------------------------------------------

    for item in elements:

        tags = item.get(
            "tags",
            {}
        )

        if "building" not in tags:
            continue

        geometry = item.get(
            "geometry",
            []
        )

        center = item.get("center")


        if center:

            center_lat = float(center["lat"])
            center_lon = float(center["lon"])

        elif geometry:

            center_lat = sum(
                p["lat"]
                for p in geometry
            ) / len(geometry)

            center_lon = sum(
                p["lon"]
                for p in geometry
            ) / len(geometry)

        else:

            continue


        buildings.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "lat": center_lat,
                "lon": center_lon,
                "tags": tags,
                "geometry": geometry
            }
        )


    # -----------------------------------------------------
    # INDOOR ELEMENTS
    # -----------------------------------------------------

    for item in elements:

        tags = item.get(
            "tags",
            {}
        )

        is_indoor = (
            bool(tags.get("indoor"))
            or bool(tags.get("room"))
            or bool(tags.get("level"))
            or bool(tags.get("entrance"))
            or tags.get("elevator") == "yes"
            or tags.get("highway") in {
                "elevator",
                "steps"
            }
            or tags.get("amenity") == "toilets"
        )

        if not is_indoor:
            continue


        if "lat" in item:

            point_lat = float(item["lat"])
            point_lon = float(item["lon"])

        elif item.get("center"):

            point_lat = float(
                item["center"]["lat"]
            )

            point_lon = float(
                item["center"]["lon"]
            )

        elif item.get("geometry"):

            geometry = item["geometry"]

            point_lat = sum(
                p["lat"]
                for p in geometry
            ) / len(geometry)

            point_lon = sum(
                p["lon"]
                for p in geometry
            ) / len(geometry)

        else:

            continue


        indoor_points.append(
            {
                "lat": point_lat,
                "lon": point_lon,
                "tags": tags
            }
        )


    # -----------------------------------------------------
    # MATCH
    # -----------------------------------------------------

    openable = []


    for building in buildings:

        for point in indoor_points:

            distance = distance_meters(
                building["lat"],
                building["lon"],
                point["lat"],
                point["lon"]
            )

            if distance <= 100:

                openable.append(building)
                break


    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    unique = {}

    for building in openable:

        key = (
            building["type"],
            building["id"]
        )

        unique[key] = building


    return list(unique.values())


# =========================================================
# BUILDING AT POINT
# =========================================================

def get_building_at_point(
    lat,
    lon,
    radius=150
):

    query = f"""
    [out:json][timeout:35];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});
    );

    out center geom;
    """


    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=45
        )

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        return None


    best = None
    best_distance = float("inf")


    for item in elements:

        tags = item.get(
            "tags",
            {}
        )

        geometry = item.get(
            "geometry",
            []
        )

        center = item.get("center")


        if center:

            center_lat = float(
                center["lat"]
            )

            center_lon = float(
                center["lon"]
            )

        elif geometry:

            center_lat = sum(
                p["lat"]
                for p in geometry
            ) / len(geometry)

            center_lon = sum(
                p["lon"]
                for p in geometry
            ) / len(geometry)

        else:

            continue


        d = distance_meters(
            lat,
            lon,
            center_lat,
            center_lon
        )


        if d < best_distance:

            best_distance = d

            best = {
                "id": item.get("id"),
                "type": item.get("type"),
                "tags": tags,
                "center": {
                    "lat": center_lat,
                    "lon": center_lon
                },
                "geometry": geometry
            }


    return best


# =========================================================
# INDOOR DATA
# =========================================================

def get_indoor_data(
    lat,
    lon,
    radius=350
):

    query = f"""
    [out:json][timeout:50];

    (
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
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        way["amenity"="toilets"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});
    );

    out center geom;
    """


    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=65
        )

        return response.json().get(
            "elements",
            []
        )

    except Exception:

        return []


def parse_indoor_data(elements):

    result = {
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "rooms": [],
        "toilets": [],
        "corridors": [],
        "other": [],
        "levels": set()
    }


    for element in elements:

        tags = element.get(
            "tags",
            {}
        )


        if "lat" in element:

            lat = float(element["lat"])
            lon = float(element["lon"])

        elif element.get("center"):

            lat = float(
                element["center"]["lat"]
            )

            lon = float(
                element["center"]["lon"]
            )

        else:

            continue


        point = {
            "lat": lat,
            "lon": lon,
            "tags": tags,
            "geometry": element.get(
                "geometry",
                []
            )
        }


        # Floors

        if tags.get("level"):

            for level in str(
                tags["level"]
            ).split(";"):

                result["levels"].add(
                    level.strip()
                )


        # Entrance

        if "entrance" in tags:

            result["entrances"].append(point)


        # Elevator

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


        # Rooms

        if (
            tags.get("room")
            or tags.get("indoor") == "room"
        ):

            result["rooms"].append(point)


        # Toilets

        if tags.get("amenity") == "toilets":

            result["toilets"].append(point)


        # Corridors

        if (
            tags.get("indoor") == "corridor"
            or tags.get("highway") == "corridor"
        ):

            result["corridors"].append(point)


        # Other

        if tags.get("indoor"):

            if tags.get("indoor") not in {
                "room",
                "corridor",
                "stairs",
                "elevator"
            }:

                result["other"].append(point)


    def sort_floor(value):

        try:
            return float(value)
        except Exception:
            return 999


    result["levels"] = sorted(
        list(result["levels"]),
        key=sort_floor
    )

    return result


# =========================================================
# OPEN BUILDING
# =========================================================

def open_building(
    building
):

    if not building:
        return None

    center = building.get("center")

    if not center:

        center = {
            "lat": building["lat"],
            "lon": building["lon"]
        }

        building["center"] = center


    with st.spinner("🏢 جاري تحميل بيانات المبنى..."):

        elements = get_indoor_data(
            center["lat"],
            center["lon"],
            radius=400
        )

        indoor = parse_indoor_data(
            elements
        )


    if not has_indoor_information(indoor):

        return None


    building["indoor"] = indoor

    return building


# =========================================================
# ROUTING
# =========================================================

def get_routes(
    start,
    destination
):

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

        return response.json().get(
            "routes",
            []
        )

    except Exception:

        return []


def get_accessibility_data(
    lat,
    lon,
    radius=1800
):

    query = f"""
    [out:json][timeout:40];

    (
        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["ramp"="yes"](around:{radius},{lat},{lon});
        way["ramp"="yes"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["amenity"="toilets"]["wheelchair"="yes"]
            (around:{radius},{lat},{lon});

        node["amenity"="parking"]["wheelchair"="yes"]
            (around:{radius},{lat},{lon});

        node["entrance"]["wheelchair"="yes"]
            (around:{radius},{lat},{lon});
    );

    out center;
    """


    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=50
        )

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        elements = []


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


    for element in elements:

        tags = element.get(
            "tags",
            {}
        )


        if "lat" in element:

            lat2 = float(element["lat"])
            lon2 = float(element["lon"])

        elif element.get("center"):

            lat2 = float(
                element["center"]["lat"]
            )

            lon2 = float(
                element["center"]["lon"]
            )

        else:

            continue


        point = {
            "lat": lat2,
            "lon": lon2,
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


        if tags.get("wheelchair") == "yes":
            result["wheelchair_yes"].append(point)


        if tags.get("wheelchair") == "no":
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


def score_route(
    route,
    accessibility
):

    score = 100

    coordinates = route[
        "geometry"
    ]["coordinates"]

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

st.title("♿ VerifyAI Access")

st.caption(
    "خريطة وصول ذكية — ابحث عن الأماكن، اكتشف المباني القابلة للفتح، واختر مسارًا مناسبًا."
)


# =========================================================
# MAIN NAVIGATION
# =========================================================

page = st.radio(
    "التنقل",
    [
        "🗺️ الخريطة",
        "🏢 المباني القابلة للفتح"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

if page == "🗺️ الخريطة":
    st.session_state.page = "الخريطة"
else:
    st.session_state.page = "المباني القابلة للفتح"


# =========================================================
# PAGE 2 — OPENABLE BUILDINGS
# =========================================================

if st.session_state.page == "المباني القابلة للفتح":

    st.header("🏢 المباني القابلة للفتح")

    st.write(
        "هذه الصفحة تعرض المباني التي وجد النظام لها بيانات داخلية "
        "في OpenStreetMap، مثل الطوابق أو الغرف أو المداخل أو المصاعد."
    )

    b1, b2 = st.columns([3, 1])

    with b1:

        building_search = st.text_input(
            "🔎 ابحث داخل القائمة باسم المبنى",
            value=st.session_state.building_search,
            placeholder="مثال: جامعة الملك عبدالعزيز"
        )

        st.session_state.building_search = building_search

    with b2:

        radius = st.selectbox(
            "📍 نطاق البحث",
            [
                2000,
                3000,
                5000,
                8000,
                10000
            ],
            index=2,
            format_func=lambda x: f"{x // 1000} كم"
        )

        st.session_state.building_radius = radius


    # Center for building list

    if st.session_state.search_center:

        building_center = st.session_state.search_center

    elif st.session_state.start_point:

        building_center = st.session_state.start_point

    elif st.session_state.destination_point:

        building_center = st.session_state.destination_point

    else:

        building_center = {
            "lat": 21.5433,
            "lon": 39.1728
        }


    if st.button(
        "🔄 تحديث قائمة المباني",
        use_container_width=True
    ):

        st.session_state.building_page_key += 1


    with st.spinner(
        "🏢 جاري البحث عن المباني القابلة للفتح..."
    ):

        openable_buildings = get_openable_buildings(
            building_center["lat"],
            building_center["lon"],
            radius=radius
        )


    # Filter by name

    if building_search.strip():

        search_lower = building_search.lower()

        filtered_buildings = []

        for b in openable_buildings:

            name = get_building_name(b)

            if search_lower in name.lower():

                filtered_buildings.append(b)

        openable_buildings = filtered_buildings


    st.success(
        f"🏢 تم العثور على {len(openable_buildings)} مبنى قابل للفتح في نطاق البحث."
    )


    if not openable_buildings:

        st.warning(
            "لم يتم العثور على مبانٍ قابلة للفتح في المنطقة الحالية. "
            "جرّب زيادة نطاق البحث أو البحث عن منطقة أخرى."
        )

    else:

        for index, b in enumerate(openable_buildings):

            name = get_building_name(b)

            distance = distance_meters(
                building_center["lat"],
                building_center["lon"],
                b["lat"],
                b["lon"]
            )

            st.markdown(
                f"""
                <div class="building-card">
                    <h3>🏢 {html.escape(name)}</h3>
                    <p>📍 يبعد تقريبًا {distance:.0f} متر</p>
                    <p>
                        <b>الإحداثيات:</b>
                        {b["lat"]:.6f}, {b["lon"]:.6f}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )


            col1, col2 = st.columns([1, 1])


            with col1:

                if st.button(
                    "🏢 فتح المبنى",
                    key=f"open_building_{index}",
                    use_container_width=True
                ):

                    opened = open_building(b)

                    if opened:

                        st.session_state.selected_building = opened
                        st.session_state.indoor_mode = True

                        levels = opened["indoor"].get(
                            "levels",
                            []
                        )

                        if levels:

                            st.session_state.selected_floor = levels[0]

                        else:

                            st.session_state.selected_floor = (
                                "كل الطوابق"
                            )

                        st.session_state.page = "الخريطة"

                        st.session_state.map_key += 1

                        st.rerun()

                    else:

                        st.error(
                            "هذا المبنى ظهر في القائمة، "
                            "لكن لم نتمكن الآن من تحميل بياناته الداخلية."
                        )


            with col2:

                if st.button(
                    "📍 عرض على الخريطة",
                    key=f"show_building_{index}",
                    use_container_width=True
                ):

                    st.session_state.search_center = {
                        "lat": b["lat"],
                        "lon": b["lon"]
                    }

                    st.session_state.page = "الخريطة"

                    st.session_state.map_key += 1

                    st.rerun()


    st.markdown("---")

    st.info(
        "ملاحظة: المباني هنا تعتمد على البيانات الداخلية الموجودة في "
        "OpenStreetMap. لذلك قد يكون مبنى موجود فعليًا، لكن لا يظهر "
        "في القائمة إذا لم تكن بياناته الداخلية مسجلة."
    )


# =========================================================
# PAGE 1 — MAP
# =========================================================

else:

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    st.subheader("🔎 البحث عن مكان")

    search_col1, search_col2 = st.columns([5, 1])

    with search_col1:

        search_query = st.text_input(
            "اكتب اسم المكان أو العنوان",
            value=st.session_state.search_query,
            placeholder="مثال: رد سي مول جدة"
        )

        st.session_state.search_query = search_query

    with search_col2:

        search_button = st.button(
            "🔍 بحث",
            use_container_width=True
        )


    if search_button and search_query.strip():

        with st.spinner("🔎 جاري البحث..."):

            results = search_places(
                search_query,
                limit=8
            )

        st.session_state.search_results = results


    if st.session_state.search_results:

        st.write("### نتائج البحث")

        for index, result in enumerate(
            st.session_state.search_results
        ):

            name = result.get(
                "display_name",
                "مكان"
            )

            lat = float(
                result["lat"]
            )

            lon = float(
                result["lon"]
            )


            st.markdown(
                f"""
                <div class="search-result">
                    📍 <b>{html.escape(name)}</b>
                </div>
                """,
                unsafe_allow_html=True
            )


            r1, r2, r3 = st.columns(3)


            with r1:

                if st.button(
                    "📍 عرض",
                    key=f"search_show_{index}",
                    use_container_width=True
                ):

                    st.session_state.search_center = {
                        "lat": lat,
                        "lon": lon
                    }

                    st.session_state.map_key += 1

                    st.rerun()


            with r2:

                if st.button(
                    "🟢 بداية",
                    key=f"search_start_{index}",
                    use_container_width=True
                ):

                    st.session_state.start_point = {
                        "lat": lat,
                        "lon": lon,
                        "name": name
                    }

                    st.session_state.search_center = {
                        "lat": lat,
                        "lon": lon
                    }

                    st.session_state.route_result = None

                    st.session_state.map_key += 1

                    st.rerun()


            with r3:

                if st.button(
                    "🔴 وجهة",
                    key=f"search_dest_{index}",
                    use_container_width=True
                ):

                    st.session_state.destination_point = {
                        "lat": lat,
                        "lon": lon,
                        "name": name
                    }

                    st.session_state.search_center = {
                        "lat": lat,
                        "lon": lon
                    }

                    st.session_state.route_result = None

                    st.session_state.map_key += 1

                    st.rerun()


    # -----------------------------------------------------
    # CONTROLS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        if st.button(
            "🟢 نقطة البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = "start"


    with c2:

        if st.button(
            "🔴 الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = "destination"


    with c3:

        if st.button(
            "🏢 اختيار مبنى",
            use_container_width=True
        ):

            st.session_state.selection_mode = "building"


    with c4:

        if st.button(
            "🗑️ مسح",
            use_container_width=True
        ):

            st.session_state.selection_mode = None

            st.session_state.start_point = None
            st.session_state.destination_point = None

            st.session_state.selected_building = None

            st.session_state.selected_floor = (
                "كل الطوابق"
            )

            st.session_state.indoor_mode = False
            st.session_state.indoor_destination = None

            st.session_state.route_result = None
            st.session_state.ai_answer = None

            st.session_state.search_results = []

            st.session_state.map_key += 1

            st.rerun()


    # -----------------------------------------------------
    # MODE MESSAGE
    # -----------------------------------------------------

    if st.session_state.selection_mode == "start":

        st.info(
            "🟢 اضغط على الخريطة لتحديد نقطة البداية."
        )

    elif st.session_state.selection_mode == "destination":

        st.info(
            "🔴 اضغط على الخريطة لتحديد الوجهة."
        )

    elif st.session_state.selection_mode == "building":

        st.info(
            "🏢 اضغط على علامة المبنى القابلة للفتح أو على مكان المبنى."
        )

    else:

        st.info(
            "🔎 ابحث بالاسم أو اضغط على الخريطة يدويًا. "
            "المباني البنفسجية 🏢 هي المباني التي يمكن فتحها."
        )


    # -----------------------------------------------------
    # MAP CENTER
    # -----------------------------------------------------

    if st.session_state.search_center:

        map_center = [
            st.session_state.search_center["lat"],
            st.session_state.search_center["lon"]
        ]

    elif st.session_state.start_point:

        map_center = [
            st.session_state.start_point["lat"],
            st.session_state.start_point["lon"]
        ]

    elif st.session_state.destination_point:

        map_center = [
            st.session_state.destination_point["lat"],
            st.session_state.destination_point["lon"]
        ]

    elif st.session_state.selected_building:

        map_center = [
            st.session_state.selected_building["center"]["lat"],
            st.session_state.selected_building["center"]["lon"]
        ]

    else:

        map_center = [
            21.5433,
            39.1728
        ]


    # -----------------------------------------------------
    # BUILDINGS
    # -----------------------------------------------------

    with st.spinner(
        "🏢 جاري تجهيز المباني القابلة للفتح..."
    ):

        openable_buildings = get_openable_buildings(
            map_center[0],
            map_center[1],
            radius=5000
        )


    # -----------------------------------------------------
    # MAP
    # -----------------------------------------------------

    outdoor_map = folium.Map(
        location=map_center,
        zoom_start=14,
        tiles="OpenStreetMap",
        control_scale=True
    )


    # -----------------------------------------------------
    # OPENABLE BUILDINGS
    # -----------------------------------------------------

    for building in openable_buildings:

        name = get_building_name(
            building
        )

        popup = (
            "<b>🏢 مبنى قابل للفتح</b><br>"
            + html.escape(name)
            + "<br><br>"
            "اضغط على العلامة لفتح الخريطة الداخلية."
        )


        folium.Marker(
            location=[
                building["lat"],
                building["lon"]
            ],
            tooltip="🏢 مبنى قابل للفتح",
            popup=folium.Popup(
                popup,
                max_width=320
            ),
            icon=folium.Icon(
                color="purple",
                icon="building",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )


    # -----------------------------------------------------
    # SEARCH CENTER
    # -----------------------------------------------------

    if st.session_state.search_center:

        folium.Marker(
            location=[
                st.session_state.search_center["lat"],
                st.session_state.search_center["lon"]
            ],
            tooltip="📍 نتيجة البحث",
            popup="📍 الموقع الذي بحثت عنه",
            icon=folium.Icon(
                color="orange",
                icon="search",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )


    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if st.session_state.start_point:

        point = st.session_state.start_point

        folium.Marker(
            location=[
                point["lat"],
                point["lon"]
            ],
            tooltip="🟢 نقطة البداية",
            popup="🟢 نقطة البداية",
            icon=folium.Icon(
                color="green",
                icon="play",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )


    # -----------------------------------------------------
    # DESTINATION
    # -----------------------------------------------------

    if st.session_state.destination_point:

        point = st.session_state.destination_point

        folium.Marker(
            location=[
                point["lat"],
                point["lon"]
            ],
            tooltip="🔴 الوجهة",
            popup="🔴 الوجهة",
            icon=folium.Icon(
                color="red",
                icon="flag",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )


    # -----------------------------------------------------
    # SELECTED BUILDING
    # -----------------------------------------------------

    if (
        st.session_state.selected_building
        and st.session_state.selected_building.get(
            "geometry"
        )
    ):

        draw_polygon(
            outdoor_map,
            st.session_state.selected_building["geometry"],
            color="#7657ff",
            fill=True,
            fill_opacity=0.25,
            weight=4,
            tooltip="🏢 المبنى المحدد"
        )


    # -----------------------------------------------------
    # SHOW MAP
    # -----------------------------------------------------

    map_data = st_folium(
        outdoor_map,
        width=None,
        height=620,
        returned_objects=[
            "last_clicked",
            "last_object_clicked",
            "last_object_clicked_tooltip",
            "last_object_clicked_popup"
        ],
        key=f"outdoor_map_{st.session_state.map_key}"
    )


    # -----------------------------------------------------
    # BUILDING MARKER CLICK
    # -----------------------------------------------------

    if map_data:

        object_clicked = map_data.get(
            "last_object_clicked"
        )

        object_tooltip = map_data.get(
            "last_object_clicked_tooltip"
        )


        if object_clicked:

            clicked_lat = float(
                object_clicked["lat"]
            )

            clicked_lon = float(
                object_clicked["lng"]
            )


            building_candidate = None
            candidate_distance = float("inf")


            for b in openable_buildings:

                d = distance_meters(
                    clicked_lat,
                    clicked_lon,
                    b["lat"],
                    b["lon"]
                )

                if d < candidate_distance:

                    candidate_distance = d
                    building_candidate = b


            is_building_marker = (
                object_tooltip == "🏢 مبنى قابل للفتح"
                or (
                    building_candidate is not None
                    and candidate_distance < 100
                )
            )


            if is_building_marker:

                building = open_building(
                    building_candidate
                )


                if building:

                    st.session_state.selected_building = (
                        building
                    )

                    st.session_state.indoor_mode = True

                    levels = building["indoor"].get(
                        "levels",
                        []
                    )

                    if levels:

                        st.session_state.selected_floor = (
                            levels[0]
                        )

                    else:

                        st.session_state.selected_floor = (
                            "كل الطوابق"
                        )

                    st.session_state.selection_mode = None

                    st.session_state.map_key += 1

                    st.rerun()

                else:

                    st.warning(
                        "تعذر تحميل البيانات الداخلية لهذا المبنى."
                    )


    # -----------------------------------------------------
    # NORMAL CLICK
    # -----------------------------------------------------

    if (
        map_data
        and map_data.get("last_clicked")
        and not map_data.get("last_object_clicked")
        and st.session_state.selection_mode
    ):

        clicked = map_data["last_clicked"]

        lat = float(clicked["lat"])
        lon = float(clicked["lng"])


        # START

        if st.session_state.selection_mode == "start":

            st.session_state.start_point = {
                "lat": lat,
                "lon": lon,
                "name": reverse_geocode(
                    lat,
                    lon
                )
            }

            st.session_state.selection_mode = None
            st.session_state.route_result = None

            st.session_state.map_key += 1

            st.rerun()


        # DESTINATION

        elif st.session_state.selection_mode == "destination":

            st.session_state.destination_point = {
                "lat": lat,
                "lon": lon,
                "name": reverse_geocode(
                    lat,
                    lon
                )
            }

            st.session_state.selection_mode = None
            st.session_state.route_result = None

            st.session_state.map_key += 1

            st.rerun()


        # BUILDING

        elif st.session_state.selection_mode == "building":

            with st.spinner(
                "🏢 البحث عن المبنى..."
            ):

                building = get_building_at_point(
                    lat,
                    lon
                )


                if building:

                    opened = open_building(
                        building
                    )


                    if opened:

                        st.session_state.selected_building = (
                            opened
                        )

                        st.session_state.indoor_mode = True

                        levels = opened["indoor"].get(
                            "levels",
                            []
                        )

                        if levels:

                            st.session_state.selected_floor = (
                                levels[0]
                            )

                        else:

                            st.session_state.selected_floor = (
                                "كل الطوابق"
                            )

                        st.session_state.selection_mode = None

                        st.session_state.map_key += 1

                        st.rerun()

                    else:

                        st.warning(
                            "المبنى موجود، لكن لا توجد له بيانات داخلية كافية."
                        )

                else:

                    st.warning(
                        "لم يتم العثور على مبنى في هذا المكان."
                    )


    # =====================================================
    # LOCATIONS
    # =====================================================

    st.subheader("📌 المواقع المحددة")


    left, right = st.columns(2)


    with left:

        if st.session_state.start_point:

            st.success(
                "🟢 البداية\n\n"
                + st.session_state.start_point["name"]
            )

        else:

            st.info(
                "لم يتم اختيار نقطة البداية."
            )


    with right:

        if st.session_state.destination_point:

            st.error(
                "🔴 الوجهة\n\n"
                + st.session_state.destination_point["name"]
            )

        else:

            st.info(
                "لم يتم اختيار الوجهة."
            )


    # =====================================================
    # BUILDING PANEL
    # =====================================================

    building = st.session_state.selected_building


    if building:

        tags = building.get(
            "tags",
            {}
        )

        indoor = building.get(
            "indoor",
            {}
        )


        building_name = get_building_name(
            building
        )


        st.divider()

        st.header(
            f"🏢 {building_name}"
        )


        st.success(
            "هذا المبنى قابل للفتح لأن النظام وجد له بيانات داخلية."
        )


        s1, s2, s3, s4 = st.columns(4)


        with s1:

            st.metric(
                "🚪 المداخل",
                len(indoor["entrances"])
            )


        with s2:

            st.metric(
                "🛗 المصاعد",
                len(indoor["elevators"])
            )


        with s3:

            st.metric(
                "📍 الأماكن",
                len(indoor["rooms"])
            )


        with s4:

            st.metric(
                "🪜 السلالم",
                len(indoor["stairs"])
            )


        levels = indoor.get(
            "levels",
            []
        )


        floor_options = (
            ["كل الطوابق"] + levels
            if levels
            else ["كل الطوابق"]
        )


        current_floor = st.session_state.selected_floor


        if current_floor not in floor_options:

            current_floor = floor_options[0]


        selected_floor = st.selectbox(
            "🏷️ اختر الطابق",
            floor_options,
            index=floor_options.index(
                current_floor
            )
        )


        st.session_state.selected_floor = selected_floor


        if st.button(
            "🗺️ فتح الخريطة الداخلية",
            use_container_width=True
        ):

            st.session_state.indoor_mode = True

            st.session_state.map_key += 1

            st.rerun()


    # =====================================================
    # INDOOR MAP
    # =====================================================

    if (
        building
        and st.session_state.indoor_mode
    ):

        indoor = building["indoor"]

        selected_floor = (
            st.session_state.selected_floor
        )


        st.divider()

        st.header("🏢 الخريطة الداخلية")


        if selected_floor == "كل الطوابق":

            st.caption(
                "جميع البيانات الداخلية المتوفرة."
            )

        else:

            st.caption(
                f"الطابق: {selected_floor}"
            )


        indoor_map = folium.Map(
            location=[
                building["center"]["lat"],
                building["center"]["lon"]
            ],
            zoom_start=19,
            tiles="OpenStreetMap",
            control_scale=True
        )


        if building.get("geometry"):

            draw_polygon(
                indoor_map,
                building["geometry"],
                color="#7657ff",
                fill=True,
                fill_opacity=0.10,
                weight=3,
                tooltip="🏢 المبنى"
            )


        # -------------------------------------------------
        # ENTRANCES
        # -------------------------------------------------

        for point in indoor["entrances"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue


            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )


            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🚪 مدخل",
                popup=folium.Popup(
                    "<b>🚪 مدخل</b><br>"
                    f"الطابق: {html.escape(str(level))}<br>"
                    f"الوصول: {html.escape(str(wheelchair))}",
                    max_width=300
                ),
                icon=folium.Icon(
                    color="green",
                    icon="sign-in",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )


        # -------------------------------------------------
        # ELEVATORS
        # -------------------------------------------------

        for point in indoor["elevators"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue


            level = point["tags"].get(
                "level",
                "غير محدد"
            )


            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🛗 مصعد",
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
            ).add_to(
                indoor_map
            )


        # -------------------------------------------------
        # STAIRS
        # -------------------------------------------------

        for point in indoor["stairs"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue


            level = point["tags"].get(
                "level",
                "غير محدد"
            )


            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🪜 درج",
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
            ).add_to(
                indoor_map
            )


        # -------------------------------------------------
        # ROOMS
        # -------------------------------------------------

        for point in indoor["rooms"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue


            name = (
                point["tags"].get("name")
                or point["tags"].get("ref")
                or "مكان داخلي"
            )


            level = point["tags"].get(
                "level",
                "غير محدد"
            )


            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )


            folium.CircleMarker(
                [
                    point["lat"],
                    point["lon"]
                ],
                radius=7,
                color="#7657ff",
                fill=True,
                fill_opacity=0.9,
                tooltip=f"📍 {name}",
                popup=folium.Popup(
                    "<b>📍 مكان داخلي</b><br>"
                    f"الاسم: {html.escape(str(name))}<br>"
                    f"الطابق: {html.escape(str(level))}<br>"
                    f"الوصول: {html.escape(str(wheelchair))}",
                    max_width=320
                )
            ).add_to(
                indoor_map
            )


        # -------------------------------------------------
        # TOILETS
        # -------------------------------------------------

        for point in indoor["toilets"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue


            level = point["tags"].get(
                "level",
                "غير محدد"
            )


            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )


            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
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
            ).add_to(
                indoor_map
            )


        # -------------------------------------------------
        # INDOOR CLICK
        # -------------------------------------------------

        indoor_result = st_folium(
            indoor_map,
            width=None,
            height=650,
            returned_objects=[
                "last_clicked"
            ],
            key=f"indoor_map_{st.session_state.map_key}"
        )


        if (
            indoor_result
            and indoor_result.get("last_clicked")
        ):

            point = indoor_result[
                "last_clicked"
            ]


            st.session_state.indoor_destination = {
                "lat": float(point["lat"]),
                "lon": float(point["lng"]),
                "level": selected_floor
            }


            st.success(
                "📍 تم اختيار نقطة داخل المبنى."
            )


        # -------------------------------------------------
        # DETAILS
        # -------------------------------------------------

        st.subheader("📋 معلومات المبنى")


        if indoor["levels"]:

            st.write(
                "**الطوابق:** "
                + "، ".join(
                    f"الطابق {x}"
                    for x in indoor["levels"]
                )
            )


        st.write(
            f"🚪 المداخل: {len(indoor['entrances'])}"
        )

        st.write(
            f"🛗 المصاعد: {len(indoor['elevators'])}"
        )

        st.write(
            f"📍 الأماكن الداخلية: {len(indoor['rooms'])}"
        )

        st.write(
            f"🪜 السلالم: {len(indoor['stairs'])}"
        )

        st.write(
            f"🚻 دورات المياه: {len(indoor['toilets'])}"
        )


        st.info(
            "لا يتم عرض أي عنصر داخلي إلا إذا كانت بياناته موجودة."
        )


    # =====================================================
    # OUTDOOR ROUTE
    # =====================================================

    if (
        st.session_state.start_point
        and st.session_state.destination_point
    ):

        st.divider()


        if st.button(
            "🚀 احسب أفضل مسار",
            use_container_width=True
        ):

            with st.spinner(
                "جاري تحليل المسارات..."
            ):

                start = st.session_state.start_point

                destination = (
                    st.session_state.destination_point
                )


                routes = get_routes(
                    start,
                    destination
                )


                accessibility = (
                    get_accessibility_data(
                        destination["lat"],
                        destination["lon"]
                    )
                )


                if routes:

                    scores = []

                    for route in routes:

                        score = score_route(
                            route,
                            accessibility
                        )

                        scores.append(
                            (
                                score,
                                route
                            )
                        )


                    scores.sort(
                        key=lambda x: x[0],
                        reverse=True
                    )


                    best_score, best_route = (
                        scores[0]
                    )


                else:

                    best_score = 0
                    best_route = None


                st.session_state.route_result = {
                    "start": start,
                    "destination": destination,
                    "route": best_route,
                    "score": best_score,
                    "accessibility": accessibility
                }


                st.session_state.ai_answer = None

                st.rerun()


    # =====================================================
    # ROUTE RESULT
    # =====================================================

    route_result = (
        st.session_state.route_result
    )


    if route_result:

        st.divider()

        st.header(
            "🚶 المسار المقترح"
        )


        route = route_result["route"]

        accessibility = route_result[
            "accessibility"
        ]

        score = route_result["score"]


        if route:

            distance_km = (
                route["distance"] / 1000
            )


            minutes = max(
                1,
                round(
                    route["duration"] / 60
                )
            )


            c1, c2, c3, c4 = st.columns(4)


            c1.metric(
                "♿ مؤشر الإتاحة",
                f"{score}%"
            )


            c2.metric(
                "🛣️ المسافة",
                f"{distance_km:.1f} كم"
            )


            c3.metric(
                "⏱️ الوقت",
                f"{minutes} دقيقة"
            )


            c4.metric(
                "🛗 المصاعد",
                len(
                    accessibility["elevators"]
                )
            )


            route_map = folium.Map(
                location=[
                    (
                        route_result["start"]["lat"]
                        + route_result["destination"]["lat"]
                    ) / 2,

                    (
                        route_result["start"]["lon"]
                        + route_result["destination"]["lon"]
                    ) / 2
                ],
                zoom_start=15,
                tiles="OpenStreetMap"
            )


            folium.Marker(
                [
                    route_result["start"]["lat"],
                    route_result["start"]["lon"]
                ],
                tooltip="🟢 البداية",
                popup="🟢 البداية",
                icon=folium.Icon(
                    color="green",
                    icon="play",
                    prefix="fa"
                )
            ).add_to(route_map)


            folium.Marker(
                [
                    route_result["destination"]["lat"],
                    route_result["destination"]["lon"]
                ],
                tooltip="🔴 الوجهة",
                popup="🔴 الوجهة",
                icon=folium.Icon(
                    color="red",
                    icon="flag",
                    prefix="fa"
                )
            ).add_to(route_map)


            points = [
                [
                    coord[1],
                    coord[0]
                ]
                for coord
                in route["geometry"]["coordinates"]
            ]


            folium.PolyLine(
                points,
                color="#7657ff",
                weight=7,
                opacity=0.9,
                tooltip="🟣 المسار المقترح"
            ).add_to(route_map)


            for point in accessibility["elevators"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🛗 مصعد",
                    popup="🛗 مصعد مسجل.",
                    icon=folium.Icon(
                        color="blue",
                        icon="arrow-up",
                        prefix="fa"
                    )
                ).add_to(route_map)


            for point in accessibility["ramps"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🛝 منحدر",
                    popup="🛝 منحدر مسجل.",
                    icon=folium.Icon(
                        color="green",
                        icon="road",
                        prefix="fa"
                    )
                ).add_to(route_map)


            for point in accessibility["stairs"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🚫 درج",
                    popup="🚫 درج مسجل.",
                    icon=folium.Icon(
                        color="red",
                        icon="warning-sign",
                        prefix="glyphicon"
                    )
                ).add_to(route_map)


            for point in accessibility["wheelchair_yes"]:

                folium.CircleMarker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    radius=7,
                    color="#00a884",
                    fill=True,
                    fill_opacity=0.9,
                    tooltip="♿ وصول مهيأ",
                    popup="♿ وصول مهيأ مسجل."
                ).add_to(route_map)


            for point in accessibility["wheelchair_no"]:

                folium.CircleMarker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    radius=8,
                    color="#e5484d",
                    fill=True,
                    fill_opacity=0.9,
                    tooltip="⚠️ غير مهيأ",
                    popup="⚠️ غير مهيأ مسجل."
                ).add_to(route_map)


            st_folium(
                route_map,
                width=None,
                height=620,
                returned_objects=[],
                key="route_result_map"
            )


            if (
                score >= 80
                and not accessibility["stairs"]
            ):

                st.success(
                    "♿ المسار يبدو مناسبًا بدرجة جيدة حسب البيانات المتاحة."
                )

            elif accessibility["stairs"]:

                st.warning(
                    "⚠️ توجد درجات مسجلة قرب منطقة المسار."
                )

            else:

                st.info(
                    "بيانات الإتاحة محدودة."
                )


        else:

            st.error(
                "تعذر العثور على مسار."
            )


    # =====================================================
    # AI
    # =====================================================

    st.divider()

    st.header("✨ VerifyAI")


    if st.button(
        "✨ تحليل المكان بالذكاء الاصطناعي",
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


                building = (
                    st.session_state.selected_building
                )


                indoor = (
                    building.get(
                        "indoor",
                        {}
                    )
                    if building
                    else {}
                )


                prompt = f"""
أنت VerifyAI Access، مساعد متخصص في الوصول الشامل.

بيانات المبنى:

المداخل:
{len(indoor.get("entrances", []))}

المصاعد:
{len(indoor.get("elevators", []))}

الأماكن الداخلية:
{len(indoor.get("rooms", []))}

السلالم:
{len(indoor.get("stairs", []))}

دورات المياه:
{len(indoor.get("toilets", []))}

الطوابق:
{", ".join(indoor.get("levels", [])) if indoor.get("levels") else "غير متوفرة"}

القواعد:

- لا تخترع أي معلومات.
- لا تقل إن المكان مضمون 100%.
- إذا لم توجد بيانات داخلية كافية، وضح ذلك.
- اشرح للمستخدم العلامات المهمة.
- اذكر أن بيانات OpenStreetMap قد تكون ناقصة.
- أجب بالعربية بشكل واضح.
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
                    f"حدث خطأ: {error}"
                )


    if st.session_state.ai_answer:

        st.info(
            st.session_state.ai_answer
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "VerifyAI Access — Smart Accessibility Navigation"
)

st.caption(
    "الوصول للجميع."
)
