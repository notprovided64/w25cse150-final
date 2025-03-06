import argparse, socket, select, signal, sys, os, re

BUFSIZE = 4096
INV_IN_MSG = "invalid input provided"

TIMEOUT = 10 # in seconds

bridgeack_regex = r"^BRIDGEACK\r\nclientID: *(\S*)\r\nIP: *([\d\.]*)\r\nPort: *(\d*)\r\n\r\n$"

class ConnectionInfo:
    def __init__(self, id:str, host:str, port:int):
        self.id = id
        self.host = host
        self.port = port

    def is_empty(self):
        return self.id == "" and self.host == "" and self.port == -1

# expects int or str
def is_valid_port(port):
    if not isinstance(port, int):
        if not port.isdigit():
            return False
        
        port = int(port)

    if not (0 < port <= 65535):
        return False

    return True

def is_valid_hostname(hostname):
    if len(hostname) > 253:
        return False

    if hostname.endswith('.'):
        hostname = hostname[:-1]

    label_regex = re.compile(r'^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$')
    labels = hostname.split('.')
    return all(label_regex.match(label) for label in labels)

def is_valid_server(server):
    if ':' not in server:
        return False
    
    host, port = server.rsplit(':', 1)
    return all((is_valid_hostname(host), is_valid_port(port)))

def validate_args(args):
    if not is_valid_port(args.port):
        print("invalid port num")
        return False
    if not is_valid_server(args.server):
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
        client_socket.connect((host, port))
        client_socket.send(contents.encode())

        data = client_socket.recv(BUFSIZE)
        msg = data.decode("utf-8")
        if msg == "":
            raise Exception("empty response recieved")
        client_socket.close()

        return msg
        
    except Exception as e:
        print(f"error occurred on {host}:{port} : {e}")
        client_socket.close()
        return None

def get_reg_req(id, port):
    host_ip = socket.gethostbyname("localhost")
    return f"REGISTER\r\nclientID: {id}\r\nIP: {host_ip}\r\nPort: {port}\r\n\r\n"

def get_bridge_req(id):
    return f"BRIDGE\r\nclientID: {id}\r\n\r\n"

def parse_bridgeack(msg):
    match = re.search(bridgeack_regex, msg)
    if match:
        id = match.group(1)
        ip = match.group(2)
        port = match.group(3)
        if not port.isdigit(): # awkward way to handle errors
            port = -1
        else:
            port = int(port)
        
        return ConnectionInfo(id, ip, port)

    return None

def chat(args, connection_info, wait):
    serv_host, serv_port = args.server.split(':')

    s = None
    try:
        if wait == True: # setup server socket to handle incoming connection
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((serv_host, serv_port))
            server_socket.settimeout(TIMEOUT)
            server_socket.listen(1)
            s, _ = server_socket.accept()
        else:            # otherwise we try to connect to connection_info 
            id, host, port = connection_info
            port = int(port)
            # separate connection_info class would be best here, validation should be integrated into the data type

            print(f"now chatting with {id}")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(port)))

            s.send("".encode()) # put chat request here if needed

        while True:
            uin = input()
            if uin == "/quit":
                s.send("QUIT".encode())
                raise KeyboardInterrupt # want same behavior anyways
            s.send(uin.encode())

            data = s.recv(BUFSIZE)
            if not data:
                print("peer ended chat?")
                raise KeyboardInterrupt

            msg = data.decode("utf-8")
            if msg == "QUIT":
                print("peer ended chat")
                raise KeyboardInterrupt
            print(msg)

        s.close()

        return msg
        
    except KeyboardInterrupt:
        if s is not None:
            s.close()
        exit()
    except Exception as e:
        print(f"error occurred while chatting: {e}")
        if s is not None:
            s.close()

def loop(args):
    host, port = args.server.split(':')
    client_ip = socket.gethostbyname(socket.gethostname())
    print(f"{args.id} running on {client_ip}:{port}")

    try:
        while(True):
            uin = input()

            if uin == "/id":
                print(args.id)
            elif uin == "/quit":
                exit()
            elif uin == "/register":
                send(host, port, get_reg_req(args.id, args.port))
            elif uin == "/bridge":
                msg = send(host, port, get_bridge_req(args.id))

                connection_info = parse_bridgeack(msg)
                if connection_info is not None:
                    print(connection_info)
                    chat(args, connection_info, connection_info.is_empty())
                    exit()

            else:
                print(INV_IN_MSG)

    except KeyboardInterrupt:
        exit()

def exit():
    print("Terminating the chat client.\nExiting program")
    sys.exit(0)

def main():
    args = parse_args()

    if not validate_args(args):
        return 1

    loop(args)

if __name__ == "__main__":
    main()
