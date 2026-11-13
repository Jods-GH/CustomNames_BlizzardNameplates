[![Discord][SVG-Discord]][Discord]
[![PayPal][SVG-PayPal]][PayPal]
[![Release][SVG-Release]][Release]
[![CustomNames][SVG-CustomNames]][CustomNames]  
# CustomNames_BlizzardNameplates
Shows [CustomNames](https://www.curseforge.com/wow/addons/libcustomnames) aliases on Blizzard's default nameplates.

[//]: # (Links)

[Discord]: https://discord.com/invite/v3gYmYamGJ (Join the Discord)
[PayPal]: https://ko-fi.com/jodsderechte (Donate via PayPal)
[Release]: https://github.com/Jods-GH/CustomNames_BlizzardNameplates/releases/latest (Latest release)
[CustomNames]: https://github.com/Jods-GH/CustomNames

[//]: # (Images)
[SVG-Discord]: https://img.shields.io/badge/Discord-7289da?logo=discord&logoColor=fff&style=flat-square
[SVG-PayPal]: https://custom-icon-badges.demolab.com/badge/-Support-lightgrey?style=flat-square&logo=kofi&color=222222
[SVG-CustomNames]: https://badgen.net/github/release/Jods-GH/CustomNames?style=flat-square
[SVG-Release]: https://badgen.net/github/release/Jods-GH/CustomNames_BlizzardNameplates?style=flat-square

## Usage

Install CustomNames and this addon, then reload the UI. Configure aliases in
CustomNames; this plugin has no separate settings or saved variables. It supports
player aliases (including cross-realm and inherited BattleTag aliases) and NPC/pet
aliases stored by CustomNames. Additions, edits, and removals refresh active plates.

Only Blizzard nameplate labels are changed. Player, target, focus, party, and raid
unit frames are excluded. Font, color, positioning, and visibility remain controlled
by Blizzard. This plugin does not enable hidden nameplates or replace third-party
nameplate renderers such as Plater or ElvUI.

## Compatibility

Targets all client families listed in the TOC and supported by CustomNames:
Retail, Forever, Mists, Wrath, Burning Crusade, and Classic Era (including Hardcore
and seasonal modes using that client). The TOC versions match the supplied
CustomNames dependency; the existing interface updater tracks these flavors.

The implementation uses the shared `C_NamePlate` and `CompactUnitFrame_UpdateName`
interfaces, detects late-loaded UI functions, and works without Retail's secret-value
APIs on Classic. It verifies frame ownership on every update, so recycled or detached
frames do not retain plugin state. Blizzard redraws native names before aliases are
applied, including when an alias is removed.

Secret names and forbidden nameplates retain Blizzard's display. Client restrictions
can therefore prevent aliases in some content, including restricted friendly plates.
No attempt is made to bypass these restrictions. If a required nameplate API is
absent, the plugin leaves the UI unchanged.

Automated compatibility checks use mocked Lua 5.1 APIs; they are not a claim that
every client has been tested in-game. Combat/taint safety and actual frame behavior
still require the per-client validation below.

## Validation

Run:

```sh
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
```

Checks cover alias replacement/restoration, NPC aliases, library delegation,
late UI loading, pooled frame reuse, hook idempotence, restricted values, ordinary
unit-frame exclusion, visibility, and TOC file paths.

Before releasing each supported client, test with only CustomNames and this plugin:

- Load and reload with friendly/enemy player, NPC, and pet nameplates enabled.
- Add, edit, and remove player, cross-realm, pet, and NPC aliases.
- Move out of range and back; switch targets and rapidly recycle nameplates.
- Enter vehicles, summon pets, and switch nameplate styles and visibility settings.
- Check world, dungeon, raid, arena, and battleground plates where available.
- Enter and leave combat; check for Lua errors, blocked actions, and stale labels.
- Confirm targeting, class colors, long/UTF-8 names, and hidden names still work.
- Confirm ordinary unit frames and settings previews are unchanged.

Reference implementations: [nameplate driver](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_NamePlates/Blizzard_NamePlates.lua),
[shared name updater](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_UnitFrame/Shared/CompactUnitFrame.lua),
and [Classic Era shared frames](https://github.com/Gethe/wow-ui-source/blob/classic_era/Interface/AddOns/Blizzard_UnitFrame/Shared/CompactUnitFrame.lua).
