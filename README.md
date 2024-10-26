# BXTools
Blender plugin/addon for Modding SSX Games.<br>
Currently focusing on SSX Tricky level editing tools for [Multitool](https://github.com/GlitcherOG/SSX-Collection-Multitool)'s JSON project format.<br>
For further game specific level editing (Instances, Triggers, Effects, etc) use [IceSaw](https://github.com/GlitcherOG/Icesaw-SSX-Level-Editor-Plugin) Unity Plugin.

**Blender version 3.6 LTS or above is required for this plugin.**

This is in early development meaning crashes may occur. Make sure to save often.<br>
Bug reports and contributions are appreciated.

## Installation
- [Download this repository as a zip file](https://github.com/Linkz64/bxtools/archive/refs/heads/main.zip).
- In Blender go to `Edit > Preferences > Add-Ons` then click Install. (In 4.2 it's hidden in the top right arrow)
- Select the zip file
- Search for BXTools and enable it

## Updating
To update follow installation steps again or use [Git](https://git-scm.com/), [GitHub Desktop](https://desktop.github.com/) or similar<br>
with the repository in your blender addons folder.

## Info
SSX Tricky Levels:
- Patch editing (e.g Terrain)
- Spline editing (e.g Rails)
- Player/Ai paths editing

Avoid these:
- Editing Control Grid topology (Extruding, deleting, decimating, etc)
	- Only change geometry (location of vertices)
