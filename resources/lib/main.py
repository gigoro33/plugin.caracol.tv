from codequick import Route, Listitem, run, Script, utils
from resources.lib.routes import categorias
from resources.lib.utils import en_vivo


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
            try:
                # Script.log(stream_data, None, Script.INFO)
                stream_data = en_vivo(url_constructor(elem["url"])) 
                item.info["plot"] = stream_data.get("title")
                item.set_path(p["src"]["hls"])
            except Exception as e:
               Script.notify("Error", "Este contenido no está disponible. Disfruta de todas las producciones que tenemos y de las noticias del entretenimiento en www.caracoltv.com", Script.NOTIFY_ERROR)
        elif(elem["id"] == "programs"):
            item.set_callback(categorias, uri=url_constructor(elem["url"]))
        yield item