import time
from enum import Enum
import os
import subprocess
import mmap
import sys


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

    def read(self, address):
        state = self.cache.get(address, MESIState.INVALID)
        if state in (MESIState.MODIFIED, MESIState.EXCLUSIVE, MESIState.SHARED):
            print(f"VM1 READ hit: Address {address}, State {state}")
            return True
        else:
            print(f"VM1 READ miss: Address {address}, State {state}")
            self._fetch_from_shared(address)
            return False

    def write(self, address):
        self._invalidate_shared_cache(address)
        file_path = "cache.txt"
        with open(file_path, "a"):
            try:
                self.update_status(file_path, address, "M")

                print(f"Modified: {file_path}")

            except Exception as e:
                print(f"Failed to modify {file_path}: {e}")
        self.cache[address] = MESIState.MODIFIED
        self.run_daxwriter(sys.argv[1])

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
        """
        Traverses the directory and modifies text files.
        """
        if not os.path.exists(self.directory):
            print(f"The directory {self.directory} does not exist.")
            return

        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".txt"):  # Example: Modify only text files
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
        print(lines)
        for line in lines:
            parts = line.strip().split()
            if parts and parts[0] == entry:  # Check if entry matches
                updated_lines.append(f"{entry}: {new_status}\n")
                print("Updated")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(f"{entry}: {new_status}\n")

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


# Test Scenarios for VM1
def test_vm1():
    mesi = MESICoherence()

    print("\n--- VM1 Operations ---")
    print("\nScenario 1: Shared Read Access")
    # mesi.read("0xABC")
    time.sleep(1)

    print("\nScenario 2: Write Invalidation")
    mesi.write("0xABC")
    time.sleep(1)

    print("\nScenario 3: Fetch from Shared")
    # mesi.read("0xDEF")


if __name__ == "__main__":
    test_vm1()
