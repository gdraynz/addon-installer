:warning: New project here: https://github.com/gdraynz/wowui

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

### Using pip

```bash
pip3 install -r requirements.txt
python3 addons.py -h
python3 addons.py -c conf.json
```

### Using pipenv

```bash
pipenv install
pipenv shell
python addons.py -h
python addons.py -c conf.json
```
