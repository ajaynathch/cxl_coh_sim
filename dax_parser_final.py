import re
from collections import OrderedDict
import subprocess


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


import json

class DAXParser:
    def __init__(self):
        self.directory = Directory()  # This is your centralized directory
        self.dax_output = ""

    def parse(self):
        """
        Parse the content of the DAX device (output of daxreader) to update the directory.
        """
        print("DAX Device Output:")
        print(self.dax_output)  # Debug print to see the raw content

        try:
            self.update_directory(self.dax_output)
        except json.JSONDecodeError as e:
            print(f"Error parsing DAX output: {e}")
            return
        except Exception as e:
            print(f"Unexpected error: {e}")
            return

    def read_dax_device(self):
        """
        Read from the DAX device and return its content.
        (For example, this might run the daxreader and capture its output.)
        """
        return subprocess.getoutput("sudo ./daxreader")  # Example command to read DAX device

    def update_directory(self, content):
        """
        Directly update the directory based on the DAX device's output.
        Example input: {0xEEE: {state: U, owners: }}
        Normalized output: {"0xEEE": {"state": "U", "owners": []}}
        """
        try:
            # Fix poorly formatted input
            # if isinstance(content, str):
            #     content = self._fix_invalid_json(content)

            # Extract the JSON portion by splitting at the newline
            _, json_data = content.split('\n', 1)
            print(json_data)

            # Parse the JSON string
            parsed_data = json.loads(json_data)
            print(parsed_data)

            # Access specific fields
            address = next(iter(parsed_data))
            main_data = parsed_data[address]

            # Extract details
            state = main_data["state"]
            owners = main_data["owners"]

            # Convert owners to a list of integers
            owner_list = list(map(int, owners.split(',')))
            self.directory.set_state(address, state, owner_list)
            print(self.directory.directory)
            # self.directory.directory[address] = {"state": state, "owners": owner_list}

        except Exception as e:
            print(f"Unexpected error while updating directory: {e}")

    # def _fix_invalid_json(self, content):
    #     """
    #     Fixes invalid JSON input by quoting keys and values appropriately.
    #     Example input: {0xEEE: {state: U, owners: }}
    #     Returns: {"0xEEE": {"state": "U", "owners": []}}
    #     """
    #     try:
    #         # Replace unquoted keys and values with quoted ones
    #         # fixed_content = re.sub(r"(?<![\{\[,])(\b[a-zA-Z0-9_]+\b)(?![\]\}])", r'"\1"', content)
    #         # # Replace empty owners with an empty list
    #         # fixed_content = re.sub(r'"owners":\s*""', '"owners":[]', fixed_content)
    #         # fixed_content = re.sub(r'"owners":\s*}', '"owners":[]}', fixed_content)
    #         return fixed_content
    #     except Exception as e:
    #         raise ValueError(f"Error fixing JSON: {e}")

    def write_address(self, address, directory):
        """
        Write the address to the directory (or perform operations on it).
        """
        # Example implementation: Add the address to the directory if not already present.
        if address in directory.directory:
            print(f"Address {address} is already in the directory.")
        else:
            print(f"Address {address} not found in directory. Adding...")
            directory.directory[address] = {"state": "U", "owners": []}


# Example Usage
if __name__ == "__main__":
    # Test with Snooping protocol format
    dax_output_snooping = "Paragraph read from DAX device:\n{'0xABC': 'Ajay', '0xCCC': 'Alas', '0xDDD': 'Ajay-1', '0xEEE': 'Ajay-2'}"
    snooping_parser = DAXParser()
    snooping_parser.set_output(dax_output_snooping)
    snooping_parser.parse()

    print("\n--- Snooping Protocol Parsed Data ---")
    snooping_parser.display_data()

    # Test with Directory protocol format
    dax_output_directory = """Paragraph read from DAX device:
    {'0xABC': {'state': 'S', 'owners': [1]}, '0xCCC': {'state': 'U', 'owners': ['']}, '0xDDD': {'state': 'U', 'owners': ['']}, '0xEEE': {'state': 'U', 'owners': ['']}}"""
    directory_parser = DAXParser()
    directory_parser.set_output(dax_output_directory)
    directory_parser.parse()

    print("\n--- Directory Protocol Parsed Data ---")
    directory_parser.display_data(protocol="Directory")

    # Example of address read and write
    print("\n--- Address Access Example ---")
    address_to_read = "0xABC"
    value = directory_parser.read_address(address_to_read, protocol="Directory")
    print(f"Value at address {address_to_read}: {value}")

    address_to_write = "0xFFF"
    value_to_write = ["NewData", "M", ["VM1"]]
    directory_parser.write_address(address_to_write, value_to_write, protocol="Directory")
    print("\nData after writing:")
    directory_parser.display_data(protocol="Directory")
