# WoW addon updater

For macOS, linux and linux-on-windows (not tested on macOS).

## Use

Select your addons by taking the name in Curse's URLs.

Ex: From `https://mods.curse.com/addons/wow/advancedinterfaceoptions`

Take `advancedinterfaceoptions`

Write your `conf.json` file:
```json
{
	"addons_path": "/Applications/World of Warcraft/Interface/AddOns",
	"addons": [
		"dejacharacterstats",
		"details",
		"dynamiccam"
	]
}
```

`addons_path` is your WoW addons folder path.

`addons` is your list of addons.

```bash
pip3 install -r requirements.txt
python3 addons.py -c conf.json --noop
python3 addons.py -c conf.json
```
