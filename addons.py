import asyncio
import json
import os
import re
import shutil
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

    def __init__(self, conf='conf.json', peggle=False):
        with open(conf, 'r') as f:
            config = json.loads(f.read())
        self.addons_path = Path(config['addons_path'])
        self.addons = config['addons']
        self.peggle = peggle
        self.session = None

        # Runtime
        self.loader = None
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

        z = zipfile.ZipFile(BytesIO(zip_data))
        z.extractall(self.addons_path)
        self.done(addon)

    async def _install_peggle(self):
        """
        Custom installation of the addon 'Peggle'.
        See https://github.com/adamz01h/wow_peggle
        """
        url = 'https://github.com/adamz01h/wow_peggle/archive/master.zip'
        async with self.session.get(url) as response:
            if response.status != 200:
                self.done('Peggle', 'could not retrieve archive from github')
                return
            zip_data = await response.read()

        tmp_path = Path('/tmp/peggle')
        z = zipfile.ZipFile(BytesIO(zip_data))
        z.extractall(tmp_path)
        shutil.move(
            tmp_path / 'wow_peggle-master/Peggle',
            self.addons_path / 'Peggle',
        )
        self.done('Peggle')

    async def install(self):
        tasks = [self._install_addon(addon) for addon in self.addons]
        if self.peggle is True:
            tasks.append(self._install_peggle())
            self.addons.append('Peggle')

        self.loader = Halo(f'Installing addons... (0/{len(tasks)})')
        self.loader.start()

        async with ClientSession() as self.session:
            await asyncio.gather(*tasks)

        self.loader.stop()

        for addon, error in self._failed:
            print(f"Failed to install: '{addon}' ({error})")
        for addon in self._done:
            print(f"Successfully installed: '{addon}'")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-c', '--conf', default='conf.json', help='Configuration file')
    parser.add_argument('--peggle', action='store_true', help='Install Peggle (from https://github.com/adamz01h/wow_peggle)')
    args = parser.parse_args()

    installer = Installer(conf=args.conf, peggle=args.peggle)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(installer.install())
    loop.close ()
