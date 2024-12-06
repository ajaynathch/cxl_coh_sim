import json
import os
import subprocess
import time
from collections import OrderedDict
from lru_cache import LRUCache
from dax_parser_new import DAXParser


# Centralized Directory
class Directory:
    def __init__(self):
        self.directory = {}

    def get_state(self, block):
        return self.directory.get(block, {"state": "U", "owners": []})

    def set_state(self, block, state, owners):
        self.directory[block] = {"state": state, "owners": owners}

    def invalidate_others(self, block, requester):
        if block in self.directory:
            self.directory[block]["owners"] = [owner for owner in self.directory[block]["owners"] if owner == requester]

    def export_states(self):
        return self.directory


# MESI Coherence Protocol for Each VM
class DirectoryCoherence:
    def __init__(self, vm_id, directory, cache_size=2, cache_filename="cache_vm1.json"):
        self.vm_id = vm_id
        self.directory = directory
        self.lru_cache = LRUCache(cache_size)
        self.cache_filename = cache_filename
        self.dax_parser = DAXParser()

    def _update_local_cache(self):
        if os.path.exists(self.cache_filename) and os.path.getsize(self.cache_filename) > 0:
            with open(self.cache_filename, "r") as file:
                self.lru_cache.cache = OrderedDict(json.load(file))

    def _persist_local_cache(self):
        with open(self.cache_filename, "w") as file:
            json.dump(self.lru_cache.cache, file, indent=4)

    def read(self, address):
        self._update_local_cache()
        dax_reader_output = self.run_daxreader(address)
        print(dax_reader_output)
        self.dax_parser.parse()
        self.directory = self.dax_parser.directory
        self.dax_parser.display_data()

        # Get directory state
        state_info = self.directory.get_state(address)
        if state_info["state"] == "U":
            print(f"VM{self.vm_id} READ miss: Block {address} not cached. Fetching from memory.")
            self.directory.set_state(address, "S", [self.vm_id])
        elif state_info["state"] == "S" and self.vm_id not in state_info["owners"]:
            print(f"VM{self.vm_id} READ hit: Adding VM{self.vm_id} as owner.")
            state_info["owners"].append(self.vm_id)
            self.directory.set_state(address, "S", state_info["owners"])
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} READ from owner VM{state_info['owners'][0]}.")
            self.directory.set_state(address, "S", state_info["owners"] + [self.vm_id])

        self.run_daxwriter()
        # Cache access
        self.lru_cache.access(address, "Data")
        self._persist_local_cache()

    def write(self, block, data):
        self._update_local_cache()
        dax_reader_output = self.run_daxreader(block)
        print(dax_reader_output)
        self.dax_parser.parse()
        self.directory = self.dax_parser.directory
        state_info = self.directory.get_state(block)

        if state_info["state"] in ["U", "S"]:
            print(f"VM{self.vm_id} WRITE miss: Invalidating other caches.")
            self.directory.invalidate_others(block, self.vm_id)
            self.directory.set_state(block, "M", [self.vm_id])
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} WRITE hit: Block already in Modified state.")

        self.run_daxwriter()
        self.lru_cache.access(block, data)
        self._persist_local_cache()

    def run_shell_script(self, script_path, *args):
        try:
            result = subprocess.run([script_path, *args], text=True, capture_output=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error in script {script_path}: {e.stderr}")
        except FileNotFoundError:
            print(f"Script {script_path} not found.")
        return ""

    def run_daxreader(self, address):
        return self.run_shell_script("./ap_ad2.sh", address)

    def run_daxwriter(self):
        message = json.dumps({k: {"state": v["state"], "owners": list(v["owners"])} for k, v in self.directory.directory.items()})
        return self.run_shell_script("./ap_ad.sh", message)


# Test Scenarios
if __name__ == "__main__":
    directory = Directory()
    vm1 = DirectoryCoherence(1, directory)
    vm2 = DirectoryCoherence(2, directory)

    print("\n--- Test Scenarios ---")

    print("\nScenario 1: VM1 reads Block A")
    vm1.read("0xABC")
    time.sleep(2)

    print("\nScenario 2: VM2 writes Block A")
    vm2.write("0xABC", "Updated Data")
    time.sleep(2)

    print("\nScenario 3: VM1 reads Block A again")
    vm1.read("0xABC")
