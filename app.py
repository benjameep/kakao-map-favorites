import streamlit as st
import requests
import pandas as pd
import json
from random import randint

st.title('Kakao Map Favorites')
KAKAO_HEADERS = { 'Authorization': 'KakaoAK d483260577bb08226008023b36bc9c3d' }

@st.cache_data
def get_folder_list(kawlt):
    headers = {
        'Cookie': f'_kawlt={kawlt}',
        'Referer': 'https://map.kakao.com/'
    }
    response = requests.get('https://map.kakao.com/folder/list.json?sort=CREATE_AT', headers=headers)
    data = response.json()
    if data['status']['code'] != 'SUCCESS':
        st.error('Failed to fetch folder list')
        st.json(data['status'])
        st.stop()
    return data.get('result')

@st.cache_data
def get_folder_items(kawlt, folder_id):
    headers = {
        'Cookie': f'_kawlt={kawlt}',
        'Referer': 'https://map.kakao.com/'
    }
    params = {
        'folderIds[]': folder_id,
        'type': 'M',
    }
    response = requests.get(f'https://map.kakao.com/favorite/list.json', params=params, headers=headers)
    data = response.json()
    if data['status']['code'] != 'SUCCESS':
        st.error('Failed to fetch folder items')
        st.json(data['status'])
        st.stop()
    return data.get('result')

def add_favorites(kawlt, data):
    headers = {
        'Cookie': f'_kawlt={kawlt}',
        'Referer': 'https://map.kakao.com/'
    }
    response = requests.post('https://map.kakao.com/favorite/add.json', json=data, headers=headers)
    data = response.json()
    if data['status']['code'] != 'SUCCESS':
        st.error('Failed to add favorites')
        st.json(data['status'])
        st.stop()

@st.cache_data
def lat_long_to_wcongnamul(lat, long):
    url = "https://dapi.kakao.com/v2/local/geo/transcoord.json"
    params = {
        "x": long,  # Longitude comes first
        "y": lat,   # Latitude comes second
        "input_coord": "WGS84",       # Input coordinate system
        "output_coord": "WCONGNAMUL" # Output coordinate system
    }
    response = requests.get(url, headers=KAKAO_HEADERS, params=params)
    data = response.json()
    if response.status_code != 200:
        st.error('Failed to fetch address')
        st.json(data)
        st.stop()
    return data['documents'][0]

kawlt = st.text_input('_kawlt cookie')
if not kawlt:
    st.write('To get the kawlt cookie value, go to [https://map.kakao.com/](https://map.kakao.com/), open the developer tools, go to the application tab, and under Storage > Cookies > map.kakao.com, copy the full value of the _kawlt cookie')
    st.image('./screenshots/kawlt.png')
    st.stop()

kawlt = kawlt.strip()
folder_list = get_folder_list(kawlt)
folder_names = { folder['folderId']: folder['title'] for folder in folder_list }
folder_id = st.selectbox('Select folder', folder_names.keys(), format_func=lambda x: folder_names[x])

folder_items = get_folder_items(kawlt, folder_id)
if folder_items:
    df = pd.DataFrame(folder_items)[['memo','display1','display2','x','y']]
    st.write('Addresses in the selected folder:')
    st.dataframe(df)
else:
    st.info('No addresses currently in the selected folder')

raw_households = st.text_input('Enter households JSON data.')
if not raw_households:
    st.write('''Go to [https://directory.churchofjesuschrist.org/api/v4/user](https://directory.churchofjesuschrist.org/api/v4/user) and copy your homeUnit number''')
    st.image('./screenshots/homeUnit.png')
    st.write('''Add your homeUnit number to the end of this url [https://directory.churchofjesuschrist.org/api/v4/households?unit=](https://directory.churchofjesuschrist.org/api/v4/households?unit=)''')
    st.image('./screenshots/households.png')
    st.write('''Copy the JSON data and paste it in the text box above''')
    st.stop()

raw_households = raw_households.strip()
households = [
    {
        'name': row['name'],
        'address1': row['address'].split('\n')[0],
        'address2': row['address'].split('\n')[1] if len(row['address'].split('\n')) > 2 else '',
        'latitude': row['coordinates']['latitude'],
        'longitude': row['coordinates']['longitude'],
    }
    for row in json.loads(raw_households)
    if 'address' in row and 'coordinates' in row
]
status_bar = st.progress(0, text='converting coordinates')
for i, household in enumerate(households):
    status_bar.progress((i+1)/len(households), text=f'converting coordinates for ' + household['name'])
    coords = lat_long_to_wcongnamul(lat=household['latitude'], long=household['longitude'])
    household['x'] = coords['x']
    household['y'] = coords['y']

st.dataframe(pd.DataFrame(households))

if st.button('Add {} addresses to the "{}" folder'.format(len(households), folder_names[folder_id])):
    add_favorites(kawlt, [
        {
            'type': 'address',
            'key': 'N3' + str(randint(1e6,1e7)),
            'display1': household['address1'],
            'display2': household['address2'],
            'x': household['x'],
            'y': household['y'],
            'color': '01',
            'folderId': folder_id,
            'memo': household['name'],
        }
        for household in households
    ])
    st.success('Successfully added addresses to the "{}" folder'.format(folder_names[folder_id]))