import os

# Define the mounted location path
MOUNTED_DIR = "/home/fedora/project/vm2/project/"
cache = {}

import time
from enum import Enum
import mmap
import os
import sys

class MESIState(Enum):
    MODIFIED = 'M'
    EXCLUSIVE = 'E'
    SHARED = 'S'
    INVALID = 'I'


def modify_files_in_directory(directory):
    """
    Traverses the directory and modifies text files.
    """
    if not os.path.exists(directory):
        print(f"The directory {directory} does not exist.")
        return

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):  # Example: Modify only text files
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        content = f.readlines()

                    # Example modification: Add a header to the file
                    content.insert(0, "Modified by Script\n")

                    with open(file_path, "w") as f:
                        f.writelines(content)

                    print(f"Modified: {file_path}")

                except Exception as e:
                    print(f"Failed to modify {file_path}: {e}")


def dax_write(address):
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <string>")
        return False

    string_to_write = sys.argv[1]
    size_to_write = len(string_to_write) + 1  # Include null terminator

    # Open the file
    try:
        fd = os.open("/dev/dax0.0", os.O_RDWR)
    except OSError as e:
        print(f"Error opening file: {e}")
        return False

    # Memory-map the file
    try:
        with mmap.mmap(fd, 4294967296, access=mmap.ACCESS_WRITE) as mm:
            # Clear the memory region
            mm[:size_to_write] = b'\x00' * size_to_write

            # Write the string to memory
            mm[:size_to_write] = string_to_write.encode('utf-8') + b'\x00'  # Add null terminator
            print("Paragraph written to DAX device successfully.")
    except Exception as e:
        print(f"Error mapping file: {e}")
        return False
    finally:
        os.close(fd)
    return True

import subprocess

def run_daxwriter(message):
    """
    Runs the daxwriter.sh script with the given message.
    """
    script_path = "./ap_ad.sh"  # Path to the shell script

    try:
        # Run the shell script with the message as an argument
        result = subprocess.run(
            [script_path, message],
            text=True,           # Capture output as text (not bytes)
            capture_output=True, # Capture standard output and error
            check=True           # Raise an exception for non-zero exit codes
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


def write(address):
    # with self.lock:
    # modify_files_in_directory(address)
    # print(f"VM1 INVALIDATE: Address {address} written to shared memory")
    # if not dax_write(address):
    #     return False
    run_daxwriter("Hi i am ajay")
    cache[address] = MESIState.MODIFIED
    print(f"VM1 WRITE: Address {address} set to MODIFIED")


def main():
    """
    Main function to initiate file modifications.
    """
    modify_files_in_directory(MOUNTED_DIR)
    write("0xABC")


if __name__ == "__main__":
    main()