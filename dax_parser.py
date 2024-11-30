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
        """
        match = re.search(r"\{(.*)\}", self.dax_output)
        if match:
            content = match.group(1)
            # Split by ',' and process each key-value pair
            for pair in content.split(","):
                key, value = pair.split(":")
                key = key.strip().strip("'")  # Strip whitespace and quotes
                value = value.strip().strip("'")  # Strip whitespace and quotes
                self.data[key] = value

    def read_address(self, address):
        """
        Read the value at a specific address.
        """
        return self.data.get(address, None)

    def write_address(self, address, value):
        """
        Write a value to a specific address.
        """
        self.data[address] = value

    def display_data(self):
        """
        Display the current data in the object.
        """
        for key, value in self.data.items():
            print(f"{key}: {value}")


# Example Usage
if __name__ == "__main__":
    dax_output = "Paragraph read from DAX device:\n{'0xABC': 'Ajay', '0xCCC': 'Alas', '0xDDD': 'Ajay-1', '0xEEE': 'Ajay-2'}"
    parser = DAXParser()

    # Set the DAX output and parse it
    parser.set_output(dax_output)
    parser.parse()

    print("Parsed Data:")
    parser.display_data()

    # Read a specific address
    address_to_read = "0xABC"
    value = parser.read_address(address_to_read)
    print(f"\nValue at address {address_to_read}: {value}")

    # Write to a specific address
    address_to_write = "0xFFF"
    value_to_write = "Ajay-New"
    parser.write_address(address_to_write, value_to_write)
    print("\nData after writing:")
    parser.display_data()
