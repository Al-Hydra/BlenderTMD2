# BlenderTMD2

A Blender addon for importing models, animations, and textures from Tamsoft Games running on TamEngine

## Supported File Formats

- **`.tmd2`** - The new tmd format v2.0.3+ most supported format by this addon.
- **`.tmd`**  - Older tmd format v2.0.0 - v2.0.3 mostly used in the Senran Kagura games and usually only found in .cat files.
- **`.tmd/.tmd0`** - These are only found in .cat files pre-v2.0.0 format. Seen mostly in Neptunia games and older Tamsoft games.
- **`.tmdv`** - PSVita variant of tmd v1.0.0
- **`.tmo`**  - Animation format, partially supported and not fully implemented
- **`.tmo1`** - A newer version of the animation format. Supported for skeletal animations.
- **`.tactpkg`** - Container file that stores multiple animations and blend data. Only the animation will be imported from it.
- **`.cat`** - this format is different for each game support for it is not guaranteed. 
- **`.lds`** - Texture container for the PC games.
- **`.gxt`** - Texture container for PS Vita games. Supported but can't be imported unless it's inside a .cat file
- **`.gnf`** - Texture container for PS4/PS5 games. Supported but can't be imported unless it's inside a .cat file

## Installation

### Method 1
1. Download the latest release or clone this repository
2. Drag and drop the zip file into blender's viewport and Install the addon

### Method 2
1. Download the latest release or clone this repository
2. In Blender, go to `Edit > Preferences > Add-ons`
3. Click on the little arrow then select `Install from Disk`
4. Enable the addon by checking the checkbox next to "BlenderTMD2"

## Usage

### Import via Menu
1. Go to `File > Import > Tamsoft TMD Importer`
2. Navigate to your file and select it
3. Click `Import`

### Import via Drag & Drop
Simply drag and drop a `.tmd2`, `.tmd`, or `.lds` file directly into the 3D viewport.
Other formats might be support but they're only there for debugging

### Texture Loading
When importing `.tmd2` files, the addon automatically scans the same directory for `.lds` files and import them for you.

## Tested Games
- Bleach Rebirth of Souls (Import/Export).
- Captain Tsubasa: Rise of New Champions (Import/Export not tested).
- Neptunia x Senran Kagura: Ninja Wars (Import/ Export not tested).
- Hyperdimension Neptunia U: Action Unleashed (Import Only)
- Hyperdimension Neptunia: Producing Perfection (Import Only)
- MegaTagmension Blanc + Neptune VS Zombies (Import Only)
- To LOVE-Ru Darkness: Battle Ecstasy (Import Only)
- Natsuiro High School: Seishun Hakusho (Import Only)
- Senran Kagura: Shinovi Versus (.cat partial import support)
- Senran Kagura: Estival Versus (.tmd import/export. No .cat support)
- Senran Kagura: Burst Re:Newal (.tmd import/export. No .cat support)
- Senran Kagura: Reflexions (.tmd import/export. No .cat support)
- Senran Kagura: Peach Ball (.tmd import/export. No .cat support)
- Senran Kagura: Peach Beach Splash (.tmd import/export. No .cat support)



## Requirements
- Blender 4.5.0 (Older or newer version might be supported)