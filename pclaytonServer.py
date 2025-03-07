import argparse, socket, select, signal, sys, os, re

BUFSIZE = 4096

TIMEOUT = 10 # in seconds

class RequestType:
    REGISTER = 0
    BRIDGE = 1

class Request():
    def __init__(self, RequestType, id, args):
        self.type = RequestType
        self.id = id
        self.args = args

reg_req_regex = r"^REGISTER\r\nclientID: (?P<id>\S+)\r\nIP: (?P<host_ip>[\d\.]+)\r\nPort: (?P<port>\d+)\r\n\r\n$"
brg_req_regex = r"^BRIDGE\r\nclientID: (?P<id>\S+)\r\n\r\n$"

def validate_port(port):
    return 1 <= port <= 65535

def parse_args():
    parser = argparse.ArgumentParser(description="server for final project")
    
    parser.add_argument("--port", type=int, required=True, help="client port")
    args = parser.parse_args()

    return args

def send(host, port, contents):
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.settimeout(TIMEOUT)

    try:
        sc.connect((host, int(port)))
        sc.send(contents.encode())
        sc.close()
        
    except socket.gaierror:
        print(f"address-related error connecting to {host} on port {port}")
        sc.close()
        return 1 #replace with exit(1)
    
    except socket.timeout:
        print(f"connection timed out when trying to connect to {host} on port {port}")
        sc.close()
        return 1
    
    except socket.error as err:
        print(f"socket error occurred: {err}")
        sc.close()
        return 1

def parse_message(data):
    try:
        msg = data.decode('utf-8')
    except Exception as e:
        print(f"error decoding: {e}")
        return None

    register_match = re.search(reg_req_regex, msg)
    if register_match:
        id = register_match.group(1) #probably should restrict valid ids, don't want someone naming themselves ""
        ip = register_match.group(2)
        port = register_match.group(3)

        return Request(RequestType.REGISTER, id, {"ip":ip, "port":port})

    bridge_match = re.search(brg_req_regex, msg)
    if bridge_match:
        id = bridge_match.group(1)

        return Request(RequestType.BRIDGE, id, None)

    print("Malformed incoming message", file=sys.stderr)
    return None

# TODO restructure code so that we operate based around Client objects instead of requests

def handle_request(request:Request, reg_info, bridge_id):
    if request.type == RequestType.REGISTER:
        print(f"REGISTER: {request.id} from {request.args['ip']}:{request.args['port']} recieved")
        return f"REGACK\r\nclientID: {request.id}\r\nIP: {request.args['ip']}\r\nPort: {request.args['port']}\r\nStatus: registered\r\n\r\n"

    elif request.type == RequestType.BRIDGE:
        client_info = reg_info.get(request.id)
        bridge_info = reg_info.get(bridge_id)
        if bridge_info is None:
            id = ""
            ip = ""
            port = ""
            ip_port = ""
        else:
            id = bridge_info.id
            ip = bridge_info.args['ip']
            port = bridge_info.args['port']
            ip_port = f"{ip}:{port}"

        print(f"BRIDGE: {client_info.id} {client_info.args['ip']}:{client_info.args['port']} {id} {ip_port}")

        return f"BRIDGEACK\r\nclientID: {id}\r\nIP: {ip}\r\nPort: {port}\r\n\r\n"

    return None

def poll(args):
    # TODO use select here to iterate over all ports we're connected on 
    port = args.port
    server_ip = socket.gethostbyname(socket.gethostname())

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, port))
    server_socket.listen(5) # arg here is size of backlog
    server_socket.setblocking(False)

    sockets = [server_socket, sys.stdin]

    reg_info = {} # eventually load
    bridge_id = None # eventually load

    print(f"server running on {server_ip}:{port}")


    while True:
        # any valid readable socket should also be writable
        readable, _, exceptional = select.select(sockets, [], sockets)
        
        for s in readable:
            if s is server_socket:
                # handle new connection
                client_socket, _ = s.accept() # client_addr not needed, we use what's advertised in reg info
                client_socket.setblocking(False)
                sockets.append(client_socket)
            elif s is sys.stdin:
                cmd = sys.stdin.readline().strip()
                if cmd == "/info":
                    for client_id, info in reg_info.items():
                        print(f"{client_id} {info.args['ip']}:{info.args['port']}")
                else:
                    print(f"Unknown command: {cmd}")
            else:
                try:
                    data = s.recv(BUFSIZE)
                    if not data:
                        sockets.remove(s)
                        s.close()
                        continue

                    request = parse_message(data)
                    if request is None:
                        s.close()
                        exit(0)

                    # register user info
                    if request.type == RequestType.REGISTER:
                        reg_info[request.id] = request

                    output = handle_request(request, reg_info, bridge_id)
                    if output is None:
                        raise Exception("failed to generate request response")

                    # if we bridged and another user hasn't already, save our registration info for the next user
                    if request.type == RequestType.BRIDGE and bridge_id == None:
                        bridge_id = request.id

                    s.send(output.encode())

                except Exception as e:
                    print(s)
                    print(f"Error: {e}")
                    sockets.remove(s)
                    s.close()


        for s in exceptional:
            sockets.remove(s)
            s.close()

def main():
    args = parse_args()

    if not validate_port(args.port):
        return 1

    try:
        poll(args)
    except KeyboardInterrupt:
        print("Terminating the chat server.\nExiting program")
        sys.exit(0)


if __name__ == "__main__":
    main()
