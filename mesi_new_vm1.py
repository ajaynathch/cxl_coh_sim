import time
from enum import Enum
import os
import subprocess
import mmap
import sys

FILENAME = "/dev/dax0.0"
REGION_SIZE = 4294967296  # 4 GB


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
        self.directory = "/home/fedora/project/vm2/project/"

    def read(self):
        address = sys.argv[1].split(":")[1].strip()
        print(address)
        print(self.cache)

        if address in self.cache.keys():
            state = self.cache[address]
            print(state)
            if state in ('M', 'E', 'S'):
                print(f"VM1 READ hit: Address {address}, State {state}")
                return True
            else:
                print(f"VM1 READ miss: Address {address}")
                self.run_daxreader(address)
                self.cache[address] = "S"
                return False
        else:
            print(f"VM1 READ miss: Address {address}")
            self.cache[address] = "I"
            self.run_daxreader(address)
            self.cache[address] = "S"
            # self.update_status(file_path, address, "M")
            return False

    def write(self):
        address = sys.argv[1].split(":")[1]
        print(address)
        self._invalidate_shared_cache(address)
        file_path = "cache_vm1.txt"
        with open(file_path, "a"):
            try:
                self.update_status(file_path, address, "M")

                print(f"Modified: {file_path}")

            except Exception as e:
                print(f"Failed to modify {file_path}: {e}")
        self.cache[address] = "M"
        self.run_daxwriter(sys.argv[1])

        print(f"VM1 WRITE: Address {address} set to MODIFIED")

    def _fetch_from_shared(self, output):
        # Simulate fetching from the shared CXL environment
        file_path = "cache_vm1.txt"
        address = output.split(':')[2]
        print(address)
        try:

            # If the address is found in the shared cache, update the state to SHARED
            self.update_status(file_path, address, "S")
            self.cache[address] = MESIState.SHARED
            print(f"VM1 FETCH: Address {address} set to SHARED")
            # else:
            #     # If not found, set to EXCLUSIVE
            #     if state == "I":
            #         self.update_status(file_path, address, "E")
            #         self.cache[address] = MESIState.EXCLUSIVE
            #         print(f"VM1 FETCH: Address {address} set to EXCLUSIVE")
            #     else:
            #         self.update_status(file_path, address, "I")
            #         self.cache[address] = MESIState.EXCLUSIVE
            #         print(f"VM1 FETCH: Address {address} set to INVALID")

        except FileNotFoundError:
            self.cache[address] = MESIState.EXCLUSIVE
            print(f"VM1 FETCH: Address {address} set to EXCLUSIVE (shared memory empty)")

    def _invalidate_shared_cache(self, address):
        """
        Traverses the directory and modifies text files.
        """
        if not os.path.exists(self.directory):
            print(f"The directory {self.directory} does not exist.")
            return

        for root, dirs, files in os.walk(self.directory):
            for file in files:
                print(file)
                if file == "cache_vm2.txt":  # Example: Modify only text files
                    file_path = os.path.join(root, file)
                    try:
                        self.update_status(file_path, address, "I")

                        print(f"Modified: {file_path}")

                    except Exception as e:
                        print(f"Failed to modify {file_path}: {e}")
        print(f"VM1 INVALIDATE: Address {address} written to shared memory")

    def update_status(self, file_path, entry, new_status):
        # Read the file content
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Update the specific entry
        updated_lines = []
        updated_flag = False
        print(lines)
        for line in lines:
            print(line)
            line = line.replace('\n', '')
            if line != '':
                parts = line.strip().split(":")
                print(parts)
                print(file_path)
                if file_path == "/home/fedora/project/vm2/project/cache_vm2.txt":
                    message = parts[0].strip()
                else:
                    message = sys.argv[1].split(':')[0]
                if len(parts) != 0:
                    if parts[1].strip() == entry:  # Check if entry matches
                        updated_lines.append(f"{message}: {entry} : {new_status}\n")
                        print("Updated")
                    else:
                        updated_lines.append(f"{message}: {entry} : {new_status}\n")
                    updated_flag = True

        if not updated_flag:
            updated_lines.append(f"{sys.argv[1].split(':')[0].strip()} : {sys.argv[1].split(':')[1].split()} : {new_status}\n")
        print(updated_lines)
        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.writelines(updated_lines)

    def run_daxwriter(self, message):
        """
        Runs the daxwriter.sh script with the given message.
        """
        script_path = "./ap_ad.sh"  # Path to the shell script

        try:
            # Run the shell script with the message as an argument
            result = subprocess.run(
                [script_path, message],
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
            self._fetch_from_shared(result.stdout)

        except subprocess.CalledProcessError as e:
            print("Error running shell script:")
            print(e.stderr)
        except Exception as e:
            print(f"An error occurred: {e}")


# Test Scenarios for VM1
def test_vm1():
    mesi = MESICoherence()
    lines = []
    with open("cache_vm1.txt", 'r') as file:
        lines = file.readlines()

    for line in lines:
        print(line.split(":"))
        mesi.cache[line.split(":")[1].strip()] = line.split(":")[2].strip().replace("\n", "")

    print("\n--- VM1 Operations ---")
    print("\nScenario 1: Shared Read Access")
    mesi.read()
    time.sleep(1)

    print("\nScenario 2: Write Invalidation")
    mesi.write()
    time.sleep(1)

    print("\nScenario 3: Fetch from Shared")
    mesi.read()


if __name__ == "__main__":
    test_vm1()