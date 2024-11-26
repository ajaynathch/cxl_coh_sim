import threading
import time
from enum import Enum


# Define MOESI states
class MOESIState(Enum):
    MODIFIED = 'M'
    OWNER = 'O'
    EXCLUSIVE = 'E'
    SHARED = 'S'
    INVALID = 'I'

# MOESI Coherence for VMs
class MOESICoherence:
    def __init__(self, vm_name):
        self.vm_name = vm_name  # Identifier for the VM
        self.cache = {}  # Local cache for the VM: {address: (state, data)}
        self.lock = threading.Lock()  # Ensure thread safety

    def read(self, address):
        with self.lock:
            if address in self.cache:
                state, data = self.cache[address]
                if state in (MOESIState.MODIFIED, MOESIState.OWNER, MOESIState.EXCLUSIVE, MOESIState.SHARED):
                    print(f"{self.vm_name} READ hit: Address {address}, State {state}, Data: {data}")
                    # Transition to OWNER if in MODIFIED state
                    if state == MOESIState.MODIFIED:
                        self.cache[address] = (MOESIState.OWNER, data)
                        print(f"{self.vm_name} State Change: Address {address} changed to OWNER")
                    return data
            # If not in cache, fetch from shared memory
            print(f"{self.vm_name} READ miss: Address {address}, State MOESIState.INVALID")
            return self._fetch_from_shared(address)

    def write(self, address, data):
        with self.lock:
            self._invalidate_shared_cache(address)
            self.cache[address] = (MOESIState.MODIFIED, data)
            print(f"{self.vm_name} WRITE: Address {address} set to MODIFIED, Data: {data}")

    def _fetch_from_shared(self, address):
        try:
            with open("/shared_cxl/cache.txt", "r") as f:
                shared_data = {}
                for line in f:
                    shared_address, shared_state, shared_value = line.strip().split(":", 2)
                    shared_data[shared_address] = (shared_state, shared_value)
                if address in shared_data:
                    state, data = shared_data[address]
                    if state == MOESIState.SHARED.value or state == MOESIState.OWNER.value:
                        self.cache[address] = (MOESIState.SHARED, data)
                        print(f"{self.vm_name} FETCH: Address {address} set to SHARED, Data: {data}")
                        return data
            # Address not in shared memory
            self.cache[address] = (MOESIState.EXCLUSIVE, None)
            print(f"{self.vm_name} FETCH: Address {address} set to EXCLUSIVE, Data: None")
            return None
        except FileNotFoundError:
            self.cache[address] = (MOESIState.EXCLUSIVE, None)
            print(f"{self.vm_name} FETCH: Address {address} set to EXCLUSIVE, Data: None (shared memory empty)")
            return None

    def _invalidate_shared_cache(self, address):
        try:
            with open("/shared_cxl/cache.txt", "a") as f:
                f.write(f"{address}:INVALIDATE:\n")
            print(f"{self.vm_name} INVALIDATE: Address {address} written to shared memory")
        except FileNotFoundError:
            print(f"Shared memory file not found for invalidation.")

    def sync_to_shared(self):
        with open("/shared_cxl/cache.txt", "w") as f:
            for address, (state, data) in self.cache.items():
                if state != MOESIState.INVALID:
                    f.write(f"{address}:{state.value}:{data}\n")
            print(f"{self.vm_name} SYNC: Cache synchronized to shared memory")


# Test Scenarios for VM1 and VM2
def test_moesi():
    vm1 = MOESICoherence("VM1")
    vm2 = MOESICoherence("VM2")

    print("\n--- VM1 Operations ---")
    # Scenario 1: Shared Read Access
    print("\nScenario 1: Shared Read Access (VM1)")
    vm1.read("0xABC")
    vm1.sync_to_shared()

    print("\n--- VM2 Operations ---")
    # Scenario 1: Shared Read Access
    print("\nScenario 1: Shared Read Access (VM2)")
    vm2.read("0xABC")
    vm2.sync_to_shared()

    # Scenario 2: Write Invalidation
    print("\nScenario 2: Write Invalidation (VM2)")
    vm2.write("0xABC", "New Data from VM2")
    vm2.sync_to_shared()

    print("\n--- VM1 Operations ---")
    # Scenario 3: Fetch from Shared
    print("\nScenario 3: Fetch from Shared (VM1)")
    vm1.read("0xDEF")
    vm1.sync_to_shared()

    print("\n--- VM2 Operations ---")
    # Scenario 4: Read After Modification
    print("\nScenario 4: Read After Modification (VM2)")
    vm2.read("0xABC")


if __name__ == "__main__":
    test_moesi()
