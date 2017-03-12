#
# mafia_game/net/client.py
#
"""
Module containing network interface for mafia games
"""

import sys
import asyncio
from argparse import ArgumentParser

from . import DEFAULT_PORT



class MafiaClient:
    """
    Class for connecting to a MafiaServer
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def run(self, loop=None):
        loop = loop if loop is not None else asyncio.get_event_loop()
        cnx_coro = asyncio.open_connection(self.host, self.port, loop=loop)
        print("Establishing connection to {}:{}".format(self.host, self.port))
        self.reader, self.writer = loop.run_until_complete(cnx_coro)
        print("  => Success")

        loop.run_until_complete(self.setup_connection())
        loop.create_task(self.handle_requests())

        self.cmd_matrix = {
            b'{request-name}': self.request_name,
        }

        loop.run_forever()

    async def setup_connection(self):
        self.writer.write(b"MAFIA|")
        await self.writer.drain()

    async def handle_requests(self):
        while True:
            cmd = await self.reader.read(1024)
            if cmd in self.cmd_matrix:
                await self.cmd_matrix[cmd]()
            else:
                print(cmd)

    async def request_name(self):
        name = input("Please input username:")
        self.writer.write(name.encode())
        await self.writer.drain()
        response = await self.reader.read(1024)
        if response == b'{request-name-set}':
            return
        elif response.startswith(b'{request-name-failure'):
            print('err', response[22:-1])
            return await self.request_name() 


def parser():
    p = ArgumentParser("mafia_game.client")
    p.add_argument("-p", "--port",
                   type=int,
                   nargs='?',
                   default=DEFAULT_PORT,
                   help="Network port of the remote server"
                   )
    p.add_argument("host",
                   help="Hostname of the server",
                   )
    return p


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parser().parse_args(argv)


    client = MafiaClient(args.host, args.port)
    client.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())