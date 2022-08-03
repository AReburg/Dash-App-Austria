# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
from urllib.request import urlopen
import pandas as pd
import numpy as np
import plotly.express as px
import json
import chardet  # ! pip install chardet
import gunicorn
import re
# loop over the list of csv files
import os
import glob

token = open(".mapbox_token").read() # you will need your own token


def bundesland(k):
    if k == 'Sa':
        return 'Salzburg'
    elif k == 'St':
        return 'Steiermark'
    elif k == 'W':
        return 'Wien'
    elif k == 'T':
        return 'Tirol'
    elif k == 'V':
        return 'Vorarlberg'
    elif k == 'K':
        return 'Kärnten'
    elif k == 'O':
        return 'Oberösterreich'
    elif k == 'N':
        return 'Niederösterreich'
    elif k == 'B':
        return 'Burgenland'

def get_value(x):
    m = re.findall(r'\d+\.\d+', str(x))
    if x== np.nan:
        return 0
    elif len(m) >0:
        return float(m[0])
    else:
        return 0


def get_df():
    csv_files = glob.glob("*.csv")
    # print(csv_files)
    dfs = []

    for f in csv_files:
        dfx = pd.read_csv(f, sep=';', index_col=False, header=6)
        dfx['year'] = re.findall(r"[0-9]{3,4}(?![0-9])", f)[0]
        if f.find("nach_staatsangehörigkeitsgruppen") > 0:
            #print(f)
            dfx['Wert2'] = dfx['%']
            try:
                dfx = dfx.drop(['Unnamed: 4'], axis=1)
            except:
                pass
            dfs.append(dfx)

        elif f.find("bevölkerung_nach_alter") > 0:
            dfx['bevölkerung'] = dfx['Wert']
            try:
                dfx = dfx.drop(['Unnamed: 3'], axis=1)
            except:
                pass
            dfs.append(dfx)
        elif f.find("bevölkerungsstand") > 0:
            dfx['bevölkerungsstand'] = dfx['Wert']
            dfs.append(dfx)

    df = pd.concat(dfs)
    df['Wert2'] = df.apply(lambda x: get_value(x.Wert2), axis=1)
    #df['bevölkerung'].astype('int')
    return df


def merge_geospatial_look_up(dfy):
    with open(r'./data/PLZ_BESTIMMUNGSORT-20220629.csv', 'rb') as rawdata:
        result = chardet.detect(rawdata.read(10000))
    tmp = pd.read_csv(r'./data/PLZ_BESTIMMUNGSORT-20220629.csv', sep=';', encoding=result['encoding'])
    tmp.rename(columns={'GEMNR': 'ID'}, inplace=True)
    df2 = tmp.groupby(['ID'], as_index=False).agg(
        {'ID': 'first', 'Bestimmungsort': 'first', 'OKZ': 'first', 'Ortschaft': 'first', 'PLZ': 'first',
         'GEMNAM': 'first'})
    with open(r'./data/PLZ_BESTIMMUNGSORT-20220629.csv', 'rb') as rawdata:
        result = chardet.detect(rawdata.read(10000))
    plz = pd.read_csv(r'./data/PLZ_Verzeichnis-20220629.csv', sep=';', encoding=result['encoding'])
    plz['Bundesland'] = plz.apply(lambda x: bundesland(x.Bundesland), axis=1)
    #df2 = df2.merge(plz[['Bundesland', 'PLZ']], on=['PLZ'], how='left')  # plz

    # get bezirk information
    with open(r'./data/counties_lookup.csv', 'rb') as rawdata:
        result = chardet.detect(rawdata.read(10000))
    bezirk = pd.read_csv(r'./data/counties_lookup.csv', sep=';', encoding=result['encoding'])

    print("Bezirk:")
    print(bezirk.columns)
    print(bezirk.head())
    df2 = df2.merge(bezirk[['PLZ', 'Bezirk']], on=['PLZ'], how='left') #plz

#    ort = df2.merge(plz[['PLZ', 'Ort', 'Bundesland', 'Bezirk']], on=['PLZ'], how='left')




    #dfy['plz'] = dfy.plz.fillna(0).astype("int64")
#    print(ort.columns)

    # merge with iso geoinformation
    dfz = dfy.merge(df2[['PLZ', 'ID', 'Ortschaft']], on=['ID'], how='outer') #, 'Bundesland', 'Bezirk'
    print(dfz[dfz['ID']==40809].head())
    dfz = dfz.merge(bezirk[['PLZ', 'Bezirk']], on=['PLZ'], how='left')  # plz
    dfz = dfz.merge(plz[['PLZ', 'Bundesland']], on=['PLZ'], how='left')
    print("Merged in Bezirk:")
   # print(df2.columns)
   # print(df2.head())


    # df['code'] = df['code'].astype("category")
    dfz['PLZ'] = dfz['PLZ'].astype("category")
    dfz['ID'] = dfz.ID.fillna(0).astype("int64")
    dfz['ID'] = dfz['ID'].astype("category")

    #dfz.dropna(subset=['Bundesland'], axis=0, inplace=True)
    return dfz


df = get_df()
df = merge_geospatial_look_up(df)
print(df.columns)
#print(df[df['Wert2'] > 1].head())

def get_geo_data(selector, source='online'):
    """ Load Austrian geojson"""
    if selector == 'municipal':
        if source == 'online':
            link = 'https://raw.githubusercontent.com/ginseng666/GeoJSON-TopoJSON-Austria/master/2021/simplified-99.5/gemeinden_995_geo.json'
            with urlopen(link, encoding='utf8') as response:
                counties = json.load(response)
        else:
            with open("./data/gemeinden_999_geo.json", encoding='utf8') as a:
                counties = json.load(a)
    elif selector == 'district':
        if source == 'online':
            link = 'https://raw.githubusercontent.com/ginseng666/GeoJSON-TopoJSON-Austria/master/2021/simplified-99.9/bezirke_999_geo.json'
            with urlopen(link, encoding='utf8') as response:
                counties = json.load(response)
        else:
            with open("./data/bezirke_999_geo.json", encoding='utf8') as a:
                counties = json.load(a)
    elif selector == 'state':
        if source == 'online':
            link = 'https://raw.githubusercontent.com/ginseng666/GeoJSON-TopoJSON-Austria/master/2021/simplified-99.9/laender_999_geo.json'
            with urlopen(link, encoding='utf8') as response:
                counties = json.load(response)
        else:
            with open("./data/laender_999_geo.json", encoding='utf8') as a:
                counties = json.load(a)
    return counties

app = Dash(__name__)

server = app.server

app.layout = html.Div([

    html.Div([
        html.Div([html.Img(src=app.get_asset_url('logo.png'), height='40 px', width='auto')],
                className = 'col-2', style = {
                        'align-items': 'center',
                        'padding-top' : '1%',
                        'height' : 'auto'}),

        html.H2('DASH - AUSTRIA in NUMBERS'),
        html.P("Select different categories and track the numbers over time."),
        # html.P("Select a property type:"),
        #dcc.RadioItems(
        #    id='property_type',
        #    options=["rented_flat", "single_family_homes", 'condominium'],
        #    value="rented_flat",
        #    inline=True
        #),
        html.Div([dcc.Dropdown(
            ['2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017',
             '2018', '2019', '2020', '2021', '2022'],
            placeholder="Select a year", id='year', value="2021",
        )], className='Select-value'),

        html.P("Select category:"),
        html.Div([dcc.Dropdown(
            ["Bevölkerung Alter", "Bevölkerung Staatsangehörigkeit", "Bevölkerung absolut"],
            placeholder="Select geospatial resolution", id='cat_data', value="Bevölkerung Alter",
        )], className='Select-value'),

        html.P("Select geospatial resolution:"),
        html.Div([dcc.Dropdown(
            ["Gemeinde", "Bezirk", 'Bundesland'],
            placeholder="Select geospatial resolution", id='resolution', value="Gemeinde",
        )], className='Select-value'),

       # dcc.RadioItems(
       #     id='resolution',
       #     options=["municipal", "district", 'state'],
       #     value="state",
       #     inline=True
       # ),
        html.P(""),
        html.P(""),
        html.P(""),
        html.A(
            href="https://github.com/AReburg/Austrian-Real-Estate-Analysis", target="_blank",
            children=[
                html.Img(
                    alt="Link to my Github",
                    src=app.get_asset_url('github_inverted.svg'), height='40 px', width='auto'
                )
            ]
        ),

        ], className='four columns div-user-controls'),




    html.Div([
        dcc.Graph(id="graph", figure={}, config={'displayModeBar': 'hover'}),
        #html.Div([
        #    dcc.RangeSlider(-5, 6,
        #        marks={i: f'Label{i}' for i in range(-5, 7)},
        #        value=[-3, 4]
        #    )
        #])
    ], className='eight columns div-for-charts bg-grey')
])


@app.callback(
    Output("graph", "figure"),
    [Input("year", "value"), Input("cat_data", "value"), Input("resolution", "value")])
def display_choropleth(year, cat_data, resolution):

    dfo = df.groupby(['year']).get_group(str(year))  # as_index = False #.index.get_level_values('Name') # .agg({'Name':'first','Abgegebene':'sum',
    if cat_data == "Bevölkerung Alter":
        value = "bevölkerung"
        print(dfo.head())
    elif cat_data == "Bevölkerung Staatsangehörigkeit":
        print("value should be wert2")
        print(dfo['Wert2'].isnull().sum())
        print(dfo.head())
        value = "Wert2"
    elif cat_data == "Bevölkerung absolut":
        print("value should be bevölkerungsstand")
        print(dfo['bevölkerungsstand'].isnull().sum())
        value = "bevölkerungsstand"

    print(df.shape[0])
    feat_key = ''
    locations = ''
    # selector = 'municipal'
    hover_data = ''
    sel = ''
    if resolution == "Gemeinde":
        feat_key = "properties.iso"
        locations = "ID"
        hover_data = ["ID", "Ortschaft", "PLZ", "Bezirk", "Bundesland"]
        hover_name = "ID"
        opacity = 0.85
        sel = 'municipal'

    elif resolution == 'Bezirk':
        feat_key = "properties.name"
        locations = "Bezirk"
        hover_data = ["Bundesland", "Bezirk"]
        hover_name = "Bezirk"
        opacity = 0.55
        sel = 'district'

    elif resolution == 'Bundesland':
        feat_key = "properties.name"
        locations = "Bundesland"
        hover_data = ["Bundesland"]
        hover_name = "Bundesland"
        opacity = 0.55
        sel = 'state'


   # print(df[value].min())
   # print(df[value].max())
   # print(df[df[value]>40].head())
    fig = px.choropleth_mapbox(dfo, geojson=get_geo_data(sel, source='offline'), locations=locations,
                               featureidkey=feat_key, color=value,
                               color_continuous_scale="Viridis",
                               range_color=(df[value].min(), df[value].max()),
                               mapbox_style="carto-positron",
                               hover_data=hover_data,
                               hover_name=hover_name,
                               zoom=6, center={"lat": 47.809490, "lon": 13.055010},
                               opacity=opacity,
                              )

    fig.update_layout(mapbox_style="dark", mapbox_accesstoken=token)
    fig.update_layout(# width=1000, height=600,
            # title_text=format_title(title[0], f"{title[1]}"),
            font=dict(family="Open Sans"),
            coloraxis_colorbar_title='€/m²'
            )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig


# Run flask app
if __name__ == "__main__":
    app.run_server(debug=True)
    # display_choropleth('2008', "a")