import asyncio
import json
import re
import sys
import zipfile
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

from aiohttp import ClientSession


class ParallelStreamWriter:

    """
    Write out messages for operations happening in parallel.
    Each operation has it's own line, and ANSI code characters are used
    to jump to the correct line, and write over the line.
    """

    def __init__(self, msg):
        self.stream = sys.stdout
        self.msg = msg
        self.lines = []

    def initialize(self, obj_index):
        self.lines.append(obj_index)
        self.stream.write("{} {} ... \r\n".format(self.msg, obj_index))
        self.stream.flush()

    def write(self, obj_index, status):
        position = self.lines.index(obj_index)
        diff = len(self.lines) - position
        # move up
        self.stream.write("%c[%dA" % (27, diff))
        # erase
        self.stream.write("%c[2K\r" % 27)
        self.stream.write("{} {} ... {}\r".format(self.msg, obj_index, status))
        # move back down
        self.stream.write("%c[%dB" % (27, diff))
        self.stream.flush()


class Installer:

    CURSE_URL = 'https://wow.curseforge.com'
    ALT_CURSE_URL = 'https://www.curseforge.com'
    ALT_REGEX = re.compile(r'class="download__link" href="(?P<path>.+)"')

    def __init__(self, conf='conf.json', noop=False):
        with open(conf, 'r') as f:
            config = json.loads(f.read())
        self.addons_path = Path(config['addons_path'])
        self.addons = config['addons']
        self.noop = noop
        self.session = None
        self.pwriter = ParallelStreamWriter('Installing')

    async def _alt_install_addon(self, addon):
        """
        Retry on standard Curse website.
        """
        url = f'{self.ALT_CURSE_URL}/wow/addons/{addon}/download'
        self.pwriter.write(addon, 'trying alternative site')

        async with self.session.get(url) as response:
            if response.status != 200:
                self.pwriter.write(addon, 'not found')
                return
            match = self.ALT_REGEX.search(await response.text())

        if not match:
            self.pwriter.write(addon, 'regex error (!)')
            return

        url = f"{self.ALT_CURSE_URL}{match.group('path')}"

        async with self.session.get(url) as response:
            if response.status != 200:
                self.pwriter.write(addon, 'not found')
                return
            zip_data = await response.read()

        if not self.noop:
            self.pwriter.write(addon, 'extracting')
            z = zipfile.ZipFile(BytesIO(zip_data))
            z.extractall(self.addons_path)

        self.pwriter.write(addon, 'done')

    async def _install_addon(self, addon):
        """
        Install from new Curse project website.
        """
        self.pwriter.initialize(addon)
        url = f'{self.CURSE_URL}/projects/{addon}/files/latest'
        self.pwriter.write(addon, 'downloading')

        async with self.session.get(url) as response:
            if response.status != 200:
                await self._alt_install_addon(addon)
                return
            zip_data = await response.read()

        if not self.noop:
            self.pwriter.write(addon, 'extracting')
            z = zipfile.ZipFile(BytesIO(zip_data))
            z.extractall(self.addons_path)

        self.pwriter.write(addon, 'done')

    async def install(self):
        tasks = []
        async with ClientSession() as self.session:
            await asyncio.gather(*[
                self._install_addon(addon)
                for addon in self.addons
            ])


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-n', '--noop', action='store_true', help='Do not install')
    parser.add_argument('-c', '--conf', default='conf.json', help='Configuration file')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    installer = Installer(conf=args.conf, noop=args.noop)
    loop.run_until_complete(installer.install())
    loop.close()
