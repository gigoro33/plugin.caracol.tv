from codequick import Route, Listitem, run, Script, utils
from resources.lib.routes import categorias, en_vivo


# Base url constructor
url_constructor = utils.urljoin_partial("https://www.caracoltv.com")

# Base items constructor
dict_constructor = [
    {"label": "Señal en vivo", "art": "live.png", "url": "", "id": "live"},
    {"label": "Programas", "art": "tv-show.png", "url": "/programas", "id": "programs"}
]
        
@Route.register
def root(plugin):
    for elem in dict_constructor:
        item = Listitem()
        item.label = elem["label"]
        item.art.local_thumb(elem["art"])
        if(elem["id"] == "live"):
            item.set_callback(en_vivo)
        elif(elem["id"] == "programs"):
            item.set_callback(categorias, uri=url_constructor(elem["url"]))
        yield item