from __future__ import division
import pandas as pd
import xlrd
import numpy as np
from plotly.offline import plot,iplot
import plotly.figure_factory as ff



sheetname = "NFIP"
sheetname1="NOAA"
sheetname2= "IA"
nfip = pd.read_excel("./Datasets/DataVizFloodsFV3_22_2017.xlsx",sheet_name=sheetname)
noaa = pd.read_excel("./Datasets/DataVizFloodsFV3_22_2017.xlsx",sheet_name=sheetname1)
nhp = pd.read_excel("./Datasets/DataVizFloodsFV3_22_2017.xlsx",sheet_name=sheetname2)


def return_fips(state_name):
    df = pd.read_csv('./Datasets/'+state_name+'.csv')
    df['state_FIPS'] = df['state_FIPS'].apply(lambda x:str(x).zfill(2))
    df['county_FIPS']= df['county_FIPS'].apply(lambda x:str(x).zfill(3))
    del df['classfp']
    df['State'] = state_name
    df['FIPS'] = df['state_FIPS']+df['county_FIPS']
    del df['state_FIPS']
    del df['county_FIPS']
    return df


def state_flood_events(noaa,state_name):
    noaa1 = noaa.copy(deep=True)
    del noaa1['Year']
    del noaa1['Lat']
    del noaa1['Lon']
    del noaa1['CountyZone']
    df = return_fips(state_name)
    df2 = pd.merge(noaa1, df, on=['State','County'])
    del df2['State']
    fips = df2['FIPS'].tolist()
    df2 = df2.groupby(['FIPS','County'], as_index=False)['NumEpisodes'].sum()
    fips = df2['FIPS'].tolist()
    values = df2['NumEpisodes'].tolist()
    endpts = list(np.mgrid[min(values):max(values):4j])
    colorscale = ["#030512","#1d1d3b","#323268","#3d4b94","#3e6ab0",
                  "#4989bc","#60a7c7","#85c5d3","#b7e0e4","#eafcfd"]
    fig = ff.create_choropleth(
        fips=fips, values=values, scope=[state_name], show_state_data=True,
        colorscale=colorscale, binning_endpoints=endpts, round_legend_values=True,
        plot_bgcolor='rgb(229,229,229)',
        paper_bgcolor='rgb(229,229,229)',
        legend_title='Flood risk by county in '+state_name,
        county_outline={'color': 'rgb(255,255,255)', 'width': 0.5}
    )
    plot(fig)

state_flood_events(noaa,'Alabama')
