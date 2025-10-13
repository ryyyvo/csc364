from threading import Thread
import utilities as util
import socket
import sys
import traceback

# The purpose of this function is to
# (a) create a server socket,
# (b) listen on a specific port,
# (c) receive and process incoming packets,
# (d) forward them on, if needed.
def start_server():
    # 1. Create a socket.
    host = "127.0.0.1"
    port = 8006
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("Socket created")
    # 2. Try binding the socket to the appropriate host and receiving port (based on the network topology diagram).
    try:
        soc.bind((host, port))
    except:
        print("Bind failed. Error : " + str(sys.exc_info()))
        sys.exit()
    # 3. Set the socket to listen.
    soc.listen(5)
    print("Socket now listening")

    # 4. Read in and store the forwarding table.
    forwarding_table = util.read_csv("./input/router_6_table.csv")
    # 5. Store the default gateway port.
    default_gateway_port = util.find_default_gateway(forwarding_table)
    # 6. Generate a new forwarding table that includes the IP ranges for matching against destination IPS.
    forwarding_table_with_range = util.generate_forwarding_table_with_range(forwarding_table)

    # 7. Continuously process incoming packets.
    while True:
        # 8. Accept the connection.
        connection, address = soc.accept()
        ip, port = address[0], str(address[1])
        print("Connected with " + ip + ":" + port)
        # 9. Start a new thread for receiving and processing the incoming packets.
        try:
            thread = Thread(target=processing_thread, args=(connection, ip, port, forwarding_table_with_range, default_gateway_port))
            thread.start()
        except:
            print("Thread did not start.")
            traceback.print_exc()


# The purpose of this function is to receive and process incoming packets.
def processing_thread(connection, ip, port, forwarding_table_with_range, default_gateway_port, max_buffer_size=5120):

    # 2. Continuously process incoming packets
    while True:
        # 3. Receive the incoming packet, process it, and store its list representation
        packet = util.receive_packet(connection, max_buffer_size, "6")

        # 4. If the packet is empty (Router 1 has finished sending all packets), break out of the processing loop
        if not packet or packet[0] == "":
            break

        # 5. Store the source IP, destination IP, payload, and TTL.
        sourceIP = packet[0]
        destinationIP = packet[1]
        payload = packet[2]
        ttl = int(packet[3])

        # 6. Decrement the TTL by 1 and construct a new packet with the new TTL.
        new_ttl = ttl - 1
        new_packet = f"{sourceIP},{destinationIP},{payload},{new_ttl}"

        # 7. Convert the destination IP into an integer for comparison purposes.
        destinationIP_int = util.ip_to_bin(destinationIP)

        # 8. Find the appropriate sending port to forward this new packet to.
        sending_port = None
        for row in forwarding_table_with_range:
            # row = [min_ip, max_ip, interface]
            min_ip = row[0]
            max_ip = row[1]
            interface = row[2]
            if min_ip <= destinationIP_int <= max_ip:
                sending_port = interface
                break
        else:
            sending_port = default_gateway_port

        # 9. If no port is found, then set the sending port to the default port.
        ## ...

        # 11. Either
        # (a) send the new packet to the appropriate port (and append it to sent_by_router_2.txt),
        # (b) append the payload to out_router_2.txt without forwarding because this router is the last hop, or
        # (c) append the new packet to discarded_by_router_2.txt and do not forward the new packet
        if sending_port == "127.0.0.1":
            print("OUT:", payload)
            util.write_to_file("./output/out_router_6.txt", payload)
        else:
            print("DISCARD:", new_packet)
            util.write_to_file("./output/discarded_by_router_6.txt", str(new_packet))


# Main Program

# 1. Start the server.
start_server()