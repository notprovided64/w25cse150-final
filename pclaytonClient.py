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

#TODO impl
def parse_bridgeack(msg):
    return None

def chat(connection_info):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)

    try:
        s.connect((connection_info.host, int(connection_info.port)))
        s.send("".encode()) # put chat request here if needed
        while True:
            uin = input()
            if uin == "/quit":
                raise KeyboardInterrupt # want same behavior anyways
            s.send(uin.encode())

            data = s.recv(BUFSIZE)
            msg = data.decode("utf-8")
            if msg == "QUIT":
                print("peer ended chat")
                raise KeyboardInterrupt
            print(msg)

        s.close()

        return msg
        
    except KeyboardInterrupt:
        s.close()
        exit()
    except Exception as e:
        print(f"error occurred while chatting: {e}")
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
            elif uin == "/register":
                send(host, port, get_reg_req(args.id, args.port))
            elif uin == "/bridge":
                msg = send(host, port, get_bridge_req(args.id))

                connection_info = parse_bridgeack(msg)
                if connection_info is not None: #if validly formatted response
                    if connection_info.id is "":#if empty bridgeack
                        wait_for_chat() #TODO impl

                    chat(connection_info)
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
