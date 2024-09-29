class Product:
    def __init__(self, url: str, productId: int, name: str, sizes: dict[int, str], v1: str):
        self.url = url
        self.productId = productId
        self.name = name
        self.sizes = sizes
        self.v1 = v1

    def __repr__(self):
        return f"Product(name={self.name}, url={self.url}, productId = {self.productId}, size={self.sizes}, v1={self.v1})"