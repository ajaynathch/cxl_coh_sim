import re
from collections import OrderedDict


class DAXParser:
    def __init__(self):
        self.dax_output = ""
        self.data = OrderedDict()

    def set_output(self, dax_output):
        """
        Set the DAX output string for parsing.
        """
        self.dax_output = dax_output

    def parse(self):
        """
        Parse the dax_output to extract key-value pairs into self.data.
        Detects the coherence protocol format (Snooping or Directory).
        """
        match = re.search(r"\{(.*)\}", self.dax_output)
        if match:
            content = match.group(1)
            # Check for Directory-Based Protocol (values are lists)
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
        Parse the Directory protocol format.
        Example: {'0xABC': ['Ajay', 'U', ''], '0xCCC': ['Alas', 'U', '']}
        """
        for pair in content.split("],"):
            key, value = pair.split(":")
            key = key.strip().strip("'")
            value = value.strip().replace("[", "").replace("]", "")
            # Convert value into a cleaned list of strings
            cleaned_value = [v.strip().strip("'") for v in value.split(",")]
            self.data[key] = cleaned_value

    def read_address(self, address):
        """
        Read the value at a specific address.
        """
        return self.data.get(address, None)

    def write_address(self, address, value):
        """
        Write a value to a specific address.
        For Directory protocol, ensure the value is in the correct format.
        """
        if isinstance(value, list):  # Directory protocol
            self.data[address] = value
        else:  # Snooping protocol
            self.data[address] = value

    def display_data(self):
        """
        Display the current data in the object.
        """
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
    dax_output_directory = "Paragraph read from DAX device:\n{'0xABC': ['Ajay', 'U', ''], '0xCCC': ['Alas', 'U', ''], '0xDDD': ['Ajay-1', 'U', ''], '0xEEE': ['Ajay-2', 'U', '']}"
    directory_parser = DAXParser()
    directory_parser.set_output(dax_output_directory)
    directory_parser.parse()

    print("\n--- Directory Protocol Parsed Data ---")
    directory_parser.display_data()

    # Example of address read and write
    print("\n--- Address Access Example ---")
    address_to_read = "0xABC"
    value = directory_parser.read_address(address_to_read)
    print(f"Value at address {address_to_read}: {value}")

    address_to_write = "0xFFF"
    value_to_write = ["NewData", "M", "VM1"]
    directory_parser.write_address(address_to_write, value_to_write)
    print("\nData after writing:")
    directory_parser.display_data()
