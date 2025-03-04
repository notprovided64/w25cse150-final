import argparse, socket, select, signal, sys, os

BUFSIZE = 4096
INV_IN_MSG = "invalid input provided"

TIMEOUT = 10 # in seconds

def validate_port(port):
    return 1 <= port <= 65535

def validate_server(server):
    if ':' not in server:
        return False
    
    host, port = server.rsplit(':', 1)
    
    if not port.isdigit():
        return False
    
    port = int(port)
    if not (0 < port <= 65535):
        return False
    
    octets = host.split('.')
    if len(octets) != 4:
        return False
    
    for octet in octets:
        if not octet.isdigit() or not (0 <= int(octet) <= 255):
            return False
    
    return True

def validate_args(args):
    if not validate_port(args.port):
        print("invalid port num")
        return False
    if not validate_server(args.server):
        print("invalid server ip")
        return False

    return True


def parse_args():
    parser = argparse.ArgumentParser(description="client for final project")
    
    parser.add_argument("--id", type=str, required=True, help="ClientID")
    parser.add_argument("--port", type=int, required=True, help="client port")
    parser.add_argument("--server", type=str, required=True, help="Server IP: Port number")

    args = parser.parse_args()

    return args

def send(host, port, contents):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(TIMEOUT)

    try:
        client_socket.connect((host, int(port)))
        client_socket.send(contents.encode())
        client_socket.close()
        
    except socket.gaierror:
        print(f"address-related error connecting to {host} on port {port}")
        client_socket.close()
        return 1 #replace with exit(1)
    
    except socket.timeout:
        print(f"connection timed out when trying to connect to {host} on port {port}")
        client_socket.close()
        return 1
    
    except socket.error as err:
        print(f"socket error occurred: {err}")
        client_socket.close()
        return 1

def get_reg_req(id, port):
    host_ip = socket.gethostbyname("localhost")
    return f"REGISTER\r\nclientID: {id}\r\nIP: {host_ip}\r\nPort: {port}\r\n\r\n"

def get_bridge_req(id):
    return f"BRIDGE\r\nclientID: {id}\r\n\r\n"

def loop(args):
    host, port = args.server.split(':')
    client_ip = socket.gethostbyname(socket.gethostname())
    print(f"{args.id} running on {client_ip}:{port}")

    try:
        while(True):
            uin = input()

            if uin == "/id":
                print(args.id)
            elif uin == "/register":
                send(host, port, get_reg_req(args.id, args.port))
            elif uin == "/bridge":
                send(host, port, get_bridge_req(args.id))
            else:
                print(INV_IN_MSG)
    except KeyboardInterrupt:
        print("Terminating the chat client.\nExiting program")
        return 0

def main():
    args = parse_args()

    if not validate_args(args):
        return 1

    loop(args)

if __name__ == "__main__":
    main()
