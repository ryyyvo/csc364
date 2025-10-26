import socket
import sys
import struct
import select
import time

MSG_LOGIN = 0
MSG_LOGOUT = 1
MSG_JOIN = 2
MSG_LEAVE = 3
MSG_SAY = 4
MSG_LIST = 5
MSG_WHO = 6
MSG_KEEPALIVE = 7

MSG_SERVER_SAY = 0
MSG_SERVER_LIST = 1
MSG_SERVER_WHO = 2
MSG_SERVER_ERROR = 3

USERNAME_SIZE = 32
CHANNEL_SIZE = 32
TEXT_SIZE = 64

CLIENT_TIMEOUT = 120  

def parse_args():
    if len(sys.argv) != 3:
        print(f"Usage: python3 server1.py <host> <port>")
        exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    return host, port

def create_socket():
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return soc
    except socket.error as err:
        print(f"Error creating socket: {err}")
        sys.exit(1)
        
def send_error(soc, client_addr, error_msg):
    packet = struct.pack('!I', MSG_SERVER_ERROR)
    packet += error_msg.encode('utf-8')[:TEXT_SIZE].ljust(TEXT_SIZE, b'\0')
    soc.sendto(packet, client_addr)


def send_say(soc, client_addr, channel, username, text):
    packet = struct.pack('!I', MSG_SERVER_SAY)
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    packet += username.encode('utf-8').ljust(USERNAME_SIZE, b'\0')
    packet += text.encode('utf-8').ljust(TEXT_SIZE, b'\0')
    soc.sendto(packet, client_addr)


def send_list(soc, client_addr, channels):
    packet = struct.pack('!I', MSG_SERVER_LIST)
    packet += struct.pack('!I', len(channels))
    for channel in channels:
        packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    soc.sendto(packet, client_addr)


def send_who(soc, client_addr, channel, users):
    packet = struct.pack('!I', MSG_SERVER_WHO)
    packet += struct.pack('!I', len(users))
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    
    for username in users:
        packet += username.encode('utf-8').ljust(USERNAME_SIZE, b'\0')
    
    soc.sendto(packet, client_addr)


def handle_login(soc, data, client_addr, users, channels):
    if len(data) < 4 + USERNAME_SIZE:
        return
    
    username = data[4:4+USERNAME_SIZE].decode('utf-8').rstrip('\0')
    
    users[client_addr] = {
        'username': username,
        'channels': set(),
        'last_activity': time.time()
    }
    
    print(f"[LOGIN][{username}] from {client_addr}")


def handle_logout(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    username = users[client_addr]['username']
    user_channels = users[client_addr]['channels'].copy()
    
    for channel_name in user_channels:
        if channel_name in channels:
            channels[channel_name].discard(client_addr)
            if not channels[channel_name]:
                del channels[channel_name]
    
    del users[client_addr]

    print(f"[LOGOUT][{username}] from {client_addr}")


def handle_join(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    if len(data) < 4 + CHANNEL_SIZE:
        return
    
    channel_name = data[4:4+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    username = users[client_addr]['username']
    
    if channel_name not in channels:
        channels[channel_name] = set()
    
    channels[channel_name].add(client_addr)
    users[client_addr]['channels'].add(channel_name)
    users[client_addr]['last_activity'] = time.time()
    
    print(f"[{channel_name}][{username}][JOIN]")


def handle_leave(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    if len(data) < 4 + CHANNEL_SIZE:
        return
    
    channel_name = data[4:4+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    username = users[client_addr]['username']

    if channel_name in channels:
        channels[channel_name].discard(client_addr)
        users[client_addr]['channels'].discard(channel_name)
        
        if not channels[channel_name]:
            del channels[channel_name]
    
    users[client_addr]['last_activity'] = time.time()
    
    print(f"[{channel_name}][{username}][LEAVE]")


def handle_say(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    if len(data) < 4 + CHANNEL_SIZE + TEXT_SIZE:
        return
    
    offset = 4
    channel_name = data[offset:offset+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    offset += CHANNEL_SIZE
    text = data[offset:offset+TEXT_SIZE].decode('utf-8').rstrip('\0')
    
    username = users[client_addr]['username']
    users[client_addr]['last_activity'] = time.time()
    
    print(f"[{channel_name}][{username}][SAY]: {text}")
    
    if channel_name in channels:
        for user_addr in channels[channel_name]:
            send_say(soc, user_addr, channel_name, username, text)


def handle_list(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    username = users[client_addr]['username']
    users[client_addr]['last_activity'] = time.time()
    
    print(f"[{username}][LIST]")
    
    channel_list = list(channels.keys())
    send_list(soc, client_addr, channel_list)


def handle_who(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    if len(data) < 4 + CHANNEL_SIZE:
        return
    
    channel_name = data[4:4+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    username = users[client_addr]['username']
    users[client_addr]['last_activity'] = time.time()
    
    print(f"[{channel_name}][{username}][WHO]")
    
    user_list = []
    if channel_name in channels:
        for user_addr in channels[channel_name]:
            if user_addr in users:
                user_list.append(users[user_addr]['username'])
    
    send_who(soc, client_addr, channel_name, user_list)


def handle_keepalive(soc, data, client_addr, users, channels):
    if client_addr not in users:
        return
    
    users[client_addr]['last_activity'] = time.time()
    username = users[client_addr]['username']
    
    print(f"[{username}][KEEPALIVE]")

def handle_client_message(soc, data, client_addr, users, channels):
    if len(data) < 4:
        return
    
    msg_type = struct.unpack('!I', data[:4])[0]
    
    if msg_type == MSG_LOGIN:
        handle_login(soc, data, client_addr, users, channels)
    elif msg_type == MSG_LOGOUT:
        handle_logout(soc, data, client_addr, users, channels)
    elif msg_type == MSG_JOIN:
        handle_join(soc, data, client_addr, users, channels)
    elif msg_type == MSG_LEAVE:
        handle_leave(soc, data, client_addr, users, channels)
    elif msg_type == MSG_SAY:
        handle_say(soc, data, client_addr, users, channels)
    elif msg_type == MSG_LIST:
        handle_list(soc, data, client_addr, users, channels)
    elif msg_type == MSG_WHO:
        handle_who(soc, data, client_addr, users, channels)
    elif msg_type == MSG_KEEPALIVE:
        handle_keepalive(soc, data, client_addr, users, channels)

def check_timeouts(users, channels):
    current_time = time.time()
    timed_out_users = []
    
    for client_addr, user_info in users.items():
        if current_time - user_info['last_activity'] > CLIENT_TIMEOUT:
            timed_out_users.append(client_addr)
    
    # remove timed out users
    for client_addr in timed_out_users:
        username = users[client_addr]['username']
        print(f"[TIMEOUT][{username}] from {client_addr}")
        
        # remove from all channels
        user_channels = users[client_addr]['channels'].copy()
        for channel_name in user_channels:
            if channel_name in channels:
                channels[channel_name].discard(client_addr)
                if not channels[channel_name]:
                    del channels[channel_name]
        
        del users[client_addr]



def main():
    host, port = parse_args()
    soc = create_socket()
    soc.bind((host, port))

    print(f"Server listening on {host}:{port}")

    users = {}  
    channels = {} 
    last_timeout_check = time.time()

    try:
        while True:
            readable, _, _ = select.select([soc], [], [], 1.0)
            
            if soc in readable:
                data, client_addr = soc.recvfrom(4096)
                handle_client_message(soc, data, client_addr, users, channels)
            
            current_time = time.time()
            if current_time - last_timeout_check >= CLIENT_TIMEOUT:
                check_timeouts(users, channels)
                last_timeout_check = current_time
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        soc.close()


if __name__ == "__main__":
    main()