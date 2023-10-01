# BXTools
Blender plugin for importing and exporting SSX Assets.<br>
Currently focusing on SSX Tricky level editing tools for [Icesaw](https://github.com/GlitcherOG/Icesaw-SSX-Level-Editor-Plugin) project format.

**Blender version 3.6 LTS is recommended for this plugin.**
Versions from 3.0 and newer should also work.

This is in early development. Crashes may occur so make sure to save often.

## Installation
- Download this repository as a [zip file](https://github.com/Linkz64/bxtools/archive/refs/heads/main.zip).
- In Blender go to `Edit > Preferences > Add-Ons` then click Install.
- Select the zip file
- Search for BXTools and enable it

## Info
What you can do:

- Tricky IceSaw
	- Patch import and export
	- Patch creation and editing
	- Spline import and export
	- Spline creation and editing
	- Limited Tricky model editing for Xbox format

Avoid these:
- Patch UV editing
	- Toggling between patch and control grid breaks UV data
- Editing Control Grid topology (Extruding, deleting, decimating, etc)
	- Only change geometry (location of vertices) if you intend to convert to patch