from codequick import Route, Listitem, run, Script, utils, Resolver
from bs4 import BeautifulSoup
import requests
import json
import re
import datetime

# Base url constructor
url_constructor = utils.urljoin_partial("https://www.caracoltv.com")

# Base items constructor
dict_constructor = [
    {"label": "Señal en vivo HD", "art": "telextrema.png", "url": "/senal-vivo", "id": "live"},
    {"label": "Programas", "art": "canalDeportivo.png", "url": "/programas", "id": "programs"},
    {"label": "Buscar", "art": "futbolLibre.png", "url": "futbolLibre", "id": "search"}
]


@Route.register
def root(plugin):
    for elem in dict_constructor:
        item = Listitem()
        item.label = elem["label"]
        # item.art.local_thumb(elem["art"])
        if(elem["id"] == "live"):
            p = en_vivo(uri=elem["url"])
            # Script.log(str(p), None, Script.INFO)
            item.info["plot"] = "La red"
            item.set_path(p["stream"])
        elif(elem["id"] == "programs"):
            item.set_callback(categorias, uri=elem["url"])
        yield item

@Route.register
def categorias(plugin, uri):
    item = Listitem()
    item.label = "Todos los programas"
    item.set_callback(programas, uri=url_constructor(uri))
    yield item
    
    url = url_constructor(uri)
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        categorias = soup.find_all('li', {"class": "ListTags-items-item"})
        for categoria in categorias:
            item = Listitem()
            item.label = categoria.text
            url = categoria.find('a').get('href')
            item.set_callback(programas, uri=url)
            yield item
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
    
@Route.register
def programas(plugin, uri):
    url = uri
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        programas = soup.find_all('div', {"class":"PromoMedia"})
        
        for programa in programas:
            item = Listitem()
            item.info.mediatype = "tvshow"
            titulo =  programa.find('span', {'class', 'Link-Media'}).text
            item.info.tvshowtitle = titulo
            item.label = titulo
            item.art["thumb"] = programa.find('img')["data-src"]
            url = programa.find('a').get('href')
            item.set_callback(capitulos, url=url, titulo=titulo)
            yield item
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
        
@Route.register
def capitulos(plugin, url, titulo):
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        capitulos = soup.find_all('ps-promo', {"class":"PromoB"})
        
        for capitulo in capitulos:
            item = Listitem()
            item.info.mediatype = "episode"
            item.info.tvshowtitle = titulo
            item.label = capitulo.find('a')["title"]
            item.info.plot = capitulo.find('h3', {"class":"PromoB-description"}).text
            # item.date = capitulo.find('div', {"class":"PromoB-timestamp"})["data-timestamp"]
            item.art["thumb"] = capitulo.find('img')["data-src"]
            url = capitulo.find('a').get('href')
            item.set_callback(play_video_show, url=url)
            yield item
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)

def en_vivo(uri):
    live_dict =  {
        "programas": [],
        "stream": ""
    }
    url = url_constructor(uri)
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Encuentra el div que contiene el atributo data-schedule
        schedule_div = soup.find('div', {"class":"PlayListItem"})
        
        if schedule_div:
            data_schedule = schedule_div.get('data-schedule')  # Extrae el valor del atributo
            programs = json.loads(data_schedule)
            
            for program in programs:
                programa = {
                    "titulo": program['title'],
                    "inicio": program['startTime'],
                    "fin": program['endTime']
                }
                live_dict["programas"].append(programa)

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
            
            r = requests.get(url)
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
                        
                        # Accede a la URL HLS
                        hls_url = options_data['src']['hls']
                        
                        live_dict["stream"] = hls_url
                        return live_dict
                    else:
                        Script.notify("Error", "No se encontró la configuración de OPTIONS en el script.", Script.NOTIFY_ERROR)
                else:
                    Script.notify("Error", "No se encontró el script que contiene 'window.MDSTRM'.", Script.NOTIFY_ERROR)
            else:
                Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
    
@Resolver.register
def play_video_show(plugin, url):

    r = requests.get(url)
    
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
            
            r = requests.get(url)
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
                        
                        # Accede a la URL HLS
                        hls_url = options_data['src']['hls']
                        
                        return hls_url
                    else:
                        Script.notify("Error", "No se encontró la configuración de OPTIONS en el script.", Script.NOTIFY_ERROR)
                else:
                    Script.notify("Error", "No se encontró el script que contiene 'window.MDSTRM'.", Script.NOTIFY_ERROR)
            else:
                Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)