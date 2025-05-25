#!/usr/bin/env python3

import streamlit as st
import torch
from PIL import Image
import folium
from streamlit_folium import st_folium
import random
import time
import requests
from folium import Marker, Popup

# Page configuration
st.set_page_config(layout="wide")
st.title("Steel Will")

# Cache YOLOv5 model to avoid reloading every time
@st.cache_resource
def load_model():
    return torch.hub.load('yolov5', 'custom', path='best.pt', source='local')

model = load_model()

# Application tabs
tabs = st.tabs(["🧠 Drone camera preview", "🗺️ Hazard Map Dashboard"])

# ========== TAB 1: Image Detection ==========
with tabs[0]:
    st.header("YOLOv5 Threat Detection from Drone Imagery")
    uploaded_file = st.file_uploader("Upload an image for analysis", type=['jpg', 'jpeg', 'png'])

    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_container_width=True)

        with st.spinner("Detecting..."):
            with torch.no_grad():
                results = model(img)
                results.render()
                st.image(results.ims[0], caption="Detection Results", use_container_width=True)

# ========== TAB 2: Map Dashboard ==========
with tabs[1]:
    st.header("Hazard Risk Map – Subcarpathian Voivodeship")

    lat_min, lat_max = 49.0, 50.5
    lon_min, lon_max = 21.0, 23.5

    risk_threshold = st.sidebar.slider("Minimum Hazard Risk to Display (%)", 0, 100, 0, 5)
    if st.sidebar.button("🔁 Regenerate Hazard Risk Points"):
        st.session_state.random_points = None
        st.session_state.display_index = 0

    if "clicked_markers" not in st.session_state:
        st.session_state.clicked_markers = []

    def get_color(percent):
        if percent < 25:
            return 'green'
        elif percent < 60:
            return 'orange'
        else:
            return 'red'

    def generate_random_points(n):
        return [{
            "lat": random.uniform(lat_min, lat_max),
            "lon": random.uniform(lon_min, lon_max),
            "risk": round(random.uniform(1, 100), 1),
            "radius": random.uniform(4, 10),
            "wind_angle": random.uniform(0, 360)
        } for _ in range(n)]

    if "random_points" not in st.session_state or st.session_state.random_points is None:
        st.session_state.random_points = generate_random_points(random.randint(10, 30))
    if "display_index" not in st.session_state:
        st.session_state.display_index = 0

    m = folium.Map(location=[50.0413, 21.9990], zoom_start=8)

    for i, point in enumerate(st.session_state["random_points"]):
        if point["risk"] < risk_threshold:
            continue

        base_size = 8
        zoom_factor = max(1, m.options["zoom"] - 6)
        radius = point.get("radius", 8) * zoom_factor
        font_size = max(10, min(16, 2 + point['radius']))

        folium.Marker(
            location=[point["lat"], point["lon"]],
            icon=folium.DivIcon(html=f"""
                <div style='animation: fadeIn 0.6s ease-out {0.1 * i}s forwards; opacity: 0;'>
                    <div style='transform: rotate({point['wind_angle']}deg); margin-bottom: 2px; font-size: {font_size}px;'>
                        <div style='animation: wiggle 1.5s infinite;'>↑</div>
                    </div>
                    <div style='width: {radius}px; height: {radius}px; background-color: {get_color(point['risk'])}; border-radius: 50%; opacity: 0.7; display: flex; align-items: center; justify-content: center;'>
                        <div style='font-size: {font_size}px; font-weight: bold; text-shadow: 1px 1px 2px white;'>
                            {point['risk']}%
                        </div>
                    </div>
                </div>
                <style>
                    @keyframes fadeIn {{ from {{ opacity: 0; transform: scale(0.8); }} to {{ opacity: 1; transform: scale(1); }} }}
                    @keyframes wiggle {{ 0% {{ transform: rotate(0deg); }} 25% {{ transform: rotate(5deg); }} 50% {{ transform: rotate(0deg); }} 75% {{ transform: rotate(-5deg); }} 100% {{ transform: rotate(0deg); }} }}
                </style>
            """),
            interactive=False
        ).add_to(m)

    for coords, address in st.session_state.clicked_markers:
        Marker(location=coords, popup=Popup(address), tooltip="Clicked Location").add_to(m)

    legend_html = """
    <div style='position: fixed; bottom: 50px; left: 50px; width: 170px; height: 120px; background-color: white; z-index:9999; border:2px solid grey; padding: 10px; font-size: 14px;'>
        <b>Hazard Risk Levels</b><br>
        <i style='color:green;'>●</i> Low (<25%)<br>
        <i style='color:orange;'>●</i> Moderate (25–60%)<br>
        <i style='color:red;'>●</i> High (>60%)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    map_data = st_folium(m, width=1000, height=650, key="animated_map")

    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lng = map_data["last_clicked"]["lng"]
        coords = [clicked_lat, clicked_lng]

        url = f"https://nominatim.openstreetmap.org/reverse?lat={clicked_lat}&lon={clicked_lng}&format=json"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        address = response.json().get("display_name", "No data available") if response.status_code == 200 else "Error retrieving address"

        st.session_state.clicked_markers.append((coords, address))
        st.write(f"Last clicked coordinates: {clicked_lat}, {clicked_lng}")
        st.write(f"Address: {address}")

    if st.session_state.display_index + 1 < len(st.session_state.random_points):
        time.sleep(0.2)
        st.session_state.display_index += 1
        st.rerun()
