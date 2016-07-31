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
	]
}
```

`addons_path` is your WoW addons folder path.

`addons` is your list of addons.

```bash
pip3 install aiohttp
python3 update.py --noop
python3 update.py
```
