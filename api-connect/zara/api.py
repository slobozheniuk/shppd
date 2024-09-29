import json
import sys
from typing import Any, List, Tuple
import requests
from zara.product import Product
from bs4 import BeautifulSoup

def get_product(product: str, v1: str) -> Product:
    url = f'https://www.zara.com/nl/en/{product}.html?v1={v1}'
    product_json = get_product_json(url)
    name: str = product_json['product']['name']
    productId: int = product_json['product']['detail']['colors'][0]['productId']
    sizes: dict[str, int] = {}
    for size in product_json['product']['detail']['colors'][0]['sizes']:
        sizes[size['sku']] = size['name']
    return Product(url, productId, name, sizes, v1)

def get_product_json(url: str) -> Any:
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    }
    # TODO: Test the string for validity
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            begin_token = 'window.zara.viewPayload = '
            if begin_token in script.text:
                index = script.text.find(begin_token)
                product_json = json.loads(script.text[index + len(begin_token):-1])
                return product_json
    raise Exception('No JSON')       

def is_size_in_stock(productId: int, sku: int) -> bool:
    stock = get_stock(productId)
    for item in stock:
        if item[0] == sku:
            return item[1]
    # Raise an error if the integer is not found in any tuple
    raise ValueError(f"Integer {productId} not found in the list of tuples.")

def get_stock(productId: int) -> List[Tuple[int, bool]]:
    print('in get stock')
    res = []
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    }
    url = f'https://www.zara.com/itxrest/1/catalog/store/11709/product/id/{productId}/availability'
    print('Availability URL ' + url)
    try:
        response = requests.get(url, headers=headers)
    except:
        print('Something happened in request')
    print('Response status' + str(response.status_code))
    if response.status_code == 200:
        result = json.loads(response.text)
        for size in result['skusAvailability']:
            res.append((size['sku'], size['availability'] == 'in_stock'))
        return res
    else:
        raise Exception(response.content)  


# Usage example
if __name__ == "__main__":
    product = get_product(sys.argv[1])
    print(product)
    stock = get_stock(product.productId)
    print(stock)

""" class Product:
    def __init__(self, url: str, productId: int, name: str, sizes: dict[int, str]):
        self.url = url
        self.productId = productId
        self.name = name
        self.sizes = sizes

    def __repr__(self):
        return f"Product(name={self.name}, url={self.url}, productId = {self.productId}, size={self.sizes})"     """