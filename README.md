Blender to Metro (.model) Exporter
A simple Blender 3.0+ addon for exporting 3D objects to the 4A Engine .model format (Metro Exodus).

Features:
- Automatically applies modifiers and transforms upon export.
- Calculates Vertex AO (Ambient Occlusion) directly during export.
- LOD Support: Export objects to specific Level of Detail slots (e.g., LOD 0).
- Physics & Collision Generation (.nxcform33x).

Requirements:
- Blender 3.0.0 or newer.

Installation:
1. Download the latest release zip file from the Releases page.
2. Open Blender.
3. Go to Edit > Preferences > Add-ons.
4. Click Install... at the top right.
5. Select the downloaded .zip file and click Install Add-on.
6. Find "Import-Export: Metro Model Exporter" in the list and enable it.

How to Use:
1. Prepare your model in the viewport. If you need a custom collision mesh, create a separate object and add the _col suffix to its name (e.g., my_svetofor_collision)
2. Go to File > Export > Metro Exodus Model (.model).
3. In the export panel on the right, configure your settings: Engine version, LOD level, enable/disable vertex AO, some modifiers and collision. 
4. Choose your destination folder and click Export.

Credits:
- AI Assistance: AI was utilized during development to analyze and reverse-engineer the binary .model file format structures.
- APAmk2: blender-uEngine by APAmk2 was used as a reference to understand the structure and reading process of the .model format.

License:
Copyright (c) 2026 VesTank

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to use and modify the Software for personal use.
However, distribution of the Software or any modified versions of it under the original creator's name, or under the same product name, is strictly prohibited.

If you use code from this project or redistribute modified versions under a different name, proper credit and attribution to the original author must be provided.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
