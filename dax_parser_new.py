import re
from collections import OrderedDict


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


class DAXParser:
    def __init__(self):
        self.dax_output = ""
        self.data = OrderedDict()
        self.directory = Directory()  # For Directory-based protocol

    def set_output(self, dax_output):
        """
        Set the DAX output string for parsing.
        """
        self.dax_output = dax_output

    def parse(self, protocol="Snooping"):
        """
        Parse the dax_output to extract key-value pairs into self.data.
        Supports both Snooping and Directory-based protocols.
        """
        if protocol not in ["Snooping", "Directory"]:
            raise ValueError("Invalid protocol. Use 'Snooping' or 'Directory'.")

        match = re.search(r"\{(.*)\}", self.dax_output)
        if match:
            content = match.group(1)
            if ":" in content and "[" in content:
                self._parse_directory(content)
            else:
                self._parse_snooping(content)

    def _parse_snooping(self, content):
        """
        Parse the Snooping protocol format.
        Example: {'0xABC': 'Ajay', '0xCCC': 'Alas'}
        """
        for pair in content.split(","):
            key, value = pair.split(":")
            key = key.strip().strip("'")  # Strip whitespace and quotes
            value = value.strip().strip("'")  # Strip whitespace and quotes
            self.data[key] = value

    def _parse_directory(self, content):
        """
        Parse the Directory-based protocol format.
        Populate the Directory object and self.data.
        Example: {'0xABC': ['Ajay', 'U', ''], '0xCCC': ['Alas', 'U', '']}
        """
        if not content.startswith("{") or not content.endswith("}"):
            content = "{" + content + "}"
        parsed_content = eval(content)  # Ensure the input is trusted

        for address, info in parsed_content.items():
            # Extract state and owners
            state = info.get("state", "U")
            owners_raw = info.get("owners", [])
            # Convert owners to integers, ignoring empty strings
            owners = [int(o) for o in owners_raw if isinstance(o, str) and o.isdigit()]
            owners += [o for o in owners_raw if isinstance(o, int)]

            # Print parsed results
            print(f"Address: {address}, State: {state}, Owners: {owners}")

            self.directory.set_state(address, state, owners)

    def read_address(self, address, protocol="Snooping"):
        """
        Read the value at a specific address.
        """
        if protocol == "Directory":
            return self.directory.get_state(address)
        return self.data.get(address, None)

    def write_address(self, address, value, protocol="Snooping"):
        """
        Write a value to a specific address.
        """
        if protocol == "Directory":
            state = value[1] if len(value) > 1 else "M"
            owners = value[2:] if len(value) > 2 else []
            self.directory.set_state(address, state, owners)
        else:
            self.data[address] = value

    def display_data(self, protocol="Snooping"):
        """
        Display the current data in the object.
        """
        if protocol == "Directory":
            for block, info in self.directory.directory.items():
                print(f"{block}: {info}")
        else:
            for key, value in self.data.items():
                print(f"{key}: {value}")


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
