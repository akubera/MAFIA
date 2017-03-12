#
# mafia_game/net/server.py
#
"""
Module containing network interface for mafia games
"""

import re
import sys
import asyncio
import logging
from argparse import ArgumentParser

from . import DEFAULT_PORT

log = logging.getLogger()


class Connection:
    def __init__(self, reader, writer, name):
        self.reader = reader
        self.writer = writer
        self.name = name


class MafiaServer:
    """
    Class for hosting Mafia-Games on the network
    """

    def __init__(self, host, port, **kw):
        """ Load with settings """
        self.host = host
        self.port = port
        self.config = kw
        self.connections = []

    def start_server(self, loop=None):
        if not hasattr(self, 'async_server'):
            self.loop = loop if loop is not None else asyncio.get_event_loop()
            srv_coro = asyncio.start_server(self.on_cnx, host=self.host, port=self.port, loop=self.loop)
            self.async_server = self.loop.run_until_complete(srv_coro)

    def loop_forever(self, loop=None):
        """ Run server and run forever """
        self.start_server(loop)
        self.loop.run_forever()

    async def on_cnx(self, reader, writer):
        data = await reader.readuntil(b'|')
        if not data.startswith(b"MAFIA|"):
            log.warn("Invalid response from client {}".format(writer.get_extra_info("peername")))
            return
        print("Accepted response from client {}".format(writer.get_extra_info("peername")))

        name = await self.get_client_name(reader, writer)
        
        self.connections.append(Connection(reader, writer, name))
        writer.write(b"{request-name-set}")
        await writer.drain()

        while True:
            msg = await reader.readline()
            self.broadcast(name, msg)

    async def get_client_name(self, r, w):
        name = await self.request_valid_name(r, w)
        while any((name == cnx.name for cnx in self.connections)):
            w.write(b"{request-name-failure:name already taken}")
            await w.drain()
            name = await self.request_valid_name(r, w)
        return name

    async def request_valid_name(self, r, w):
        name = await self.issue_command(r, w, 'request-name')
        name = name.strip()
        while not re.match(br"[a-zA-Z]+[a-zA-Z_\-0-9]*", name):
            w.write(b"{request-name-failure:invalid-username}")
            await w.drain()
            name = await self.issue_command(r, w, 'request-name')
            name = name.strip()
        return name

    async def issue_command(self, r, w, command):
        if isinstance(command, str):
            command = command.encode()
        w.write(b"{%s}" % command)
        await w.drain()
        response = await r.readline()
        return response

    def broadcast(self, name, message):
        for cnx in self.connections:
            if cnx.name != name:
                cnx.writer.write(b'%s:: %s' % (name, message))


def parser():
    p = ArgumentParser("mafia_game.server")
    p.add_argument("-p","--port",
                   type=int,
                   nargs='?',
                   default=DEFAULT_PORT,
                   )
    p.add_argument("--host",
                   type=str,
                   nargs='?',
                   default='127.0.0.1',
                   )
    return p


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parser().parse_args(argv)

    srv = MafiaServer(args.host, args.port)
    srv.start_server()
    try:
        srv.loop_forever()
    # cleanly exit from ctrl-c
    except KeyboardInterrupt:
        return 0
    


if __name__ == "__main__":
    sys.exit(main())