def parse_zara_url(url: str):
    product_end = url.find('.html')
    product_begin = url.rfind('/', 0, product_end) + 1
    product = url[product_begin:product_end]

    v1_begin = url.find('v1=') + 3
    v1_end = url.find('&', v1_begin)
    v1 = url[v1_begin:v1_end]

    return {
        'product': product,
        'v1': v1
    }

def map_sizes_to_bools(sizes_dict, tuple_array):
    return {sizes_dict[chat_id]: is_true for chat_id, is_true in tuple_array if chat_id in sizes_dict}
