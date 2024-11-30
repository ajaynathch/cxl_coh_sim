from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.miss_count = 0
        self.total_count = 0

    def access(self, key, value=None):
        self.total_count += 1
        if key in self.cache:
            self.cache.move_to_end(key)
            return f"Cache hit: {key} -> {self.cache[key]}"
        else:
            self.miss_count += 1
            if len(self.cache) >= self.capacity:
                evicted_key, evicted_value = self.cache.popitem(last=False)
                print(f"Evicting LRU: {evicted_key} -> {evicted_value}")
            self.cache[key] = value
            return f"Cache miss: Added {key} -> {value}"

    def display(self):
        return list(self.cache.items())


