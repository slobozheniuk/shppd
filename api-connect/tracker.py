from apscheduler.schedulers.background import BackgroundScheduler
from zara.util import parse_zara_url, map_sizes_to_bools
from zara.api import get_product, get_stock

class Tracker:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def get_zara(self, url):
        parsed = parse_zara_url(url)
        product = get_product(parsed['product'], parsed['v1'])
        stock = get_stock(product.productId)
        print({
            "url": product.url,
            "name": product.name,
            "productId": product.productId,
            "sizes": map_sizes_to_bools(product.sizes, stock),
            "v1": product.v1
        })

    def subscribe(self, url):
        self.scheduler.add_job(
            func=self.get_zara,
            trigger='interval',
            seconds=5,
            args=[url],
            id=f'get_zara_{url}',
            replace_existing=True
        )

    