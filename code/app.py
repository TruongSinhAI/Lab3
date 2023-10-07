from dash import Dash, dcc, html, Input, Output
import pandas as pd
import folium
from folium import plugins
import json
from branca.colormap import linear

# Load the crime data
df_crime = pd.read_csv("fixed_data.csv")
df_crime.rename(columns={'PdDistrict': 'DISTRICT'}, inplace=True)
# df_crime = df_crime.head(500)

# Load the GeoJSON data
with open('../lab3 san-francisco.geojson', 'r') as file:
    geo_data = json.load(file)

# Load the crime level data
crime_level = pd.read_csv('crime_level.csv')

# Create the Dash app
app = Dash(__name__)

# Define a color palette from the colorbrewer set (e.g., Blues, Greens, Reds)
color_palette = linear.PuRd_09.scale(0, crime_level['CrimeLevel'].max())  # Use the correct DataFrame

district_crime_levels = dict(zip(crime_level['DISTRICT'], crime_level['CrimeLevel']))
total_crime = crime_level['CrimeLevel'].sum()

for feature in geo_data['features']:
    district_name = feature['properties']['DISTRICT']
    crime_level2 = district_crime_levels.get(district_name, 0)  # Default to 0 if data is missing
    feature['properties']['CrimeLevel'] = crime_level2
    feature['properties']['Percentage'] = f'{round(crime_level2/total_crime * 100, 2)}%'

cache = {}
# Define a function to create a Folium map with the Choropleth layer using the color palette
def create_folium_map(selected_districts):
    # Filter the crime data based on selected districts
    filtered_data = df_crime[df_crime['DISTRICT'].isin(selected_districts)]

    # Create a map centered at San Francisco
    m = folium.Map(location=[37.77, -122.42], zoom_start=12)
    
    crime_level_fix = crime_level.copy()
    crime_level_fix.loc[~crime_level_fix['DISTRICT'].isin(selected_districts), 'CrimeLevel'] = 0

    # Add the GeoJSON layer for San Francisco neighborhoods
    folium.GeoJson(
    geo_data,
    name='San Francisco Neighborhoods',
    style_function=lambda feature: {
        'fillColor': color_palette(crime_level_fix[crime_level_fix['DISTRICT'] == feature['properties']['DISTRICT']]['CrimeLevel'].values[0]),
        'fillOpacity': 0.8,
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=['DISTRICT', 'Percentage'],
        aliases=['District','Percentage Crime'],
        labels=True,
    ),
    ).add_to(m)
    
    marker_cluster = {}
    # Create a MarkerCluster layer
    for i in range(len(selected_districts)):
        marker_cluster[i] = plugins.MarkerCluster(name = selected_districts[i]).add_to(m)

    # Add markers for filtered crime data
    for index, row in filtered_data.iterrows():
        if row['DISTRICT'] in selected_districts:
            x = selected_districts.index(row['DISTRICT'])
            folium.Marker(
                location=[row['Y'], row['X']],
                popup=row['Category'],
            ).add_to(marker_cluster[x])

    return m

# Define the layout
app.layout = html.Div([
    html.H1("Bản đồ San Francisco", style={'text-align': 'center', 'font-size': '24px'}),
    dcc.Checklist(
        id='district-checkboxes',
        options=[{'label': district, 'value': district} for district in crime_level['DISTRICT'][::-1]],
        value= crime_level['DISTRICT'],
        style={'display': 'flex', 'gap': '10px', 'padding': '10px',
               'border': '1px solid #ddd', 'border-radius': '5px', 'background-color': '#f9f9f9'}
    ),
    html.Iframe(id='crime-map', srcDoc='', width='100%', height='600', style={'border': 'none'}),

])

# Define a callback to update the map based on user input
@app.callback(
    Output('crime-map', 'srcDoc'),
    Input('district-checkboxes', 'value')
)
def update_map(selected_districts):
    
    global cache
    selected_districts.sort()
    cache_key = tuple(selected_districts)
    if cache_key in cache.keys(): 
        updated_map = cache[cache_key]
    else:
        updated_map = create_folium_map(selected_districts).get_root().render()
        cache[cache_key] = updated_map

    return updated_map


if __name__ == '__main__':
    app.run_server(port=8005, host='10.1.103.13', debug=True)
