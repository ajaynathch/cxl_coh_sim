import mmap
import os

# Replace with your DAX device file path
FILENAME = "/dev/dax0.0"
REGION_SIZE = 4294967296  # 4 GB


def dax_reader():
    # Open the file
    try:
        fd = os.open(FILENAME, os.O_RDWR)
    except OSError as e:
        print(f"Error opening file: {e}")
        return 1

    # Memory-map the file
    try:
        with mmap.mmap(fd, REGION_SIZE, access=mmap.ACCESS_READ) as mm:
            print("Paragraph read from DAX device:")
            print(mm[:4096].decode('utf-8', errors='ignore'))  # Read and print 4096 bytes
    except Exception as e:
        print(f"Error mapping file: {e}")
        return 1
    finally:
        os.close(fd)

    return 0


if __name__ == "__main__":
    dax_reader()