from zara.api import get_product

def test_get_product():
    product = 'heavyweight-regular-fit-basic-t-shirt-p01887455'
    v1 = '452744597'
    result = get_product(product, v1)
    print(result)
    assert result.url == f'https://www.zara.com/nl/en/{product}.html?v1={v1}'
    assert result.v1 == v1
    assert 'S' in result.sizes.values()
    assert 'M' in result.sizes.values()
    assert 'L' in result.sizes.values()
    assert 'XL' in result.sizes.values()
    assert 'XXL' in result.sizes.values()
    assert len(result.sizes) == 5    