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

def bundesland(x):
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



        #print(dfx.head())

    df = pd.concat(dfs)
    df['Wert2'] = df.apply(lambda x: bundesland(x.Wert2), axis=1)
    #df['bevölkerung'].astype('int')
    return df

df = get_df()
print(df[df['Wert2'] > 1].head())

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
            ['2008', '2009', '2021'],
            placeholder="Select a year", id='year', value="2021",
        )], className='Select-value'),

        html.P("Select geospatial resolution:"),
        html.Div([dcc.Dropdown(
            ["Bevölkerung Alter", "Bevölkerung Staatsangehörigkeit"],
            placeholder="Select geospatial resolution", id='resolution', value="Bevölkerung Alter",
        )], className='Select-value'),

       # dcc.RadioItems(
       #     id='resolution',
       #     options=["municipal", "district", 'state'],
       #     value="state",
       #     inline=True
       # ),
        html.P("Total number of properties: 98.000"),
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
    [Input("year", "value"), Input("resolution", "value")])
def display_choropleth(year, resolution):

    dfo = df.groupby(['year']).get_group(str(year))  # as_index = False #.index.get_level_values('Name') # .agg({'Name':'first','Abgegebene':'sum',
    if resolution == "Bevölkerung Alter":
        value = "bevölkerung"
        print(dfo.head())
    elif resolution == "Bevölkerung Staatsangehörigkeit":
        print("value should be wert2")
        print(dfo['Wert2'].isnull().sum())
        print(dfo.head())
        value = "Wert2"


    feat_key = ''
    locations = ''
    selector = 'municipal'
    if selector == 'municipal':
        feat_key = "properties.iso"
        locations = "ID"

    print(df[value].min())
    print(df[value].max())
    print(df[df[value]>40].head())
    fig = px.choropleth_mapbox(dfo, geojson=get_geo_data(selector, source='offline'), locations=locations,
                               featureidkey=feat_key, color=value,
                               color_continuous_scale="Viridis",
                               range_color=(df[value].min(), df[value].max()),
                               mapbox_style="carto-positron",
                               zoom=6, center={"lat": 47.809490, "lon": 13.055010},
                               opacity=0.85,
                              )

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