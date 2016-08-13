from aiohttp import ClientSession
from argparse import ArgumentParser
import asyncio
import json
import logging
import re
from tempfile import TemporaryFile
import zipfile


log = logging.getLogger(__name__)


class Installer:

    def __init__(self, conf='conf.json', noop=False):
        with open(conf, 'r') as f:
            config = json.loads(f.read())
        self.addons_path = config['addons_path']
        self.addons = config['addons']
        self.noop = noop
        self.session = None
        if self.noop:
            log.info('NOOP mode')

    async def _install_addon(self, addon):
        url = 'https://mods.curse.com/addons/wow/{}/download'.format(addon)
        async with self.session.get(url) as response:
            m = re.search(
                r'(?P<url>http:\/\/addons\.curse\.cursecdn\.com\/files\/\d+\/\d+\/(?P<version>.+)\.zip)',
                await response.text(),
                re.IGNORECASE
            )
        if not m:
            log.error('%s: Addon not found' % addon)
            return

        download_url = m.group('url')
        download_version = m.group('version')
        log.info('%s: Downloading from %s', addon, download_url)
        if not self.noop:
            async with self.session.get(download_url) as response:
                zip_data = await response.read()
            tmp = TemporaryFile()
            tmp.write(zip_data)
            z = zipfile.ZipFile(tmp)
            z.extractall(self.addons_path)
        log.info('%s: Extracting to %s', addon, self.addons_path)
        log.info('%s: Successfully updated to version %s', addon, download_version)

    async def install(self):
        tasks = []
        with ClientSession() as self.session:
            for addon in self.addons:
                tasks.append(asyncio.ensure_future(
                    self._install_addon(addon)
                ))
            await asyncio.wait(tasks)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s %(levelname)-8s %(message)s'
    )
    parser = ArgumentParser()
    parser.add_argument('-n', '--noop', action='store_true', help='Do not install')
    parser.add_argument('-c', '--conf', default='conf.json', help='Configuration file')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    installer = Installer(conf=args.conf, noop=args.noop)

    loop.run_until_complete(installer.install())

    loop.close()
