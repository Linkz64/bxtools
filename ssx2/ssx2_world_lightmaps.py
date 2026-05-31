import bpy
from mathutils import Vector

import os
from math import ceil

from ..general.bx_utils import natural_key

def find_layer_collection(layer_collection, name):
    """Find collection in the outliner/layer"""
    found = None
    if layer_collection.name == name:
        return layer_collection
    for layer in layer_collection.children:
        found = find_layer_collection(layer, name)
        if found:
            return found

def getset_image(name, res_x, res_y):
    image = bpy.data.images.get(name) # check if bake exists first
    if image is None:
        image = bpy.data.images.new(name, alpha=False, width=res_x, height=res_y)
    image.alpha_mode = 'NONE'
    return image

def getset_image_udim(name, res_x, res_y):
    image = bpy.data.images.get(name) # check if bake exists first
    if image is None:
        image = bpy.data.images.new(name, alpha=False, width=res_x, height=res_y, tiled=True)
    return image

def setup_lightmap_uvs_top_left(uv_scale, num_patches):
    """
    uv_scale = uv tile scale (0.0625 for 8x8 tile if atlas texture is 128x128)
    num_patches = number of patches

    note: blender origin is bottom left, ssx origin is top left
          therefore y is set to start at 0.9375 (1.0 - uv_scale)
    """
    x = 0.0
    y = 1.0 - uv_scale
    uvs = [(x, y)]
    for i in range(num_patches):
        #print(f"{i:3} {x:6} {y:6}")
        if x + uv_scale < 1.0:
            x += uv_scale
        else:
            x = 0.0
            y = y - uv_scale
        if y == -uv_scale:
            y = 1.0 - uv_scale
        uvs.append((x, y))
        #print(f"{i:3} {x:6} {y:6}")
    return uvs

def flip_image_y(img, width, height, channels=4):
    pixels = list(img.pixels)

    rows = [
        pixels[i * width * channels:(i + 1) * width * channels]
        for i in range(height)
    ]
    rows.reverse()

    flipped_pixels = [channel for row in rows for channel in row]

    img.pixels = flipped_pixels
    # img.update()

def generate_atlas_tiles_pixel_indices(res, tile_size=8):
    """
    returns a list of tuples.
    each tuple contains pixel indices for its tile.
    """
    tiles = []

    tiles_xy = res // tile_size

    for tile_y in range(tiles_xy):
        for tile_x in range(tiles_xy):

            indices = []

            for y in range(tile_size):
                for x in range(tile_size):

                    px = tile_x * tile_size + x
                    py = tile_y * tile_size + y

                    pixel_index = py * res + px
                    indices.append(pixel_index)

            tiles.append(tuple(indices))

    return tiles


class SSX2_OP_BakeTest(bpy.types.Operator):
    bl_idname = 'object.ssx2_bake_test'
    bl_label = "Bake Test"
    bl_description = "Lightmap bake test"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        print("\nClicked: Bake Lightmaps")

        """
        TODO

        - Check if patches are missing materials
        - Consider: Sampling the pixels from the original diffuse image without rescaling by 
            sampling surrounding pixels and doing bilinear math. (For PS2 color math)
        - Ignore patches with render disabled (outliner). Could be a bad idea.
        - Replace the name suffix adding code with unique incremental names.
        - Create atlas textures
        - Weighted option for seam fix.
        - Re-enable PS2 color convert
        - Should it require patch exporting to be enabled?
        - Convert other BXT patch types to mesh
        - Add this to the "Baking" UI category where baking of lightmaps and instance light matrices will be.
        - Should the lightmap bake mesh remain after baking is done?
            It could be useful for custom light painting and blending between old and new lightmaps.
            Before or after PS2 color conversion?
        - For patches with custom UVs consider doing a distance test for all UV bounds.
            Nearest corners and nearest boundary edges.
            This is not a solution. Rather a temporary workaround.
        - Average the normals on touching vertices to get rid of sharp/inaccurate pixel transitions.
            Include angle option to ignore sharp angles.
            Include "merge distance" aka round vertex coords 
            Advanced: Take face normal/winding into account to exclude flipped patches.
        - Consider: Caching the atlas indices and tile indices. Basically an index per-patch.
        """

        import time
        time_start = time.time()
        print("Timer started")


        
        atlas_res = 128
        tile_res = 8
        uv_scale = 0.0625




        prev_render_engine = bpy.context.scene.render.engine

        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_color = False
        #bpy.context.scene.render.bake.use_clear = False
        bpy.context.scene.render.bake.margin_type = 'EXTEND'
        bpy.context.scene.render.bake.margin = 0



        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode = "OBJECT")
        bpy.ops.object.select_all(action = "DESELECT")

        pch_col = bpy.data.collections.get("Patches")

        if pch_col is None:
            self.report({'WARNING'}, "No 'Patches' Collection found!")
            return {'CANCELLED'}
        
        patches = [obj for obj in pch_col.all_objects if obj.type == 'SURFACE' and not obj.hide_get()]
        patches.sort(key=lambda obj: natural_key(obj.name))

        num_patches = len(patches)

        uvs = setup_lightmap_uvs_top_left(uv_scale, num_patches)
        num_atlases = ceil(num_patches / 256)


        collection_name = "BXT_LIGHTMAP_MESHES"


        new_collection = bpy.data.collections.get(collection_name)
        if new_collection is None:
            bpy.data.collections.new(collection_name)
            new_collection = bpy.data.collections.get(collection_name)
        if collection_name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(new_collection)



        diffuse_images = []
        diffuse_image_indices = []

        graph = bpy.context.evaluated_depsgraph_get()

        new_materials = []
        bake_images = []

        print("\nCreating bake images and materials")
        tmp_time_start = time.time()


        for i in range(num_atlases):
            bake_img = getset_image(f"0.BXT_BAKE_ATLAS_IMG.{i}", atlas_res, atlas_res)
            bake_img.alpha_mode = 'NONE'

            bake_images.append(bake_img)

            print(f"0.BXT_BAKE_ATLAS_IMG.{i}")

            new_mat = bpy.data.materials.new(name=f"0.BXT_BAKE_MAT.{i}")
            new_mat.use_nodes = True

            nodes = new_mat.node_tree.nodes
            bake_node = nodes.new(type='ShaderNodeTexImage')
            bake_node.name = "BXT_BAKE_NODE"
            bake_node.select = True
            bake_node.image = bake_img
            # bake_node.interpolation = 'Linear'
            bake_node.interpolation = 'Closest'
            bake_node.extension = 'EXTEND'

            nodes.active = bake_node


            # new_obj.data.materials.append(newer_mat)
            new_materials.append(new_mat)


        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")




        current_atlas_index = -1

        print("\nCreating bake meshes and scaled down diffuse textures")
        tmp_time_start = time.time()

        for i, patch in enumerate(patches):

            if i % (atlas_res * 2) == 0:
                current_atlas_index += 1

            new_mesh_name = f"BXT_LIGHTMAP_BAKE_MESH.{i}"
            print(i, new_mesh_name, patch.name)

            mat = patch.data.materials[0] # TODO: handle error
            diffuse_node = mat.node_tree.nodes["Image Texture"]
            img = diffuse_node.image

            new_name = "0.BXT_DIFF_" + img.name

            if new_name in diffuse_images:
                diffuse_image_indices.append(diffuse_images.index(new_name))
            else:
                print("\tRescaling image", new_name)

                new_img = bpy.data.images.new(new_name, width=img.size[0], height=img.size[1], alpha=False)
                new_img.alpha_mode = 'NONE'
                new_img.pixels = list(img.pixels)
                new_img.scale(tile_res, tile_res)


                diffuse_images.append(new_name)
                diffuse_image_indices.append(len(diffuse_images) - 1)


            mesh = bpy.data.meshes.new_from_object(patch.evaluated_get(graph))
            uv_layer = mesh.uv_layers.new(name=f"BXT_LIGHTMAP_UVMAP")
            uv_layer.active_render = True
            mesh.uv_layers.active = uv_layer

            new_obj = bpy.data.objects.new(new_mesh_name, mesh)
            new_obj.matrix_world = patch.matrix_world
            new_obj.color = patch.color
            new_obj.data.materials.clear()
            new_obj.data.materials.append(new_materials[current_atlas_index])

            new_collection.objects.link(new_obj)
            new_obj.select_set(True)


            for poly in mesh.polygons:
                for vtx_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                    uv_layer.data[loop_idx].uv.y -= 1
                    uv_layer.data[loop_idx].uv.y *= -1
                    uv_layer.data[loop_idx].uv *= uv_scale
                    uv_layer.data[loop_idx].uv += Vector((uvs[i][0], uvs[i][1])) # .translate the data[].uv instead?


        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")


        



        print("\nFinalizing bake mesh object")
        tmp_time_start = time.time()

        new_obj = new_collection.objects[0]
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj

        outliner = find_layer_collection(bpy.context.view_layer.layer_collection, pch_col.name)
        outliner.exclude = True


        bpy.ops.object.join()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")


        print("\nBaking lightmaps. This may take a while.")
        tmp_time_start = time.time()

        bpy.ops.object.bake(type='DIFFUSE')

        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")




        if True:
            print("\nLinking bake nodes to material outputs")
            tmp_time_start = time.time()

            for bake_img, new_mat in zip(bake_images, new_materials):
                print(bake_img.name, "-", new_mat.name)

                nodes = new_mat.node_tree.nodes
                bake_node = nodes.get("BXT_BAKE_NODE")


                output_node = nodes.get("Material Output")
                new_mat.node_tree.links.new(bake_node.outputs["Color"], output_node.inputs["Surface"])

            time_taken = round(time.time() - tmp_time_start, 2)
            print(f"Took: {time_taken} seconds.")



        from pathlib import Path

        if bpy.data.filepath:
            abs_path = bpy.path.abspath("//Lightmaps")
            folder_path = Path(bpy.path.abspath("//Lightmaps"))
            folder_path.mkdir(parents=True, exist_ok=True)
        else:
            folder_path = Path(f"{str(Path.home())}/Downloads/BXTools_Lightmap")
            folder_path.mkdir(parents=True, exist_ok=True)


        atlas_tiles_pixel_indices = generate_atlas_tiles_pixel_indices(atlas_res)
        # tile indicies starting from the top left of the atlas
        tile_indices = [y * 16 + x for y in reversed(range(16)) for x in range(16)]



        if True:
            print("\nConverting to PS2 colors")
            tmp_time_start = time.time()

            """
            diffC = diffuse color texture but scaled down to 8x8
            lightC = baked lightmap color
            newC  = new Ps2 lightmap color
            alpha = new alpha channel. generated from the luminosity of lightC

            
            Generating:

            # "alpha channel as the luminosity of the lightmap"
            alpha = max(lightC.r, lightC.g, lightC.b)

            newC = diffC - ((diffC * lightC) / alpha)
            """

            n_t = tile_res - 1

            lut = [[[None] * tile_res for _ in range(tile_res)] for _ in range(8)]

            for y in range(tile_res):
                for x in range(tile_res):
                    lut[1][y][x] = (x, y)             # Rotate Left
                    lut[3][y][x] = (n_t - y, x)       # Default
                    lut[2][y][x] = (n_t - x, n_t - y) # Rotate Right
                    lut[4][y][x] = (y, n_t - x)       # Rotate 180
                    lut[7][y][x] = (n_t - x, y)       # Mirror X, Rotate Left
                    lut[0][y][x] = (x, n_t - y)       # Mirror X, Rotate Right
                    lut[6][y][x] = (y, x)             # Mirror Y
                    lut[5][y][x] = (n_t - y, n_t - x) # Mirror X


            orientations = [int(patch.ssx2_PatchProps.texMapPreset) for patch in patches]


            current_atlas_index = -1
            tile_index = -1

            for i in range(num_patches):

                if i % (atlas_res * 2) == 0:
                    current_atlas_index += 1
                    tile_index = 0

                bake_img = bake_images[current_atlas_index]
                diff_idx = diffuse_image_indices[i]
                orientation = orientations[i]
                tile_pixel_indices = atlas_tiles_pixel_indices[tile_indices[tile_index]]
                tile_index += 1

                diff = bpy.data.images.get(diffuse_images[diff_idx]).pixels

                for y in range(tile_res):
                    for x in range(tile_res):

                        tx, ty = lut[orientation][y][x]

                        src_i = (ty * tile_res + tx) * 4

                        diff_r = diff[src_i    ]
                        diff_g = diff[src_i + 1]
                        diff_b = diff[src_i + 2]

                        dst_i = tile_pixel_indices[y * tile_res + x] * 4

                        bake_r = bake_img.pixels[dst_i    ]
                        bake_g = bake_img.pixels[dst_i + 1]
                        bake_b = bake_img.pixels[dst_i + 2]

                        alpha = max(bake_r, bake_g, bake_b)

                        if alpha != 0:
                            bake_img.pixels[dst_i    ] = diff_r - (diff_r * bake_r) / alpha
                            bake_img.pixels[dst_i + 1] = diff_g - (diff_g * bake_g) / alpha
                            bake_img.pixels[dst_i + 2] = diff_b - (diff_b * bake_b) / alpha
                            bake_img.pixels[dst_i + 3] = alpha
                        else:
                            bake_img.pixels[dst_i    ] = 0.0
                            bake_img.pixels[dst_i + 1] = 0.0
                            bake_img.pixels[dst_i + 2] = 0.0
                            bake_img.pixels[dst_i + 3] = 0.0


                if False:
                    print("Saved to", os.path.join(folder_path, f"BXT_BAKE.{i}.png"))
                    bake_img.save_render(os.path.join(folder_path, f"BXT_BAKE.{i}.png"))

            time_taken = round(time.time() - tmp_time_start, 2)
            print(f"Took: {time_taken} seconds.")




        print("\nFixing seams")

        bpy.ops.object.mode_set(mode='OBJECT')

        tmp_time_start = time.time()

        color_samples = []

        new_mesh = new_obj.data
        uv_layer_data = new_mesh.uv_layers.active.data
        # uv_layer = new_mesh.uv_layers.get("BXT_LIGHTMAP_UVMAP").data
        polys = new_mesh.polygons
        verts = new_mesh.vertices

        do_weighted = False

        # cardinals and quadrants based on default bxtools orientation (with top view).
        # important to know: on the UV mesh they start from the top left going down
        BOUNDARY_VERTS_INDICES = (
            # non-corners
             1,  2,  3,  4,  5,  6, # south
             8, 16, 24, 32, 40, 48, # west
            15, 23, 31, 39, 47, 55, # east
            57, 58, 59, 60, 61, 62, # north
            # corners
             0, # south west
             7, # south east
            56, # north west
            63, # north east
        )

        # equivelant to BOUNDARY_VERTS_INDICES
        # cardinals and quadrants based on image view
        EQUIV_PIXEL_INDICES = (
            # non-corners
            48, 40, 32, 24, 16,  8, # west
            57, 58, 59, 60, 61, 62, # north
             1,  2,  3,  4,  5,  6, # south
            55, 47, 39, 31, 23, 15, # east
            # corners
            56, # north west
             0, # south west
            63, # north east
             7, # south east
        )


        boundaries = {}

        current_atlas_index = -1
        tile_index = -1

        for i in range(num_patches):

            vtx_start = i * 64

            if i % (atlas_res * 2) == 0:
                current_atlas_index += 1
                tile_index = 0

            bake_img = bake_images[current_atlas_index]
            tile_pixel_indices = atlas_tiles_pixel_indices[tile_indices[tile_index]]
            tile_index += 1

            for j, vtx_idx in enumerate(BOUNDARY_VERTS_INDICES):

                print(i, j, vtx_idx)

                pxl_idx = tile_pixel_indices[EQUIV_PIXEL_INDICES[j]] * 4
                
                rgb = Vector((
                    bake_img.pixels[pxl_idx    ],
                    bake_img.pixels[pxl_idx + 1],
                    bake_img.pixels[pxl_idx + 2],
                ))


                vtx = verts[vtx_start + vtx_idx].co.to_tuple(3)
                key = boundaries.get(vtx)

                # key: (rgb, [(img_idx/pch_idx, pxl_idx), ...])

                if key is None:
                    boundaries[vtx] = [rgb, [(current_atlas_index, pxl_idx)]]
                else:
                    key[0] += rgb
                    key[1].append((current_atlas_index, pxl_idx))



                # print(vtx, (rgb, [i, pxl_idx]))

            # break

        for _, b in boundaries.items():

            num_images = len(b[1])
            if num_images == 1:
                continue

            # print(_, b)

            new_color = b[0] / num_images

            for img_idx, pxl_idx in b[1]:
                # print(img_idx, pxl_idx)

                bake_images[img_idx].pixels[pxl_idx    ] = new_color.x
                bake_images[img_idx].pixels[pxl_idx + 1] = new_color.y
                bake_images[img_idx].pixels[pxl_idx + 2] = new_color.z


        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")



        if True:
            print("\nSaving to folder")
            tmp_time_start = time.time()

            for i, bake_img in enumerate(bake_images):
                print("Saved to", os.path.join(folder_path, f"{i:04}.png"))
                bake_img.save_render(os.path.join(folder_path, f"{i:04}.png"))

            time_taken = round(time.time() - tmp_time_start, 2)
            print(f"Took: {time_taken} seconds.")



        print("\nUpdating patch properties")
        tmp_time_start = time.time()

        current_atlas_index = -1
        for i, patch in enumerate(patches):
            if x + uv_scale < 1.0:
                x += uv_scale
            else:
                x = 0.0
                y += uv_scale

            if i % (atlas_res * 2) == 0:
                current_atlas_index += 1
                x = 0.0
                y = 0.0

            patch["lightmap_id"] = current_atlas_index
            patch["lightmap_uvs"] = [x, y, uv_scale, uv_scale]

        time_taken = round(time.time() - tmp_time_start, 2)
        print(f"Took: {time_taken} seconds.")




        bpy.context.scene.render.engine = prev_render_engine


        time_taken = round(time.time() - time_start, 2)
        print(f"\nFINISHED: {time_taken} seconds.")

        return {"FINISHED"}