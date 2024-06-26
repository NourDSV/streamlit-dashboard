import streamlit as st
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
import json
from folium.features import GeoJsonTooltip
import branca
from folium.plugins import TagFilterButton
from folium.plugins import TimeSliderChoropleth
from folium.plugins import Draw
from folium.plugins import GroupedLayerControl
from folium.plugins import Search
from branca.colormap import linear

APP_TITLE= "Shipment Profile"

@st.cache_data
def read_excel(path):
        return pd.read_excel(path)

@st.cache_data
def read_geojson(path):
        return gpd.read_file(path)

levl0=read_geojson("europe.geojson")
levl2=read_geojson("NUTS_2_Q2.geojson")
levl1=read_geojson("NUTS_1_Q1.geojson")
levl3=read_geojson("NUTS_3_Q1.geojson")

shipement_profil=read_excel("MATRICE shipment profile.xlsx")
zip_code=read_excel("zipcode_nuts with uk instead of gb.xlsx")
zip_code_for_tag0=read_excel("zip code for tag 0.xlsx")
dsv=read_excel("DSV Branches.xlsx")

levl3.drop_duplicates(subset="NUTS_ID", keep="first", inplace=True)

shipement_profil=shipement_profil.groupby(["ZC from" , "ZC to"],as_index=False)['PW DSV'].sum()

shipement_profil=pd.merge(shipement_profil,zip_code,on='ZC to',how="left")



st.title("Shippment profile")

st.sidebar.title("Select filters")

selected_map = st.selectbox("Select Nuts Level", ["Nuts 0 ", "Nuts 1 ","Nuts 2 ","Nuts 3 "])
def map(shipement_profil,data,level):

    shipement_profil=shipement_profil.groupby(["ZC from" , "ZC to"],as_index=False)['PW DSV'].sum()
    shipement_profil=pd.merge(shipement_profil,zip_code,on='ZC to',how="left")
    shipement_profil=shipement_profil.groupby([level],as_index=False)["PW DSV"].sum()

    m= folium.Map(location=[54.5260,15.2551],zoom_start=4)

    merge=pd.merge(data,shipement_profil,right_on=level ,left_on="NUTS_ID",how="right")

    folium.Choropleth(
        geo_data=merge,
        name="choropleth",
        data=merge,
        columns=[level,"PW DSV"],
        key_on="properties.NUTS_ID",
        fill_color='OrRd',
        fill_opacity=0.7,
        legend=True,
        highlight=True, 
        ).add_to(m)

    folium.features.GeoJson(
                    data=merge,
                    name='test',
                    smooth_factor=2,
                    style_function=lambda x: {'color':'black','fillColor':'transparent','weight':0.5},
                    tooltip=folium.features.GeoJsonTooltip(
                        fields=["NUTS_NAME","PW DSV"],
                        aliases=["To : " , "Value: "], 
                        localize=True,
                        sticky=False,
                        labels=True,
                        style="""
                            background-color: #F0EFEF;
                            border: 2px solid black;
                            border-radius: 3px;
                            box-shadow: 3px;
                        """,
                        max_width=800,),
                            highlight_function=lambda x: {'weight':3,'fillColor':'grey'},
                        ).add_to(m) 
    
    return(folium_static(m))
    
if selected_map=="Nuts 1" :
       map(shipement_profil,levl1,"NUTS1")





