#!/usr/bin/env python3

import streamlit as st
import folium
from streamlit_folium import st_folium
import random
import time
import requests
from folium import Marker, Popup

st.set_page_config(layout="wide")
st.title("Hazard Risk Map in Subcarpathian Voivodeship")

# Region bounding box
lat_min, lat_max = 49.0, 50.5
lon_min, lon_max = 21.0, 23.5

# Sidebar controls
risk_threshold = st.sidebar.slider("Minimum Fire Risk to Display (%)", 0, 100, 0, 5)
if st.sidebar.button("🔁 Regenerate Fire Risk Points"):
    st.session_state.random_points = None
    st.session_state.display_index = 0

# Initialize session state for clicked markers
if "clicked_markers" not in st.session_state:
    st.session_state.clicked_markers = []

# Get fire risk color
def get_color(percent):
    if percent < 25:
        return 'green'
    elif percent < 60:
        return 'orange'
    else:
        return 'red'

# Generate random fire risk points
def generate_random_points(n):
    points = []
    for _ in range(n):
        lat = random.uniform(lat_min, lat_max)
        lon = random.uniform(lon_min, lon_max)
        risk = round(random.uniform(1, 100), 1)
        radius = random.uniform(4, 10)  # Zmniejszony zakres rozmiarów
        wind_angle = random.uniform(0, 360)
        points.append({
            "lat": lat,
            "lon": lon,
            "risk": risk,
            "radius": radius,
            "wind_angle": wind_angle
        })
    return points

# Initialize session state for fire points
if "random_points" not in st.session_state or st.session_state.random_points is None:
    st.session_state.random_points = generate_random_points(random.randint(5, 30))
if "display_index" not in st.session_state:
    st.session_state.display_index = 0

# Create folium map
m = folium.Map(location=[50.0413, 21.9990], zoom_start=8)

# Draw animated fire points up to current index
visible_points = st.session_state.random_points[:st.session_state.display_index + 1]

for i, point in enumerate(st.session_state["random_points"]):
    if point["risk"] < risk_threshold:
        continue

    # Adjusted sizes based on zoom level
    base_size = 8  # Bazowy rozmiar dla zoom=8
    zoom_factor = max(1, m.options["zoom"] - 6)  # Współczynnik skalowania

    radius = point.get("radius", 8) * zoom_factor
    font_size = max(10, min(16, 2 + point['radius']))  # Ograniczony rozmiar czcionki

    # Create marker with non-interactive icon
    folium.Marker(
        location=[point["lat"], point["lon"]],
        icon=folium.DivIcon(
            html=f"""
                <div style="
                    position: relative;
                    animation: fadeIn 0.6s ease-out forwards;
                    animation-delay: {0.1 * i}s;
                    opacity: 0;
                    transform: translate(-50%, -50%);
                    text-align: center;
                    font-family: sans-serif;
                    line-height: 1;
                    pointer-events: none;
                ">
                    <!-- Wind Arrow -->
                    <div style="
                        transform: rotate({point['wind_angle']}deg);
                        transform-origin: center;
                        margin-bottom: 2px;
                        font-size: {font_size}px;
                    ">
                        <div style="
                            display: inline-block;
                            animation: wiggle 1.5s infinite ease-in-out;
                        ">↑</div>
                    </div>

                    <!-- Circle Background -->
                    <div style="
                        width: {radius}px;
                        height: {radius}px;
                        background-color: {get_color(point['risk'])};
                        border-radius: 50%;
                        opacity: 0.7;
                        margin: 0 auto;
                        box-shadow: 0 0 5px rgba(0,0,0,0.2);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <!-- Emoji + Percentage Label -->
                        <div style="
                            font-size: {font_size}px;
                            font-weight: bold;
                            text-shadow: 1px 1px 2px white;
                            line-height: 1;
                        ">
                            {point['risk']}%
                        </div>
                    </div>
                </div>

                <style>
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: scale(0.8); }}
                    to {{ opacity: 1; transform: scale(1); }}
                }}
                @keyframes wiggle {{
                    0% {{ transform: rotate(0deg); }}
                    25% {{ transform: rotate(5deg); }}
                    50% {{ transform: rotate(0deg); }}
                    75% {{ transform: rotate(-5deg); }}
                    100% {{ transform: rotate(0deg); }}
                }}
                </style>
            """
        ),
        interactive=False
    ).add_to(m)

# Add user clicked markers
for coords, address in st.session_state.clicked_markers:
    Marker(
        location=coords,
        popup=Popup(address, parse_html=False),
        tooltip="Kliknięte miejsce",
    ).add_to(m)

# Add legend
legend_html = """
<div style="
    position: fixed;
    bottom: 50px; left: 50px; width: 170px; height: 120px;
    background-color: white; z-index:9999;
    border:2px solid grey; padding: 10px; font-size: 14px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
">
<b>🔥 Fire Risk Levels</b><br>
<i style="color:green;">●</i> Low (&lt;25%)<br>
<i style="color:orange;">●</i> Moderate (25–60%)<br>
<i style="color:red;">●</i> High (&gt;60%)<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# Display map
map_data = st_folium(m, width=1000, height=650, key="animated_map")

# Handle map click
if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lng = map_data["last_clicked"]["lng"]
    coords = [clicked_lat, clicked_lng]

    # Reverse geocoding
    url = f"https://nominatim.openstreetmap.org/reverse?lat={clicked_lat}&lon={clicked_lng}&format=json"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code == 200:
        data = response.json()
        address = data.get("display_name", "Brak danych")
    else:
        address = "Błąd pobierania adresu"

    # Add new marker to the list
    st.session_state.clicked_markers.append((coords, address))

    # Display click info
    st.write(f"Ostatnio kliknięte współrzędne: {clicked_lat}, {clicked_lng}")
    st.write(f"Adres: {address}")

# Animation control
if st.session_state.display_index + 1 < len(st.session_state.random_points):
    time.sleep(0.2)  # wait before showing the next point
    st.session_state.display_index += 1
    st.rerun()
