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
        # Normalize SKU keys as ints so they match availability payloads.
        sizes[int(size['sku'])] = size['name']
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

    response = fetch_zara_product_page(url)
    soup = BeautifulSoup(response, 'html.parser')
    scripts = soup.find_all('script')
    for script in scripts:
        begin_token = 'window.zara.viewPayload = '
        if begin_token in script.text:
            index = script.text.find(begin_token)
            product_json = json.loads(script.text[index + len(begin_token):-1])
            return product_json     

def fetch_zara_product_page(product_url: str) -> str:
    """
    Fetch the HTML of a Zara product page by mimicking the browser’s
    four-step sequence of requests.  Steps:
      1. Initial GET to the product page (no cookies).
      2. GET to the interstitial page.
      3. POST to the verification endpoint.
      4. Final GET to the product page (cookies now included automatically).
    """

    session = requests.Session()

    # Common headers for the first and final HTML requests.
    base_headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "upgrade-insecure-requests": "1",
        # Add a User-Agent string to imitate Chrome on macOS.
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
    }

    # Step 1: initial GET to the product page (no cookies yet).
    init_headers = {
        **base_headers,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
    }
    resp1 = session.get(product_url, headers=init_headers)
    resp1.raise_for_status()

    # Step 2: GET the interstitial page.
    interstitial_url = "https://www.zara.com/interstitial/ic.html"
    interstitial_headers = {
        **base_headers,
        "sec-fetch-dest": "iframe",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "referer": product_url,
    }
    resp2 = session.get(interstitial_url, headers=interstitial_headers)
    resp2.raise_for_status()

    # Step 3: POST the verification challenge.
    verify_url = "https://www.zara.com/_sec/verify?provider=interstitial"
    verify_payload = {
        "bm-verify": (
            "AAQAAAAM/////2myCBVAzD/wdtrRTzheVjpmarHbFVaBSraNduw6MQoDCiiv"
            "UgQHj5a+TChMv1TihB6CCcmG5hO2xYdx/CEPW7oZvP3ZepXeB5WW71JifpdEv"
            "tJBttCSZyz/gAA7nDO8TBXRtnB4mFuqnNCz39eHzfnDFhPeRDL1PskPZqBelS"
            "xRpv4Y35FpjPuFH5ni7UmoHSVFRU58wJgRnOspnu+lfHnUnG/USu1TRSponv1"
            "YQNXdOmm//3R4/sQfPdblAhL7qVOhZ5c+QCW2+ci20lqcJFKzFPsOyT8uyMc1"
            "nxvJhy3b9tHs4nyo/AZcbgWO01fapSndqZKkJN8ljsmWGH7zx953HmTl6/3V5"
            "puDIZuwUNkA/97FBg=="
        ),
        "pow": 2475238890,
    }
    verify_headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "priority": "u=0, i",
        "sec-ch-ua": base_headers["sec-ch-ua"],
        "sec-ch-ua-mobile": base_headers["sec-ch-ua-mobile"],
        "sec-ch-ua-platform": base_headers["sec-ch-ua-platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "referer": product_url,
        "user-agent": base_headers["user-agent"],
    }
    resp3 = session.post(verify_url,
                         headers=verify_headers,
                         data=json.dumps(verify_payload))
    resp3.raise_for_status()

    # Step 4: Final GET to the product page with cookies set.
    final_headers = {
        **base_headers,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        # no 'sec-fetch-user' needed here (matches your final call)
        "referer": product_url,
    }
    resp4 = session.get(product_url, headers=final_headers)
    resp4.raise_for_status()

    return resp4.text

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
            # Normalize SKU as int to match get_product().
            res.append((int(size['sku']), size['availability'] == 'in_stock'))
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
