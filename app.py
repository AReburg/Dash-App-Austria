# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
from urllib.request import urlopen
import pandas as pd

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import chardet  # ! pip install chardet
import gunicorn
# loop over the list of csv files
import os
from scripts import data_wrangling


token = open(".mapbox_token").read() # you will need your own token


pd.set_option('display.max_columns', None)
df = data_wrangling.get_data()
print(df.columns)


app = Dash(__name__)
server = app.server

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

app.layout = html.Div([

    html.Div([
        html.Div([html.Img(src=app.get_asset_url('logo.png'), height='40 px', width='auto')],
                className = 'col-2', style = {
                        'align-items': 'center',
                        'padding-top' : '1%',
                        'height' : 'auto'}),
        html.H2('DASH - AUSTRIA in NUMBERS'),
        html.P("Select different categories and track the numbers over time."),
        html.Div([dcc.Dropdown(
            ['2002','2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017',
             '2018', '2019', '2020', '2021', '2022'],
            placeholder="Select a year", id='year', value="2013",
        )], className='Select-value'),

        html.P("Select category:"),
        html.Div([dcc.Dropdown(
            ["Bevölkerung Alter", "Familie nach Typ", "Bevölkerung Staatsangehörigkeit", "Bevölkerung absolut", "Fläche"],
            placeholder="Select geospatial resolution", id='cat_data', value="Bevölkerung Alter",
        )], className='Select-value'),

        html.P("Select geospatial resolution:"),
        html.Div([dcc.Dropdown(
            ["Gemeinde", "Bezirk", 'Bundesland'],
            placeholder="Select geospatial resolution", id='resolution', value="Gemeinde",
        )], className='Select-value'),
        html.Br(),
        html.A(
            href="https://github.com/AReburg/", target="_blank",
            children=[
                html.Img(
                    alt="My Github",
                    src=app.get_asset_url('githublogo.png'), height='23 px', width='auto'
                )
            ]
        ),

        ], className='four columns div-user-controls'),


    html.Div([
        html.Div([
            dcc.Graph(id="graph", hoverData={'points': [{'customdata': '50407'}]}, figure={}, config={'displayModeBar': 'hover'}),
        ], className='dash-graph'), # #dcc.Graph(id='y-time-series'),
        html.Div(["Time-series of the selected category:"], className='text-padding'),
        html.Div([dcc.Graph(id='y-time-series'), ], className='dash-graph')   #
    ], className='eight columns div-for-charts bg-grey')
    # html.Div([dcc.Graph(id='x-time-series')]),   html.Pre(id='hover-data', style=styles['pre']),
])


@app.callback(
    Output("graph", "figure"),
    [Input("year", "value"), Input("cat_data", "value"), Input("resolution", "value")])
def display_choropleth(year, cat_data, resolution):
    if cat_data == "Bevölkerung Alter":
        value = "bevölkerung_nach_alter"
    elif cat_data == "Bevölkerung Staatsangehörigkeit":
        value = "bevölkerung_nach_staatsangehörigkeitsgruppen_abs"
    elif cat_data == "Bevölkerung absolut":
        value = "bevölkerungsstand"
    elif cat_data == "Fläche":
        value = "FL"
    elif cat_data == "Familie nach Typ":
        value = "familien_nach_typ_abs"


    dfo = df.query(f'year == "{year}"') # df[df.year.categories == [year]]
    # dfo = dfk.groupby([year])# .get_group(str(year))

    feat_key = ''
    locations = ''
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

    fig = px.choropleth_mapbox(dfo, geojson=data_wrangling.get_geo_data(sel, source='offline'), locations=locations,
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
    fig.update_layout(
            font=dict(family="Open Sans"),
            coloraxis_colorbar_title='€/m²',
            legend_font_size=14
            )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_yaxes(linewidth=1, linecolor='LightGrey', gridwidth=1, gridcolor='LightGrey', mirror=True,
                     ticks='outside', showline=True)
    return fig

"""@app.callback(
    Output('hover-data', 'children'),
    Input('graph', 'hoverData'))
def display_hover_data(hoverData):
    return json.dumps(hoverData, indent=2)"""

@app.callback(
    Output('y-time-series', 'figure'),
    Input('graph', 'hoverData'),
    Input("cat_data", "value"), Input("resolution", "value"))
def update_x_timeseries(hoverData, cat_data, resolution):
    id = hoverData['points'][0]['customdata'][0]
    if cat_data == "Bevölkerung Alter":
        value = "bevölkerung_nach_alter"
    elif cat_data == "Bevölkerung Staatsangehörigkeit":
        value = "bevölkerung_nach_staatsangehörigkeitsgruppen_p"
    elif cat_data == "Bevölkerung absolut":
        value = "bevölkerungsstand"
    elif cat_data == "Fläche":
        value = "FL"
    elif cat_data == "Familie nach Typ":
        value = "familien_nach_typ_abs"

    if resolution == "Gemeinde":
        dff = df[(df['ID'] == id) & (df[value] > 0)]#[['ID', 'year', value]]
        dff = dff.groupby(['year']).agg({'ID':'first','year':'first', value:'first'})  #dff = dff.groupby(['year']).groupby(['year']).get_group(str(year))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=dff['year'], y=dff[value], showlegend=False,  line=dict(
                    color='#2c6e81',
                    width=5))) #line_color="#2c6e81"
    fig.update_layout(
            font=dict(family="Open Sans"),
            legend_font_size=14)
    fig.update_yaxes(tickfont=dict(family='Helvetica', size=17, color='#9c9c9c'), titlefont=dict(size=19), title_font_color='#9c9c9c', title_text=cat_data, mirror=True,
    ticks='outside', showline=True, gridwidth=1, gridcolor='#4c4c4c')
    fig.update_xaxes(tickfont=dict(family='Helvetica', size=17, color='#9c9c9c'), titlefont=dict(size=19), title_font_color='#9c9c9c', title_text="Jahre", mirror=True,
    ticks='outside', showline=True, gridwidth=1, gridcolor='#4c4c4c')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    # fig.update_layout(bordercolor='#9c9c9c', borderwidth =10)
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)

