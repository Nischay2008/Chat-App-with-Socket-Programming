"""Terminal client for server.py. Run with: python client.py [host] [port]"""

import socket
import sys
import threading

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000


def receive(sock, stopped):
    buffer = ""
    try:
        while not stopped.is_set():
            data = sock.recv(1024)
            if not data:
                print("\nDisconnected from server.")
                break
            buffer += data.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                print("\r" + line)
    except OSError:
        if not stopped.is_set():
            print("\nConnection lost.")
    finally:
        stopped.set()


def main():
    stopped = threading.Event()
    try:
        sock = socket.create_connection((HOST, PORT))
    except OSError as error:
        print("Could not connect to {}:{}: {}".format(HOST, PORT, error))
        return

    print("Connected to {}:{}".format(HOST, PORT))
    threading.Thread(target=receive, args=(sock, stopped), daemon=True).start()
    try:
        nickname = input("Nickname: ").strip()
        sock.sendall(("NICK " + nickname + "\n").encode("utf-8"))
        while not stopped.is_set():
            try:
                line = input()
            except EOFError:
                line = "/quit"
            if not line:
                continue
            sock.sendall((line + "\n").encode("utf-8"))
            if line == "/quit":
                break
    except (KeyboardInterrupt, OSError):
        try:
            sock.sendall(b"/quit\n")
        except OSError:
            pass
    finally:
        stopped.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()


if __name__ == "__main__":
    main()
