import socket
import struct
import time
import matplotlib.pyplot as plt
import sys

CHUNK_SIZE = 1024
TIMEOUT = 0.5
INITIAL_SSTHRESH = 64
DUPLICATE_ACK_THRESHOLD = 3

def parse_ack(ack_data):
    if len(ack_data) >= 4:
        ack_num = struct.unpack('!I', ack_data[:4])[0]
        return ack_num
    return None

def divide_file_into_chunks(file_data):
    chunks = []
    seq_num = 0
    
    for i in range(0, len(file_data), CHUNK_SIZE):
        chunk = file_data[i:i + CHUNK_SIZE]
        chunks.append((seq_num, chunk))
        seq_num += len(chunk)
    
    return chunks

def send_packet(sock, server_address, seq_num, data):
    checksum = sum(data) % 65535
    header = struct.pack('!IH', seq_num, checksum)
    packet = header + data
    sock.sendto(packet, server_address)

def receive_ack(sock, timeout):
    sock.settimeout(timeout)
    try:
        ack_data, _ = sock.recvfrom(1024)
        return parse_ack(ack_data)
    except socket.timeout:
        return None

def main():
    loss_rate = 0.10 # default 10% packet loss
    if len(sys.argv) > 1:
        loss_rate = float(sys.argv[1])

    server_address = ('127.0.0.1', 12345)
    filename = 'gistfile1.txt'
    
    with open(filename, 'rb') as f:
        file_data = f.read()
    
    chunks = divide_file_into_chunks(file_data)
    total_chunks = len(chunks)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    cwnd = 1.0 
    ssthresh = INITIAL_SSTHRESH
    base = 0
    next_seq_num = 0 
    duplicate_ack_count = {} 
    
    start_time = time.time()
    total_transmissions = 0
    retransmissions = 0
    
    timers = {}

    cwnd_log = [(0, cwnd)]
    retransmit_log = [(0, 0)]
    
    try:
        while base < total_chunks:
            while next_seq_num < total_chunks and next_seq_num < base + int(cwnd):
                seq_num, data = chunks[next_seq_num]
                send_packet(sock, server_address, seq_num, data)
                timers[next_seq_num] = time.time()
                total_transmissions += 1
                next_seq_num += 1
            
            ack_num = receive_ack(sock, TIMEOUT)
            current_time = time.time() - start_time
            
            if ack_num is not None:
                ack_chunk_idx = None
                for idx, (seq, chunk) in enumerate(chunks):
                    if seq == ack_num:
                        ack_chunk_idx = idx
                        break
                    elif idx < len(chunks) - 1 and seq < ack_num < chunks[idx + 1][0]:
                        ack_chunk_idx = idx + 1
                        break
                    elif idx == len(chunks) - 1 and ack_num >= seq + len(chunk):
                        ack_chunk_idx = total_chunks
                        break
                
                if ack_chunk_idx is None:
                    continue
                                
                if ack_chunk_idx == base:
                    if ack_chunk_idx not in duplicate_ack_count:
                        duplicate_ack_count[ack_chunk_idx] = 0
                    duplicate_ack_count[ack_chunk_idx] += 1
                                        
                    if duplicate_ack_count[ack_chunk_idx] == DUPLICATE_ACK_THRESHOLD:
                        seq_num, data = chunks[base]
                        send_packet(sock, server_address, seq_num, data)
                        timers[base] = time.time()
                        retransmissions += 1
                        total_transmissions += 1
                        
                        ssthresh = max(cwnd / 2, 2)
                        cwnd = ssthresh + 3
                        
                        duplicate_ack_count[ack_chunk_idx] = 0

                        cwnd_log.append((current_time, cwnd))
                        retransmit_log.append((current_time, retransmissions))
                
                elif ack_chunk_idx > base:
                    packets_acked = ack_chunk_idx - base
                    
                    if base in duplicate_ack_count:
                        del duplicate_ack_count[base]
                    
                    base = ack_chunk_idx
                    
                    if cwnd < ssthresh:
                        cwnd += packets_acked
                    else:
                        cwnd += packets_acked / cwnd            

                    cwnd_log.append((current_time, cwnd))

                    for idx in range(base - packets_acked, base):
                        if idx in timers:
                            del timers[idx]
                
            else:                
                seq_num, data = chunks[base]
                send_packet(sock, server_address, seq_num, data)
                timers[base] = time.time()
                retransmissions += 1
                total_transmissions += 1
                
                ssthresh = max(cwnd / 2, 2)
                cwnd = 1.0                
                next_seq_num = base + 1

                cwnd_log.append((current_time, cwnd))
                retransmit_log.append((current_time, retransmissions))
        
        end_time = time.time()
        total_time = end_time - start_time

        print(f"\nTotal time: {total_time:.2f} seconds")
        print(f"Total transmissions: {total_transmissions}")
        print(f"Retransmissions: {retransmissions}")
        print(f"Retransmission rate: {(retransmissions/total_transmissions)*100}%")

        times, cwnds = zip(*cwnd_log)
        plt.figure(figsize=(10, 4))
        plt.plot(times, cwnds, marker="o", markersize=3)
        plt.title(f"Congestion Window (cwnd) vs Time\n(Packet Loss: {loss_rate*100}%)")
        plt.xlabel("Time (Seconds)")
        plt.ylabel("Congestion Window (Packets)")
        plt.grid(True)
        cwnd_filename = f"cwnd_vs_time_{int(loss_rate*100)}.png"
        plt.savefig(cwnd_filename)
        plt.close()

        if retransmit_log:
            r_times, r_counts = zip(*retransmit_log)
            plt.figure(figsize=(10, 4))
            plt.step(r_times, r_counts, where='post')
            plt.title(f"Cumulative Retransmissions vs Time\n(Packet Loss: {loss_rate*100}%)")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Retransmissions")
            plt.grid(True)
            retrans_filename = f"retransmissions_vs_time_{int(loss_rate*100)}.png"
            plt.savefig(retrans_filename)
            plt.close()
        else:
            print("No retransmissions were recorded.")

    finally:
        sock.close()

if __name__ == "__main__":
    main()