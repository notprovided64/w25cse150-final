import argparse, socket, select, signal, sys, os, re

BUFSIZE = 4096
INV_IN_MSG = "invalid input provided"

TIMEOUT = 30 # in seconds

bridgeack_regex = r"^BRIDGEACK\r\nclientID: *(\S*)\r\nIP: *([\d\.]*)\r\nPort: *(\d*)\r\n\r\n$"
chat_regex = r"^CHAT\r\nclientID: *(\S*)\r\nIP: *([\d\.]*)\r\nPort: *(\d*)\r\n\r\n$"

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
        client_socket.connect((host, int(port)))
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

def wait(args):

    s = None
    try:
        serv_host = socket.gethostbyname("localhost")
        serv_port = args.port

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((serv_host, int(serv_port)))
        server_socket.settimeout(TIMEOUT * 10)
        server_socket.listen(1)
        s, s_addr = server_socket.accept()

        data = s.recv(BUFSIZE) #hopefully should be a /CHAT
        if data is None:
            raise Exception()
        msg = data.decode()
        match = re.search(chat_regex, msg)
        if not match:
            raise Exception("invalid chat message recieved")

        id = match.group(1)
        ip = match.group(2)
        port = match.group(3)

        # can delete
        client_ip, client_port = s_addr
        print(f"socket info: {client_ip=}{client_port=}")

        print(f"Incoming chat request from {id} {ip}:{port}")
        chat_loop(s, False)

    except KeyboardInterrupt:
        if s is not None:
            s.close()
        exit()
    except Exception as e:
        print(f"error occurred while waiting: {e}")
        if s is not None:
            s.close()

def chat_init(args, info):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(TIMEOUT)

    try:
        localhost = socket.gethostbyname("localhost")
        port = args.port

        print(f"shouldn't exist{info.host}")
        client_socket.connect((info.host, info.port))
        client_socket.send(f"CHAT\r\nclientID: {args.id}\r\nIP: {localhost}\r\nPort: {port}\r\n\r\n".encode())
        #parse input message on s, if it's "CHAT", then call loop
        chat_loop(client_socket, True)

    except KeyboardInterrupt:
        client_socket.close()
        exit()
    except Exception as e:
        print(f"error occurred while chatting: {e}")
        client_socket.close()


def chat_loop(s:socket.SocketType, is_writing:bool):
    try:
        while True:
            if is_writing:
                uin = input()
                if uin == "/quit":
                    raise KeyboardInterrupt # want same behavior anyways
                s.send(uin.encode())
                is_writing = False
            else:
                data = s.recv(BUFSIZE)
                if not data:
                    print("peer ended chat?")
                    raise KeyboardInterrupt

                msg = data.decode("utf-8")
                if msg == "QUIT":
                    print("peer ended chat")
                    raise KeyboardInterrupt
                print(msg)
                is_writing = True
                
    except KeyboardInterrupt:
        s.send("QUIT".encode())
        exit()        


def loop(args):
    host, port = args.server.split(':')
    client_ip = socket.gethostbyname(socket.gethostname())
    print(f"{args.id} running on {client_ip}:{port}")
    bridge_info = None

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
                print(connection_info.host, connection_info.port)

                if connection_info.is_empty():
                    wait(args)
                    continue

                bridge_info = connection_info
            elif uin == "/chat":        
                if not bridge_info:
                    print("you don't have anything saved")
                    continue

                chat_init(args, bridge_info)

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
