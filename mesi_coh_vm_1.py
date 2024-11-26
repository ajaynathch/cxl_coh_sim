import threading
import time
from enum import Enum


# Define MESI states
class MESIState(Enum):
    MODIFIED = 'M'
    EXCLUSIVE = 'E'
    SHARED = 'S'
    INVALID = 'I'


# MESI Coherence for VM1
class MESICoherence:
    def __init__(self):
        self.cache = {}  # Local cache for VM1
        self.lock = threading.Lock()  # Ensure thread safety

    def read(self, address):
        with self.lock:
            state = self.cache.get(address, MESIState.INVALID)
            if state in (MESIState.MODIFIED, MESIState.EXCLUSIVE, MESIState.SHARED):
                print(f"VM1 READ hit: Address {address}, State {state}")
                return True
            else:
                print(f"VM1 READ miss: Address {address}, State {state}")
                self._fetch_from_shared(address)
                return False

    def write(self, address):
        with self.lock:
            self._invalidate_shared_cache(address)
            self.cache[address] = MESIState.MODIFIED
            print(f"VM1 WRITE: Address {address} set to MODIFIED")

    def _fetch_from_shared(self, address):
        # Simulate fetching from the shared CXL environment
        try:
            with open("/shared_cxl/cache.txt", "r") as f:
                shared_cache = f.read().strip().split("\n")
                if address in shared_cache:
                    self.cache[address] = MESIState.SHARED
                    print(f"VM1 FETCH: Address {address} set to SHARED")
                else:
                    self.cache[address] = MESIState.EXCLUSIVE
                    print(f"VM1 FETCH: Address {address} set to EXCLUSIVE")
        except FileNotFoundError:
            self.cache[address] = MESIState.EXCLUSIVE
            print(f"VM1 FETCH: Address {address} set to EXCLUSIVE (shared memory empty)")

    def _invalidate_shared_cache(self, address):
        # Invalidate shared cache entry for the address
        with open("/home/fedora/vm2/project/cache.txt", "a") as f:
            f.write(f"{address}\n")
        print(f"VM1 INVALIDATE: Address {address} written to shared memory")


# Test Scenarios for VM1
def test_vm1():
    mesi = MESICoherence()

    print("\n--- VM1 Operations ---")
    print("\nScenario 1: Shared Read Access")
    mesi.read("0xABC")
    time.sleep(1)

    print("\nScenario 2: Write Invalidation")
    mesi.write("0xABC")
    time.sleep(1)

    print("\nScenario 3: Fetch from Shared")
    mesi.read("0xDEF")


if __name__ == "__main__":
    test_vm1()
