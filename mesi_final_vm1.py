import time
import os
import subprocess
import sys
import json
from lru_cache import *
from dax_parser import *


# MESI Coherence for VM1
class MESICoherence:
    def __init__(self):
        self.directory = "/home/fedora/project/vm2/project/"
        self.address = sys.argv[1].split(":")[0].strip().replace(" ", "")
        self.data = sys.argv[1].split(':')[1].strip().replace(" ", "")
        self.lru_cache = LRUCache(2)
        self.dax_parser = DAXParser()
        self.vm1_cache_filename = "cache_vm1.txt"
        self.vm2_cache_filename = "/home/fedora/project/vm2/project/cache_vm2.txt"

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

    def read(self):
        self.read_from_local_cache(self.vm1_cache_filename)
        if self.address in self.lru_cache.cache.keys():
            state = self.lru_cache.cache[self.address]
            print(f"VM1 READ hit: address {self.address}, State {state}")
            if state[1] == "I":
                print(f"Read from the Memory for {self.address}, as state: {state}")
                output = self.run_daxreader(self.address)
                self.parse_shared_cache(output, self.address)
                self.lru_cache.access(self.address, "S")
            elif state[1] == "E":
                print(f"VM1 READ Hit change {state} to Shared: address {self.address}")
                self.read_from_local_cache(self.vm1_cache_filename)
                self.lru_cache.cache[self.address] = [self.data, "S"]
                self.write_to_local_cache(self.vm1_cache_filename)
                return True
        else:
            print(f"VM1 READ miss: address {self.address}")
            self.lru_cache.cache[self.address] = [self.data, "I"]
            output = self.run_daxreader(self.address)
            self.parse_shared_cache(output, self.address)
            return False

    def parse_shared_cache(self, output, address):
        self.dax_parser.dax_output = output
        self.dax_parser.parse()
        data = self.dax_parser.read_address(address)
        self.read_from_local_cache(self.vm1_cache_filename)
        self.lru_cache.cache[self.address] = [data, "S"]
        self.write_to_local_cache(self.vm1_cache_filename)
        print(f"VM1 FETCH: Address {address} set to SHARED")

    def write(self):
        vm2_exists = self.invalidate_vm2_cache(self.address)
        output = self.run_daxreader(self.address)
        self.dax_parser.dax_output = output
        self.dax_parser.parse()
        self.lru_cache.cache[self.address] = [self.data, "M"]
        self.dax_parser.write_address(self.address, self.data)
        self.run_daxwriter(self.dax_parser.data)
        if not vm2_exists:
            self.read_from_local_cache(self.vm1_cache_filename)
            self.lru_cache.cache[self.address] = [self.data, "E"]
            self.write_to_local_cache(self.vm1_cache_filename)
            print(f"VM1 EXCLUSIVE: Address {self.address}")

        print(f"VM1 WRITE: address {self.address} set to MODIFIED")

    def invalidate_vm2_cache(self, address):
        is_exists = self.read_from_local_cache(self.vm2_cache_filename)
        if is_exists:
            if self.address in self.lru_cache.cache.keys():
                data = self.lru_cache.cache[self.address][0]
                self.lru_cache.cache[self.address] = [data, "S"]
                self.write_to_local_cache(self.vm2_cache_filename)
                print(f"VM2 INVALIDATE: Address {address}")
                return True
            else:
                return False

    def run_daxwriter(self, message):
        """
        Runs the daxwriter.sh script with the given message.
        """
        script_path = "./ap_ad.sh"  # Path to the shell script

        try:
            # Convert message to a JSON-like string or another suitable format
            if isinstance(message, (dict, OrderedDict)):
                message_str = "{" + ", ".join(f"'{k}': '{v}'" for k, v in message.items()) + "}"
                # message_str = json.dumps(message, separators=(",", ":"))  # Convert to string (JSON-like representation)
            else:
                message_str = message  # Use directly if already a string

            # Run the shell script with the message as an argument
            result = subprocess.run(
                [script_path, message_str],
                text=True,  # Capture output as text (not bytes)
                capture_output=True,  # Capture standard output and error
                check=True  # Raise an exception for non-zero exit codes
            )

            # Print the script's output
            print("Script output:")
            print(result.stdout)

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


# Test Scenarios for VM1
def test_vm1():
    mesi = MESICoherence()

    print("\n--- VM1 Operations ---")
    print("\nScenario 1: Shared Read Access")
    mesi.read()

    print("\nScenario 2: Write Invalidation")
    mesi.write()
    time.sleep(2)
    #
    print("\nScenario 3: Fetch from Shared")
    mesi.read()

    time.sleep(2)

    print("\nScenario 4: Fetch from Shared")
    mesi.read()


if __name__ == "__main__":
    test_vm1()