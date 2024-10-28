import argparse
import os
import socket
import struct
from typing import Tuple


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="TFTP Client")
    parser.add_argument("file", nargs='?', default="data.txt",
                        help="The name of the file to transfer (default: data.txt)")
    parser.add_argument("-m", help="Mode (rx for read)", default="rx")
    parser.add_argument("-p", type=int, help="Port number", default=6969)
    return parser.parse_args()


def send_rrq(client_socket: socket.socket, server_address: Tuple[str, int], filename: str) -> None:
    """
    Send a Read Request (RRQ) to the TFTP server.

    :param client_socket: The UDP socket.
    :param server_address: The server address.
    :param filename: The name of the file to request.
    """
    if not os.path.isfile(filename):
        print(f"Error: The file '{filename}' does not exist.")
        return

    if not os.access(filename, os.R_OK):
        print(f"Error: The file '{filename}' cannot be read due to permission issues.")
        return

    packet = struct.pack("!H", 1) + bytes(filename, 'utf-8') + b'\x00octet\x00'
    client_socket.sendto(packet, server_address)
    print(f"Starting TFTP transfer to IP={server_address[0]} and PORT={server_address[1]} to get FILE={filename}")


import logging

def receive_data(client_socket: socket.socket, server_address: Tuple[str, int], filename: str) -> None:
    """
    Receive data from the TFTP server and write it to a file.

    :param client_socket: The UDP socket.
    :param server_address: The server address.
    :param filename: The name of the file to write the received data to.
    """
    block_num = 1
    retries = 0
    max_retries = 3
    ack_packet = None

    with open(filename, 'wb') as file:
        while True:
            try:
                data, addr = client_socket.recvfrom(516)
                opcode, block = struct.unpack("!HH", data[:4])

                if opcode != 3:  # Expected DATA packet
                    logging.error(f"Received packet with unexpected opcode {opcode}. Terminating.")
                    break

                if block != block_num:
                    logging.error(f"Received out-of-order block #{block}. Expected block #{block_num}. Terminating.")
                    break

                logging.info(f"Received block #{block}")
                file.write(data[4:])  # Write data to file
                logging.debug(f"Written {len(data[4:])} bytes to file")
                # Send ACK
                ack_packet = struct.pack("!HH", 4, block)
                client_socket.sendto(ack_packet, addr)
                block_num += 1
                retries = 0  # Reset retries on successful receive

                if len(data[4:]) < 512:
                    logging.info("Finished receiving file.")
                    break
            except socket.timeout:
                retries += 1
                if retries > max_retries:
                    logging.error("Timeout waiting for data, maximum retries reached. Terminating.")
                    break
                logging.warning(f"Timeout waiting for data, retrying... ({retries}/{max_retries})")
                if ack_packet:
                    client_socket.sendto(ack_packet, server_address)  # Resend last ACK to trigger retransmission

def main() -> None:
    """
    Main function to run the TFTP client.
    """
    args = parse_arguments()
    server_address = ("127.0.0.1", args.p)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2)

    try:
        if args.m == "rx":
            send_rrq(client_socket, server_address, args.file)
            receive_data(client_socket, server_address, args.file)
        else:
            print("Unsupported mode. Use -m rx for reading a file.")
    finally:
        client_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()