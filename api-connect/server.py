from flask import Flask, request
from zara.util import parse_zara_url

app = Flask(__name__)

@app.get('/zara/item')
def get_zara_item_data():
    url = request.args.get('url')

    # Validate that 'url' parameter is present
    if not url:
        return 'URL parameter is missing', 400

    return parse_zara_url(url)
    

# Run the app if the script is executed
if __name__ == '__main__':
    app.run(debug=True)