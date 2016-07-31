# WoW addon updater
(for you mac users out there)

## Use

Write your `conf.json` file:
```json
{
	"addons_path": "/Applications/World of Warcraft/Interface/AddOns",
	"addons": [
		"advancedinterfaceoptions",
		"dejacharacterstats",
		"details",
		"dynamiccam"
	],
	"noop": true
}
```

`addons_path` is your WoW addons folder path.

`addons` is your list of addons.

`noop` will disable any addon download.

```bash
pip3 install aiohttp
python3 update.py
```
