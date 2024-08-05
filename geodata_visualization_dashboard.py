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
from branca.colormap import linear
from streamlit_folium import folium_static
from folium.plugins import Fullscreen
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import base64
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from streamlit_option_menu import option_menu

levl0=gpd.read_file("europe.geojson")
levl2=gpd.read_file("NUTS_2_Q2.geojson")
levl1=gpd.read_file("NUTS_1_Q1.geojson")
levl3=gpd.read_file("NUTS_3_Q1.geojson")
levl3.drop_duplicates(subset="NUTS_ID", keep="first", inplace=True)
zip_code=pd.read_excel("zipcode_nuts with uk instead of gb.xlsx")
dsv=pd.read_excel("DSV Branches.xlsx")


st.set_page_config(layout='wide')

# Function to load data
# @st.cache_data
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
        data["PW DSV"]=data["Payweight 330/1750"]
        data['Date'] = data['Date'].dt.date
    return data

def ldm_calc(data):
    data["ldm"]=data["kg"]*1
    return data

if 'page' not in st.session_state:
    st.session_state.page = 'Upload data'

selected = option_menu(
menu_title=None,
options=["Upload data", "Shipment Summary", "Shipment Profile","Maps","Collection Analysis"],
icons=["bi-cloud-upload", "bi bi-bar-chart-fill", "graph-up","bi bi-globe-europe-africa","bi bi-calendar-event"],
menu_icon="cast",
default_index=0,
orientation="horizontal",
)

st.session_state.page = selected
# Page for uploading and viewing the Excel file
if selected == "Upload data":
    
    st.title('Upload your data')
    uploaded_file = st.file_uploader("Put your shipment profile here", type=['xlsx'])
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        
        data = pd.read_excel(uploaded_file)
        if 'Date' in data.columns:
            data['Date'] = data['Date'].apply(lambda x: pd.to_datetime(x) if pd.notnull(x) and x != '' else x)
        st.write(data)
        has_ldm = st.radio("Does your shipment profile have the 'Ldm' data ?", ("Yes", "No"))
        if has_ldm == "No":
            
                if 'kg' in data.columns:
                    ldm_calc(data)
                    st.write("this is your new data")
                    st.write(data)
                else:
                    st.write("error can't calculate ldm because kg does not existe ")



    
    


if selected == "Shipment Summary":
        
        
        data = load_data()
        
        col1,col2=st.columns([1,7],gap="large")         
        with col1:
                st.write("**Filters option**")
                selected_branch = st.multiselect('Select branch', options=data['Branch'].unique())
                if selected_branch:
                    data = data[data['Branch'].isin(selected_branch)]
                else:
                    data = data
               
                filtered_cntry_from = data['Cntry from'].unique()
                selected_cntry_from = st.multiselect('Select Country From', filtered_cntry_from)
                if selected_cntry_from:
                    data = data[data['Cntry from'].isin(selected_cntry_from)]
                else:
                    data = data  

                
                filtered_zc_from = data['ZC from'].unique()
                selected_zc_from = st.multiselect('Select Zip Code From', filtered_zc_from)

                filtered_cntry_to = data['Cntry to'].unique()
                selected_cntry_to = st.multiselect('Select Country To', filtered_cntry_to)
                if selected_cntry_to:
                    data = data[data['Cntry to'].isin(selected_cntry_to)]
                else:
                    data = data  

               
                filtered_zc_to = data['ZC to'].unique()
                selected_zc_to = st.multiselect('Select Zip Code To', filtered_zc_to)
                selected_product = st.multiselect('Select type of product', options=data['Product'].unique())
                selected_way = st.multiselect('Select way', options=data['Way'].unique())
                
            
                data = data[
                (data['Cntry from'].isin(selected_cntry_from) if selected_cntry_from else data['Cntry from'].notnull()) &
                (data['ZC from'].isin(selected_zc_from) if selected_zc_from else data['ZC from'].notnull()) &
                (data['Cntry to'].isin(selected_cntry_to) if selected_cntry_to else data['Cntry to'].notnull()) &
                (data['ZC to'].isin(selected_zc_to) if selected_zc_to else data['ZC to'].notnull())&
                (data['Product'].isin(selected_product) if selected_product else data['Product'].notnull())&
                (data['Way'].isin(selected_way) if selected_way else data['Way'].notnull())&
                (data['Branch'].isin(selected_branch) if selected_branch else data['Branch'].notnull())]
        
        with col2:
            st.header("Shipment summary")
            dom=data["ZC from"][data["Way"]=="Dom"].count()
            exp=data["ZC from"][data["Way"]=="Exp"].count()
            imp=data["ZC from"][data["Way"]=="Imp"].count()
            X_trade=data["ZC from"][data["Way"]=="X-trade"].count()

            values_way=[dom,exp,imp,X_trade]
            labels_way=["Dom","Exp","Imp","X_trade"]

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
                annotations=[dict(text='Shipments', x=0.27, y=0.5, font_size=20, showarrow=False)])
                st.write("<h5><b>Product</b></h5>", unsafe_allow_html=True)
                st.plotly_chart(fig,use_container_width=True)
                
            with col2:
                fig = make_subplots(rows=1, cols=1, specs=[[{'type':'domain'}]])
                fig.add_trace(go.Pie(labels=labels_way, values=values_way, name="Way"),1,1)
                fig.update_traces(hole=.5,marker=dict(colors=['#002664','#5D7AB5','#A9BCE2','#000000']))
                fig.update_layout(annotations=[dict(text='Way', x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.write("<h5><b>Type</b></h5>", unsafe_allow_html=True)
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
                    # title="Shipments per brackets ",
                    xaxis_title='',
                    yaxis_title='Shipments',
                    xaxis=dict(type='category'))
                fig.update_coloraxes(showscale=False)
                st.write("<h5><b>Shipments per brackets</b></h5>", unsafe_allow_html=True)
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
                
                st.write("<h5><b>Countries</b></h5>", unsafe_allow_html=True)


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
                    merge2 ['radius']= merge2['radius'].fillna(10)
                         
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=merge2['radius'].iloc[k],
                        color='None',
                        fill=True,
                        fill_color="red",
                        fill_opacity=1,
                        tooltip=f'Collecting country: {merge2["NAME"].iloc[k]} <br> PayWeight: {merge2["PW DSV"].iloc[k]}'
                    ).add_to(m)
            
                

                folium_static(m,width=450, height=325)
                st.write("""
                <span style='font-size: small;'>🔴  Collecting countries &nbsp;&nbsp; 🔷  Delivered countries</span>
                """, unsafe_allow_html=True)
                
            col1,col2,col3,col4 = st.columns([1,1,2,2.5])
            with col2:

                df6=data.groupby(['ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
                df6=df6.rename(columns={'Date' : 'Number of shipments'})
                df6=df6.sort_values(by="Number of shipments",ascending= False )
                df6=df6.head(10)
                df6=df6.sort_values(by="Number of shipments",ascending= True )
                df6 = df6.reset_index()
                fig = px.bar(df6, y='ZC to', x='Number of shipments', 
                color='Number of shipments', 
                color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
                orientation='h',
                hover_data={'kg': True, 'ldm': True, 'PW DSV': True})  
                fig.update_layout(
                    xaxis_title='Shipments',  
                    yaxis_title='' )
                fig.update_coloraxes(showscale=False)
                st.write("<h5><b>Top 10 delivery</b></h5>", unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                

            with col1:
                df7=data.groupby(['ZC from']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
                df7=df7.rename(columns={'Date' : 'Number of shipments'})
                df7=df7.sort_values(by="Number of shipments",ascending= False )
                df7=df7.head(10)
                df7=df7.sort_values(by="Number of shipments",ascending= True )
                df7 = df7.reset_index()
                fig = px.bar(df7, y='ZC from', x='Number of shipments', 
                color='Number of shipments', 
                color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
                orientation='h',
                hover_data={'kg': True, 'ldm': True})  
                fig.update_layout(
                xaxis_title='Shipments',  
                yaxis_title='' )
                fig.update_coloraxes(showscale=False)
                st.write("<h5><b>Top 10 collection</b></h5>", unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                
            
            with col3:
                df3=data.groupby(['ZC from','ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
                df3=df3.rename(columns={'Date' : 'Number of shipments'})
                df3=df3.sort_values(by="Number of shipments",ascending=False )
                # df3["%"]=df3["PW DSV"]/(sum(df3["PW DSV"]))*100
                # df3["cum"]=df3["%"].cumsum()
                df3=df3.head(10)
                df3 = df3.reset_index()
                df3["From-to"]=  df3['ZC from'] + ' - ' + df3['ZC to']
                df3.index=df3["From-to"].tolist()
                fig = px.bar(df3, y='Number of shipments', x='From-to',color='Number of shipments', color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'])
                    
                fig.update_layout(
                    xaxis_title='',  
                    yaxis_title='' )
                fig.update_coloraxes(showscale=False)
                st.write("<h5><b>Top 10 main lanes</b></h5>", unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                
            with col4:
                data['Month'] = pd.to_datetime(data['Date']).dt.to_period('M')
                df4=data.groupby('Month').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' }).reset_index()
                df4=df4.rename(columns={'Date': 'Shipments'})
                df4['Month'] = df4['Month'].astype(str)
                fig_ship = px.line(df4, x='Month', y='Shipments', markers=True , line_shape='spline')
                fig_ship.update_layout( 
                    xaxis_title='',
                    yaxis_title='Shipments',
                    xaxis={'type': 'category', 'categoryorder': 'array', 'categoryarray': df4['Month'],"showgrid":True})
                st.write("<h5><b>Seasonality</b></h5>", unsafe_allow_html=True)
                st.plotly_chart(fig_ship,use_container_width=True)
                


            col1,col2,col3=st.columns([1.5,1,1.5])

            with col1:
                df4=data.groupby(["Product"]).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
                df4=df4.rename(columns={'Date' : 'Shipments'})
                df4 = df4.applymap(lambda x: int(x) if isinstance(x, (int, float)) else x)
                df4=df4.T
                df4["Total"]=df4.sum(axis=1)
                df4 = df4.reset_index()
                df4=df4.rename(columns={'index':"Type"})
                df7=df4.set_index('Type')
                
                df7=df7.applymap(lambda x: '{:,.0f}'.format(x).replace(',', ' ') if pd.notna(x) and isinstance(x, (int, float)) else x)
                st.dataframe(df7)
            with col2:
                df5=data.pivot_table(index="Way", columns="Product", values="Date",aggfunc="count")
                df5["Total"]=df5.sum(axis=1)
                df5= df5.fillna(0)
                
                df5=df5.applymap(lambda x: '{:,.0f}'.format(x).replace(',', ' ') if pd.notna(x) and isinstance(x, (int, float)) else x)
            

            

                st.write(df5)

            


            


elif selected == "Shipment Profile":
        
        data = load_data()
        col1,col2=st.columns([1,7],gap="large")         
        with col1:
            st.write("**Filters option**")
            selected_branch = st.multiselect('Select branch', options=data['Branch'].unique())
            if selected_branch:
                data = data[data['Branch'].isin(selected_branch)]
            else:
                data = data
            
            filtered_cntry_from = data['Cntry from'].unique()
            selected_cntry_from = st.multiselect('Select Country From', filtered_cntry_from)
            if selected_cntry_from:
                data = data[data['Cntry from'].isin(selected_cntry_from)]
            else:
                data = data  

            
            filtered_zc_from = data['ZC from'].unique()
            selected_zc_from = st.multiselect('Select Zip Code From', filtered_zc_from)

            filtered_cntry_to = data['Cntry to'].unique()
            selected_cntry_to = st.multiselect('Select Country To', filtered_cntry_to)
            if selected_cntry_to:
                data = data[data['Cntry to'].isin(selected_cntry_to)]
            else:
                data = data  

            
            filtered_zc_to = data['ZC to'].unique()
            selected_zc_to = st.multiselect('Select Zip Code To', filtered_zc_to)
            selected_product = st.multiselect('Select type of product', options=data['Product'].unique())
            selected_way = st.multiselect('Select way', options=data['Way'].unique())
            
        
            data = data[
            (data['Cntry from'].isin(selected_cntry_from) if selected_cntry_from else data['Cntry from'].notnull()) &
            (data['ZC from'].isin(selected_zc_from) if selected_zc_from else data['ZC from'].notnull()) &
            (data['Cntry to'].isin(selected_cntry_to) if selected_cntry_to else data['Cntry to'].notnull()) &
            (data['ZC to'].isin(selected_zc_to) if selected_zc_to else data['ZC to'].notnull())&
            (data['Product'].isin(selected_product) if selected_product else data['Product'].notnull())&
            (data['Way'].isin(selected_way) if selected_way else data['Way'].notnull())&
            (data['Branch'].isin(selected_branch) if selected_branch else data['Branch'].notnull())]
        with col2:
            def can_convert_to_int(value):
                try:
                    int(value)  # Try to convert to integer
                    return True
                except (ValueError, TypeError):
                    return False
            st.header("Shipment Profile")
            data.dropna(subset=['Bracket'])
            data=data[data['Bracket'].apply(can_convert_to_int)]
            
             
            
            data['Bracket'] = data['Bracket'].astype(str)
            pivot=pd.pivot_table(data,values="Cost",index=["Cntry from","ZC from","Cntry to","ZC to"],columns="Bracket",aggfunc="count")
            pivot["total"]=pivot.sum(axis=1)
            pivot["%"]=round(pivot["total"] /( pivot['total'].sum())*100,2)
            pivot.fillna(0, inplace=True)
            pivot=pivot[pivot['total']!=0]

            
            
            # st.dataframe(pivot,width=1000,height=1000)
            st.write('**Total**')
            bracket_columns = [col for col in pivot.columns if col not in ['total', '%']]
            
            pivot[bracket_columns] = pivot[bracket_columns].astype(int)

            
            sorted_bracket_columns = sorted(bracket_columns, key=lambda x: int(x) if x.isdigit() else float('inf'))
            pivot = pivot[sorted_bracket_columns + ['total', '%'] ]
            pivot= pivot.reset_index()
            columns_order = ['%','Cntry from', 'ZC from', 'Cntry to', 'ZC to'] + [col for col in pivot.columns if col not in ['Cntry from', 'ZC from', 'Cntry to', 'ZC to', '%', 'total']]+['total']
            pivot = pivot[columns_order]

            total_row = pivot.sum(numeric_only=True).to_dict()
            total_row.update({'Cntry from': 'Total', 'ZC from': '', 'Cntry to': '', 'ZC to': '', '%': pivot['%'].sum(), 'total': pivot['total'].sum()})
            total_row=pd.DataFrame([total_row])
            
            
            cols = ['%','Cntry from', 'ZC from', 'Cntry to', 'ZC to'] + [col for col in pivot.columns if col not in ['Cntry from', 'ZC from', 'Cntry to', 'ZC to', '%', 'total']]+['total']
            total_row= total_row[cols]
            total_row.drop(columns=['ZC from', 'Cntry to', 'ZC to',"%"], inplace=True)
            percentage=pivot.sum(numeric_only=True).to_dict()
            percentage.update({'Cntry from': '%', 'ZC from': '', 'Cntry to': '', 'ZC to': '', '%': pivot['%'].sum(), 'total': pivot['total'].sum()})
            percentage=pd.DataFrame([percentage])
            
            percentage= percentage[cols]
            percentage.drop(columns=['ZC from', 'Cntry to', 'ZC to',"%"], inplace=True)
            def custom_operation(x):
                if isinstance(x, (int, float)):
                    return round((x / total_row["total"].iloc[0]) * 100, 1)
                return x
            # percentage=(percentage/(total_row["total"].iloc[0])*100).round(1)
            percentage=percentage.applymap(custom_operation)
            
            total_row= pd.concat([percentage,total_row])
            # pivot = pd.concat([pivot, pd.DataFrame([total_row])], ignore_index=True)
           
                
            min_value = pivot['%'].min()
            max_value = pivot['%'].max()
            min_total = pivot['total'].min()
            max_total = pivot['total'].max()
            min_value1 = percentage.drop(columns=["Cntry from", "total"]).min().min()
            max_value1 = percentage.drop(columns=["Cntry from", "total"]).max().max()
            
            
            
            
##################
            gb = GridOptionsBuilder.from_dataframe(pivot)
            

            

            gb.configure_default_column(floatingFilter=True, resizable=False)
            gb.configure_column('Cntry from', headerName="Cntry from", filter="agSetColumnFilter", minWidth=98, maxWidth=300)
            gb.configure_column('ZC from', headerName="ZC from", filter="agSetColumnFilter", minWidth=90, maxWidth=300)
            gb.configure_column('Cntry to', headerName="Cntry to", filter="agSetColumnFilter", minWidth=85, maxWidth=300)
            gb.configure_column('ZC to', headerName="ZC to", filter="agSetColumnFilter", minWidth=80, maxWidth=300)
            gb.configure_column('total', headerName="Total", filter="agNumberColumnFilter", minWidth=70, maxWidth=150)
            gb.configure_column('%', headerName="%", filter="agNumberColumnFilter", minWidth=70, maxWidth=150)

            jscode = JsCode(f"""
                function(params) {{
                    var value = params.value;
                    var minValue = {min_value};
                    var maxValue = {max_value};
                    var normalizedValue = (value - minValue) / (maxValue - minValue) * 100;
                    var color;
                    
                    if (normalizedValue >= 75) {{
                        color = 'green';
                    }} else if (normalizedValue >= 50) {{
                        color = 'orange';
                    }} else {{
                        color = 'red';
                    }}

                    return {{
                        'background': 'linear-gradient(90deg, ' + color + ' ' + normalizedValue + '%,' + ' transparent ' + normalizedValue + '%)',
                        'color': 'black'
                    }};
                }}
            """)
            jscode_total = JsCode("""
                function(params) {
                    var value = params.value;
                    var color = value >= 80 ? '#267326' : // Dark Green
                                value >= 60 ? '#39ac39' : // Medium Green
                                value >= 30 ? '#79d279' : // Medium Green
                                '#d9f2d9'; // Light Green
                    return {
                        'backgroundColor': color,
                        'color': 'black'
                    };
                }
                """)
            jscode1 = JsCode(f"""
                function(params) {{
                    var rowIndex = params.node.rowIndex;
                    var colId = params.column.colId;
                    var value = params.value;
                    var minValue = {min_value1};
                    var maxValue = {max_value1};
                    var normalizedValue = (value - minValue) / (maxValue - minValue) * 100;
                    var color;

                    if (rowIndex === 0 && colId !== 'Total' && colId !== '%') {{
                        if (normalizedValue >= 80) {{
                            color = 'green';
                        }} else if (normalizedValue >= 30) {{
                            color = 'orange';
                        }} else {{
                            color = 'red';
                        }}
                        return {{
                            'background': 'linear-gradient(90deg, ' + color + ' ' + normalizedValue + '%,' + ' transparent ' + normalizedValue + '%)',
                            'color': 'black'
                        }};
                    }}
                    return {{
                        'color': 'black'
                    }};
                }}
            """)
            gb1 = GridOptionsBuilder.from_dataframe(total_row)
            gb1.configure_default_column( resizable=False)
            gb1.configure_column('Cntry from', headerName="Bracket", minWidth=429, maxWidth=429)
            gb.configure_column('%', cellStyle=jscode)
            # gb.configure_column('total', cellStyle=jscode_total)
            for col in total_row.columns:
                if col not in ["Cntry from","total"]:
                    gb1.configure_column(col, cellStyle=jscode1)
            
            gridOptions = gb.build()
            gridOptions1 = gb1.build()
            
            
            AgGrid(total_row,height=91,fit_columns_on_grid_load=True ,allow_unsafe_jscode=True,gridOptions=gridOptions1)
            # Display the AgGrid table in Streamlit
           
            st.write('**Pivot table**')
            st.write("Left filters will apply on the table, you can also: use the filters on top of the table, sort the columns, move the columns, ...")
            
            response = AgGrid(
                pivot,
                gridOptions=gridOptions,
                update_mode=GridUpdateMode.NO_UPDATE,
                enable_enterprise_modules=True,
                allow_unsafe_jscode=True,
                fit_columns_on_grid_load=True,
                height=500
                 
            )
  
elif selected == "Collection Analysis":
    st.title('Collection Analysis')
    data = load_data()
    col1,col2=st.columns([1,7],gap="large")         
    with col1:
                st.write("**Filters option**")
                selected_branch = st.multiselect('Select branch', options=data['Branch'].unique())
                if selected_branch:
                    data = data[data['Branch'].isin(selected_branch)]
                else:
                    data = data
               
                filtered_cntry_from = data['Cntry from'].unique()
                selected_cntry_from = st.multiselect('Select Country From', filtered_cntry_from)
                if selected_cntry_from:
                    data = data[data['Cntry from'].isin(selected_cntry_from)]
                else:
                    data = data  

                
                filtered_zc_from = data['ZC from'].unique()
                selected_zc_from = st.multiselect('Select Zip Code From', filtered_zc_from)

                filtered_cntry_to = data['Cntry to'].unique()
                selected_cntry_to = st.multiselect('Select Country To', filtered_cntry_to)
                if selected_cntry_to:
                    data = data[data['Cntry to'].isin(selected_cntry_to)]
                else:
                    data = data  

               
                filtered_zc_to = data['ZC to'].unique()
                selected_zc_to = st.multiselect('Select Zip Code To', filtered_zc_to)
                selected_product = st.multiselect('Select type of product', options=data['Product'].unique())
                selected_way = st.multiselect('Select way', options=data['Way'].unique())
                
            
                data = data[
                (data['Cntry from'].isin(selected_cntry_from) if selected_cntry_from else data['Cntry from'].notnull()) &
                (data['ZC from'].isin(selected_zc_from) if selected_zc_from else data['ZC from'].notnull()) &
                (data['Cntry to'].isin(selected_cntry_to) if selected_cntry_to else data['Cntry to'].notnull()) &
                (data['ZC to'].isin(selected_zc_to) if selected_zc_to else data['ZC to'].notnull())&
                (data['Product'].isin(selected_product) if selected_product else data['Product'].notnull())&
                (data['Way'].isin(selected_way) if selected_way else data['Way'].notnull())&
                (data['Branch'].isin(selected_branch) if selected_branch else data['Branch'].notnull())]
    with col2:        
        col1,col2=st.columns([1,2.5], gap='large')
        with col1:
        
            
            df1=data.groupby('Date').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' })
            df1=df1.rename(columns={'Date': 'Shipments'})
            df6=df1.applymap(lambda x: '{:,.0f}'.format(x).replace(',', ' ') if pd.notna(x) and isinstance(x, (int, float)) else x)
            st.dataframe(df6,use_container_width=True)
            df2=df1.sum(numeric_only=True).to_frame().T
            df2.index=["Total"]
            df2=df2.applymap(lambda x: '{:,.0f}'.format(x).replace(',', ' ') if pd.notna(x) and isinstance(x, (int, float)) else x)
            st.dataframe(df2,use_container_width=True)
            df7=df1.describe()
            df1.reset_index(inplace=True)
            df1['Date'] = pd.to_datetime(df1['Date'])
            df1['Is_Working_Day'] = df1['Date'].dt.weekday < 5
            num_working_days = df1['Is_Working_Day'].sum()
            total_days = len(df1)
            average_working_days = num_working_days / total_days
            df8= pd.DataFrame({
                'Total collection days': [total_days],
                'Working days': [num_working_days],
                'Average collection per day': [average_working_days]})
            df8.set_index('Total collection days', inplace=True)
            st.dataframe(df8,use_container_width=True)

            st.dataframe(df7) 
        with col2:
            data= data.dropna(subset=['ldm'])
            df3=data.groupby('Date').agg({ 'ldm': 'sum' })
            
            def collection(x):
                if x <= 0.5:
                    return 0.5
                elif x <= 1:
                    return 1
                elif x <= 2:
                    return 2
                elif x <= 3:
                    return 3
                elif x <= 4:
                    return 4
                elif x <= 5:
                    return 5
                elif x <= 6:
                    return 6
                elif x <= 7:
                    return 7
                elif x <= 8:
                    return 8
                elif x <= 9:
                    return 9
                elif x <= 10:
                    return 10
                elif 10<x <= 13.6:
                    return "FTL"
                elif x > 13.6:
                    return "sup.FTL"
                
            df3['LDM'] = df3['ldm'].apply(collection)
            
            df3=df3.groupby('LDM').agg({'ldm': 'count' })
            
            df3=df3.rename(columns={'ldm': 'collection'})
            df3=df3.reset_index()
            df4=pd.DataFrame()
            fig=px.bar(df3,x="LDM",y="collection", color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'], text='collection')
            fig.update_layout(
                            title="nbr collections per ldm  ",
                            xaxis_title='',
                            yaxis_title='',
                            xaxis=dict(type='category'))
            st.plotly_chart(fig)
            data['Month'] = pd.to_datetime(data['Date']).dt.to_period('M')
            df4=data.groupby('Month').agg({'kg': 'count' }).reset_index()
            df4=df4.rename(columns={'kg': 'Collection'})
            df4['Month'] = df4['Month'].astype(str)
            fig_ship = px.line(df4, x='Month', y='Collection', markers=True, line_shape='spline')
            fig_ship.update_layout(
                        title='Seasonality of collection per month', 
                        xaxis_title='Month',
                        yaxis_title='Number of collection'
                    )
            st.plotly_chart(fig_ship)
            


           
#########################
           

            
            #     st.title("Seasonality")
            
            

            #     data['Month'] = data['Date'].dt.to_period('M')
            #     df4=data.groupby('Month').agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum' }).reset_index()
            #     df4=df4.rename(columns={'Date': 'Shipments'})
            #     df4['Month'] = df4['Month'].astype(str)
                
            #     st.write("")
            #     st.dataframe(df4)
            #     metric = st.selectbox("Select fig to show",['Shipments', 'kg', 'ldm', 'PW DSV'])
            # with col2:

            #         fig_ship = px.line(df4, x='Month', y='Shipments', markers=True)
            #         fig_ship.update_layout(
            #             title='Monthly Shipments', 
            #             xaxis_title='Month',
            #             yaxis_title='Number of Shipments'
            #         )

            #         fig_kg = px.line(df4, x='Month', y='kg', markers=True)
            #         fig_kg.update_layout(title=' Kg per month', xaxis_title='Month', yaxis_title='KG')

            #         fig_ldm = px.line(df4, x='Month', y='ldm', markers=True)
            #         fig_ldm.update_layout(title=' ldm per month', xaxis_title='Month', yaxis_title='Meters')

            #         fig_pw = px.line(df4, x='Month', y='PW DSV', markers=True)
            #         fig_pw.update_layout(title=' Pay Weight per month', xaxis_title='Month', yaxis_title='Kg')

            #         if metric == 'Shipments':
            #             st.plotly_chart(fig_ship)
            #         elif metric == 'kg':
            #             st.plotly_chart(fig_kg)
            #         elif metric == 'ldm':
            #             st.plotly_chart(fig_ldm)
            #         elif metric == 'PW DSV':
            #             st.plotly_chart(fig_pw)


    # with col2:
    #         st.title("  :bar_chart: Shipment per bracket ")
    #         my_list = sorted(data["Bracket"].tolist())
    #         count = Counter(my_list)
    #         total_items = sum(count.values())
    #         count_list = list(count.items())
    #         count_percentage_list = [(item, count, f"{round((count / total_items) * 100, 2)}%") for item, count in count.items()]
    #         df = pd.DataFrame(count_percentage_list, columns=['bracket', 'Count', 'percentage'])
    #         fig = px.bar(df, x='bracket', y='Count',color_discrete_sequence=['#002664'], text='percentage')
    #         fig.update_layout(
                
    #             xaxis_title='Bracket',
    #             yaxis_title='Count',
    #             xaxis=dict(type='category')  
    #         )
    #         st.plotly_chart(fig)
    #         st.title("")
    #         st.table(df.describe())


# Page for basic data analysis
elif selected == "Maps":
    st.write("**Filters option**")
    
    data = load_data()

    col1,col2=st.columns([1,7],gap="large")         
    with col1:
        if not data.empty:
                
                selected_branch = st.multiselect('Select branch', options=data['Branch'].unique())
                selected_level = st.selectbox('Select a level', ["country level", "Nuts1", "Nuts2", "Nuts3"])
                produit= st.multiselect('Select type of product', options=data['Product'].unique())
                data=data[(data['Product'].isin(produit) if produit else data['Product'].notnull())&
                    (data['Branch'].isin(selected_branch) if selected_branch else data['Branch'].notnull())]
                m= folium.Map(location=[54.5260,15.2551],zoom_start=4,width='100%', control_scale=True)
                m1= folium.Map(location=[54.5260,15.2551],zoom_start=4,width='100%', control_scale=True)
                if st.checkbox('show DSV branches'):
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
                     

                        folium.Marker(
                        location=location,
                        tags=[dsv["Country"].iloc[k]],
                        icon=folium.Icon(color='darkblue',icon_color='White', icon="info-sign"),
                        tooltip=dsv["Office Name"].iloc[k] + " , click for more information",
                        popup = folium.Popup(iframe, max_width=500)).add_to(m1)
                    TagFilterButton(categories).add_to(m)
                    TagFilterButton(categories).add_to(m1) 

        df7=data.groupby(['ZC from']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
        df7=df7.rename(columns={'Date' : 'Number of shipments'})
        df7=df7.sort_values(by="Number of shipments",ascending= False )
        df7=df7.head(10)
        df7=df7.sort_values(by="Number of shipments",ascending= True )
        df7 = df7.reset_index()
        fig = px.bar(df7, y='ZC from', x='Number of shipments', 
        color='Number of shipments', 
        color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
        orientation='h',
        hover_data={'kg': True, 'ldm': True})  
        fig.update_layout(
        xaxis_title='Shipments',  
        yaxis_title='',
        height=300,
        title="Top 10 collections ZC" )
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, height=50)

        df6=data.groupby(['ZC to']).agg({'Date': 'count' ,'kg': 'sum', 'ldm': 'sum', 'PW DSV': 'sum'  })
        df6=df6.rename(columns={'Date' : 'Number of shipments'})
        df6=df6.sort_values(by="Number of shipments",ascending= False )
        df6=df6.head(10)
        df6=df6.sort_values(by="Number of shipments",ascending= True )
        df6 = df6.reset_index()
        fig = px.bar(df6, y='ZC to', x='Number of shipments', 
        color='Number of shipments', 
        color_continuous_scale=['#A9BCE2','#5D7AB5','#002664'],
        orientation='h',
        hover_data={'kg': True, 'ldm': True, 'PW DSV': True})  
        fig.update_layout(
            xaxis_title='Shipments',  
            yaxis_title='',
            height=300,
            title= "Top 10 deliveries ZC")
        fig.update_coloraxes(showscale=False)
        
        st.plotly_chart(fig, use_container_width=True)
                    

        
   
    with col2:
        st.header('Map')
        tab1,tab2=st.tabs(["Outbound from a single ZC","Inbound to a single ZC"])
        with tab1:
            col3,col4=st.columns([1,9])
            with col3:
                ship_from = data['ZC from'].dropna().unique().tolist()
                selected_country = st.selectbox('Select Shipments from:', ship_from)
            with col4:
                st.empty()

            data_to = data[(data['ZC from'] == selected_country)]
            

            data_to=data_to.groupby(["ZC to"],as_index=False)["PW DSV"].sum()
            data_to=pd.merge(data_to,zip_code,on='ZC to',how="left")
            data_to['count'] = data_to.groupby('ZC to')['ZC to'].transform('count')
            data_to["PW DSV"]=(data_to["PW DSV"])/data_to["count"]

    
        

            if selected_level== "country level":
                data_to=data_to.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl0,data_to,right_on="nuts0" ,left_on="ISO2",how="right")
                colums=["nuts0","PW DSV"]
                key="properties.ISO2"
                field=["NAME","PW DSV"]
                alias=["To : ", "Value: "]
                
            
            elif selected_level== "Nuts1":
                data_to=data_to.groupby(["nuts1"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl1,data_to,right_on="nuts1" ,left_on="NUTS_ID",how="right")
                colums=["nuts1","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]
            elif selected_level== "Nuts2":
                data_to=data_to.groupby(["nuts2"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl2,data_to,right_on="nuts2" ,left_on="NUTS_ID",how="right")
                colums=["nuts2","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]
            elif selected_level== "Nuts3":
                data_to=data_to.groupby(["NUTS3"],as_index=False)["PW DSV"].sum()
                merge=pd.merge(levl3,data_to,right_on="NUTS3" ,left_on="NUTS_ID",how="right")
                colums=["NUTS3","PW DSV"]
                key="properties.NUTS_ID"
                field=["NUTS_NAME","NUTS_ID","PW DSV"]
                alias=["To: " ,"NUTS_ID: ",  "Value: "]

    
            
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

            with tab2:
                col3,col4=st.columns([1,9])
                with col3:
                    ship_to=data['ZC to'].dropna().unique().tolist()
                    selected_country_to = st.selectbox('Select Shipments to:', ship_to)
                with col4:
                    st.empty()
                data_to = data[(data['ZC to'] == selected_country_to)]

                data_to=data_to.groupby(["ZC from"],as_index=False)["PW DSV"].sum()
                data_to=pd.merge(data_to,zip_code,right_on='ZC to',left_on="ZC from",how="left")
                data_to['count'] = data_to.groupby('ZC from')['ZC from'].transform('count')
                data_to["PW DSV"]=(data_to["PW DSV"])/data_to["count"]

        
            

                if selected_level== "country level":
                    data_to=data_to.groupby(["nuts0"],as_index=False)["PW DSV"].sum()
                    merge_to=pd.merge(levl0,data_to,right_on="nuts0" ,left_on="ISO2",how="right")
                    colums=["nuts0","PW DSV"]
                    key="properties.ISO2"
                    field=["NAME","PW DSV"]
                    alias=["From : ", "Value: "]
                    
                
                elif selected_level== "Nuts1":
                    data_to=data_to.groupby(["nuts1"],as_index=False)["PW DSV"].sum()
                    merge_to=pd.merge(levl1,data_to,right_on="nuts1" ,left_on="NUTS_ID",how="right")
                    colums=["nuts1","PW DSV"]
                    key="properties.NUTS_ID"
                    field=["NUTS_NAME","NUTS_ID","PW DSV"]
                    alias=["From: " ,"NUTS_ID: ",  "Value: "]
                elif selected_level== "Nuts2":
                    data_to=data_to.groupby(["nuts2"],as_index=False)["PW DSV"].sum()
                    merge_to=pd.merge(levl2,data_to,right_on="nuts2" ,left_on="NUTS_ID",how="right")
                    colums=["nuts2","PW DSV"]
                    key="properties.NUTS_ID"
                    field=["NUTS_NAME","NUTS_ID","PW DSV"]
                    alias=["From: " ,"NUTS_ID: ",  "Value: "]
                elif selected_level== "Nuts3":
                    data_to=data_to.groupby(["NUTS3"],as_index=False)["PW DSV"].sum()
                    merge_to=pd.merge(levl3,data_to,right_on="NUTS3" ,left_on="NUTS_ID",how="right")
                    colums=["NUTS3","PW DSV"]
                    key="properties.NUTS_ID"
                    field=["NUTS_NAME","NUTS_ID","PW DSV"]
                    alias=["From: " ,"NUTS_ID: ",  "Value: "]

        
                
                choropleth1=folium.Choropleth(
                geo_data=merge_to,
                name="choropleth",
                data=merge_to,
                columns=colums,
                key_on=key,
                fill_color='Blues',
                fill_opacity=0.7,
                legend=True,
                highlight=True,                   
                ).geojson.add_to(m1)

                folium.features.GeoJson(
                                data=merge_to,
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
                                    ).add_to(choropleth1)
                if selected_country_to == selected_country_to :
                    try:
                        nuts_of_the_ZC=zip_code["NUTS3"].loc[zip_code["ZC to"]==selected_country_to]
                        polygon = levl3['geometry'].loc[levl3["NUTS_ID"]==(nuts_of_the_ZC.tolist()[0])]
                        centroid = polygon.centroid
                        long=centroid.x.tolist()[0]
                        lat=centroid.y.tolist()[0]
                        folium.Marker([lat, long],icon=folium.Icon(color='blue', ), tooltip=f" To {selected_country_to}").add_to(m1)
                    except Exception :
                        print ("error")
                Fullscreen(position="topleft").add_to(m1)
                html_string = m1.get_root().render()
                
                folium_static(m1, height=700,width=1200)
                
                def create_download_button(html_string, filename):
                        b64 = base64.b64encode(html_string.encode()).decode()
                        href = f'<a href="data:text/html;base64,{b64}" download="{filename}">Download this the map </a>'
                        return href
                st.markdown(create_download_button(html_string, "map.html"), unsafe_allow_html=True)
            

                    
            
                    
        

        
        



if 'uploaded_file' not in st.session_state:
     st.session_state['uploaded_file'] = None
