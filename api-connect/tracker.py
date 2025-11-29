from apscheduler.schedulers.background import BackgroundScheduler
from zara.util import parse_zara_url, map_sizes_to_bools
from zara.api import get_product, get_stock
from persist import Persist
import logging
import requests
from requests import Response
baseUrl = 'http://telegram-bot:3000/event'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class Tracker:
    def __init__(self, persist) -> None:
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.persist: Persist = persist

    def get_zara(self, chat_id, url, selected_sizes=None):
        logging.info(f'Checking {url} for {chat_id}')
        parsed = parse_zara_url(url)
        try:
            product = get_product(parsed['product'], parsed['v1'])
            stock = get_stock(product.productId)
            sizes = map_sizes_to_bools(product.sizes, stock)
            selected_sizes = selected_sizes if selected_sizes is not None else self.persist.get_selected_sizes(chat_id, url)
            logging.info({
                "url": product.url,
                "name": product.name,
                "productId": product.productId,
                "sizes": sizes,
                "v1": product.v1
            })
            sizes_to_check = sizes
            if selected_sizes:
                sizes_to_check = {k: v for (k, v) in sizes.items() if k in selected_sizes}

            if sizes_to_check and any(sizes_to_check.values()):
                message = f'{url}\n{product.name}\n'
                for size in sizes_to_check.keys():
                    message += f"{size}: {'In stock' if sizes_to_check[size] else 'Not in stock'}\n"
                response: Response = requests.post(
                url=baseUrl, 
                json={"userId": chat_id, "message": message},
                headers={"Content-Type": "application/json"})
                self.persist.remove_product(chat_id, url)    
                self.scheduler.remove_job(f'get_zara_{chat_id}_{url}')
        except:
            logging.warning('No product on url ' + url)
            response: Response = requests.post(
                url=baseUrl, 
                json={"userId": chat_id, "message": f'This product does not exist. TODO: Use check on tgbot\n{response.text}'},
                headers={"Content-Type": "application/json"})
            logging.info(response.status_code)
            logging.info(response.text)
            #self.persist.remove_product(chat_id, url)    
            #self.scheduler.remove_job(f'get_zara_{url}')

                
    def subscribe(self, chat_id, url, selected_sizes=None):
        logging.info(f'Subscribing to {url} sizes={selected_sizes}')
        self.scheduler.add_job(
            func=self.get_zara,
            trigger='interval',
            seconds=5,
            args=[chat_id, url, selected_sizes],
            id=f'get_zara_{chat_id}_{url}',
            replace_existing=True
        )

    
