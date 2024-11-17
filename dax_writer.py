import mmap
import os
import sys

# Replace with your DAX device file path
FILENAME = "/dev/dax0.0"
REGION_SIZE = 4294967296  # 4 GB


def dax_writer():
    # Check command-line arguments
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <string>")
        return 1

    string_to_write = sys.argv[1]
    size_to_write = len(string_to_write) + 1  # Include null terminator

    # Open the file
    try:
        fd = os.open(FILENAME, os.O_RDWR)
    except OSError as e:
        print(f"Error opening file: {e}")
        return 1

    # Memory-map the file
    try:
        with mmap.mmap(fd, REGION_SIZE, access=mmap.ACCESS_WRITE) as mm:
            # Clear the memory region
            mm[:size_to_write] = b'\x00' * size_to_write

            # Write the string to memory
            mm[:size_to_write] = string_to_write.encode('utf-8') + b'\x00'  # Add null terminator
            print("Paragraph written to DAX device successfully.")
    except Exception as e:
        print(f"Error mapping file: {e}")
        return 1
    finally:
        os.close(fd)

    return 0


if __name__ == "__main__":
    dax_writer()
