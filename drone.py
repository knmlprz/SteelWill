import streamlit as st
from streamlit_autorefresh import st_autorefresh
import folium
from streamlit_folium import st_folium
import time, math, random, os

st.set_page_config(layout="wide")
st_autorefresh(interval=2000, limit=None, key="autorefresh")
st.title("🛰️  Symulacja dronów + losowe zagrożenia w obszarze skanu")

# ───────── PARAMETRY ─────────
STEP_FRACTION   = 0.05
UPDATE_INTERVAL = 2
SCAN_RADIUS     = 300
HAZARD_PROB     = 0.06
EARTH_R         = 6_371_000
OFFSET_LAT      = 0.0025  # przesunięcie między dronami w stopniach szerokości geograficznej

# ───────── STATE ─────────
st.session_state.setdefault("num_drones", 3)

state_defaults = dict(
    clicks=[],
    drones=[],
    sim_active=False,
    selected_hazard_index=None,
    zoom_level=13,
)
for k, v in state_defaults.items():
    st.session_state.setdefault(k, v)

# ───────── OPISY & ZDJĘCIA ─────────
hazard_descriptions = [
    "Zgłoszenie: podejrzenie osoby poszkodowanej…",
    "Zgłoszenie: możliwe nieautoryzowane zgromadzenie…",
    "Zgłoszenie: potencjalny wypadek…",
    "Zgłoszenie: potencjalny rabunek…",
    "Zgłoszenie: potencjalny wypadek z wynikiem śmiertelnym…",
]
image_paths = ["images/patrol.jpg", "images/patrol2.jpg", "images/patrol3.jpg"]
image_pool  = [p for p in image_paths if os.path.exists(p)]

# ───────── FUNKCJE ─────────
def interp(a, b, f):
    return (a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f)

def rand_in_circle(lat, lon, r):
    d = r*math.sqrt(random.random()); t = random.uniform(0, 2*math.pi)
    dlat = d*math.cos(t)/EARTH_R; dlon = d*math.sin(t)/(EARTH_R*math.cos(math.radians(lat)))
    return lat+math.degrees(dlat), lon+math.degrees(dlon)

# ───────── UI: USTAL LICZBĘ DRONÓW ─────────
st.sidebar.number_input("Liczba dronów", min_value=1, max_value=10, value=st.session_state.num_drones, step=1, key="num_drones")

# ───────── WYBÓR PUNKTÓW ─────────
if len(st.session_state.clicks) < 2:
    st.subheader("Kliknij na mapie punkt startowy i docelowy")
    sel_map = folium.Map(location=[50.5714, 22.0522], zoom_start=st.session_state.zoom_level)
    for i,(la,lo) in enumerate(st.session_state.clicks):
        folium.Marker([la,lo], icon=folium.Icon(color="green" if i==0 else "red"), tooltip="Start" if i==0 else "Cel").add_to(sel_map)
    if (d:=st_folium(sel_map, height=700, width=800)) and d.get("last_clicked"):
        st.session_state.clicks.append((d["last_clicked"]["lat"], d["last_clicked"]["lng"]))
        st.rerun()

# ───────── INICJALIZACJA DRONÓW ─────────
if len(st.session_state.clicks) == 2 and not st.session_state.drones:
    base_start = st.session_state.clicks[0]
    for i in range(st.session_state.num_drones):
        offset = (i - (st.session_state.num_drones - 1)/2) * OFFSET_LAT
        start_pos = (base_start[0] + offset, base_start[1])
        st.session_state.drones.append(dict(
            pos=start_pos,
            points=[], hazards=[], hazards_pos=[], hazard_imgs=[], hazard_desc_id=[]
        ))

# ───────── SYMULACJA ─────────
if len(st.session_state.clicks) == 2:
    start, end = st.session_state.clicks

    if st.session_state.sim_active:
        updated = False
        for i, drone in enumerate(st.session_state.drones):
            if time.time() - st.session_state.get("last_update", 0) >= UPDATE_INTERVAL:
                frac = (len(drone["points"])+1)*STEP_FRACTION
                if frac < 1.0:
                    offset = (i - (st.session_state.num_drones - 1)/2) * OFFSET_LAT
                    start_offset = (start[0] + offset, start[1])
                    end_offset   = (end[0] + offset, end[1])
                    new = interp(start_offset, end_offset, frac)
                    drone["points"].append(new)
                    haz = random.random() < HAZARD_PROB
                    haz_pos = rand_in_circle(*new, SCAN_RADIUS) if haz else None
                    drone["hazards"].append(haz)
                    drone["hazards_pos"].append(haz_pos)
                    drone["hazard_desc_id"].append(random.randrange(len(hazard_descriptions)) if haz else None)
                    drone["hazard_imgs"].append(random.choice(image_pool) if haz and image_pool else None)
                    drone["pos"] = new
                    updated = True
        if updated:
            st.session_state.last_update = time.time()
            st.rerun()

    # ───────── MAPA ─────────
    center = ((start[0]+end[0])/2, (start[1]+end[1])/2)
    m = folium.Map(center, zoom_start=st.session_state.zoom_level)
    folium.PolyLine([start,end], color="blue").add_to(m)
    folium.Marker(start, icon=folium.Icon(color="green"), tooltip="Start").add_to(m)
    folium.Marker(end, icon=folium.Icon(color="red"), tooltip="Cel").add_to(m)

    for i, drone in enumerate(st.session_state.drones):
        for j, pt in enumerate(drone["points"]):
            folium.Circle(pt, SCAN_RADIUS, color="#3186cc", fill=True, fill_color="#3186cc", fill_opacity=.35).add_to(m)
            folium.CircleMarker(pt, radius=4, color="orange", fill=True).add_to(m)
            if drone["hazards"][j]:
                folium.Marker(drone["hazards_pos"][j], icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"), tooltip=f"Zagrożenie D{i+1}.{j+1}").add_to(m)
        folium.Marker(drone["pos"], icon=folium.Icon(color="blue", icon="plane", prefix="fa"), tooltip=f"Dron {i+1}").add_to(m)

    col_map, col_info = st.columns([3,1])

    # mapa
    with col_map:
        click = st_folium(m, height=700, width=1000)
        if click and click.get("last_object_clicked"):
            lat_c, lon_c = click["last_object_clicked"]["lat"], click["last_object_clicked"]["lng"]
            for d_idx, drone in enumerate(st.session_state.drones):
                for idx, pos in enumerate(drone["hazards_pos"]):
                    if pos and abs(pos[0]-lat_c)<1e-4 and abs(pos[1]-lon_c)<1e-4:
                        st.session_state.selected_hazard_index = (d_idx, idx)
                        break

    with col_info:
        st.subheader("Lista zagrożeń")
        for d_idx, drone in enumerate(st.session_state.drones):
            for idx, val in enumerate(drone["hazards"]):
                if val:
                    btn = f"Dron {d_idx+1} – Zagrożenie {idx+1}"
                    if st.button(btn, key=f"haz_btn_{d_idx}_{idx}"):
                        st.session_state.selected_hazard_index = (d_idx, idx)

        st.markdown("---")
        st.subheader("🚨 Szczegóły")
        sel = st.session_state.selected_hazard_index
        if sel:
            d_idx, h_idx = sel
            drone = st.session_state.drones[d_idx]
            lat, lon = drone["hazards_pos"][h_idx]
            desc_id = drone["hazard_desc_id"][h_idx]
            st.write(f"**X:** {lat:.5f}")
            st.write(f"**Y:** {lon:.5f}")
            st.markdown(f"**Opis:** {hazard_descriptions[desc_id]}")
            if drone["hazard_imgs"][h_idx]:
                st.image(drone["hazard_imgs"][h_idx], caption="Zdjęcie z patrolu", use_container_width=True)

    # ───────── PANEL BOCZNY ─────────
    st.sidebar.write(f"**Start:** {start[0]:.5f}, {start[1]:.5f}")
    st.sidebar.write(f"**Cel:**  {end[0]:.5f}, {end[1]:.5f}")
    st.sidebar.write(f"**Dronów:** {len(st.session_state.drones)}")
    st.sidebar.write(f"**Skanów razem:** {sum(len(d['points']) for d in st.session_state.drones)}")
    st.sidebar.write(f"**Zagrożeń:** {sum(sum(d['hazards']) for d in st.session_state.drones)}")
    st.sidebar.markdown("---")
    if st.session_state.sim_active:
        if st.sidebar.button("⏸️ Pauza"):
            st.session_state.sim_active = False; st.rerun()
    else:
        if st.sidebar.button("▶️ Start"):
            st.session_state.sim_active = True; st.rerun()

# ───────── RESET ─────────
if st.sidebar.button("🔄 Reset"):
    for k,v in state_defaults.items():
        st.session_state[k] = v if not isinstance(v, list) else []
    st.session_state.drones = []
    st.rerun()
