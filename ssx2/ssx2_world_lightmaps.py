import bpy
from mathutils import Vector

import os

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
    uv_scale = uv tile scale (0.0625 for 8x8 tile if texture is 128x128)
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

class SSX2_OP_BakeTest(bpy.types.Operator):
    bl_idname = 'object.ssx2_bake_test'
    bl_label = "Bake Test"
    bl_description = "Lightmap bake test"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        print("\nClicked: Bake Lightmaps")

        """


        Options for fixing the seams
            - Average the normals.
                Simply merging causes some faces to collapse into triangles.
                Try finding neighbors and averaging normals or
                create a new all-in-one island mesh with custom normals.
                
                This won't fix the seam issue. In-game each tile does bilinear filtering individually.
                Which means the boundary edges need the same pixels as the ones on the neighbors.

            - Scale each uv tile down (by 0.875?).
                Not sure if this would help but I want to see what would happen.
                Might work if I start with a high res bake.

            - Neighbors use the same pixels on touching boundary edges.
                Make a list of all neighbors (by finding touching corners. If 2 and 2 touch then its a direct neighbor).
                Get the pixels on both sides of the touching edges and average them. Also add options for weighted and custom.  

        

        - Consider: Sampling the pixels from the original diffuse image without rescaling by 
            sampling surrounding pixels and doing bilinear math. (For PS2 color math)

        - Ignore patches with render disabled (outliner)

        - Replace the name suffix adding code with short incremental names.

        """

        import time
        time_start = time.time()
        print("Timer started")


        # temp patch count limit for testing
        has_cap = False
        cap = 10

        
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

        if has_cap:
            uvs = setup_lightmap_uvs_top_left(uv_scale, cap)
        else:
            uvs = setup_lightmap_uvs_top_left(uv_scale, num_patches)



        new_collection = bpy.data.collections.get("meshes_for_lightmaps")
        if new_collection is None:
            bpy.data.collections.new("meshes_for_lightmaps")
            new_collection = bpy.data.collections.get("meshes_for_lightmaps")
        if "meshes_for_lightmaps" not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(new_collection)



        diffuse_images = []
        diffuse_image_indices = []

        graph = bpy.context.evaluated_depsgraph_get()

        new_materials = []
        bake_images = []

        print("\nCreating bake materials")


        for i in range(num_patches):
            # bake_img = getset_image(f"0.BXT_BAKE_IMG.{i}", atlas_res, atlas_res)
            bake_img = bpy.data.images.new(f"0.BXT_BAKE_IMG.{i}", width=tile_res, height=tile_res, alpha=False)
            bake_img.alpha_mode = 'NONE'


            bake_images.append(bake_img)

            print(f"0.BXT_BAKE_MAT.{i}")

            new_mat = bpy.data.materials.new(name=f"0.BXT_BAKE_MAT.{i}")
            new_mat.use_nodes = True
            nodes = new_mat.node_tree.nodes
            bake_node = nodes.new(type='ShaderNodeTexImage')
            bake_node.name = "BXT_BAKE_NODE"
            bake_node.select = True
            bake_node.image = bake_img
            nodes.active = bake_node


            # new_obj.data.materials.append(newer_mat)
            new_materials.append(new_mat)


        # current_atlas_index = 0

        print("\nCreating bake meshes and scaled down diffuse textures")

        for i, patch in enumerate(patches):

            if i >= cap and has_cap:
                print("STOPPED DUE TO CAP")
                break

            # if i % (atlas_res * 2) == 0:
            #     current_atlas_index += 1

            print(i, patch.name + '.lightmapper')

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

                # flip_image_y(new_img, tile_res, tile_res)

                diffuse_images.append(new_name)
                diffuse_image_indices.append(len(diffuse_images) - 1)


            mesh = bpy.data.meshes.new_from_object(patch.evaluated_get(graph))
            uv_layer = mesh.uv_layers.new(name=f"UVMap.Lightmap")
            uv_layer.active_render = True
            mesh.uv_layers.active = uv_layer

            new_obj = bpy.data.objects.new(patch.name + '.lightmapper', mesh)
            new_obj.matrix_world = patch.matrix_world
            new_obj.color = patch.color
            new_obj.data.materials.clear()
            new_obj.data.materials.append(new_materials[i])

            new_collection.objects.link(new_obj)
            new_obj.select_set(True)


            for poly in mesh.polygons:
                for vtx_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                    uv_layer.data[loop_idx].uv.y -= 1
                    uv_layer.data[loop_idx].uv.y *= -1
                #     # uv_layer.data[loop_idx].uv *= uv_scale
                #     # uv_layer.data[loop_idx].uv += Vector((uvs[i][0], uvs[i][1])) # .translate the data[].uv instead?



        new_obj = new_collection.objects[0]
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj

        outliner = find_layer_collection(bpy.context.view_layer.layer_collection, pch_col.name)
        outliner.exclude = True


        bpy.ops.object.join()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')


        print("\nBaking lightmaps. This may take a while.")

        bpy.ops.object.bake(type='DIFFUSE')




        if True:
            print("\nConverting to PS2 colors")

            from pathlib import Path

            if bpy.data.filepath:
                abs_path = bpy.path.abspath("//Lightmaps")
                folder_path = Path(bpy.path.abspath("//Lightmaps"))
                folder_path.mkdir(parents=True, exist_ok=True)
            else:
                folder_path = Path(f"{str(Path.home())}/Downloads/BXTools_Lightmap")
                folder_path.mkdir(parents=True, exist_ok=True)

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


            def transform_xy(x, y, mode):

                if mode == 1:   # Rotate Left
                    return x, y
                elif mode == 3: # Default
                    return n_t - y, x
                elif mode == 2: # Rotate Right
                    return n_t - x, n_t - y
                elif mode == 4: # Rotate 180
                    return y, n_t - x
                elif mode == 7: # Mirror X, Rotate Left
                    return n_t - x, y
                elif mode == 0: # Mirror X, Rotate Right
                    return x, n_t - y
                elif mode == 6: # Mirror Y
                    return y, x
                elif mode == 5: # Mirror X
                    return n_t - y, n_t - x


            # lut = [[None] * (tile_res * tile_res) for _ in range(8)]

            # for y in range(tile_res):
            #     row = y * tile_res
            #     for x in range(tile_res):
            #         i = row + x

            #         lut[1][i] = (x, y)             # Rotate Left
            #         lut[3][i] = (n_t - y, x)       # Default
            #         lut[2][i] = (n_t - x, n_t - y) # Rotate Right
            #         lut[4][i] = (y, n_t - x)       # Rotate 180
            #         lut[7][i] = (n_t - x, y)       # Mirror X, Rotate Left
            #         lut[0][i] = (x, n_t - y)       # Mirror X, Rotate Right
            #         lut[6][i] = (y, x)             # Mirror Y
            #         lut[5][i] = (n_t - y, n_t - x) # Mirror X

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

            for i, (bake_img, diff_idx, orientation) in enumerate(zip(bake_images, diffuse_image_indices, orientations)):
                bake = bake_img.pixels[:]
                diff = bpy.data.images.get(diffuse_images[diff_idx]).pixels

                new_pixels = [0] * (tile_res * tile_res * 4)

                for y in range(tile_res):
                    for x in range(tile_res):

                        # lut_index = y * tile_res + x
                        tx, ty = lut[orientation][y][x]
                        # tx, ty = transform_xy(x, y, orientation)

                        src_i = (ty * tile_res + tx) * 4
                        dst_i = (y * tile_res + x) * 4

                        alpha = max(bake[dst_i], bake[dst_i + 1], bake[dst_i + 2])
                        diff_r = diff[src_i]
                        diff_g = diff[src_i + 1]
                        diff_b = diff[src_i + 2]

                        if alpha != 0:
                            new_pixels[dst_i]     = diff_r - (diff_r * bake[dst_i    ]) / alpha
                            new_pixels[dst_i + 1] = diff_g - (diff_g * bake[dst_i + 1]) / alpha
                            new_pixels[dst_i + 2] = diff_b - (diff_b * bake[dst_i + 2]) / alpha
                            new_pixels[dst_i + 3] = alpha
                        else:
                            new_pixels[dst_i]     = 0.0
                            new_pixels[dst_i + 1] = 0.0
                            new_pixels[dst_i + 2] = 0.0
                            new_pixels[dst_i + 3] = 0.0

                bake_img.pixels = new_pixels




                if True:
                    print("Saved to", os.path.join(folder_path, f"bake{i}.png"))

                    bake_img.save_render(os.path.join(folder_path, f"bake{i}.png"))



        
            """
            

            for i, bake_img, diff_idx in zip(range(num_patches), bake_images, diffuse_image_indices):

                bxs = bake_img.pixels
                dxs = bpy.data.images.get(diffuse_images[diff_idx]).pixels

                new_pxs = []

                for j in range(0, (tile_res ** 2) * 4, 4): # 256 for 8 | 1024 for 16

                    alpha = max(bxs[j + 0], bxs[j + 1], bxs[j + 2])

                    if alpha != 0:
                        new_pxs.append(dxs[j    ] - ((dxs[j    ] * bxs[j    ]) / alpha))
                        new_pxs.append(dxs[j + 1] - ((dxs[j + 1] * bxs[j + 1]) / alpha))
                        new_pxs.append(dxs[j + 2] - ((dxs[j + 2] * bxs[j + 2]) / alpha))
                        new_pxs.append(alpha)
                    else:
                        new_pxs.extend((0, 0, 0, 0))

                bake_img.pixels = new_pxs

                print(bake_img.name)

                bake_img.save_render(os.path.join(folder_path, f"bake{i}.png"))

                #bake_img.filepath = f"X:/Downloads/bx_test/lightmaps/bake{i}.png"
                #bake_img.save()


            """



        bpy.context.scene.render.engine = prev_render_engine


        time_taken = round(time.time() - time_start, 2)
        print(f"FINISHED: {time_taken} seconds.")

        return {"FINISHED"}