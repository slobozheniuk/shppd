import pytest
from zara.util import parse_zara_url

@pytest.mark.parametrize("url,product,v1", [
    ('https://www.zara.com/share/straight-blazer-zw-collection-p08771510.html?v1=402153953&v2=2420942&utm_campaign=productShare&utm_medium=mobile_sharing_iOS&utm_source=red_social_movil', 'straight-blazer-zw-collection-p08771510', '402153953'), 
    ('https://www.zara.com/nl/en/straight-blazer-zw-collection-p08771510.html?v1=402153953&v2=2420942', 'straight-blazer-zw-collection-p08771510', '402153953')
])
def test_parsing_valid_zara_urls(url, product, v1):
    value = parse_zara_url(url)
    assert value['product'] == product
    assert value['v1'] == v1