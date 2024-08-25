from codequick import Script, Resolver, utils
from bs4 import BeautifulSoup
import requests
import json
import re

def get_cast(url):
    p = []
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        # Encuentra el elemento <a> que contiene el texto "Personajes"
        enlace_personajes = soup.find('a', string='Personajes')

        # Verifica si se encontró el enlace y muestra el resultado
        if enlace_personajes:
            r = requests.get(enlace_personajes['href'])
        
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                personajes = soup.find_all('ps-promo', {"class":"PromoG"})
                
                for personaje in personajes:
                    nombre = personaje.find('div', {"class": "PromoG-content"}).find('a').text.strip()
                    actor = personaje.find('div', {"class": "PromoG-description"}).text.strip()
                    foto = personaje.find('div', {"class": "PromoG-media"}).find("img")["data-src"].strip()
                    p.append({
                        "role": nombre,
                        "name": actor.replace("Interpretado por:", "").replace("Interpretada por:", "").strip(),
                        "thumbnail": foto
                    })    
    return p

def embedUrl_MDSTRM(uri):
    
    r = requests.get(uri)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
                
        # Busca el script que contiene la configuración de MDSTRM
        script_tag = soup.find('script', text=re.compile('window.MDSTRM'))
                
        if script_tag:
            # Extrae el contenido del script
            script_content = script_tag.string
                    
            # Busca la parte que contiene la configuración de OPTIONS
            options_match = re.search(r'window\.MDSTRM\.OPTIONS\s*=\s*(\{.*?\});', script_content, re.DOTALL)
                    
            if options_match:
                # Convierte el string JSON a un objeto de Python
                options_data = json.loads(options_match.group(1))
                return options_data
    else:
        return None

def en_vivo(uri):
    r = requests.get(uri)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        # Encuentra el div que contiene el data-mediastream
        media_stream_div = soup.find('div', class_='MediaStreamVideoPlayer-media')
        
        if media_stream_div:
            # Extrae el atributo data-mediastream
            data_mediastream = media_stream_div.get('data-mediastream')
            
            # Convierte el string JSON a un objeto de Python
            media_stream_data = json.loads(data_mediastream)
            
            first_stream = media_stream_data[0]
            source_url = first_stream['sourceUrl']
            video_id = first_stream['videoId']
            
            url = f"{source_url}{video_id}"            
            return embedUrl_MDSTRM(url)
    else: 
        return None

def iso8601_duration_to_seconds(duration):
    total_seconds = 0
    if duration.startswith('PT'):
        duration = duration[2:]
        time_parts = duration.split('H')
        if len(time_parts) > 1:
            hours = int(time_parts[0])
            total_seconds += hours * 3600
            duration = time_parts[1]
        time_parts = duration.split('M')
        if len(time_parts) > 1:
            minutes = int(time_parts[0])
            total_seconds += minutes * 60
            duration = time_parts[1]
        if duration.endswith('S'):
            seconds = int(duration[:-1])
            total_seconds += seconds
    return total_seconds
 
def play_video_show(url):
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Encuentra todos los scripts de tipo application/ld+json
        scripts = soup.find_all('script', type='application/ld+json')

        # Itera sobre los scripts y busca el que contiene el NewsArticle
        for script in scripts:
            json_data = json.loads(script.string)
            if "video" in json_data:
                return json_data.get('video')
            elif json_data.get('@type') == 'VideoObject':
                return json_data
            else:
                None
            
    else:
        return None
        
@Resolver.register
def play_youtube_video(plugin, url):
    # Extract a playable video url using youtubeDL
    return plugin.extract_source(url)