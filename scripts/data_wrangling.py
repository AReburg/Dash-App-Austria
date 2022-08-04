# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output

from urllib.request import urlopen
import pandas as pd
pd.set_option('display.max_columns', None)
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import chardet  # ! pip install chardet
import gunicorn
import re

import os





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

def get_df_v2():

    df1 = pd.read_csv('./data/bevölkerung_nach_alter.csv', sep=',', index_col=False)
    df2 = pd.read_csv('./data/bevölkerungsstand.csv', sep=',', index_col=False)
    df3 = pd.read_csv('./data/familien_nach_typ.csv', sep=',', index_col=False)
    df4 = pd.read_csv('./data/nach_staatsangehörigkeitsgruppen.csv', sep=',', index_col=False)

    df1 = df1.merge(df2, on=['year', 'ID', 'Name'], how='outer')
    df1 = df1.merge(df3, on=['year', 'ID', 'Name'], how='outer')
    df1 = df1.merge(df4, on=['year', 'ID', 'Name'], how='outer')
    df1['bevölkerung_nach_staatsangehörigkeitsgruppen_p'] = df1['bevölkerung_nach_staatsangehörigkeitsgruppen_p'].astype(float)
    df1['bevölkerung_nach_staatsangehörigkeitsgruppen_abs'] = df1['bevölkerung_nach_staatsangehörigkeitsgruppen_abs'].astype(float)
    df1['year'] = df1[
        'year'].astype('str')
    return df1


def get_df():
    csv_files = glob.glob("*.csv")
    dfs = []

    for f in csv_files:
        dfx = pd.read_csv(f, sep=';', index_col=False, header=6)
        dfx['year'] = re.findall(r"[0-9]{3,4}(?![0-9])", f)[0]
        if f.find("familien_nach_typ") > 0:
            dfx['familien_nach_typ_p'] = dfx['%']
            dfx['familien_nach_typ_abs'] = dfx['abs.']
            dfs.append(dfx)
    df = pd.concat(dfs)
    df = df.drop(['Unnamed: 4'], axis=1)
    df = df.drop(['%'], axis=1)
    df = df.drop(['abs.'], axis=1)
    df['familien_nach_typ_p'] = df['familien_nach_typ_p'].str.replace(",", ".")
    #df = df['familien_nach_typ_p'].astype("float")
    df.to_csv("familien_nach_typ.csv", index=False)
    #df['Wert2'] = df.apply(lambda x: get_value(x.Wert2), axis=1)
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

    df2 = df2.merge(bezirk[['PLZ', 'Bezirk']], on=['PLZ'], how='left') #plz


    with open(r'./data/0003450398_100_Verwaltungseinheiten_KG_2021.csv', 'rb') as rawdata:
        result = chardet.detect(rawdata.read(10000))
    verwaltungseinheit = pd.read_csv(r'./data/0003450398_100_Verwaltungseinheiten_KG_2021.csv', sep=';', encoding=result['encoding'])
    verwaltungseinheit.rename(columns={'GKZ': 'ID'}, inplace=True)
    # merge with iso geoinformation
    dfz = dfy.merge(df2[['PLZ', 'ID', 'Ortschaft']], on=['ID'], how='outer') #, 'Bundesland', 'Bezirk'
    dfz = dfz.merge(bezirk[['PLZ', 'Bezirk']], on=['PLZ'], how='left')  # plz
    dfz = dfz.merge(plz[['PLZ', 'Bundesland']], on=['PLZ'], how='left')
    dfz = dfz.merge(verwaltungseinheit[['ID', 'FL']], on=['ID'], how='left')

    dfz['PLZ'] = dfz['PLZ'].astype("category")
    dfz['ID'] = dfz.ID.fillna(0).astype("int64")
    dfz['ID'] = dfz['ID'].astype("category")
    return dfz

def get_data():
    #df = get_df()
    df = get_df_v2()
    df = merge_geospatial_look_up(df)
    return df



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