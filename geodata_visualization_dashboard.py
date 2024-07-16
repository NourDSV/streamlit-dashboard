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
levl3.drop_duplicates(subset="NUTS_ID", keep="first", inplace=True)
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
    if not data.empty:
        country_codes = ['AD', 'ME', 'RU', 'XK', 'UA', 'BY', 'BA']
        for code in country_codes:
            data.loc[data['ZC from'].str[:2] == code, 'ZC from'] = code
            data.loc[data['ZC to'].str[:2] == code, 'ZC to'] = code
        data['ZC from'] = data['ZC from'].apply(lambda x: 'UK' + x[2:] if x.startswith('GB') else x)
        data['ZC to'] = data['ZC to'].apply(lambda x: 'UK' + x[2:] if x.startswith('GB') else x)
    
    return data

def ldm_calc(data):
    data["ldm"]=data["kg"]*1
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
        has_ldm = st.radio("Does your shipment profile have the 'Ldm' data ?", ("Yes", "No"))
        if has_ldm == "No":
            
                if 'kg' in data.columns:
                    ldm_calc(data)
                    st.write("this is your new data")
                    st.write(data)
                else:
                    st.write("error can't calculate ldm because kg does not existe ")


def summary_page():
        
        st.title("Shipment summary")
        data = load_data()

        dom=data["ZC from"][data["Way"]=="Dom"].count()
        exp=data["ZC from"][data["Way"]=="Exp"].count()
        imp=data["ZC from"][data["Way"]=="Imp"].count()
        trans=data["ZC from"][data["Way"]=="Trans"].count()

        values_way=[dom,exp,imp,trans]
        labels_way=["Dom","Exp","Imp","Trans"]

        col1, col2,col3,col4 = st.columns([1.3,1.3,2,2])
        with col1:
            produit=data["Product"].unique().tolist()
            labels = []
            sh_values = []
            dict_product={}
            for k in produit:
                summ=(data["Product"]==k).sum()
                dict_product[f'nbr_{k}']=summ
                sh_values.append(summ)
                labels.append(k)
            colors =['#002664','#5D7AB5','#A9BCE2']
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
            count_percentage_list = [(item, count, f"{round((count / total_items) * 100, 2)}%") for item, count in count.items()]
            df_bracket = pd.DataFrame(count_percentage_list, columns=['bracket', 'Count', 'percentage'])
            fig = px.bar(df_bracket, x='bracket', y='Count',color='Count', 
            color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'], text='percentage')
            fig.update_layout(
                title="Shipments per brackets ",
                xaxis_title='',
                yaxis_title='Shipments',
                xaxis=dict(type='category'))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig,use_container_width=True)
            
        with col4:
            #  removing the decimal after the comma for the column PW
            data["PW DSV"]=data["PW DSV"].astype(int)

            # creating the folium map
            data1=data.groupby(["ZC to"],as_index=False)["PW DSV"].sum()
            data1=pd.merge(data1,zip_code,on='ZC to',how="left")
            data1['count'] = data1.groupby('ZC to')['ZC to'].transform('count')
            data1["PW DSV"]=(data1["PW DSV"])/data1["count"]
            data1=data1.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
            merge=pd.merge(levl0,data1,right_on="nuts0" ,left_on="ISO2",how="right")
            
            m = folium.Map(location=[55.6761, 12.5683], zoom_start=2.5, zoom_control=False, tiles = "CartoDB Positron" )
            colums=["nuts0","PW DSV"]
            key="properties.ISO2"
            st.write("**Countries**")


            choropleth=folium.Choropleth(
                geo_data=merge,
                name="choropleth",
                data=merge,
                columns=colums,
                key_on=key,
                fill_color='Blues',
                fill_opacity=0.7,
                legend=False,
                highlight=True,
                ).geojson.add_to(m)
            tooltip = GeoJsonTooltip(
                fields=colums,
                aliases=["Delivery country", "Total pay weight"],
                localize=True
            )
            choropleth.add_child(tooltip)

           

            
            data2=data.groupby(["ZC from"],as_index=False)["PW DSV"].sum()
            data2=pd.merge(data2,zip_code,right_on='ZC to',left_on="ZC from")
            data2['count'] = data2.groupby('ZC from')['ZC from'].transform('count')
            data2["PW DSV"]=(data2["PW DSV"])/data2["count"]
            data2=data2.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
            merge2=pd.merge(levl0,data2,right_on="nuts0" ,left_on="ISO2",how="right")


            for k in range (len(merge2)):
                lat=merge2["LAT"].iloc[k]
                lon=merge2["LON"].iloc[k]

                
                merge2['radius'] = (merge2['PW DSV'] - merge2['PW DSV'].min()) / (merge2['PW DSV'].max() - merge2['PW DSV'].min()) * (20 - 5) + 5
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=merge2['radius'].iloc[k],
                    color='None',
                    fill=True,
                    fill_color="red",
                    fill_opacity=1,
                    tooltip=f'Collecting country: {merge2["NAME"].iloc[k]} <br> PayWeight: {merge2["PW DSV"].iloc[k]}'
                ).add_to(m)
          
            

            folium_static(m,width=450, height=330)
            st.write("""
            <span style='font-size: small;'>🔴 : Collecting countries &nbsp;&nbsp; 🟦 : Delivered countries</span>
            """, unsafe_allow_html=True)
        col1,col2,col3,col4 = st.columns([1,1,2,2.5])
        with col2:

            df6=data.groupby(['ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
            df6=df6.rename(columns={'Date' : 'Number of shipments'})
            df6=df6.sort_values(by="Number of shipments",ascending= False )
            df6=df6.head(10)
            df6=df6.sort_values(by="Number of shipments",ascending= True )
            df6 = df6.reset_index()
            fig = px.bar(df6, y='ZC to', x='Number of shipments', title="  Top 10 delivery",
            color='Number of shipments', 
            color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
            orientation='h',
            hover_data={'kg': True, 'ldm': True, 'PW DSV': True})  
            fig.update_layout(
                xaxis_title='Shipments',  
                yaxis_title='' )
            fig.update_coloraxes(showscale=False)

            st.plotly_chart(fig, use_container_width=True)

        with col1:
                df7=data.groupby(['ZC from']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
                df7=df7.rename(columns={'Date' : 'Number of shipments'})
                df7=df7.sort_values(by="Number of shipments",ascending= False )
                df7=df7.head(10)
                df7=df7.sort_values(by="Number of shipments",ascending= True )
                df7 = df7.reset_index()
                fig = px.bar(df7, y='ZC from', x='Number of shipments', title=" Top 10 collection",
                color='Number of shipments', 
                color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
                orientation='h',
                hover_data={'kg': True, 'ldm': True})  
                fig.update_layout(
                xaxis_title='Shipments',  
                yaxis_title='' )
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            df3=data.groupby(['ZC from','ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
            df3=df3.rename(columns={'Date' : 'Number of shipments'})
            df3=df3.sort_values(by="Number of shipments",ascending=False )
            # df3["%"]=df3["PW DSV"]/(sum(df3["PW DSV"]))*100
            # df3["cum"]=df3["%"].cumsum()
            df3=df3.head(10)
            df3 = df3.reset_index()
            df3["From-to"]=  df3['ZC from'] + ' to ' + df3['ZC to']
            df3.index=df3["From-to"].tolist()
            fig = px.bar(df3, y='Number of shipments', x='From-to', title=" Top 10 main lanes",color='Number of shipments', color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'])
                
            fig.update_layout(
                xaxis_title='',  
                yaxis_title='' )
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with col4:
            data['Month'] = data['Date'].dt.to_period('M')
            df4=data.groupby('Month').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' }).reset_index()
            df4=df4.rename(columns={'Date': 'Shipments'})
            df4['Month'] = df4['Month'].astype(str)
            fig_ship = px.line(df4, x='Month', y='Shipments', markers=True , line_shape='spline')
            fig_ship.update_layout(
                title='Seasonality', 
                xaxis_title='',
                yaxis_title='Shipments',
                xaxis={'type': 'category', 'categoryorder': 'array', 'categoryarray': df4['Month']})
            st.plotly_chart(fig_ship,use_container_width=True)


        container = st.container(border=True)

        with container:
            df4=data.groupby(["Product"]).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
            df4=df4.rename(columns={'Date' : 'Number of shipments'})
            df4 = df4.applymap(lambda x: int(x) if isinstance(x, (int, float)) else x)
            df4=df4.T
            df4["Total"]=df4.sum(axis=1)
            df4 = df4.reset_index()
            df4=df4.rename(columns={'index':"type"})
            df7=df4.set_index('type')
            st.title("")
            st.dataframe(df7)
            df5=data.pivot_table(index="Way", columns="Product", values="Date",aggfunc="count")
            df5["Total"]=df5.sum(axis=1)
            
            st.write(df5)
    
            


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
    

    st.title("Seasonality")
    col3, col4 = st.columns([1,2])
    with col3:

            data['Month'] = data['Date'].dt.to_period('M')
            df4=data.groupby('Month').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' }).reset_index()
            df4=df4.rename(columns={'Date': 'Shipments'})
            df4['Month'] = df4['Month'].astype(str)
            
            st.write("")
            st.dataframe(df4)
            metric = st.selectbox("Select fig to show",['Shipments', 'kg', 'ldm', 'PW DSV'])
    with col4:

            fig_ship = px.line(df4, x='Month', y='Shipments', markers=True)
            fig_ship.update_layout(
                title='Monthly Shipments', 
                xaxis_title='Month',
                yaxis_title='Number of Shipments'
            )

            fig_kg = px.line(df4, x='Month', y='kg', markers=True)
            fig_kg.update_layout(title=' Kg per month', xaxis_title='Month', yaxis_title='KG')

            fig_ldm = px.line(df4, x='Month', y='ldm', markers=True)
            fig_ldm.update_layout(title=' ldm per month', xaxis_title='Month', yaxis_title='Meters')

            fig_pw = px.line(df4, x='Month', y='PW DSV', markers=True)
            fig_pw.update_layout(title=' Pay Weight per month', xaxis_title='Month', yaxis_title='Kg')

            if metric == 'Shipments':
                st.plotly_chart(fig_ship)
            elif metric == 'kg':
                st.plotly_chart(fig_kg)
            elif metric == 'ldm':
                st.plotly_chart(fig_ldm)
            elif metric == 'PW DSV':
                st.plotly_chart(fig_pw)


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
            st.table(df.describe())


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

def collection():
    st.title('Collection')
    data = load_data()
     
    df1=data.groupby('Date').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' })
    df1=df1.rename(columns={'Date': 'Shipments'})
    st.write(df1)
    df2=df1.sum(numeric_only=True).to_frame().T
    df2.index=["Total"]
    st.dataframe(df2)
     

    
    
    

        

st.sidebar.image("1200px-DSV_Logo.svg.png", use_column_width=True)
st.sidebar.header("Go to")




if 'page' not in st.session_state:
    st.session_state.page = 'Upload Data'
if st.sidebar.button('Upload Data'):
        st.session_state.page = 'Upload Data'
if st.sidebar.button('Shipment Summary'):
        st.session_state.page = 'Shipment Summary'
if st.sidebar.button('Shipment Profile'):
        st.session_state.page = 'Shipment Profile'
if st.sidebar.button('Maps'):
        st.session_state.page = 'Maps'
if st.sidebar.button("Collection"):
     st.session_state.page="Collection"


if st.session_state.page == 'Upload Data':
    upload_view_page()
elif st.session_state.page == 'Shipment Summary':
    summary_page()
elif st.session_state.page == 'Shipment Profile':
    analysis_page()
elif st.session_state.page == 'Maps':
    map()
elif st.session_state.page=="Collection":
     collection()
                                              

# Initialize session state for file storage
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
