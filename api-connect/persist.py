class Persist:
    def __init__(self):
        self.tracked_items = []

    def add_item(self, chat_id, url):
        if url not in self.get_urls_by_chat_id(chat_id):
            self.tracked_items.append((chat_id, url))

    def remove_product(self, chat_id, url):
        try:
            self.tracked_items.remove((chat_id, url))
            print(f"Removed {(chat_id, url)} from chat_urls.")
        except ValueError:
            print(f"Tuple {(chat_id, url)} not found in chat_urls.")

    def user_exist(self, chat_id):
        for cid, _ in self.tracked_items:
            if cid == chat_id:
                return True
        return False
       
    def get_urls_by_chat_id(self, chat_id):   
        return [url for (cid, url) in self.tracked_items if cid == chat_id]