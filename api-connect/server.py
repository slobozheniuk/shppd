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
    selected_sizes = request.json.get('sizes')
    logging.info(f'Adding url: {url}')

    if not url:
        return 'URL parameter is missing', 400
    
    parsed = parse_zara_url(url)
    url = f"https://www.zara.com/nl/en/{parsed['product']}.html?v1={parsed['v1']}"

    try:
        product = get_product(parsed['product'], parsed['v1'])
        size_names = list(dict.fromkeys(product.sizes.values()))
        requires_selection = len(size_names) > 1 and not selected_sizes

        created, updated_sizes = persist.add_subscription(chat_id, product, selected_sizes=selected_sizes)

        if requires_selection:
            logging.info("Chat %s needs to pick sizes for %s", chat_id, product.productId)
            return {
                "requires_size_selection": True,
                "sizes": size_names,
                "product": {
                    "productId": product.productId,
                    "name": product.name,
                    "url": product.url,
                    "v1": product.v1
                }
            }, 200

        # If no selection required, default to all sizes for single-size products
        if selected_sizes is not None and len(selected_sizes) == 0:
            return {"requires_size_selection": True, "sizes": size_names, "product": {"productId": product.productId, "name": product.name, "url": product.url, "v1": product.v1}}, 200
        sizes_to_track = size_names if not selected_sizes else selected_sizes

        if not created and not updated_sizes and selected_sizes:
            logging.info("Chat %s already follows product %s with same sizes", chat_id, product.productId)
            return 'Already subscribed', 200

        logging.info(f'Subscribing to {url} for sizes {sizes_to_track}')
        tracker.subscribe(chat_id, product.url, sizes_to_track)
        return 'Success', 200
    except Exception as exc:
        logging.exception(f'Item not found with URL {url}')
        return {'error': 'Not found', 'details': str(exc)}, 200

# Run the app if the script is executed
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5508)
