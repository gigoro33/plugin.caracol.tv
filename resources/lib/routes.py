from codequick import Route, Listitem, Script, utils
from bs4 import BeautifulSoup
import requests
from resources.lib.utils import play_video_show, get_cast, iso8601_duration_to_seconds, play_youtube_video
from urllib.parse import urlparse, urlunparse

@Route.register
def categorias(plugin, uri):
    item = Listitem()
    item.label = "Todos los programas"
    item.set_callback(programas, uri=uri)
    yield item
    
    r = requests.get(uri)
    
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
def secciones(plugin, uri, data_show):
    r = requests.get(uri)
    
    if r.status_code == 200:
        data_show["personajes"] = get_cast(url=uri)
        soup = BeautifulSoup(r.text, 'html.parser')
        categorias = soup.find_all('li', {"class": "SectionNavigation-items-item"})
        if categorias:
            for categoria in categorias:
                if categoria.find('a').text.strip() != "Personajes":
                    item = Listitem()
                    item.label = categoria.text
                    url = categoria.find('a').get('href')
                    item.info.tvshowtitle = data_show["titulo"]
                    item.info.plot = data_show["titulo"]
                    item.art["thumb"] = data_show["img"]
                    item.art["poster"] = data_show["img"]
                    item.listitem.setCast(data_show["personajes"])
                    item.set_callback(capitulos, url=url, data_show=data_show)
                    yield item
        else:
            uri = f"{uri}/capitulos"
            item = Listitem()
            item.label = "Capítulos"
            item.info.tvshowtitle = data_show["titulo"]
            item.info.plot = data_show["titulo"]
            item.art["thumb"] = data_show["img"]
            item.art["poster"] = data_show["img"]
            item.listitem.setCast(data_show["personajes"])
            item.set_callback(capitulos, url=uri, data_show=data_show)
            yield item
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
    
@Route.register
def programas(plugin, uri):
    r = requests.get(uri)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        programas = soup.find_all('div', {"class":"PromoMedia"})
        
        for programa in programas:
            url = programa.find('a').get('href')
            data_show = {
                "titulo": programa.find('span', {'class', 'Link-Media'}).text,
                "img": programa.find('img')["src"],
                "personajes": []
            }
            
            item = Listitem()
            item.info.mediatype = "tvshow"
            item.info.tvshowtitle = data_show["titulo"]
            item.label = data_show["titulo"]
            item.art["thumb"] = data_show["img"]
            item.art["poster"] = data_show["img"]
            item.listitem.setCast(data_show["personajes"])
            item.set_callback(secciones, uri=url, data_show=data_show)
            yield item
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)
        
@Route.register
def capitulos(plugin, url, data_show, initial_page=True):
    r = requests.get(url)
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        parsed_url = urlparse(url)
        base_url = urlunparse(parsed_url._replace(query=''))
        try:
            next_page = base_url + soup.find_all('div', 'ListD-nextPage')[-1].find('a')["data-original-href"]
        except Exception as e:
            None
        else:
            if next_page:  
                item = Listitem()
                yield item.next_page(url=next_page, data_show=data_show, initial_page=False)
        
        capitulos = []

        # Encuentra todos los elementos 'ps-list-loadmore'
        list_loadmores = soup.find_all('ps-list-loadmore')

        if initial_page:
            for list_g_item in soup.find_all('li', {'class': 'ListG-items-column'}):
                promos = list_g_item.find_all('ps-promo', {"class": 'PromoB', "data-content-type": "video"})
                capitulos.extend(promos)  # Agrega los resultados a la lista 'capitulos'
                
            # Si estamos en la página inicial, buscamos 'ps-promo' en todos los 'ps-list-loadmore'
            for list_loadmore in list_loadmores:
                promos = list_loadmore.find_all('ps-promo', {"class": 'PromoB', "data-content-type": "video"})
                capitulos.extend(promos)  # Agrega los resultados a la lista 'capitulos'
        else:
            # Si no estamos en la página inicial, buscamos 'ps-promo' solo en el último 'ps-list-loadmore'
            if list_loadmores:  # Verificamos que haya al menos un 'ps-list-loadmore'
                promos = list_loadmores[-1].find_all('ps-promo', {"class": 'PromoB', "data-content-type": "video"})
                capitulos.extend(promos)  # Agrega los resultados a la lista 'capitulos'
        
        for capitulo in capitulos: 
            plot = capitulo.find('h3', {"class":"PromoB-description"})
            item = Listitem()
            item.info.mediatype = "episode"
            item.info.tvshowtitle = data_show["titulo"]
            item.listitem.setCast(data_show["personajes"])
            item.label = capitulo.find('a')["title"]
            item.info.plot = plot.text if plot else capitulo.find('a')["title"]
            item.art["thumb"] = capitulo.find('img')["src"]
            url = capitulo.find('a').get('href')
            options_data = play_video_show(url=url)
            if options_data:
                if "duration" in options_data:
                    item.info.duration = iso8601_duration_to_seconds(options_data.get("duration"))
                if "uploadDate" in options_data:
                    item.info.date(options_data.get("uploadDate"), "%Y-%m-%dT%H:%M:%S%z")
                if 'contentUrl' in options_data:
                    item.set_path(options_data.get('contentUrl'))
                elif 'embedUrl' in options_data:
                    item.set_callback(play_youtube_video, url=options_data.get('embedUrl'))
                yield item
            
    else:
        Script.notify("Error al realizar la solicitud:", f"{url} {r.status_code}", Script.NOTIFY_ERROR)