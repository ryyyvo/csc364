import socket
import sys
import time
import os
import glob
import traceback
from threading import Thread

# The purpose of this function is to set up a socket connection.
def create_socket(host, port):
    # 1. Create a socket.
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 2. Try connecting the socket to the host and port.
    try:
        soc.connect((host, port))
    except:
        print("Connection Error to", port)
        sys.exit()
    # 3. Return the connected socket.
    return soc

# The purpose of this function is to read in a CSV file.
def read_csv(path):
    # 1. Open the file for reading.
    table_file = open(path, "r")
    # 2. Store each line.
    table = table_file.readlines()
    # 3. Create an empty list to store each processed row.
    table_list = []
    # 4. For each line in the file:
    for line in table:
        # 5. split it by the delimiter,
        parts = line.strip().split(",")
        # 6. remove any leading or trailing spaces in each element, and
        parts = [p.strip() for p in parts]
        # Skip empty lines
        if len(parts) == 1 and parts[0] == "":
            continue
        # 7. append the resulting list to table_list.
        table_list.append(parts)
    # 8. Close the file and return table_list.
    table_file.close()
    return table_list

# The purpose of this function is to find the default port
# when no match is found in the forwarding table for a packet's destination IP.
def find_default_gateway(table):
    # 1. Traverse the table, row by row,
    for row in table:
        # 2. and if the network destination of that row matches 0.0.0.0,
        if row[0] == "0.0.0.0":
            # 3. then return the interface of that row.
            return row[3]

# The purpose of this function is to convert a string IP to its binary representation.
def ip_to_bin(ip):
    # 1. Split the IP into octets.
    ip_octets = ip.strip().split(".")
    if len(ip_octets) != 4:
        raise ValueError(f"Invalid IPv4 address: {ip}")
    # 2. Create an empty string to store each binary octet.
    ip_bin_string = ""
    # 3. Traverse the IP, octet by octet,
    for octet in ip_octets:
        # 4. and convert the octet to an int,
        int_octet = int(octet)
        if int_octet < 0 or int_octet > 255:
            raise ValueError(f"Invalid IPv4 octet: {octet}")
        # 5. convert the decimal int to binary,
        bin_octet = bin(int_octet)
        # 6. convert the binary to string and remove the "0b" at the beginning of the string,
        bin_octet_string = bin_octet[2:]
        # 7. while the sting representation of the binary is not 8 chars long,
        # then add 0s to the beginning of the string until it is 8 chars long
        # (needs to be an octet because we're working with IP addresses).
        while len(bin_octet_string) < 8:
            bin_octet_string = "0" + bin_octet_string
        # 8. Finally, append the octet to ip_bin_string.
        ip_bin_string += bin_octet_string
    # 9. Once the entire string version of the binary IP is created, convert it into an actual binary int.
    ip_int = int(ip_bin_string, 2)
    # 10. Return the binary representation of this int.
    return bin(ip_int)


# The purpose of this function is to perform a bitwise NOT on an unsigned integer.
def bit_not(n, numbits=32):
    return (1 << numbits) - 1 - n

# The purpose of this function is to write packets/payload to file.
def write_to_file(path, packet_to_write, send_to_router=None):
    # 1. Open the output file for appending.
    out_file = open(path, "a")
    # 2. If this router is not sending, then just append the packet to the output file.
    if send_to_router is None:
        out_file.write(packet_to_write + "\n")
    # 3. Else if this router is sending, then append the intended recipient, along with the packet, to the output file.
    else:
        out_file.write(packet_to_write + " " + "to Router " + send_to_router + "\n")
    # 4. Close the output file.
    out_file.close()