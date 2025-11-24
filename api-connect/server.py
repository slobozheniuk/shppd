from flask import Flask, request
from zara.util import parse_zara_url, map_sizes_to_bools
from zara.api import get_product, get_stock
from persist import Persist
from tracker import Tracker
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

persist = Persist()
tracker = Tracker(persist)
app = Flask(__name__)

@app.get('/zara/item')
def get_zara_item_data():
    url = request.args.get('url')

    # Validate that 'url' parameter is present
    if not url:
        return 'URL parameter is missing', 400

    parsed = parse_zara_url(url)
    product = get_product(parsed['product'], parsed['v1'])
    stock = get_stock(product.productId)
    return {
        "url": product.url,
        "name": product.name,
        "productId": product.productId,
        "sizes": map_sizes_to_bools(product.sizes, stock),
        "v1": product.v1
    }

@app.get('/follow/<chat_id>')
def get_followed_items(chat_id):
    if not persist.user_exist(chat_id):
        return f'Chat ID {chat_id} is not saved in DB'
    return persist.get_products_by_chat_id(chat_id)

@app.post('/follow/<chat_id>')
def follow_item(chat_id):
    url = request.json['url']
    logging.info(f'Adding url: {url}')

    if not url:
        return 'URL parameter is missing', 400
    
    parsed = parse_zara_url(url)
    url = f"https://www.zara.com/nl/en/{parsed['product']}.html?v1={parsed['v1']}"

    try:
        product = get_product(parsed['product'], parsed['v1'])
        created = persist.add_subscription(chat_id, product)

        if not created:
            logging.info("Chat %s already follows product %s", chat_id, product.productId)
            return 'Already subscribed', 200

        logging.info(f'Subscribing to {url}')
        tracker.subscribe(chat_id, product.url)
        return 'Success', 200
    except Exception:
        logging.error(f'Item not found with URL {url}')
        return 'Not found', 200

# Run the app if the script is executed
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5508)
