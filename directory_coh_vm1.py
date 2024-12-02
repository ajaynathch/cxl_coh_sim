import re
from lru_cache import *
from dax_parser_new import *
import json
import os
import sys
import subprocess


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


# MESI Coherence Protocol for Each VM
class DirectoryCoherence:
    def __init__(self, vm_id, directory):
        self.vm_id = vm_id
        self.directory = directory
        self.lru_cache = LRUCache(2)  # Local cache for the VM
        self.dax_parser = DAXParser()
        self.vm1_cache_filename = "cache_vm1.txt"
        self.address = sys.argv[1].split(":")[0].strip().replace(" ", "")
        self.data = sys.argv[1].split(':')[1].strip().replace(" ", "")

    def write_to_local_cache(self, filename):
        with open(filename, 'w') as file:
            json.dump(self.lru_cache.cache, file, indent=4)

    def read_from_local_cache(self, filename):
        with open(filename, 'r') as file:
            if os.path.getsize(filename) != 0:
                self.lru_cache.cache = OrderedDict(json.load(file))
                return True
            else:
                return False

    def read(self,):
        self.read_from_local_cache(self.vm1_cache_filename)
        output = self.run_daxreader(self.address)
        self.dax_parser.dax_output = output
        self.dax_parser.parse()
        self.directory = self.dax_parser.directory
        state_info = self.directory.get_state(self.address)
        if state_info["state"] == "U":
            print(f"VM{self.vm_id} READ miss: Block {self.address} not cached. Fetching from memory.")
            self.directory.set_state(self.address, "S", [self.vm_id])
            self.dax_parser.write_address(self.address, self.directory)
            self.run_daxwriter(self.dax_parser.directory)
        elif state_info["state"] == "S":
            print(f"VM{self.vm_id} READ hit: Block {self.address} in state {state_info['state']}.")
            if self.vm_id not in state_info["owners"]:
                state_info["owners"].append(self.vm_id)
                self.directory.set_state(self.address, "S", state_info["owners"])
                self.dax_parser.write_address(self.address, self.directory)
                self.run_daxwriter(self.dax_parser.directory)
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} READ from owner VM{state_info['owners'][0]}.")
            self.directory.set_state(self.address, "S", state_info["owners"] + [self.vm_id])
            self.dax_parser.write_address(self.address, self.directory)
            self.run_daxwriter(self.dax_parser.directory)

        # Simulate adding to local cache
        self.lru_cache.access(self.address, "Data")

    def write(self, block, data):
        state_info = self.directory.get_state(block)
        if state_info["state"] in ["U", "S"]:
            print(f"VM{self.vm_id} WRITE miss: Block {block}. Invalidating other caches.")
            self.directory.invalidate_others(block, self.vm_id)
            self.directory.set_state(block, "M", [self.vm_id])
        elif state_info["state"] == "M":
            print(f"VM{self.vm_id} WRITE hit: Block {block} already in Modified state.")

        # Update the local cache
        self.lru_cache.access(block, data)

    def run_daxwriter(self, message):
        """
        Runs the daxwriter.sh script with the given message.
        The message must be a dictionary representing directory states or a valid JSON string.
        """
        script_path = "./ap_ad.sh"  # Path to the shell script

        try:
            # Debugging: Print the message type and value for tracing
            print(f"Received message: {message}, Type: {type(message)}")

            # Ensure message is a dictionary
            if isinstance(message, str):
                # Try to parse the string as JSON
                try:
                    message = json.loads(message)
                    print("Message parsed from JSON.")
                except json.JSONDecodeError as e:
                    raise ValueError("Message is a string but not valid JSON.")
            elif not isinstance(message, dict):
                raise ValueError("Message must be a dictionary or a valid JSON string.")

            # Format the dictionary for the script
            formatted_message = {
                k: {"state": v["state"], "owners": ",".join(map(str, v["owners"]))}
                for k, v in message.items()
            }
            message_str = json.dumps(formatted_message, separators=(",", ":"))

            # Run the shell script with the message as an argument
            result = subprocess.run(
                [script_path, message_str],
                text=True,  # Capture output as text
                capture_output=True,  # Capture standard output and error
                check=True  # Raise an exception for non-zero exit codes
            )

            # Print the script's output
            print("Script output:")
            print(result.stdout)

        except ValueError as ve:
            print(f"Value Error: {ve}")
        except subprocess.CalledProcessError as e:
            # Handle script execution errors
            print("Error occurred while running the script:")
            print(e.stderr)
        except FileNotFoundError:
            print(f"Error: Script {script_path} not found. Ensure the path is correct.")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def run_daxreader(self, address):

        script_path = "./ap_ad2.sh"  # Path to the shell script
        try:
            # Ensure the address is passed as a hexadecimal string
            if not isinstance(address, str) or not address.startswith("0x"):
                raise ValueError("Address must be a hexadecimal string (e.g., '0xABC').")

            # Run the shell script with sudo and the address as an argument
            result = subprocess.run(
                [script_path, address],
                check=True,  # Raise an exception on non-zero exit
                text=True,  # Ensure output is a string
                capture_output=True  # Capture stdout and stderr
            )
            print("Shell script output:")
            print(result.stdout)

            return result.stdout

        except subprocess.CalledProcessError as e:
            print("Error running shell script:")
            print(e.stderr)
        except Exception as e:
            print(f"An error occurred: {e}")



# Test Scenarios
if __name__ == "__main__":
    # Initialize the shared directory
    directory = Directory()

    # Create VM instances
    vm1 = DirectoryCoherence(1, directory)
    vm2 = DirectoryCoherence(2, directory)

    # Test Scenarios
    print("\n--- Test Scenarios ---")

    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)
    print("\nScenario 1: VM1 reads Block A")
    vm1.read()
    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)

    print("\nScenario 2: VM2 reads Block A")
    vm2.read()
    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)

    print("\nScenario 3: VM2 writes Block A")
    vm2.write("0xA", "Data_VM2")
    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)

    print("\nScenario 4: VM1 writes Block B")
    vm1.write("0xB", "Data_VM1")
    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)

    print("\nScenario 5: VM1 reads Block A (after VM2 modified it)")
    vm1.read()
    print(vm1.directory.directory)
    print(vm1.lru_cache.cache)
    print(vm2.directory.directory)
    print(vm2.lru_cache.cache)
