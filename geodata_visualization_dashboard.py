import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
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
from streamlit_folium import folium_static
from folium.plugins import Fullscreen
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import base64

levl0=gpd.read_file("europe.geojson")
levl2=gpd.read_file("NUTS_2_Q2.geojson")
levl1=gpd.read_file("NUTS_1_Q1.geojson")
levl3=gpd.read_file("NUTS_3_Q1.geojson")
zip_code=pd.read_excel("zipcode_nuts with uk instead of gb.xlsx")
dsv=pd.read_excel("DSV Branches.xlsx")


st.set_page_config(layout='wide')

# Function to load data
def load_data():
    uploaded_file = st.session_state.get('uploaded_file', None)
    if uploaded_file is not None:
        data = pd.read_excel(uploaded_file)
    else:
        data = pd.DataFrame()
    return data

# Page for uploading and viewing the Excel file
def upload_view_page():
    st.title('Upload your data')
    uploaded_file = st.file_uploader("Put your shipment profile here", type=['xlsx'])
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        data = pd.read_excel(uploaded_file)
        data['Date'] = pd.to_datetime(data['Date'])
        st.write(data)

def summary_page():
        st.title("Shipment summary")
        data = load_data()

        nb_grp=(data["Product"]=="GRP").sum()
        nb_ltl=(data["Product"]=="LTL").sum()
        nb_ftl=(data["Product"]=="FTL").sum()
        nb_total= len(data)

        kg_grp=data["kg"][data["Product"]=="GRP"].sum()
        kg_ltl=data["kg"][data["Product"]=="LTL"].sum()
        kg_ftl=data["kg"][data["Product"]=="FTL"].sum()
        kg_total=data["kg"].sum()

        m_grp=data["m3"][data["Product"]=="GRP"].sum()
        m_ltl=data["m3"][data["Product"]=="LTL"].sum()
        m_ftl=data["m3"][data["Product"]=="FTL"].sum()
        m_total=data["m3"].sum()

        ldm_grp=data["ldm"][data["Product"]=="GRP"].sum()
        ldm_ltl=data["ldm"][data["Product"]=="LTL"].sum()
        ldm_ftl=data["ldm"][data["Product"]=="FTL"].sum()
        ldm_total=data["ldm"].sum()

        
        pw_grp=data["PW DSV"][data["Product"]=="GRP"].sum()
        pw_ltl=data["PW DSV"][data["Product"]=="LTL"].sum()
        pw_ftl=data["PW DSV"][data["Product"]=="FTL"].sum()
        pw_total=data["PW DSV"].sum()

        labels = ['GRP','FTL','LTL']
        colors =['#002664','#5D7AB5','#A9BCE2']
        sh_values = [nb_grp, nb_ftl, nb_ltl]
        kg_values=[kg_grp,kg_ltl,kg_ftl]
        m3_values=[m_grp,m_ltl,m_ftl]
        ldm_values=[ldm_grp,ldm_ltl,ldm_ftl]
        pw_values=[pw_grp,pw_ltl,pw_ftl]

        dom=data["ZC from"][data["Way"]=="Dom"].count()
        exp=data["ZC from"][data["Way"]=="Exp"].count()
        imp=data["ZC from"][data["Way"]=="Imp"].count()
        trans=data["ZC from"][data["Way"]=="Trans"].count()

        values_way=[dom,exp,imp,trans]
        labels_way=["Dom","Exp","Imp","Trans"]

        col1, col2,col3,col4 = st.columns([1.3,1.3,2,2])
        with col1:
            fig = make_subplots(rows=1, specs=[[{'type':'domain'}]])
            fig.add_trace(go.Pie(labels=labels, values=sh_values, name="nbr of shipment"),1,1)
            fig.update_traces(hole=.5,marker=dict(colors=colors))
            fig.update_layout(
            title_text="Product",
            annotations=[dict(text='Shipments', x=0.27, y=0.5, font_size=20, showarrow=False)])
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            fig = make_subplots(rows=1, cols=1, specs=[[{'type':'domain'}]])
            fig.add_trace(go.Pie(labels=labels_way, values=values_way, name="Way"),1,1)
            fig.update_traces(hole=.5,marker=dict(colors=['#002664','#5D7AB5','#A9BCE2','#000000']))
            fig.update_layout(annotations=[dict(text='Way', x=0.5, y=0.5, font_size=20, showarrow=False)],
            title_text="Type")
            st.plotly_chart(fig,use_container_width=True)
        
        with col3:
            
            my_list = sorted(data["Bracket"].tolist())
            count = Counter(my_list)
            total_items = sum(count.values())
            count_list = list(count.items())
            count_percentage_list = [(item, count, f"{round((count / total_items) * 100, 2)}%") for item, count in count.items()]
            df = pd.DataFrame(count_percentage_list, columns=['bracket', 'Count', 'percentage'])
            fig = px.bar(df, x='bracket', y='Count',color_discrete_sequence=['#002664'], text='percentage')
            fig.update_layout(
                title="Brackets",
                xaxis_title='Bracket',
                yaxis_title='Count',
                xaxis=dict(type='category')  
            )
            st.plotly_chart(fig,use_container_width=True)
            
        with col4:
             
            data1=data.groupby(["ZC to"],as_index=False)["PW DSV"].sum()
            data1=pd.merge(data,zip_code,on='ZC to',how="left")
            data1['count'] = data1.groupby('ZC to')['ZC to'].transform('count')
            data1["PW DSV"]=(data1["PW DSV"])/data1["count"]
            data1=data1.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
            merge=pd.merge(levl0,data1,right_on="nuts0" ,left_on="ISO2",how="right")
            m = folium.Map(location=[55.6761, 12.5683], zoom_start=2.5, zoom_control=False, scroll_wheel_zoom=False )
            colums=["nuts0","PW DSV"]
            key="properties.ISO2"
            st.write("**Countries**")
            choropleth=folium.Choropleth(
                geo_data=merge,
                name="choropleth",
                data=merge,
                columns=colums,
                key_on=key,
                fill_color='OrRd',
                fill_opacity=0.7,
                legend=True,
                highlight=True,
                
                ).geojson.add_to(m)
            
            folium_static(m,width=450, height=350)

        col1,col2 = st.columns([2,1])
        with col1:
            df4=data.groupby(["Product"]).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
            df4=df4.rename(columns={'Date' : 'Number of shipments'})
            df4=df4.T
            df4["Total"]=df4.sum(axis=1)
            
            st.table(df4)
             
        with col2:
            df5=data.pivot_table(index="Way", columns="Product", values="Date",aggfunc="count")
            df5["Total"]=df5.sum(axis=1)
            st.table(df5)


def analysis_page ():
    st.title("Shipment Profile")
    data = load_data()
    st.sidebar.markdown("## Filter Options for the pivot table")
    
    selected_cntry_from = st.sidebar.multiselect('Select Country From', options=data['Cntry from'].unique())
    selected_zc_from = st.sidebar.multiselect('Select Zip Code From', options=data['ZC from'].unique())
    selected_cntry_to = st.sidebar.multiselect('Select Country To', options=data['Cntry to'].unique())
    selected_zc_to = st.sidebar.multiselect('Select Zip Code To', options=data['ZC to'].unique())
    selected_product = st.sidebar.multiselect('Select type of product', options=data['Product'].unique())
    selected_way = st.sidebar.multiselect('Select way', options=data['Way'].unique())
    selected_branch = st.sidebar.multiselect('Select branch', options=data['Branch'].unique())

    data = data[
    (data['Cntry from'].isin(selected_cntry_from) if selected_cntry_from else data['Cntry from'].notnull()) &
    (data['ZC from'].isin(selected_zc_from) if selected_zc_from else data['ZC from'].notnull()) &
    (data['Cntry to'].isin(selected_cntry_to) if selected_cntry_to else data['Cntry to'].notnull()) &
    (data['ZC to'].isin(selected_zc_to) if selected_zc_to else data['ZC to'].notnull())&
    (data['Product'].isin(selected_product) if selected_product else data['Product'].notnull())&
    (data['Way'].isin(selected_way) if selected_way else data['Way'].notnull())&
    (data['Branch'].isin(selected_branch) if selected_branch else data['Branch'].notnull())]

    pivot=pd.pivot_table(data,values="Cost",index=["Cntry from","ZC from","Cntry to","ZC to"],columns="Bracket",aggfunc="count")
    pivot["total"]=pivot.sum(axis=1)
    pivot["%"]=round(pivot["total"] /( pivot['total'].sum())*100,2)
    pivot.fillna('', inplace=True)

    
        
        
    col1, col2 = st.columns(2)
    with col1:
            st.title('Pivot Table')
            st.write(pivot)

            st.title('Collection')
            df1=data.groupby('Date').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' })
            df1=df1.rename(columns={'Date': 'Shipments'})
            st.write(df1)
            df2=df1.sum(numeric_only=True).to_frame().T
            df2.index=["Total"]
            st.dataframe(df2)

            df3=data.groupby(['ZC from','ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
            df3=df3.rename(columns={'Date' : 'Number of shipments'})
            df3=df3.sort_values(by="Number of shipments",ascending=False )
            df3=df3.head(8)
            df3 = df3.reset_index()
            df3["From-to"]=  'From ' + df3['ZC from'] + ' to ' + df3['ZC to']
            df3=df3.drop(columns=["ZC from","ZC to"])
            index_list=df3["From-to"].tolist()
            df3.index=index_list
            df3=df3.drop(columns=["From-to"])


            st.title("important shipments")
            st.write(df3)
           
            

    with col2:
            st.title("  :bar_chart: Shipment per bracket ")
            my_list = sorted(data["Bracket"].tolist())
            count = Counter(my_list)
            total_items = sum(count.values())
            count_list = list(count.items())
            count_percentage_list = [(item, count, f"{round((count / total_items) * 100, 2)}%") for item, count in count.items()]
            df = pd.DataFrame(count_percentage_list, columns=['bracket', 'Count', 'percentage'])
            fig = px.bar(df, x='bracket', y='Count',color_discrete_sequence=['#002664'], text='percentage')
            fig.update_layout(
                
                xaxis_title='Bracket',
                yaxis_title='Count',
                xaxis=dict(type='category')  
            )
            st.plotly_chart(fig)
            st.title("")
            st.table(df1.describe())


# Page for basic data analysis
def map():
    st.title('Map')
    data = load_data()
    if not data.empty:
            st.sidebar.markdown("Options")
            ship_from = data['ZC from'].dropna().unique().tolist()
            selected_country = st.sidebar.selectbox('Select Shipment from', ship_from)
            selected_level = st.sidebar.selectbox('Select level', ["country level", "Nuts1", "Nuts2", "Nuts3"])
            st.sidebar.write("Filters")
            produit= st.sidebar.multiselect('Select type of product', options=data['Product'].unique())
            data=data[ (data['Product'].isin(produit) if produit else data['Product'].notnull())]

            
                
        
            # Data filtering options
            
            ship_from = data['ZC from'].dropna().unique().tolist()
            data = data[data['ZC from'] == selected_country]

            data=data.groupby(["ZC to"],as_index=False)["PW DSV"].sum()
            data=pd.merge(data,zip_code,on='ZC to',how="left")
            data['count'] = data.groupby('ZC to')['ZC to'].transform('count')
            data["PW DSV"]=(data["PW DSV"])/data["count"]

        
            

            if selected_level== "country level":
                data=data.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl0,data,right_on="nuts0" ,left_on="ISO2",how="right")
                colums=["nuts0","PW DSV"]
                key="properties.ISO2"
                field=["NAME","PW DSV"]
                alias=["To : ", "Value: "]
                
            
            elif selected_level== "Nuts1":
                data=data.groupby(["nuts1"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl1,data,right_on="nuts1" ,left_on="NUTS_ID",how="right")
                colums=["nuts1","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]
            elif selected_level== "Nuts2":
                data=data.groupby(["nuts2"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl2,data,right_on="nuts2" ,left_on="NUTS_ID",how="right")
                colums=["nuts2","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]
            elif selected_level== "Nuts3":
                data=data.groupby(["NUTS3"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl3,data,right_on="NUTS3" ,left_on="NUTS_ID",how="right")
                colums=["NUTS3","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]

        
            m= folium.Map(location=[54.5260,15.2551],zoom_start=4,width='100%', control_scale=True)
            choropleth=folium.Choropleth(
            geo_data=merge,
            name="choropleth",
            data=merge,
            columns=colums,
            key_on=key,
            fill_color='OrRd',
            fill_opacity=0.7,
            legend=True,
            highlight=True,                   
            ).geojson.add_to(m)

            folium.features.GeoJson(
                            data=merge,
                            name='test',
                            smooth_factor=2,
                            style_function=lambda x: {'color':'black','fillColor':'transparent','weight':0.5},
                            tooltip=folium.features.GeoJsonTooltip(
                                fields=field,    
                                aliases=alias,  
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
                                ).add_to(choropleth)
            
        
    
            
            if st.sidebar.checkbox('show DSV branches'):
                    categories=dsv["Country"].unique().tolist()
                    for k in range(len(dsv)):
                        location = dsv["lat"].iloc[k],dsv["lon"].iloc[k]
                        html= f"<span style='font-family:Arial;''><span style='color:#002664;'><b>{ dsv['Office Name'].iloc[k]} <br> { dsv['ZC'].iloc[k]}  </b> </span><br> <br>  &#9743; {dsv['Phone'].iloc[k]} <br> <span style='font-size:12px'> &#128343; </span> {dsv['Opening hours'].iloc[k]} </span>"
                        iframe = branca.element.IFrame(html=html, width=250, height=140)

                        folium.Marker(
                        location=location,
                        tags=[dsv["Country"].iloc[k]],
                        icon=folium.Icon(color='darkblue',icon_color='White', icon="info-sign"),
                        tooltip=dsv["Office Name"].iloc[k] + " , click for more information",
                        popup = folium.Popup(iframe, max_width=500)).add_to(m)

                    TagFilterButton(categories).add_to(m)
            if selected_country == selected_country :
                try:
                    nuts_of_the_ZC=zip_code["NUTS3"].loc[zip_code["ZC to"]==selected_country]
                    polygon = levl3['geometry'].loc[levl3["NUTS_ID"]==(nuts_of_the_ZC.tolist()[0])]
                    centroid = polygon.centroid
                    long=centroid.x.tolist()[0]
                    lat=centroid.y.tolist()[0]
                    folium.Marker([lat, long],icon=folium.Icon(color='red', ), tooltip=f" From {selected_country}").add_to(m)
                except Exception :
                    print ("error")

            Fullscreen(position="topleft").add_to(m)
            html_string = m.get_root().render()
            
            folium_static(m, height=700,width=1200)
            def create_download_button(html_string, filename):
                    b64 = base64.b64encode(html_string.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">Download this the map </a>'
                    return href
            st.markdown(create_download_button(html_string, "map.html"), unsafe_allow_html=True)

    
    
    

        

# Sidebar for navigation
st.sidebar.header("Go to")




if 'page' not in st.session_state:
    st.session_state.page = 'Upload Data'

col1, col2 = st.sidebar.columns(2)
with col1:
     
    if st.sidebar.button('Upload Data'):
        st.session_state.page = 'Upload Data'
    if st.sidebar.button('Shipment Summary'):
        st.session_state.page = 'Shipment Summary'
with col2:

    if st.sidebar.button('Shipment Profile'):
        st.session_state.page = 'Shipment Profile'
    if st.sidebar.button('Maps'):
        st.session_state.page = 'Maps'

if st.session_state.page == 'Upload Data':
    upload_view_page()
elif st.session_state.page == 'Shipment Summary':
    summary_page()
elif st.session_state.page == 'Shipment Profile':
    analysis_page()
elif st.session_state.page == 'Maps':
    map()
                                              

# Initialize session state for file storage
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
