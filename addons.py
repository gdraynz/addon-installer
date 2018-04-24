import asyncio
import json
import re
import sys
import zipfile
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

from aiohttp import ClientSession
from halo import Halo


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

        # Runtime
        self.loader = Halo(f'Installing addons... (0/{len(self.addons)})')
        self._done = []
        self._failed = []

    def done(self, addon, error=None):
        if error is not None:
            self._failed.append((addon, error))
        else:
            self._done.append(addon)
        errors = f', {len(self._failed)} errors' if self._failed else ''
        self.loader.text = f'Installing addons... ({len(self._done) + len(self._failed)}/{len(self.addons)}{errors})'

    async def _alt_install_addon(self, addon):
        """
        Retry on standard Curse website.
        """
        url = f'{self.ALT_CURSE_URL}/wow/addons/{addon}/download'
        async with self.session.get(url) as response:
            if response.status != 200:
                self.done(addon, 'not found')
                return
            match = self.ALT_REGEX.search(await response.text())

        if not match:
            self.done(addon, 'regex error /!\\')
            return

        url = f"{self.ALT_CURSE_URL}{match.group('path')}"
        async with self.session.get(url) as response:
            if response.status != 200:
                self.done(addon, 'not found')
                return
            zip_data = await response.read()

        if not self.noop:
            z = zipfile.ZipFile(BytesIO(zip_data))
            z.extractall(self.addons_path)

        self.done(addon)

    async def _install_addon(self, addon):
        """
        Install from new Curse project website.
        """
        url = f'{self.CURSE_URL}/projects/{addon}/files/latest'
        async with self.session.get(url) as response:
            if response.status != 200:
                await self._alt_install_addon(addon)
                return
            zip_data = await response.read()

        if not self.noop:
            z = zipfile.ZipFile(BytesIO(zip_data))
            z.extractall(self.addons_path)

        self.done(addon)

    async def install(self):
        self.loader.start()
        async with ClientSession() as self.session:
            await asyncio.gather(*[
                self._install_addon(addon) for addon in self.addons
            ])
        self.loader.stop()

        for addon, error in self._failed:
            print(f"Failed to install: '{addon}' ({error})")
        for addon in self._done:
            print(f"Successfully installed: '{addon}'")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-n', '--noop', action='store_true', help='Do not install')
    parser.add_argument('-c', '--conf', default='conf.json', help='Configuration file')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    installer = Installer(conf=args.conf, noop=args.noop)
    loop.run_until_complete(installer.install())
    loop.close()
