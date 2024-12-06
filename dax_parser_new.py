import re
from collections import OrderedDict


class Directory:
    def __init__(self):
        self.directory = {}

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


class DAXParser:
    def __init__(self):
        self.dax_output = ""
        self.directory = Directory()  # For Directory-based protocol

    def set_output(self, dax_output):
        """
        Set the DAX output string for parsing.
        """
        self.dax_output = dax_output

    def parse(self):
        """
        Parse the dax_output to extract key-value pairs into the Directory object.
        """
        match = re.search(r"Paragraph read from DAX device:\s*(\{.*\}\})", self.dax_output)
        if match:
            content = match.group(1)
            self._parse_directory(content)

    def _parse_directory(self, content):
        """
        Parse the Directory-based protocol format and populate the Directory object.
        Example: {'0xABC': {'state': 'S', 'owners': [1]}, '0xCCC': {'state': 'U', 'owners': []}}
        """
        if not content.startswith("{") or not content.endswith("}"):
            content = "{" + content + "}"
        parsed_content = eval(content)

        for address, info in parsed_content.items():
            # Extract state and owners
            state = info.get("state", "U")
            owners = info.get("owners", [])
            # Print parsed results
            print(f"Address: {address}, State: {state}, Owners: {owners}")
            self.directory.set_state(address, state, owners)

    def read_address(self, address):
        """
        Read the value at a specific address.
        """
        return self.directory.get_state(address)

    def write_address(self, address, state, owners):
        """
        Write a value to a specific address in the Directory object.
        """
        self.directory.set_state(address, state, owners)

    def display_data(self):
        """
        Display the current data in the Directory object.
        """
        for block, info in self.directory.directory.items():
            print(f"{block}: {info}")


