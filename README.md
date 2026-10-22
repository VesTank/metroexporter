Blender to Metro (.model) Exporter. 
A simple Blender 3.0+ addon for exporting 3D objects to the 4A Engine .model format (Metro Exodus).

### RU

Имеется возможность:
- Применения модификаций и трансформаций перед экспортом.
- Расчёт Vertex AO (Ambient Occlusion) перед экспортом.
- Поддержка LOD-ов: уровней детализации модели (т.е. LOD 0, LOD 1, LOD 2...)
- Генерация коллизии (.nxcform33x)

Требования:
- Blender 3.0.0 или новее

Установка: 
1. Загрузить последнюю версию аддона со страницы релизов.
2. Открыть Blender.
3. Перейти во вкладку Edit > Preferences > Add-ons.
4. Нажать Install... в верхнем правом углу.
5. Выбрать загруженный .zip архив и нажать на Install Add-on.
6. Найти "Import-Export: Metro Model Exporter" и включить его.

Как использовать:
1. Подготовьте модель. Если требуется кастомная коллизия, подготовьте дополнительные модели с суффиксом _col в конце имени (например, my_svetofor_collision).
2. Вкладка File > Export > Metro Exodus Model (.model).
3. В панели справа примените подходящую конфигурацию: версия движка, уровень LOD, просчитать AO, применить модификаторы и т.д.
4. Выберете папку и нажмите Export.

Credits:
- AI: ИИ использовался для ревёрса и анализа бинарников .model, структуры.
- APAmk2: blender-uEngine by APAmk использовался для начального понимания структуры .model формата.

### EN

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
