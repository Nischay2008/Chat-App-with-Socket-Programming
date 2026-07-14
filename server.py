"""Threaded TCP chat server.  Run with: python server.py"""

import queue
import socket
import threading
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000
MAX_LINE = 4096


class Client:
    def __init__(self, sock, address):
        self.sock = sock
        self.address = address
        self.nickname = None
        self.outbox = queue.Queue()
        self.closed = threading.Event()


class ChatServer:
    def __init__(self):
        self.clients = {}  # nickname (case-insensitive) -> Client
        self.lock = threading.RLock()
        self.running = threading.Event()
        self.running.set()

    @staticmethod
    def stamp(message):
        return "[{}] {}\n".format(datetime.now().strftime("%H:%M:%S"), message)

    @staticmethod
    def valid_nickname(name):
        return bool(name) and len(name) <= 24 and all(c.isalnum() or c in "_-" for c in name)

    def send(self, client, message):
        if not client.closed.is_set():
            client.outbox.put(message)

    def broadcast(self, message, exclude=None):
        line = self.stamp(message)
        with self.lock:
            recipients = list(self.clients.values())
        for client in recipients:
            if client is not exclude:
                self.send(client, line)
        print(line, end="")

    def remove_client(self, client, announce=True):
        """Remove a client exactly once and close its connection."""
        if client.closed.is_set():
            return
        client.closed.set()
        nickname = client.nickname
        removed = False
        with self.lock:
            if nickname and self.clients.get(nickname.lower()) is client:
                del self.clients[nickname.lower()]
                removed = True
        try:
            client.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            client.sock.close()
        except OSError:
            pass
        if announce and removed:
            self.broadcast("* {} left the chat".format(nickname))

    def set_nickname(self, client, name, initial=False):
        if not self.valid_nickname(name):
            self.send(client, "ERROR nickname must be 1-24 letters, digits, _ or -\n")
            return False
        key = name.lower()
        with self.lock:
            existing = self.clients.get(key)
            if existing is not None and existing is not client:
                self.send(client, "ERROR nickname is already in use\n")
                return False
            old_name = client.nickname
            if old_name:
                self.clients.pop(old_name.lower(), None)
            self.clients[key] = client
            client.nickname = name
        if initial:
            self.send(client, "OK welcome, {}. Type /help for help.\n".format(name))
            self.broadcast("* {} joined the chat".format(name), exclude=client)
        else:
            self.send(client, "OK nickname changed to {}\n".format(name))
            self.broadcast("* {} is now known as {}".format(old_name, name))
        return True

    def writer(self, client):
        try:
            while not client.closed.is_set():
                try:
                    message = client.outbox.get(timeout=0.5)
                except queue.Empty:
                    continue
                client.sock.sendall(message.encode("utf-8", errors="replace"))
        except OSError:
            pass
        finally:
            self.remove_client(client)

    def handle_line(self, client, line):
        if client.nickname is None:
            command, _, name = line.partition(" ")
            if command.upper() != "NICK" or not self.set_nickname(client, name.strip(), initial=True):
                if command.upper() != "NICK":
                    self.send(client, "ERROR first command must be: NICK yourname\n")
            return

        if line == "/list":
            with self.lock:
                names = sorted(c.nickname for c in self.clients.values())
            self.send(client, "USERS {}\n".format(", ".join(names)))
        elif line.startswith("/nick "):
            self.set_nickname(client, line[6:].strip())
        elif line == "/quit":
            self.send(client, "BYE\n")
            self.remove_client(client)
        elif line == "/help":
            self.send(client, "Commands: /list, /nick NEWNAME, /quit, /help\n"
                              "Private message: @username message\n")
        elif line.startswith("/"):
            self.send(client, "ERROR unknown command; use /help\n")
        elif line.startswith("@"):
            target_name, separator, text = line[1:].partition(" ")
            with self.lock:
                target = self.clients.get(target_name.lower())
            if not separator or not text.strip():
                self.send(client, "ERROR private message format: @username message\n")
            elif target is None:
                self.send(client, "ERROR user '{}' is not online\n".format(target_name))
            else:
                self.send(target, self.stamp("[private] {}: {}".format(client.nickname, text)))
                if target is not client:
                    self.send(client, self.stamp("[private to {}] {}".format(target.nickname, text)))
        elif line:
            self.broadcast("{}: {}".format(client.nickname, line))

    def reader(self, client):
        buffer = ""
        try:
            while not client.closed.is_set():
                data = client.sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                # A peer that never sends a newline must not grow memory forever.
                if "\n" not in buffer and len(buffer) > MAX_LINE:
                    self.send(client, "ERROR line is too long\n")
                    buffer = ""
                    continue
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if len(line) > MAX_LINE:
                        self.send(client, "ERROR line is too long\n")
                    else:
                        self.handle_line(client, line)
        except OSError:
            pass
        finally:
            self.remove_client(client)

    def accept_client(self, sock, address):
        client = Client(sock, address)
        print("Connection from {}:{}".format(*address))
        self.send(client, "Welcome. Identify yourself with: NICK yourname\n")
        threading.Thread(target=self.writer, args=(client,), daemon=True).start()
        threading.Thread(target=self.reader, args=(client,), daemon=True).start()

    def serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((HOST, PORT))
            listener.listen()
            listener.settimeout(1.0)
            print("Chat server listening on {}:{}".format(HOST, PORT))
            try:
                while self.running.is_set():
                    try:
                        sock, address = listener.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    self.accept_client(sock, address)
            except KeyboardInterrupt:
                print("\nStopping server...")
            finally:
                self.running.clear()
                with self.lock:
                    clients = list(self.clients.values())
                for client in clients:
                    self.remove_client(client, announce=False)


if __name__ == "__main__":
    ChatServer().serve()
