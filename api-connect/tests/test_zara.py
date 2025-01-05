from zara.api import get_product

def test_get_product():
    product = 'straight-blazer-zw-collection-p08771510'
    v1 = '40215395'
    result = get_product(product, v1)
    print(result)
    assert result.url == f'https://www.zara.com/nl/en/{product}.html?v1={v1}'
    assert result.name == 'STRAIGHT BLAZER ZW COLLECTION'
    assert result.productId == 402153953
    assert result.v1 == v1
    assert 'XS' in result.sizes.values()
    assert 'S' in result.sizes.values()
    assert 'M' in result.sizes.values()
    assert 'L' in result.sizes.values()
    assert 'XL' in result.sizes.values()
    assert 'XXL' in result.sizes.values()
    assert len(result.sizes) == 6    