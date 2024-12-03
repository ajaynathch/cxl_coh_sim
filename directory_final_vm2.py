import re
from lru_cache import LRUCache
from dax_parser_new import DAXParser
import json
import os
import sys
import subprocess
from collections import OrderedDict
import time

# Centralized Directory
class Directory:
    def __init__(self):
        self.directory = {}  # Tracks memory blocks, e.g., {"0xABC": {"state": "Shared", "owners": [1, 2]}}

    def get_state(self, block):
        return self.directory.get(block, {"state": "U", "owners": []})

    def set_state(self, block, state, owners):
        self.directory[block] = {"state": state, "owners": owners}

    def invalidate_others(self, block, requester):
        """Invalidate other caches for a given block."""
        if block in self.directory:
            owners = self.directory[block]["owners"]
            for owner in owners:
                if owner != requester:
                    print(f"Invalidate block {block} in VM{owner}.")
            # Remove all owners except the requester
            self.directory[block]["owners"] = [requester]

    def export_states(self):
        """Export all directory states as a dictionary."""
        return self.directory


# MESI Coherence Protocol for Each VM
class DirectoryCoherence:
    def __init__(self, vm_id, directory):
        self.vm_id = vm_id
        self.directory = directory
        self.lru_cache = LRUCache(2)  # Local cache for the VM
        self.dax_parser = DAXParser()
        self.vm2_cache_filename = "cache_vm2.txt"
        self.address = ""
        self.data = ""

    def write_to_local_cache(self, filename):
        with open(filename, 'w') as file:
            json.dump(self.lru_cache.cache, file, indent=4)

    def read_from_local_cache(self, filename):
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r') as file:
                self.lru_cache.cache = OrderedDict(json.load(file))
                return True
        return False

    def read(self, address):
        # Read from local cache first
        self.read_from_local_cache(self.vm2_cache_filename)
        self.address = address

        # Fetch block's state from the directory using daxreader
        output = self.run_daxreader(self.address)
        self.dax_parser.dax_output = output
        self.dax_parser.parse()

        # Use self.directory instead of replacing it
        state_info = self.directory.get_state(self.address)

        # Handle cache miss (U state)
        if state_info["state"] == "U":
            print(f"VM{self.vm_id} READ miss: Block {self.address} not cached. Fetching from memory.")
            self.directory.set_state(self.address, "S", [self.vm_id])  # Set state to Shared, add VM as owner
            self.dax_parser.write_address(self.address, self.directory)

            print(f"Directory state before script execution: {self.directory.get_state(self.address)}")
            directory_data = self.dax_parser.directory.directory  # Get the directory states as a dictionary
            self.run_daxwriter(directory_data)  # Pass updated state to daxwriter

            print(f"Directory state after script execution: {self.directory.get_state(self.address)}")

        # Handle cache hit (S state)
        elif state_info["state"] == "S":
            print(f"VM{self.vm_id} READ hit: Block {self.address} in state {state_info['state']}.")
            if self.vm_id not in state_info["owners"]:
                # Add this VM to the list of owners
                state_info["owners"].append(self.vm_id)
                self.directory.set_state(self.address, "S", state_info["owners"])
                self.dax_parser.write_address(self.address, self.directory)
                directory_data = self.directory.export_states()
                self.run_daxwriter(directory_data)  # Pass updated state to daxwriter

        # Handle read from Modified state (M state)
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} READ from owner VM{state_info['owners'][0]}.")
            # Set state to Shared, add this VM as owner
            self.directory.set_state(self.address, "S", state_info["owners"] + [self.vm_id])
            self.dax_parser.write_address(self.address, self.directory)
            directory_data = self.directory.export_states()
            self.run_daxwriter(directory_data)  # Pass updated state to daxwriter

        # Access the LRU cache
        self.lru_cache.access(self.address, "Data")

    def write(self, block, data):
        state_info = self.directory.get_state(block)
        if state_info["state"] in ["U", "S"]:
            print(f"VM{self.vm_id} WRITE miss: Block {block}. Invalidating other caches.")
            self.directory.invalidate_others(block, self.vm_id)
            self.directory.set_state(block, "M", [self.vm_id])
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} WRITE hit: Block {block} already in Modified state.")
        self.lru_cache.access(block, data)

    def run_daxwriter(self, message):
        """
        Runs the daxwriter.sh script with the given message.
        The message must be a dictionary representing directory states or a valid JSON string.
        """
        script_path = "./ap_ad.sh"  # Path to the shell script

        try:
            print(f"Received message: {message}, Type: {type(message)}")

            if isinstance(message, str):
                try:
                    message = json.loads(message)
                    print("Message parsed from JSON.")
                except json.JSONDecodeError as e:
                    raise ValueError("Message is a string but not valid JSON.")
            elif not isinstance(message, dict):
                raise ValueError("Message must be a dictionary or a valid JSON string.")
            # ",".join(map(str, v["owners"])
            formatted_message = {
                k: {"state": v["state"], "owners": list(v["owners"])}
                for k, v in message.items()
            }
            message_str = json.dumps(formatted_message)

            result = subprocess.run(
                [script_path, message_str],
                text=True,
                capture_output=True,
                check=True
            )

            print("Script output:")
            print(result.stdout)

        except ValueError as ve:
            print(f"Value Error: {ve}")
        except subprocess.CalledProcessError as e:
            print("Error occurred while running the script:")
            print(e.stderr)
        except FileNotFoundError:
            print(f"Error: Script {script_path} not found. Ensure the path is correct.")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def run_daxreader(self, address):
        script_path = "./ap_ad2.sh"  # Path to the shell script

        try:
            if not isinstance(address, str) or not address.startswith("0x"):
                raise ValueError("Address must be a hexadecimal string (e.g., '0xABC').")

            result = subprocess.run(
                [script_path, address],
                check=True,
                text=True,
                capture_output=True
            )

            return result.stdout

        except subprocess.CalledProcessError as e:
            print("Error running shell script:")
            print(e.stderr)
        except Exception as e:
            print(f"An error occurred: {e}")


# Test Scenarios
if __name__ == "__main__":
    directory = Directory()
    vm1 = DirectoryCoherence(1, directory)
    vm2 = DirectoryCoherence(2, directory)

    print("\n--- Test Scenarios ---")
    time.sleep(1)

    print("\nScenario 1: vm2 reads Block A")
    vm2.read("0xABC")

    #print("\nScenario 2: VM2 reads Block A")
    #vm2.read()

    # print("\nScenario 3: VM2 writes Block A")
    # vm2.write("0xABC", "a=2")
    # time.sleep(2)
    #
    # #print("\nScenario 4: VM1 writes Block B")
    # #vm2.write("0xB", "Data_vm2")
    #
    # print("\nScenario 5: vm2 reads Block A (after VM2 modified it)")
    # vm1.read("0xABC")
    # time.sleep(2)
    #
    # vm1.read("0xCCC")
