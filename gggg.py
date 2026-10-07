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

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/5.0"
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
    "start_point": None,
    "destination_point": None,
    "selection_mode": None,
    "selected_building": None,
    "selected_floor": "كل الطوابق",
    "indoor_mode": False,
    "indoor_destination": None,
    "route_result": None,
    "ai_answer": None,
    "map_key": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# GEOCODING
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

        return data.get(
            "display_name",
            "الموقع المحدد"
        )

    except Exception:
        return "الموقع المحدد"


# =========================================================
# DISTANCE
# =========================================================

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
# POINT IN POLYGON
# =========================================================

def point_in_polygon(lat, lon, polygon):

    if len(polygon) < 3:
        return False

    inside = False

    j = len(polygon) - 1

    for i in range(len(polygon)):

        xi = polygon[i][1]
        yi = polygon[i][0]

        xj = polygon[j][1]
        yj = polygon[j][0]

        intersects = (
            ((yi > lat) != (yj > lat))
            and (
                lon
                < (
                    (xj - xi)
                    * (lat - yi)
                    / ((yj - yi) or 1e-12)
                    + xi
                )
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


# =========================================================
# OPENABLE BUILDINGS
# =========================================================

def get_openable_buildings(
    lat,
    lon,
    radius=1800
):

    query = f"""
    [out:json][timeout:55];

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

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:
        return []

    buildings = []
    indoor_points = []

    # -----------------------------------------------------
    # COLLECT BUILDINGS
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

        center = item.get(
            "center"
        )

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
    # COLLECT INDOOR ELEMENTS
    # -----------------------------------------------------

    for item in elements:

        tags = item.get(
            "tags",
            {}
        )

        has_indoor_tag = (
            tags.get("indoor")
            or tags.get("room")
            or tags.get("level")
            or tags.get("entrance")
            or tags.get("elevator") == "yes"
            or tags.get("highway") == "elevator"
        )

        if not has_indoor_tag:
            continue

        if "lat" in item:

            point_lat = float(
                item["lat"]
            )

            point_lon = float(
                item["lon"]
            )

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
    # MATCH INDOOR DATA TO BUILDINGS
    # -----------------------------------------------------

    openable = []

    for building in buildings:

        building_geometry = building.get(
            "geometry",
            []
        )

        polygon = [
            [
                p["lat"],
                p["lon"]
            ]
            for p in building_geometry
        ]

        has_indoor = False

        for point in indoor_points:

            # First choice: exact polygon containment
            if len(polygon) >= 3:

                if point_in_polygon(
                    point["lat"],
                    point["lon"],
                    polygon
                ):

                    has_indoor = True
                    break

            # Fallback for buildings without polygon geometry
            nearby = distance_meters(
                building["lat"],
                building["lon"],
                point["lat"],
                point["lon"]
            )

            if nearby <= 60:

                has_indoor = True
                break

        if has_indoor:

            openable.append(
                building
            )

    # Limit visible markers to prevent overload
    return openable[:100]


# =========================================================
# FIND SELECTED BUILDING
# =========================================================

def get_building_at_point(
    lat,
    lon,
    radius=120
):

    query = f"""
    [out:json][timeout:30];

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
            timeout=40
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

        center = item.get(
            "center"
        )

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

        distance = distance_meters(
            lat,
            lon,
            center_lat,
            center_lon
        )

        if distance < best_distance:

            best_distance = distance

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
    radius=300
):

    query = f"""
    [out:json][timeout:45];

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
            timeout=60
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

            lat = float(
                element["lat"]
            )

            lon = float(
                element["lon"]
            )

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

        if tags.get("level"):

            for level in str(
                tags["level"]
            ).split(";"):

                result["levels"].add(
                    level.strip()
                )

        if "entrance" in tags:

            result["entrances"].append(
                point
            )

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
            or tags.get("indoor") == "elevator"
        ):

            result["elevators"].append(
                point
            )

        if (
            tags.get("highway") == "steps"
            or tags.get("indoor") == "stairs"
        ):

            result["stairs"].append(
                point
            )

        if (
            tags.get("room")
            or tags.get("indoor") == "room"
        ):

            result["rooms"].append(
                point
            )

        if tags.get(
            "amenity"
        ) == "toilets":

            result["toilets"].append(
                point
            )

        if (
            tags.get("indoor") == "corridor"
            or tags.get("highway") == "corridor"
        ):

            result["corridors"].append(
                point
            )

        if tags.get("indoor"):

            if tags.get("indoor") not in {
                "room",
                "corridor",
                "stairs",
                "elevator"
            }:

                result["other"].append(
                    point
                )

    def floor_sort(value):

        try:
            return float(value)
        except Exception:
            return 999

    result["levels"] = sorted(
        list(result["levels"]),
        key=floor_sort
    )

    return result


# =========================================================
# OUTDOOR ACCESSIBILITY
# =========================================================

def get_accessibility_data(
    lat,
    lon,
    radius=1800
):

    query = f"""
    [out:json][timeout:35];

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

            lat2 = float(
                element["lat"]
            )

            lon2 = float(
                element["lon"]
            )

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

        if tags.get(
            "highway"
        ) == "steps":

            result["stairs"].append(point)

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
        ):

            result["elevators"].append(point)

        if tags.get(
            "ramp"
        ) == "yes":

            result["ramps"].append(point)

        if tags.get(
            "wheelchair"
        ) == "yes":

            result["wheelchair_yes"].append(
                point
            )

        if tags.get(
            "wheelchair"
        ) == "no":

            result["wheelchair_no"].append(
                point
            )

        if (
            tags.get("amenity") == "toilets"
            and tags.get("wheelchair") == "yes"
        ):

            result["toilets"].append(
                point
            )

        if (
            tags.get("amenity") == "parking"
            and tags.get("wheelchair") == "yes"
        ):

            result["parking"].append(
                point
            )

        if (
            tags.get("entrance")
            and tags.get("wheelchair") == "yes"
        ):

            result["entrances"].append(
                point
            )

    return result


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

        for stair in accessibility[
            "stairs"
        ]:

            if distance_meters(
                lat,
                lon,
                stair["lat"],
                stair["lon"]
            ) < 80:

                score -= 15

        for bad in accessibility[
            "wheelchair_no"
        ]:

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
# POLYGON
# =========================================================

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

        if "lat" in point
        and "lon" in point
    ]

    if len(points) >= 3:

        folium.Polygon(
            points,
            **kwargs
        ).add_to(
            map_object
        )


# =========================================================
# HEADER
# =========================================================

st.title(
    "♿ VerifyAI Access"
)

st.caption(
    "خريطة وصول ذكية — اختر الأماكن والمباني بالضغط على الخريطة."
)


# =========================================================
# ACTION BUTTONS
# =========================================================

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
        "🏢 فتح مبنى",
        use_container_width=True
    ):

        st.session_state.selection_mode = "building"


with c4:

    if st.button(
        "🗑️ مسح",
        use_container_width=True
    ):

        st.session_state.start_point = None
        st.session_state.destination_point = None
        st.session_state.selection_mode = None
        st.session_state.selected_building = None
        st.session_state.selected_floor = "كل الطوابق"
        st.session_state.indoor_mode = False
        st.session_state.indoor_destination = None
        st.session_state.route_result = None
        st.session_state.ai_answer = None
        st.session_state.map_key += 1

        st.rerun()


# =========================================================
# CURRENT MODE
# =========================================================

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
        "🏢 اضغط داخل مبنى أو على علامة 🏢 لفتحه."
    )

else:

    st.info(
        "اختر وضعًا من الأعلى ثم اضغط على الخريطة."
    )


# =========================================================
# OUTDOOR MAP
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

    # Jeddah
    map_center = [
        21.5433,
        39.1728
    ]


outdoor_map = folium.Map(
    location=map_center,
    zoom_start=13,
    tiles="OpenStreetMap"
)


# =========================================================
# OPENABLE BUILDING MARKERS
# =========================================================

openable_buildings = get_openable_buildings(
    map_center[0],
    map_center[1],
    radius=1800
)


for building in openable_buildings:

    building_tags = building.get(
        "tags",
        {}
    )

    building_name = (
        building_tags.get("name")
        or building_tags.get("official_name")
        or "مبنى يدعم الخريطة الداخلية"
    )

    popup_text = (
        "<b>🏢 مبنى قابل للفتح</b><br>"
        + html.escape(building_name)
        + "<br><br>"
        "توجد بيانات داخلية لهذا المبنى.<br>"
        "فعّل «فتح مبنى» ثم اضغط عليه."
    )

    folium.Marker(
        [
            building["lat"],
            building["lon"]
        ],
        tooltip="🏢 مبنى قابل للفتح",
        popup=folium.Popup(
            popup_text,
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


# =========================================================
# SELECTED START
# =========================================================

if st.session_state.start_point:

    point = st.session_state.start_point

    folium.Marker(
        [
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


# =========================================================
# SELECTED DESTINATION
# =========================================================

if st.session_state.destination_point:

    point = st.session_state.destination_point

    folium.Marker(
        [
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


# =========================================================
# SELECTED BUILDING HIGHLIGHT
# =========================================================

if (
    st.session_state.selected_building
    and st.session_state.selected_building.get(
        "geometry"
    )
):

    draw_polygon(
        outdoor_map,
        st.session_state.selected_building[
            "geometry"
        ],
        color="#7657ff",
        fill=True,
        fill_opacity=0.22,
        weight=4,
        tooltip="🏢 المبنى المحدد"
    )


# =========================================================
# SHOW MAP
# =========================================================

map_data = st_folium(
    outdoor_map,
    width=None,
    height=620,
    returned_objects=[
        "last_clicked",
        "last_object_clicked"
    ],
    key=f"outdoor_map_{st.session_state.map_key}"
)


# =========================================================
# HANDLE MAP CLICK
# =========================================================

clicked = None

if map_data:

    clicked = map_data.get(
        "last_clicked"
    )


if clicked and st.session_state.selection_mode:

    lat = float(
        clicked["lat"]
    )

    lon = float(
        clicked["lng"]
    )


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

        st.rerun()


    # BUILDING

    elif st.session_state.selection_mode == "building":

        with st.spinner(
            "جاري فتح المبنى..."
        ):

            building = get_building_at_point(
                lat,
                lon
            )

            if building:

                indoor_elements = get_indoor_data(
                    building["center"]["lat"],
                    building["center"]["lon"]
                )

                building["indoor"] = parse_indoor_data(
                    indoor_elements
                )

                has_indoor_data = (
                    len(
                        building["indoor"]["levels"]
                    ) > 0
                    or len(
                        building["indoor"]["rooms"]
                    ) > 0
                    or len(
                        building["indoor"]["elevators"]
                    ) > 0
                    or len(
                        building["indoor"]["entrances"]
                    ) > 0
                )

                if has_indoor_data:

                    st.session_state.selected_building = building
                    st.session_state.indoor_mode = True

                    levels = building[
                        "indoor"
                    ]["levels"]

                    if levels:
                        st.session_state.selected_floor = levels[0]
                    else:
                        st.session_state.selected_floor = "كل الطوابق"

                else:

                    st.warning(
                        "هذا المبنى موجود على الخريطة، "
                        "لكن لا توجد له بيانات داخلية كافية لفتحه حاليًا."
                    )

            else:

                st.warning(
                    "لم يتم العثور على مبنى في هذه النقطة."
                )

        st.session_state.selection_mode = None
        st.rerun()


# =========================================================
# LOCATIONS
# =========================================================

st.subheader(
    "📌 المواقع المحددة"
)

left, right = st.columns(2)

with left:

    if st.session_state.start_point:

        st.success(
            "🟢 البداية\n\n"
            + st.session_state.start_point[
                "name"
            ]
        )

    else:

        st.info(
            "لم يتم اختيار البداية."
        )


with right:

    if st.session_state.destination_point:

        st.error(
            "🔴 الوجهة\n\n"
            + st.session_state.destination_point[
                "name"
            ]
        )

    else:

        st.info(
            "لم يتم اختيار الوجهة."
        )


# =========================================================
# BUILDING PANEL
# =========================================================

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

    building_name = (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("building")
        or "المبنى"
    )

    st.divider()

    st.header(
        f"🏢 {building_name}"
    )

    st.success(
        "هذا المبنى عليه علامة 🏢 في الخريطة لأنه يحتوي على بيانات داخلية."
    )

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        st.metric(
            "🚪 المداخل",
            len(indoor["entrances"])
        )

    with b2:
        st.metric(
            "🛗 المصاعد",
            len(indoor["elevators"])
        )

    with b3:
        st.metric(
            "📍 الأماكن الداخلية",
            len(indoor["rooms"])
        )

    with b4:
        st.metric(
            "🪜 السلالم",
            len(indoor["stairs"])
        )

    levels = indoor.get(
        "levels",
        []
    )

    if levels:

        floor_options = [
            "كل الطوابق"
        ] + levels

    else:

        floor_options = [
            "كل الطوابق"
        ]

    selected_floor = st.selectbox(
        "🏷️ اختر الطابق",
        floor_options,
        index=(
            floor_options.index(
                st.session_state.selected_floor
            )
            if st.session_state.selected_floor in floor_options
            else 0
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


# =========================================================
# INDOOR MAP
# =========================================================

if building and st.session_state.indoor_mode:

    indoor = building["indoor"]
    selected_floor = st.session_state.selected_floor

    st.divider()

    st.header(
        "🏢 الخريطة الداخلية"
    )

    if selected_floor == "كل الطوابق":

        st.caption(
            "عرض جميع البيانات الداخلية المتوفرة."
        )

    else:

        st.caption(
            f"الطابق المحدد: {selected_floor}"
        )

    indoor_map = folium.Map(
        location=[
            building["center"]["lat"],
            building["center"]["lon"]
        ],
        zoom_start=19,
        tiles="OpenStreetMap"
    )

    # BUILDING
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

    def floor_visible(point):

        if selected_floor == "كل الطوابق":
            return True

        point_level = (
            point.get("tags", {})
            .get("level")
        )

        if not point_level:
            return True

        values = str(
            point_level
        ).split(";")

        return str(selected_floor) in [
            str(v).strip()
            for v in values
        ]

    # -----------------------------------------------------
    # ENTRANCES
    # -----------------------------------------------------

    for point in indoor["entrances"]:

        if not floor_visible(point):
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

    # -----------------------------------------------------
    # ELEVATORS
    # -----------------------------------------------------

    for point in indoor["elevators"]:

        if not floor_visible(point):
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

    # -----------------------------------------------------
    # STAIRS
    # -----------------------------------------------------

    for point in indoor["stairs"]:

        if not floor_visible(point):
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

    # -----------------------------------------------------
    # ROOMS
    # -----------------------------------------------------

    for point in indoor["rooms"]:

        if not floor_visible(point):
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

    # -----------------------------------------------------
    # TOILETS
    # -----------------------------------------------------

    for point in indoor["toilets"]:

        if not floor_visible(point):
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

    # -----------------------------------------------------
    # SHOW INDOOR MAP
    # -----------------------------------------------------

    indoor_click = st_folium(
        indoor_map,
        width=None,
        height=650,
        returned_objects=[
            "last_clicked"
        ],
        key=f"indoor_map_{st.session_state.map_key}"
    )

    if (
        indoor_click
        and indoor_click.get("last_clicked")
    ):

        clicked_inside = indoor_click[
            "last_clicked"
        ]

        st.session_state.indoor_destination = {
            "lat": float(
                clicked_inside["lat"]
            ),
            "lon": float(
                clicked_inside["lng"]
            ),
            "level": selected_floor
        }

        st.success(
            "📍 تم اختيار نقطة داخل المبنى."
        )

    # -----------------------------------------------------
    # INDOOR SUMMARY
    # -----------------------------------------------------

    st.subheader(
        "📋 تفاصيل المبنى"
    )

    if indoor["levels"]:

        st.write(
            "**الطوابق الموجودة:** "
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
        "المعلومات الداخلية هنا تعتمد على البيانات المتاحة فعليًا "
        "في OpenStreetMap. المباني التي لا تحتوي بيانات داخلية "
        "لن يتم اختراع غرف أو طوابق لها."
    )


# =========================================================
# OUTDOOR ROUTE
# =========================================================

if (
    st.session_state.start_point
    and st.session_state.destination_point
):

    st.divider()

    if st.button(
        "🚀 احسب أفضل مسار خارجي",
        use_container_width=True
    ):

        with st.spinner(
            "جاري تحليل المسارات..."
        ):

            start = (
                st.session_state.start_point
            )

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

                best_score, best_route = (
                    scored_routes[0]
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


# =========================================================
# ROUTE RESULT
# =========================================================

route_result = (
    st.session_state.route_result
)

if route_result:

    st.divider()

    st.header(
        "🚶 المسار المقترح"
    )

    route = route_result["route"]

    accessibility = (
        route_result["accessibility"]
    )

    route_score = route_result["score"]

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

        with c1:
            st.metric(
                "♿ مؤشر الإتاحة",
                f"{route_score}%"
            )

        with c2:
            st.metric(
                "🛣️ المسافة",
                f"{distance_km:.1f} كم"
            )

        with c3:
            st.metric(
                "⏱️ الوقت",
                f"{minutes} دقيقة"
            )

        with c4:
            st.metric(
                "🛗 المصاعد",
                len(
                    accessibility[
                        "elevators"
                    ]
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
            popup="🟢 نقطة البداية",
            icon=folium.Icon(
                color="green",
                icon="play",
                prefix="fa"
            )
        ).add_to(
            route_map
        )

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
        ).add_to(
            route_map
        )

        route_points = [
            [
                coordinate[1],
                coordinate[0]
            ]
            for coordinate
            in route["geometry"]["coordinates"]
        ]

        folium.PolyLine(
            route_points,
            color="#7657ff",
            weight=7,
            opacity=0.9,
            tooltip="🟣 المسار المقترح"
        ).add_to(
            route_map
        )

        for point in accessibility[
            "elevators"
        ]:

            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🛗 مصعد",
                popup="🛗 مصعد مسجل على الخريطة.",
                icon=folium.Icon(
                    color="blue",
                    icon="arrow-up",
                    prefix="fa"
                )
            ).add_to(
                route_map
            )

        for point in accessibility[
            "ramps"
        ]:

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
            ).add_to(
                route_map
            )

        for point in accessibility[
            "stairs"
        ]:

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
            ).add_to(
                route_map
            )

        for point in accessibility[
            "wheelchair_yes"
        ]:

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
            ).add_to(
                route_map
            )

        for point in accessibility[
            "wheelchair_no"
        ]:

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
                popup="⚠️ موقع مسجل كغير مهيأ."
            ).add_to(
                route_map
            )

        st_folium(
            route_map,
            width=None,
            height=620,
            returned_objects=[]
        )

        with st.expander(
            "📍 معنى العلامات"
        ):

            st.write(
                "🏢 **مبنى قابل للفتح** — توجد له بيانات داخلية."
            )

            st.write(
                "🟣 **المسار المقترح** — الطريق الذي اختاره النظام."
            )

            st.write(
                "🟢 **البداية** — نقطة الانطلاق."
            )

            st.write(
                "🔴 **الوجهة** — نقطة الوصول."
            )

            st.write(
                "🛗 **مصعد** — مصعد مسجل."
            )

            st.write(
                "🛝 **منحدر** — منحدر مسجل."
            )

            st.write(
                "♿ **وصول مهيأ** — موقع مسجل كمتاح."
            )

            st.write(
                "🚫 **درج** — درج مسجل."
            )

            st.write(
                "⚠️ **غير مهيأ** — موقع مسجل كغير مناسب."
            )

        if (
            route_score >= 80
            and not accessibility["stairs"]
        ):

            st.success(
                "♿ المسار يبدو مناسبًا بدرجة جيدة حسب البيانات المتاحة."
            )

        elif accessibility["stairs"]:

            st.warning(
                "⚠️ توجد درجات مسجلة قرب منطقة المسار. "
                "راجع العلامات على الخريطة."
            )

        else:

            st.info(
                "بيانات الإتاحة محدودة؛ عدم وجود علامة "
                "لا يعني أن المكان مهيأ."
            )

    else:

        st.error(
            "تعذر العثور على مسار للمشاة بين النقطتين."
        )


# =========================================================
# AI
# =========================================================

st.divider()

st.header(
    "✨ VerifyAI"
)

if st.button(
    "✨ تحليل المكان والمسار",
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

            route_info = (
                st.session_state.route_result
            )

            prompt = f"""
أنت VerifyAI Access، مساعد متخصص في الوصول الشامل.

المعلومات المتاحة:

هل يوجد مسار خارجي:
{bool(route_info and route_info.get("route"))}

معلومات المبنى:
المداخل = {len(indoor.get("entrances", []))}
المصاعد = {len(indoor.get("elevators", []))}
الأماكن الداخلية = {len(indoor.get("rooms", []))}
السلالم = {len(indoor.get("stairs", []))}
دورات المياه = {len(indoor.get("toilets", []))}
الطوابق = {", ".join(indoor.get("levels", [])) if indoor.get("levels") else "غير متوفرة"}

القواعد:
- لا تخترع أي معلومة.
- لا تقل إن الوصول مضمون 100%.
- إذا لم توجد بيانات داخلية كافية فقل ذلك.
- اشرح معنى العلامات المهمة.
- اذكر أن البيانات قد تكون ناقصة أو قديمة.
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

st.markdown("---")

st.caption(
    "VerifyAI Access — Smart Accessibility Navigation"
)

st.caption(
    "الوصول للجميع."
)
