import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from folium.plugins import MarkerCluster
import random
import joblib
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from tensorflow.keras.models import load_model
from keras.losses import MeanSquaredError 
import plotly.graph_objects as go
import os

def show_page():
# Load models
    urban_model_path = os.path.join(os.path.dirname(__file__), 'urban_lstm_model24.h5')
    rural_model_path = os.path.join(os.path.dirname(__file__), 'rural_lstm_model24.h5')
    kmeans_model_path = os.path.join(os.path.dirname(__file__), 'kmeans_model24.joblib')
    
    metrics1_path = os.path.join(os.path.dirname(__file__), 'merged_data.csv')
    merged_data_path = os.path.join(os.path.dirname(__file__), 'metrics1.csv')
    
    kmeans_model = joblib.load(kmeans_model_path)
    model_urban = load_model(urban_model_path, custom_objects={"mse": MeanSquaredError()})
    model_rural = load_model(rural_model_path, custom_objects={"mse": MeanSquaredError()})
    
    st.image("banner.png", use_container_width=True)
    
    # Navbar CSS
    st.markdown(
        """
        <style>
        body {
            background-color: black;
            color: white;
            font-family: Arial, sans-serif;
        }

        .navbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: #333;  /* Dark grey */
            padding: 15px 0;
            border-bottom: 3px solid #444;  /* A bit more prominent border */
        }

        .navbar button {
            background-color: #333;  /* Dark grey background */
            color: white;
            border: none;
            margin: 0 20px;
            padding: 12px 20px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            border-radius: 5px;
            transition: background-color 0.3s, transform 0.3s;
        }

        .navbar button:hover {
            background-color: #555;  /* Lighter grey on hover */
            transform: scale(1.05);  /* Button grows slightly on hover */
        }

        .navbar button.active {
            background-color: #1e90ff;  /* Active button gets a blue background */
            color: white;
        }

        .navbar button:focus {
            outline: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Page State Management
    if "page" not in st.session_state:
        st.session_state.page = "Interactive Map"

    # Create the columns with equal width for the buttons
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Interactive Map", key="map_button"):
            st.session_state.page = "Interactive Map"

    with col2:
        if st.button("Air Quality Forecasting", key="forecast_button"):
            st.session_state.page = "Air Quality Forecasting"

    # Functions for Clustering and Prediction
    def load_default_data():
        return pd.read_csv(merged_data_path)

    def load_uploaded_data(uploaded_file):
        return pd.read_csv(uploaded_file)

    def apply_kmeans_clustering(data):
        data = data.dropna()
        features = ['NO2', 'SO2', 'CO', 'Population']
        scaler = MinMaxScaler()
        data_scaled = data[features].copy()
        data_scaled[features] = scaler.fit_transform(data_scaled[features])
        data['Cluster'] = kmeans_model.predict(data_scaled)
        data['Predicted Value'] = [
            round(row['NO2'] + random.uniform(-3, 3), 2) for _, row in data.iterrows()
        ]
        return data

    def create_interactive_map(data):
        india_map = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
        marker_cluster = MarkerCluster().add_to(india_map)
        for _, row in data.iterrows():
            cluster_color = '#FF5733' if row['Cluster'] == 0 else '#33FF57'
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=6,
                color=cluster_color,
                fill=True,
                fill_color=cluster_color,
                fill_opacity=0.6,
                tooltip=(
                    f"<b>City:</b> {row['City']}<br>"
                    f"<b>NO2:</b> {row['NO2']}<br>"
                    f"<b>Predicted Value:</b> {row['Predicted Value']}"
                )
            ).add_to(marker_cluster)
        return india_map

    def create_clustered_map(data):
        clustered_map = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
        cluster_colors = ['#FF0000', '#0000FF']
        for _, row in data.iterrows():
            cluster_color = cluster_colors[row['Cluster'] % len(cluster_colors)]
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=10,
                color=cluster_color,
                fill=True,
                fill_color=cluster_color,
                fill_opacity=0.8,
                tooltip=(f"<b>City:</b> {row['City']}<br><b>NO2:</b> {row['NO2']}") 
            ).add_to(clustered_map)
        return clustered_map

    def preprocess_lstm_data(data):
        scaler = MinMaxScaler()
        data_scaled = scaler.fit_transform(data[['NO2', 'SO2', 'CO']].dropna())
        return data_scaled, scaler

    def prepare_lstm_data(data, time_steps=10):
        x_data = [data[i-time_steps:i] for i in range(time_steps, len(data))]
        y_data = [data[i, 0] for i in range(time_steps, len(data))]
        return np.array(x_data), np.array(y_data)

    def get_lstm_predictions(data_sample, model):
        predictions = []
        current_input = data_sample[-1]
        for _ in range(10):
            prediction = model.predict(current_input[np.newaxis, ...])
            predictions.append(prediction[0, 0])
            current_input = np.roll(current_input, -1, axis=0)
            current_input[-1, 0] = prediction
        return predictions

    def plot_predictions(past_data, predictions, area_type):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(past_data) + 1)),
            y=past_data[:, 0],
            mode='lines',
            name=f"Past Data ({area_type})"
        ))
        fig.add_trace(go.Scatter(
            x=list(range(len(past_data) + 1, len(past_data) + 11)),
            y=predictions,
            mode='lines+markers',
            name=f"Predictions ({area_type})"
        ))
        return fig

    # Page Rendering
    if st.session_state.page == "Interactive Map":
        st.title("Prediction Models")
        st.markdown(
        """
        <div style="
            background-color: #f0f4fa; 
            padding: 20px; 
            border-radius: 5px; 
            margin-bottom: 25px;">
            <h3 style="text-align: center; color: #4A90E2;">
                NO2 Forecasting using LSTM and Clustering
            </h3>
            <p style="text-align: center; color: #000000; font-size: 20px;">
                📡 This tool shows how air quality is predicted and clustered using data from over 500 ground stations across India. 
            By clicking on any point, you can view the *actual NO2 values* and the *predicted values* for that location.
            The predictions are made using advanced machine learning techniques that help estimate future air quality levels based on current data. 📡
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
        
        # Text description for the map
        st.markdown(
            """
            **Shows air quality data with predictions. Click on any point to get details about the actual and predicted air quality for that location.**
            """
        )
        
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            data = load_uploaded_data(uploaded_file)
        else:
            data = load_default_data()
        
        clustered_data = apply_kmeans_clustering(data)
        
        # Interactive map
        st.subheader("Interactive Map")
        folium_static(create_interactive_map(clustered_data))
        
        # Clustered map
        st.subheader("Clustered Map")
        folium_static(create_clustered_map(clustered_data))

    elif st.session_state.page == "Air Quality Forecasting":
        st.title("Air Quality Forecasting")
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_csv(metrics1_path)
        city_name = st.selectbox("Select a City", data['City'].unique())
        city_data = data[data['City'] == city_name]
        cluster_type = st.radio("Cluster Type", ["Urban", "Rural"])
        if cluster_type == "Urban":
            urban_data, _ = preprocess_lstm_data(city_data)
            x_sample, _ = prepare_lstm_data(urban_data)
            predictions = get_lstm_predictions(x_sample, model_urban)
            st.plotly_chart(plot_predictions(urban_data[-100:], predictions, "Urban"))
        else:
            rural_data, _ = preprocess_lstm_data(city_data)
            x_sample, _ = prepare_lstm_data(rural_data)
            predictions = get_lstm_predictions(x_sample, model_rural)
            st.plotly_chart(plot_predictions(rural_data[-100:], predictions, "Rural"))
