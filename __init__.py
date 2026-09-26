"""
Metro 4A Engine — прямой экспортёр .model для Blender
Формат: Metro Exodus Static Model (version 44, model_type 1)
Поддержка: Vertex AO, генерация коллизии .nxcform33x
"""

bl_info = {
    "name": "4A Engine — Model Exporter (.model)",
    "author": "VesTank",
    "version": (0, 7, 0),
    "blender": (3, 0, 0),
    "location": "File > Export > Metro Exodus Model (.model)",
    "description": "Экспортирует статические меши в .model для 4A Engine (Exodus SDK / M3 SDK)",
    "category": "Import-Export",
}

import os
import struct
import math
import ctypes
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper

# ===========================================================================
# БИНАРНЫЙ СЛОЙ — ЧАНКИ И ГЕОМЕТРИЯ .model
# ===========================================================================

def pack_chunk(chunk_id, payload):
    return struct.pack("<II", chunk_id, len(payload)) + payload

def stringz(s):
    return s.encode("utf-8") + b"\x00"

def calc_bounds(positions):
    mins = [min(p[i] for p in positions) for i in range(3)]
    maxs = [max(p[i] for p in positions) for i in range(3)]
    center = [(a + b) * 0.5 for a, b in zip(mins, maxs)]
    radius = max(math.dist(center, p) for p in positions)
    return mins, maxs, center, radius

def make_model_header(positions, version, model_type):
    mins, maxs, center, radius = calc_bounds(positions)
    data = struct.pack("<BBH", version, model_type, 0xFFFF)
    data += struct.pack("<10f", *mins, *maxs, *center, radius)
    data += struct.pack("<f3If", 1500.0, 0, 0, 0, 0.333)
    return data

def pack_snorm(component):
    return max(0, min(255, round((component + 1.0) * 127.5)))

def pack_vec3_u32(x, y, z, w):
    return struct.pack("<4B", pack_snorm(x), pack_snorm(y), pack_snorm(z), w)

def compute_tangent_binormal(normal):
    nx, ny, nz = normal
    up = (0.0, 1.0, 0.0) if abs(ny) < 0.9 else (1.0, 0.0, 0.0)
    dot = up[0]*nx + up[1]*ny + up[2]*nz
    t = (up[0] - dot*nx, up[1] - dot*ny, up[2] - dot*nz)
    tlen = math.sqrt(t[0]**2 + t[1]**2 + t[2]**2) or 1.0
    t = (t[0]/tlen, t[1]/tlen, t[2]/tlen)
    b = (ny*t[2] - nz*t[1], nz*t[0] - nx*t[2], nx*t[1] - ny*t[0])
    blen = math.sqrt(b[0]**2 + b[1]**2 + b[2]**2) or 1.0
    b = (b[0]/blen, b[1]/blen, b[2]/blen)
    return t, b

def pack_vertex(pos, normal, uv, ao=1.0):
    tangent, binormal = compute_tangent_binormal(normal)
    ao_byte = max(0, min(255, round(ao * 255.0)))
    data = struct.pack("<3f", *pos)
    data += pack_vec3_u32(normal[0], normal[1], normal[2], ao_byte)
    data += pack_vec3_u32(tangent[0], tangent[1], tangent[2], 0x00)
    data += pack_vec3_u32(binormal[0], binormal[1], binormal[2], 0x00)
    data += struct.pack("<2f", *uv)
    return data

def blender_to_engine(v):
    return (v[0], v[2], v[1])

def make_material_chunk(texture, shader, game_material, name):
    data = stringz(texture) + stringz(shader) + stringz(game_material) + stringz(name)
    data += bytes([0x02, 0x00, 0x04, 0x00, 0x01])
    return data

def make_part_header(positions, version):
    return make_model_header(positions, version, model_type=0)

def make_vertex_chunk(vertices):
    header = struct.pack("<IIH", 2, len(vertices), 0)
    body = b"".join(pack_vertex(p, n, uv, ao) for p, n, uv, ao in vertices)
    return header + body

def make_face_chunk(faces):
    data = struct.pack("<IH", len(faces), 0)
    for f in faces:
        data += struct.pack("<3H", *f)
    return data

def make_part(positions_engine, vertices, faces, version,
              texture="", shader="geometry\\default",
              game_material="default", name="material"):
    part_header = make_part_header(positions_engine, version)
    mat_bytes   = make_material_chunk(texture, shader, game_material, name)
    vert_bytes  = make_vertex_chunk(vertices)
    face_bytes  = make_face_chunk(faces)
    return (pack_chunk(1, part_header) +
            pack_chunk(2, mat_bytes) +
            pack_chunk(3, vert_bytes) +
            pack_chunk(4, face_bytes))

def make_model(parts_payloads, all_positions, version=44):
    parts_blob = b"".join(pack_chunk(i, p) for i, p in enumerate(parts_payloads))
    extras = (pack_chunk(37, bytes(24)) + pack_chunk(39, bytes(24)) +
              pack_chunk(40, bytes(4)) + pack_chunk(41, bytes(1)))
    top_header = make_model_header(all_positions, version, model_type=1)
    return pack_chunk(9, parts_blob) + extras + pack_chunk(1, top_header)

# ===========================================================================
# ГЕНЕРАТОР КОЛЛИЗИИ .nxcform33x (Есть некоторые баги...)
# ===========================================================================

# ---------------------------------------------------------------------------
# NxTriangleMesh v14 — бинарная часть до BV4
# ---------------------------------------------------------------------------

def _nx_trimesh_header(vertices, faces):
    """NxTriangleMesh без BV4 секции."""
    vc, fc = len(vertices), len(faces)
    data = b"NXS\x01MESH"          # 4E 58 53 01 4D 45 53 48
    data += struct.pack("<I", 14)   # version
    data += struct.pack("<I", 1)    # flags
    data += struct.pack("<I", 4)    # unk (константа из сэмпла?)
    data += struct.pack("<I", vc)
    data += struct.pack("<I", fc)
    for v in vertices:
        data += struct.pack("<3f", *v)
    if vc <= 255:
        for f in faces:
            data += struct.pack("<3B", f[0], f[1], f[2])
    else:
        for f in faces:
            data += struct.pack("<3H", f[0], f[1], f[2])
    return data

# ---------------------------------------------------------------------------
# BV4 acceleration structure (насколько я понял)
# ---------------------------------------------------------------------------

def _face_normal(v0, v1, v2):
    ax, ay, az = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
    bx, by, bz = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
    nx = ay*bz - az*by
    ny = az*bx - ax*bz
    nz = ax*by - ay*bx
    l = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
    return nx/l, ny/l, nz/l

def _build_bv4(vertices, faces):
    mins = [min(v[i] for v in vertices) for i in range(3)]
    maxs = [max(v[i] for v in vertices) for i in range(3)]
    d = math.sqrt(sum((maxs[i]-mins[i])**2 for i in range(3)))

    b = b"BV4 "
    b += struct.pack(">I", 1)
    b += struct.pack(">3I", 0, 0, 0)
    b += struct.pack(">f", d)

    b += struct.pack(">I", 2)
    for _ in faces:
        b += bytes([0x38, 0x00, 0x07, 0x8E])

    b += struct.pack(">I", 4)
    b += bytes([
        0x7F,0xF1,0x7F,0xFF, 0x80,0x01,0x7F,0xFF,
        0x80,0x01,0x7F,0xFF, 0x00,0x00,0x00,0x00,
        0x80,0x01,0x7F,0xFF, 0x7F,0xF1,0x7F,0xFF,
        0x80,0x01,0x7F,0xFF, 0x00,0x00,0x00,0x00,
        0x80,0x01,0x7F,0xFF, 0x80,0x01,0x7F,0xFF,
        0x80,0x01,0x7F,0xFF, 0x00,0x00,0x00,0x00,
    ])

    b += struct.pack(">I", 5)
    b += struct.pack(">I", 0x45)
    b += struct.pack(">I", 0x91)
    b += struct.pack(">I", 0xFFFFFFFF)

    b += struct.pack("<3f", *mins)
    b += struct.pack("<3f", *maxs)
    b += struct.pack("<I", 0)

    return b

def _build_nxtrimesh(vertices, faces):
    return _nx_trimesh_header(vertices, faces) + _build_bv4(vertices, faces)

# ---------------------------------------------------------------------------
# 4A Engine обёртка, u know
# ---------------------------------------------------------------------------

def _4a_lenstr(s):
    enc = s.encode("utf-8") + b"\x00"
    return struct.pack("<I", len(enc)) + enc

def _4a_block(material, game_material, nx_blob):
    payload  = bytes(14)                        
    payload += _4a_lenstr(material)
    payload += struct.pack("<II", 1, 0)         
    payload += _4a_lenstr(game_material)
    payload += _4a_lenstr("material")
    payload += struct.pack("<H", 0xFFFF)        
    payload += struct.pack("<I", 0)             
    payload += struct.pack("<B", 1)             
    payload += struct.pack("<I", len(nx_blob))
    payload += nx_blob

    return struct.pack("<II", 1, len(payload)) + payload

def write_nxcform(mesh_parts, output_path):
    data = b""
    for part in mesh_parts:
        nx = _build_nxtrimesh(part["vertices"], part["faces"])
        data += _4a_block(
            part.get("material", "geometry\\default@no_tess=1"),
            part.get("game_material", "default"),
            nx,
        )
    with open(output_path, "wb") as f:
        f.write(data)
    return data

# ---------------------------------------------------------------------------
# Извлечение collision mesh из Blender-объектов
# ---------------------------------------------------------------------------

def export_collision_from_objects(objects, output_path, apply_transform=True):
    col_suffixes = ("_col", "_collision", "_phys", "_px")
    col_objects = [o for o in objects
                   if any(o.name.lower().endswith(s) for s in col_suffixes)]
    if not col_objects:
        col_objects = objects

    mesh_parts = []

    for obj in col_objects:
        if obj.type != "MESH":
            continue

        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(
            obj.evaluated_get(depsgraph),
            preserve_all_data_layers=False, depsgraph=depsgraph)

        try:
            if apply_transform:
                mesh.transform(obj.matrix_world)
                mesh.update()

            mesh.calc_loop_triangles()

            verts_e = [blender_to_engine(
                (float(v.co.x), float(v.co.y), float(v.co.z)))
                for v in mesh.vertices]

            faces_e = [(t.vertices[0], t.vertices[2], t.vertices[1])
                       for t in mesh.loop_triangles]

            if not verts_e or not faces_e:
                continue

            mat = mesh.materials[0] if mesh.materials else None
            if mat:
                shader   = mat.metro_shader
                game_mat = mat.metro_game_material or "default"
            else:
                shader   = "geometry\\default"
                game_mat = "default"

            material_str = shader + "@no_tess=1"

            mesh_parts.append({
                "vertices":      verts_e,
                "faces":         faces_e,
                "material":      material_str,
                "game_material": game_mat,
            })

        finally:
            bpy.data.meshes.remove(mesh)

    if not mesh_parts:
        raise ValueError("Нет мешей для генерации коллизии.")

    return write_nxcform(mesh_parts, output_path)

# ===========================================================================
# РАСЧЁТ AO И ИЗВЛЕЧЕНИЕ ГЕОМЕТРИИ
# ===========================================================================

def bake_ao_on_object(obj):
    prev_mode = obj.mode
    prev_active = bpy.context.view_layer.objects.active
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        bpy.ops.paint.vertex_color_dirt(
            dirt_angle=math.radians(90),
            clean_angle=math.radians(110),
            dirt_only=False
        )
    except Exception as e:
        print(f"[Metro Exporter] AO bake failed: {e}")
    finally:
        if bpy.context.object and bpy.context.object.mode != prev_mode:
            bpy.ops.object.mode_set(mode=prev_mode)
        bpy.context.view_layer.objects.active = prev_active


def extract_parts(obj, apply_modifiers, apply_transform, version, calc_ao=False):
    if calc_ao:
        bake_ao_on_object(obj)

    if apply_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(
            obj.evaluated_get(depsgraph),
            preserve_all_data_layers=True, depsgraph=depsgraph)
    else:
        mesh = obj.data.copy()

    try:
        if apply_transform:
            mesh.transform(obj.matrix_world)
            mesh.update()

        mesh.calc_loop_triangles()
        if hasattr(mesh, "calc_normals_split"):
            mesh.calc_normals_split()

        color_layer = None
        if hasattr(mesh, "color_attributes") and mesh.color_attributes:
            color_layer = (mesh.color_attributes.active_color
                           or mesh.color_attributes[0])
        elif hasattr(mesh, "vertex_colors") and mesh.vertex_colors:
            color_layer = mesh.vertex_colors.active or mesh.vertex_colors[0]

        mat_indices = sorted({tri.material_index
                              for tri in mesh.loop_triangles})
        parts = []

        for mat_idx in mat_indices:
            mat = (mesh.materials[mat_idx]
                   if mat_idx < len(mesh.materials) else None)

            if mat:
                tex   = mat.metro_texture
                shd   = mat.metro_shader
                gmat  = mat.metro_game_material
                mname = mat.metro_part_name if mat.metro_part_name else mat.name
            else:
                tex, shd, gmat, mname = "", "geometry\\default", "default", obj.name

            verts, faces, vmap = [], [], {}

            for tri in mesh.loop_triangles:
                if tri.material_index != mat_idx:
                    continue
                tri_indices = []
                for loop_idx in tri.loops:
                    loop = mesh.loops[loop_idx]
                    vert = mesh.vertices[loop.vertex_index]

                    pos_e = blender_to_engine(
                        (float(vert.co.x), float(vert.co.y), float(vert.co.z)))

                    n_bl = loop.normal
                    n_e = blender_to_engine(
                        (float(n_bl.x), float(n_bl.y), float(n_bl.z)))
                    nlen = math.sqrt(sum(x*x for x in n_e)) or 1.0
                    n_e = tuple(x / nlen for x in n_e)

                    if mesh.uv_layers.active:
                        raw = mesh.uv_layers.active.data[loop_idx].uv
                        uv = (float(raw.x), 1.0 - float(raw.y))
                    else:
                        uv = (0.0, 0.0)

                    ao_val = 1.0
                    if color_layer:
                        domain = getattr(color_layer, "domain", "CORNER")
                        col = (color_layer.data[loop_idx].color
                               if domain == 'CORNER'
                               else color_layer.data[loop.vertex_index].color)
                        ao_val = (col[0] + col[1] + col[2]) / 3.0

                    key = (loop.vertex_index,
                           round(uv[0], 5), round(uv[1], 5),
                           round(n_e[0], 4), round(n_e[1], 4), round(n_e[2], 4),
                           round(ao_val, 2))

                    if key not in vmap:
                        vmap[key] = len(verts)
                        verts.append((pos_e, n_e, uv, ao_val))

                    tri_indices.append(vmap[key])

                faces.append((tri_indices[0], tri_indices[2], tri_indices[1]))

            if verts:
                parts.append(dict(
                    positions_engine=[v[0] for v in verts],
                    vertices=verts, faces=faces,
                    texture=tex, shader=shd,
                    game_material=gmat, name=mname,
                ))
        return parts
    finally:
        bpy.data.meshes.remove(mesh)

def export_objects(objects, apply_modifiers=True, apply_transform=True,
                   version=44, calc_ao=False):
    all_parts_payloads, all_positions = [], []
    for obj in objects:
        if obj.type != "MESH":
            continue
        parts = extract_parts(obj, apply_modifiers, apply_transform,
                              version, calc_ao)
        for p in parts:
            payload = make_part(
                p["positions_engine"], p["vertices"], p["faces"], version,
                texture=p["texture"], shader=p["shader"],
                game_material=p["game_material"], name=p["name"],
            )
            all_parts_payloads.append(payload)
            all_positions.extend(p["positions_engine"])

    if not all_parts_payloads:
        raise ValueError("Нет мешей для экспорта.")
    if not all_positions:
        raise ValueError("Меши не содержат вершин.")
    return make_model(all_parts_payloads, all_positions, version)

# ===========================================================================
# ИНТЕРФЕЙС BLENDER (UI)
# ===========================================================================

class METRO_OT_export_model(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.metro_model"
    bl_label = "Экспорт Metro .model"
    bl_options = {"PRESET"}

    filename_ext = ".model"
    filter_glob: StringProperty(default="*.model", options={"HIDDEN"})

    model_version: EnumProperty(
        name="Версия движка",
        items=[
            ("44", "Metro Exodus (v44)", "Полная поддержка"),
            ("22", "Metro Last Light (v22)", "В разработке"),
            ("7",  "Metro 2033 / LL (v7)",  "В разработке"),
        ],
        default="44",
    )

    use_selection: BoolProperty(
        name="Только выделенное",
        default=True,
    )

    calc_ao: BoolProperty(
        name="Рассчитать AO (Vertex AO)",
        description="Запечь затенение полостей и углов в вершины модели",
        default=True,
    )

    export_collision: BoolProperty(
        name="Создать коллизию (.nxcform33x)",
        description=(
            "Сгенерировать файл коллизии рядом с .model. "
            "Объекты с суффиксом _col/_collision/_phys используются "
            "как отдельный collision mesh; иначе — основная геометрия"
        ),
        default=False,
    )

    lod_level: EnumProperty(
        name="Уровень детализации (LOD)",
        description="[В РАЗРАБОТКЕ] Назначить эту геометрию как конкретный LOD",
        items=[
            ("0", "LOD 0 (Основной)", "Высокое качество, вблизи"),
            ("1", "LOD 1 (Средний)",  "Среднее качество"),
            ("2", "LOD 2 (Низкий)",   "Низкое качество, вдали"),
        ],
        default="0",
    )

    apply_modifiers: BoolProperty(name="Применить модификаторы", default=True)
    apply_transform: BoolProperty(name="Применить трансформацию", default=True)

    def execute(self, context):
        if self.use_selection:
            objects = [o for o in context.selected_objects if o.type == "MESH"]
        else:
            objects = [o for o in context.scene.objects if o.type == "MESH"]

        if not objects:
            self.report({"ERROR"}, "Нет меш-объектов для экспорта!")
            return {"CANCELLED"}

        if self.model_version != "44":
            self.report({"WARNING"},
                        "Экспорт для старых версий пока в разработке. "
                        "Файл сохранён как v44.")

        try:
            data = export_objects(
                objects,
                self.apply_modifiers,
                self.apply_transform,
                44,
                calc_ao=self.calc_ao,
            )
            filepath = self.filepath
            if not filepath.endswith(".model"):
                filepath += ".model"
            with open(filepath, "wb") as f:
                f.write(data)
            self.report({"INFO"}, f"Экспортировано: {filepath}")
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if self.export_collision:
            col_path = filepath.replace(".model", ".nxcform33x")
            try:
                export_collision_from_objects(
                    objects, col_path,
                    apply_transform=self.apply_transform,
                )
                self.report({"INFO"}, f"Коллизия: {col_path}")
            except Exception as exc:
                self.report({"WARNING"}, f"Коллизия не создана: {exc}")

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Основные настройки:", icon='PREFERENCES')
        box.prop(self, "model_version")
        box.prop(self, "use_selection")

        box = layout.box()
        box.label(text="Геометрия и свет:", icon='MESH_DATA')
        box.prop(self, "apply_modifiers")
        box.prop(self, "apply_transform")
        box.prop(self, "calc_ao")
        box.prop(self, "lod_level")

        box = layout.box()
        box.label(text="Физика:", icon='PHYSICS')
        box.prop(self, "export_collision")
        if self.export_collision:
            box.label(
                text="  Объекты с суффиксом _col используются как collision mesh",
                icon='INFO')

# ===========================================================================
# ПАНЕЛЬ МАТЕРИАЛОВ
# ===========================================================================

class METRO_PT_material(bpy.types.Panel):
    bl_label = "Metro Material (4A Engine)"
    bl_idname = "METRO_PT_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        mat = context.material
        layout = self.layout
        layout.prop(mat, "metro_texture",       text="Texture")
        layout.prop(mat, "metro_shader",        text="Shader")
        layout.prop(mat, "metro_game_material", text="Game Material")
        layout.prop(mat, "metro_part_name",     text="Part Name")
        layout.separator()
        layout.operator("metro.init_mat",
                        text="Сбросить / Инициализировать",
                        icon="FILE_REFRESH")


class METRO_OT_init_mat(bpy.types.Operator):
    bl_idname = "metro.init_mat"
    bl_label = "Инициализировать Metro Material"

    def execute(self, context):
        mat = context.material
        if not mat:
            return {"CANCELLED"}
        mat.metro_texture       = ""
        mat.metro_shader        = "geometry\\default"
        mat.metro_game_material = "default"
        mat.metro_part_name     = mat.name
        return {"FINISHED"}


def _menu_func(self, context):
    self.layout.operator(METRO_OT_export_model.bl_idname,
                         text="Metro Exodus Model (.model)")

# ===========================================================================
# РЕГИСТРАЦИЯ
# ===========================================================================

CLASSES = (
    METRO_OT_export_model,
    METRO_PT_material,
    METRO_OT_init_mat,
)

def register():
    bpy.types.Material.metro_texture = StringProperty(
        name="Texture", default="")
    bpy.types.Material.metro_shader = EnumProperty(
        name="Shader Preset",
        items=[
            ("geometry\\default",  "default",  "Стандартный шейдер"),
            ("geometry\\snow",     "snow",     "Снег"),
            ("geometry\\add_alpha","add_alpha","Альфа-канал?"),
            ("geometry\\invalid",  "invalid",  "-"),
            ("geometry\\wet",      "wet",      "Мокрые поверхности"),
            ("geometry\\glass",    "glass",    "Стекло"),
            ("geometry\\invisible","invisible","Невидимый"),
            ("geometry\\wood",     "wood",     "Дерево"),
        ],
        default="geometry\\default",
    )
    bpy.types.Material.metro_game_material = StringProperty(
        name="Game Material", default="default")
    bpy.types.Material.metro_part_name = StringProperty(
        name="Part Name", default="")

    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(_menu_func)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_func)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Material.metro_texture
    del bpy.types.Material.metro_shader
    del bpy.types.Material.metro_game_material
    del bpy.types.Material.metro_part_name

if __name__ == "__main__":
    register()