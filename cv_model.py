#!/usr/bin/env python3

import torch
from PIL import Image
import streamlit as st
import os

# Załaduj model
model = torch.hub.load('yolov5', 'custom', path='best.pt', source='local')

# Interfejs Streamlit
st.title("🔥 Detekcja pożarów/dymu z YOLOv5")

uploaded_file = st.file_uploader("Wgraj obraz do analizy", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    st.image(img, caption="Wgrany obraz", use_column_width=True)

    with st.spinner("Wykrywanie..."):
        results = model(img)
        results.render()
        st.image(results.ims[0], caption="Wyniki detekcji", use_column_width=True)
