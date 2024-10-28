# Create a data.txt file and write multiple blocks of data to it
block_size = 512
num_blocks = 5  # Number of blocks to write

with open('data.txt', 'w') as file:
    for i in range(num_blocks):
        file.write(f"Block {i+1}\n" + "A" * (block_size - len(f"Block {i+1}\n")))