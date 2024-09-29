import pytest
from zara.util import parse_zara_url, map_sizes_to_bools

@pytest.mark.parametrize("url,product,v1", [
    ('https://www.zara.com/share/straight-blazer-zw-collection-p08771510.html?v1=402153953&v2=2420942&utm_campaign=productShare&utm_medium=mobile_sharing_iOS&utm_source=red_social_movil', 'straight-blazer-zw-collection-p08771510', '402153953'), 
    ('https://www.zara.com/nl/en/straight-blazer-zw-collection-p08771510.html?v1=402153953&v2=2420942', 'straight-blazer-zw-collection-p08771510', '402153953')
])
def test_parsing_valid_zara_urls(url, product, v1):
    value = parse_zara_url(url)
    assert value['product'] == product
    assert value['v1'] == v1

def test_mapping_1():
    sizes_dict = {383659357: 'XS', 383659358: 'S', 383659353: 'M', 383659354: 'L', 383659355: 'XL', 383659356: 'XXL'}
    tuple_array = [(383659358, True), (383659356, True), (383659357, True), (383659354, True), (383659355, True), (383659353, True)]

    result = map_sizes_to_bools(sizes_dict, tuple_array)
    assert result['XS'] == True
    assert result['S'] == True
    assert result['M'] == True
    assert result['L'] == True
    assert result['XL'] == True
    assert result['XXL'] == True

def test_mapping_2():
    sizes_dict = {383659357: 'XS', 383659358: 'S', 383659353: 'M', 383659354: 'L', 383659355: 'XL', 383659356: 'XXL'}
    tuple_array = [(383659358, False), (383659356, False), (383659357, False), (383659354, True), (383659355, False), (383659353, False)]

    result = map_sizes_to_bools(sizes_dict, tuple_array)
    assert result['XS'] == False
    assert result['S'] == False
    assert result['M'] == False
    assert result['L'] == False
    assert result['XL'] == False
    assert result['XXL'] == False    

def test_mapping_3():
    sizes_dict = {383659357: 'XS', 383659358: 'S', 383659353: 'M', 383659354: 'L', 383659355: 'XL', 383659356: 'XXL'}
    tuple_array = [(383659358, False), (383659356, False), (383659357, False), (383659354, True), (383659355, False), (383659353, False), (383659471, False)]

    result = map_sizes_to_bools(sizes_dict, tuple_array)
    assert result['XS'] == False
    assert result['S'] == False
    assert result['M'] == False
    assert result['L'] == True
    assert result['XL'] == False
    assert result['XXL'] == False        