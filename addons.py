import re
import sys
import json
import asyncio
import logging
import zipfile
from aiohttp import ClientSession
from argparse import ArgumentParser
from tempfile import TemporaryFile


log = logging.getLogger(__name__)


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

    def __init__(self, conf='conf.json', noop=False):
        with open(conf, 'r') as f:
            config = json.loads(f.read())
        self.addons_path = config['addons_path']
        self.addons = config['addons']
        self.noop = noop
        self.session = None
        self.pwriter = ParallelStreamWriter('Installing')
        # Avoid overloading curse from requests
        self.semaphore = asyncio.Semaphore(5)
        if self.noop:
            log.debug('NOOP mode')

    async def _install_addon(self, addon):
        self.pwriter.initialize(addon)
        url = 'https://mods.curse.com/addons/wow/{}/download'.format(addon)
        async with self.semaphore:
            async with self.session.get(url) as response:
                m = re.search(
                    r'(?P<url>https:\/\/addons\.curse\.cursecdn\.com\/files\/\d+\/\d+\/(?P<version>.+)\.zip)',
                    await response.text(),
                    re.IGNORECASE
                )

        if not m:
            log.debug('%s: Addon not found' % addon)
            self.pwriter.write(addon, 'not found')
            return

        download_url = m.group('url')
        download_version = m.group('version')
        log.debug('%s: Downloading from %s', addon, download_url)
        self.pwriter.write(addon, 'downloading')

        if not self.noop:
            async with self.semaphore:
                async with self.session.get(download_url) as response:
                    zip_data = await response.read()

            log.debug('%s: Extracting to %s', addon, self.addons_path)
            self.pwriter.write(addon, 'extracting')

            tmp = TemporaryFile()
            tmp.write(zip_data)
            z = zipfile.ZipFile(tmp)
            z.extractall(self.addons_path)

        log.debug('%s: Successfully updated to version %s', addon, download_version)
        self.pwriter.write(addon, 'done')

    async def install(self):
        tasks = []
        with ClientSession() as self.session:
            for addon in self.addons:
                tasks.append(asyncio.ensure_future(
                    self._install_addon(addon)
                ))
            await asyncio.wait(tasks)


if __name__ == '__main__':
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)-15s %(levelname)-8s %(message)s'
    # )
    parser = ArgumentParser()
    parser.add_argument('-n', '--noop', action='store_true', help='Do not install')
    parser.add_argument('-c', '--conf', default='conf.json', help='Configuration file')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    installer = Installer(conf=args.conf, noop=args.noop)
    loop.run_until_complete(installer.install())
    loop.close()
