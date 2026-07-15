# Python Socket Chat App

A simple multi-client terminal chat application built with Python sockets and threads. It uses no external libraries.

## Requirements

- Python 3
- Two or more terminals for testing multiple clients

## Run the server

From this folder, start the server:

```bash
python server.py
```

The server listens on port `5000` and accepts connections from multiple clients.

## Run a client

Open another terminal and run:

```bash
python client.py
```

Enter a nickname when prompted. To connect to another machine, provide its IP address and (optionally) port:

```bash
python client.py 192.168.1.10 5000
```

## Chat protocol

Each client must identify itself before chatting:

```text
NICK yourname
```

The included client sends this automatically after it asks for your nickname. Nicknames can contain letters, numbers, `_`, and `-`, with a maximum length of 24 characters.

## Messages and commands

| Input | Description |
| --- | --- |
| `Hello everyone` | Sends a public message to every connected user. |
| `@username Hello` | Sends a private message to `username`. |
| `/list` | Shows connected users. |
| `/nick NEWNAME` | Changes your nickname. |
| `/help` | Shows available commands. |
| `/quit` | Disconnects from the server. |

Public messages, joins, leaves, nickname changes, and private messages include a server timestamp.

## Files

- `server.py` — manages client connections, nickname registration, broadcasts, private messages, and cleanup.
- `client.py` — terminal client for connecting and chatting.

## Notes

- Start the server before connecting clients.
- If clients connect from another device, allow port `5000` through the server computer's firewall.
- Press `Ctrl+C` in the server terminal to stop the server.
