import socket
import struct
import random

HEADER_SIZE = 6 
PACKET_LOSS_PROBABILITY = 0.50
OUTPUT_FILE = 'received.txt'

def parse_packet(packet_data):
    if len(packet_data) < HEADER_SIZE:
        return None
    try:
        seq_num, checksum = struct.unpack('!IH', packet_data[:HEADER_SIZE])
        data = packet_data[HEADER_SIZE:]
        return seq_num, checksum, data
    except struct.error:
        return None

def validate_checksum(data, received_checksum):
    calculated_checksum = sum(data) % 65535
    return calculated_checksum == received_checksum

def send_ack(sock, client_address, ack_num):
    ack_packet = struct.pack('!I', ack_num)
    sock.sendto(ack_packet, client_address)

def main():
    server_address = ('127.0.0.1', 12345)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)
    
    received_data = {}
    next_expected_seq = 0

    packets_received = 0
    packets_corrupted = 0
    packets_dropped = 0
    duplicate_packets = 0
    
    try:
        while True:
            packet_data, client_address = sock.recvfrom(2048)
            packets_received += 1
            
            if random.random() < PACKET_LOSS_PROBABILITY:
                packets_dropped += 1
                print(f"Dropped: Simulated packet loss (total dropped: {packets_dropped})")
                continue

            parsed = parse_packet(packet_data)
            if parsed is None:
                print("Error: Invalid packet format")
                continue
            
            seq_num, checksum, data = parsed

            if not validate_checksum(data, checksum):
                packets_corrupted += 1
                print(f"Corrupted: Packet with seq_num {seq_num} failed checksum validation")
                continue
            
            print(f"Received: Packet seq_num={seq_num}, size={len(data)} bytes, checksum={checksum}")

            if seq_num in received_data:
                duplicate_packets += 1
                print(f"Duplicate: Packet seq_num={seq_num} already received")
                send_ack(sock, client_address, next_expected_seq)
                continue
            
            received_data[seq_num] = data
            
            while next_expected_seq in received_data:
                chunk = received_data[next_expected_seq]
                next_expected_seq += len(chunk)

            send_ack(sock, client_address, next_expected_seq)
            
    except KeyboardInterrupt:        
        sorted_seq_nums = sorted(received_data.keys())
        
        with open(OUTPUT_FILE, 'wb') as f:
            for seq_num in sorted_seq_nums:
                f.write(received_data[seq_num])
        
        print(f"\nTotal packets received: {packets_received}")
        print(f"Packets dropped: {packets_dropped}")
        print(f"Packets corrupted: {packets_corrupted}")
        print(f"Duplicate packets: {duplicate_packets}")
        
    finally:
        sock.close()

if __name__ == "__main__":
    main()