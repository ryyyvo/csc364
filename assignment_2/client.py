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

def parse_args():
    if len(sys.argv) != 4:
        print(f"Usage: python3 client.py <host> <port> <username>")
        exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    
    if len(username) > USERNAME_SIZE:
        print(f"Error: Username must be {USERNAME_SIZE} characters or less")
        exit(1)
    
    return host, port, username

def create_socket():
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return soc
    except socket.error as err:
        print(f"Error creating socket: {err}")
        sys.exit(1)

def send_login(soc, server_addr, username):
    packet = struct.pack('!I', MSG_LOGIN)
    packet += username.encode('utf-8').ljust(USERNAME_SIZE, b'\0')
    soc.sendto(packet, server_addr)

def send_logout(soc, server_addr):
    packet = struct.pack('!I', MSG_LOGOUT)
    soc.sendto(packet, server_addr)

def send_join(soc, server_addr, channel):
    packet = struct.pack('!I', MSG_JOIN)
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    soc.sendto(packet, server_addr)

def send_leave(soc, server_addr, channel):
    packet = struct.pack('!I', MSG_LEAVE)
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    soc.sendto(packet, server_addr)

def send_say(soc, server_addr, channel, text):
    packet = struct.pack('!I', MSG_SAY)
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    packet += text.encode('utf-8').ljust(TEXT_SIZE, b'\0')
    soc.sendto(packet, server_addr)

def send_list(soc, server_addr):
    packet = struct.pack('!I', MSG_LIST)
    soc.sendto(packet, server_addr)

def send_who(soc, server_addr, channel):
    packet = struct.pack('!I', MSG_WHO)
    packet += channel.encode('utf-8').ljust(CHANNEL_SIZE, b'\0')
    soc.sendto(packet, server_addr)

def send_keepalive(soc, server_addr):
    packet = struct.pack('!I', MSG_KEEPALIVE)
    soc.sendto(packet, server_addr)

def parse_command(user_input):
    if not user_input.startswith('/'):
        return 'say', [user_input]
    
    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    
    if command == '/exit':
        return 'exit', []
    elif command == '/join':
        if len(parts) < 2:
            return 'error', ["Usage: /join <channel>"]
        return 'join', [parts[1]]
    elif command == '/leave':
        if len(parts) < 2:
            return 'error', ["Usage: /leave <channel>"]
        return 'leave', [parts[1]]
    elif command == '/list':
        return 'list', []
    elif command == '/who':
        if len(parts) < 2:
            return 'error', ["Usage: /who <channel>"]
        return 'who', [parts[1]]
    elif command == '/switch':
        if len(parts) < 2:
            return 'error', ["Usage: /switch <channel>"]
        return 'switch', [parts[1]]
    else:
        return 'error', [f"Unknown command: {command}"]

def handle_server_say(data, current_input):
    if len(data) < 4 + CHANNEL_SIZE + USERNAME_SIZE + TEXT_SIZE:
        return
    
    offset = 4
    channel = data[offset:offset+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    offset += CHANNEL_SIZE
    username = data[offset:offset+USERNAME_SIZE].decode('utf-8').rstrip('\0')
    offset += USERNAME_SIZE
    text = data[offset:offset+TEXT_SIZE].decode('utf-8').rstrip('\0')
    
    print('\r' + ' ' * (len(current_input) + 2), end='')
    print(f"\r[{channel}][{username}]: {text}")
    print(f"> {current_input}", end='', flush=True)

def handle_server_list(data, current_input):
    if len(data) < 8:
        return
    
    num_channels = struct.unpack('!I', data[4:8])[0]
    
    print('\r' + ' ' * (len(current_input) + 2), end='')
    print("\rExisting channels:")
    
    offset = 8
    for i in range(num_channels):
        if len(data) < offset + CHANNEL_SIZE:
            break
        channel = data[offset:offset+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
        print(f"  {channel}")
        offset += CHANNEL_SIZE
    
    print(f"> {current_input}", end='', flush=True)

def handle_server_who(data, current_input):
    if len(data) < 8:
        return
    
    num_users = struct.unpack('!I', data[4:8])[0]
    offset = 8
    
    if len(data) < offset + CHANNEL_SIZE:
        return
    
    channel = data[offset:offset+CHANNEL_SIZE].decode('utf-8').rstrip('\0')
    offset += CHANNEL_SIZE
    
    print('\r' + ' ' * (len(current_input) + 2), end='')
    print(f"\rUsers on channel {channel}:")
    
    for i in range(num_users):
        if len(data) < offset + USERNAME_SIZE:
            break
        username = data[offset:offset+USERNAME_SIZE].decode('utf-8').rstrip('\0')
        print(f"  {username}")
        offset += USERNAME_SIZE
    
    print(f"> {current_input}", end='', flush=True)

def handle_server_error(data, current_input):
    if len(data) < 4 + TEXT_SIZE:
        return
    
    error_msg = data[4:4+TEXT_SIZE].decode('utf-8').rstrip('\0')
    
    print('\r' + ' ' * (len(current_input) + 2), end='')
    print(f"\rError: {error_msg}")
    print(f"> {current_input}", end='', flush=True)

def handle_server_message(data, current_input):
    if len(data) < 4:
        return
    
    msg_type = struct.unpack('!I', data[:4])[0]
    
    if msg_type == MSG_SERVER_SAY:
        handle_server_say(data, current_input)
    elif msg_type == MSG_SERVER_LIST:
        handle_server_list(data, current_input)
    elif msg_type == MSG_SERVER_WHO:
        handle_server_who(data, current_input)
    elif msg_type == MSG_SERVER_ERROR:
        handle_server_error(data, current_input)

def main():
    host, port, username = parse_args()
    server_address = (host, port)
    soc = create_socket()
    
    active_channel = None
    subscribed_channels = set()
    last_send_time = time.time()
    current_input = "" 

    try:
        send_login(soc, server_address, username)
        last_send_time = time.time()
        
        send_join(soc, server_address, "Common")
        active_channel = "Common"
        subscribed_channels.add("Common")
        last_send_time = time.time()
        
        print("> ", end='', flush=True)
        
        while True:
            current_time = time.time()
            if current_time - last_send_time >= 60:
                send_keepalive(soc, server_address)
                last_send_time = current_time
            
            readable, _, _ = select.select([sys.stdin, soc], [], [], 1.0)
            
            if sys.stdin in readable:
                user_input = sys.stdin.readline().strip()
                current_input = "" 
                
                cmd_type, args = parse_command(user_input)
                
                if cmd_type == 'exit':
                    send_logout(soc, server_address)
                    break
                elif cmd_type == 'join':
                    channel = args[0]
                    if len(channel) > CHANNEL_SIZE:
                        print(f"Error: Channel name must be {CHANNEL_SIZE} characters or less")
                    else:
                        send_join(soc, server_address, channel)
                        active_channel = channel
                        subscribed_channels.add(channel)
                        last_send_time = time.time()
                elif cmd_type == 'leave':
                    channel = args[0]
                    send_leave(soc, server_address, channel)
                    subscribed_channels.discard(channel)
                    if channel == active_channel:
                        active_channel = None
                    last_send_time = time.time()
                elif cmd_type == 'list':
                    send_list(soc, server_address)
                    last_send_time = time.time()
                elif cmd_type == 'who':
                    send_who(soc, server_address, args[0])
                    last_send_time = time.time()
                elif cmd_type == 'switch':
                    if args[0] in subscribed_channels:
                        active_channel = args[0]
                    else:
                        print(f"Error: Not subscribed to channel {args[0]}")
                elif cmd_type == 'say':
                    if active_channel:
                        text = args[0]
                        if len(text) > TEXT_SIZE:
                            text = text[:TEXT_SIZE]
                        send_say(soc, server_address, active_channel, text)
                        last_send_time = time.time()
                elif cmd_type == 'error':
                    print(args[0])
                
                print("> ", end='', flush=True)
            
            if soc in readable:
                data, _ = soc.recvfrom(4096)
                handle_server_message(data, current_input)
    
    except KeyboardInterrupt:
        print("\nExiting...")
        send_logout(soc, server_address)
    finally:
        soc.close()

if __name__ == "__main__":
    main()