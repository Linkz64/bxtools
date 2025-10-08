import bpy
from mathutils import Vector

class SSX2_OP_BakeTest(bpy.types.Operator):
    bl_idname = 'object.ssx2_bake_test'
    bl_label = "Bake Test"
    bl_description = "Lightmap bake test"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        print("\nClicked: Bake Lightmaps")

        import time
        time_start = time.time()
        print("Timer started")


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
            return image
        def getset_image_udim(name, res_x, res_y):
            image = bpy.data.images.get(name) # check if bake exists first
            if image is None:
                image = bpy.data.images.new(name, alpha=False, width=res_x, height=res_y, tiled=True)
            return image

        def setup_lightmap_uvs(uv_scale, length):
            """
            uv_scale = uv tile scale (0.0625 for 8x8 tile if texture is 128x128)
            length = number of patches

            note: blender origin is bottom left, ssx origin is top left
                  therefore y is set to start at 0.9375 (1.0 - uv_scale)
            """
            x = 0.0
            y = 1.0 - uv_scale
            uvs = [(x, y)]
            for i in range(length):
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

        def getUVIslandsForActiveObject(): # from "raubana Dylan J. Raub" https://blenderartists.org/t/modifying-uvs-in-python-while-in-object-mode-affects-how-uv-islands-work/1378510/4
            islands = []
            obj = bpy.context.view_layer.objects.active
            
            poly_index_lists = bpy_extras.mesh_utils.mesh_linked_uv_islands( obj.data )
            
            for poly_index_list in poly_index_lists:
                island = []
                for poly_index in poly_index_list:
                    island.append( obj.data.polygons[poly_index] )
                islands.append( island )
            
            return islands

        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_color = False
        #bpy.context.scene.render.bake.use_clear = False      # may speed things up
        #bpy.context.scene.render.bake.margin_type = 'EXTEND'
        bpy.context.scene.render.bake.margin = 4

        #bpy.context.scene.render.use_file_extension = True
        #bpy.context.scene.render.image_settings.file_format = 'PNG'
        #bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        #bpy.context.scene.render.image_settings.color_depth = '8'
        #bpy.context.scene.render.image_settings.compression = 0


        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode = "OBJECT")
        bpy.ops.object.select_all(action = "DESELECT")

        collection = bpy.data.collections.get("Patches")

        if collection is None:
            self.report({'WARNING'}, "No 'Patches' Collection found!")
            return {'CANCELLED'}
        
        patches = [i for i in collection.all_objects if i.type == 'SURFACE']

        

        method = 2 # smoothing bounding normals

        length = len(patches)
        cap = 10 #length    # temp patch count limit for testing
        res = 128 # texture resolution
        uv_scale = 0.0625#*4 # lightmap uv scale. for scaling down to fill 8x8 pixels
        uvs = setup_lightmap_uvs(uv_scale, cap)



        # for i, obj in enumerate(patches):
        #     obj.select_set(True)

        # bpy.context.view_layer.objects.active = patches[0]
        # bpy.ops.object.convert(target='MESH')



        if method == 2: # select all, merge


            # TODO:
            # - duplicate the patches and eval to mesh
            # - remove materials from duplicates
            # - merge all duplicates
            # - make a new material type that's only for the final bake mesh 


            bpy.context.scene.render.bake.margin = 0

            collection.hide_select = False

            bpy.context.view_layer.objects.active = patches[0] # for bpy.ops.object.bake()

            num_patches = len(patches)
            mat_index_list = [] # per patch
            mat_keys = bpy.data.materials.keys()

            mat_slots = [mat_keys.index(patches[0].material_slots[0].material.name)]

            for i, patch in enumerate(patches):
                if i < cap:
                    patch.select_set(True)
                    try:
                        mat_index_list.append(mat_keys.index(patch.material_slots[0].material.name))

                        if mat_index_list[i] in mat_slots:
                            pass
                        else:
                            mat_slots.append(mat_index_list[i])
                    except:
                        self.report({'ERROR'}, f"No surface patch material applied to {patch.name}")
                        return {'CANCELLED'}

                    # if i > 1:
                    #     break
                else:
                    print("STOPPED")
                    break
                    return {'CANCELLED'}
            print('mat slots', mat_slots)

            bpy.ops.object.join()
            bpy.ops.object.convert(target='MESH')
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles() # calculate threshold=* according to world scale
            bpy.ops.object.mode_set(mode='OBJECT')

            obj = patches[0]
            mesh = obj.data
            uv_layer = mesh.uv_layers.new(name="UVMap.Lightmap")
            #uv_layer.active_render = True
            mesh.uv_layers.active = uv_layer


            num_fittable = int(1 / uv_scale ** 2)
            map_width = 0
            num_maps = 0
            for i in range(cap):
                if i % num_fittable == 0:
                    map_width += res
                    num_maps += 1
            image = getset_image(f"0.2.bake", int(map_width), res)
            uv_rescale = 1.0 / num_maps
            print(map_width, num_maps, uv_rescale, num_fittable)

            obj.data.materials.clear()
            for i, mat_slot in enumerate(mat_slots):
                current_mat = bpy.data.materials[mat_slot]
                obj.data.materials.append(current_mat)

                nodes = current_mat.node_tree.nodes
                bake_node = nodes["Bake"]
                bake_node.select = True
                nodes.active = bake_node
                
                bake_node.image = image


            current_map_index = -1 # texture index
            uv_index = -1 # uv or patch index

            current_mat_index = 0
            for i, poly in enumerate(mesh.polygons):
                if i % 49 == 0:
                    #print(i, "NEW UV")
                    uv_index += 1

                    if uv_index % num_fittable == 0:
                        current_map_index += 1
                        print('map', current_map_index)

                    current_mat_index = mat_slots.index(mat_index_list[uv_index])

                poly.material_index = current_mat_index

                for loop_idx in poly.loop_indices:
                    #uv_layer.data[loop_idx].uv.x *= uv_rescale
                    uv_layer.data[loop_idx].uv *= uv_scale
                    uv_layer.data[loop_idx].uv += Vector((uvs[uv_index][0]+current_map_index, uvs[uv_index][1])) # .translate the data[].uv instead?
                    uv_layer.data[loop_idx].uv.x *= uv_rescale


            # self.report({'INFO'}, f"Baking lightmaps. This may take a while.")
            print(f"Baking lightmaps. This may take a while.")
            bpy.ops.object.bake(type='DIFFUSE')

            #return {'FINISHED'}
        

        if method == 1: # convert one at a time, setup uvs, merge

            new_collection = bpy.data.collections.get("meshes_for_lightmaps")
            if new_collection is None:
                bpy.data.collections.new("meshes_for_lightmaps")
                new_collection = bpy.data.collections.get("meshes_for_lightmaps")
            if "meshes_for_lightmaps" not in bpy.context.scene.collection.children:
                bpy.context.scene.collection.children.link(new_collection)

            current_map_index = 0 # texture index

            graph = bpy.context.evaluated_depsgraph_get()
            
            for i, patch in enumerate(patches):

                if i < cap:
                    # if patch.visible_get() == True: # maybe I can exclude the entire collection instead
                    #     patch.hide_set(True)        # and do the new mesh in another collection

                    if i % res*2 == 0:
                        image = getset_image(f"0.1.bake{current_map_index}", res, res)
                        current_map_index += 1

                    mesh = bpy.data.meshes.new_from_object(patch.evaluated_get(graph))
                    uv_layer = mesh.uv_layers.new(name="UVMap.Lightmap")
                    uv_layer.active_render = True
                    mesh.uv_layers.active = uv_layer


                    new_obj = bpy.data.objects.new(patch.name+'.lightmapper', mesh)
                    new_obj.matrix_world = patch.matrix_world
                    new_obj.color = patch.color
                    new_collection.objects.link(new_obj)

                    new_obj.select_set(True)

                    # edit UVs
                    for poly in mesh.polygons:
                        for vtx_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                            uv_layer.data[loop_idx].uv *= uv_scale
                            uv_layer.data[loop_idx].uv += Vector((uvs[i][0], uvs[i][1])) # .translate the data[].uv instead?
                            
                
                    #mesh.uv_layers[0].active_render = True # set back to first UV layer after baking, can be commented out
                else:
                    print("STOPPED")
                    break
                    return {'CANCELLED'}

            new_collection.objects[0].select_set(True)
            bpy.context.view_layer.objects.active = new_collection.objects[0]

            outliner = find_layer_collection(bpy.context.view_layer.layer_collection, collection.name)
            outliner.exclude = True

            bpy.ops.object.join()

            #new_merged = new_collection.objects[0]

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

            bpy.ops.mesh.remove_doubles() # calculate threshold=* according to world scale

            #return {'FINISHED'}
        

        if method == 0: # one at a time

            images_to_save = []

            for i, obj in enumerate(patches):

                
                # obj.hide_viewport = False
                # obj.hide_render = False
                
                # bpy.ops.object.select_all(action = "DESELECT")

                print(i, 'of', cap, 'time elapsed:', round(time.time() - time_start, 2))

                if i < cap:

                    obj.hide_set(True)
                    # if obj.visible_get() == True:
                    #     obj.hide_set(True)

                    #bpy.ops.object.convert(target='MESH')
                    #a = obj.data.copy()
                    #print(a)

                    graph = bpy.context.evaluated_depsgraph_get()
                    obj_eval = obj.evaluated_get(graph)
                    mesh = bpy.data.meshes.new_from_object(obj_eval)

                    new_obj = bpy.data.objects.new(obj.name+'.lightmapper', mesh)
                    new_obj.matrix_world = obj.matrix_world
                    # new_obj.color = obj.color
                    collection.objects.link(new_obj)

                    new_obj.select_set(True)
                    bpy.context.view_layer.objects.active = new_obj # for bpy.ops.object.bake()

                    try:
                        mat = new_obj.material_slots[0].material
                    except:
                        self.report({'ERROR'}, f"No surface patch material applied to {obj.name}")
                        return {'CANCELLED'}

                    nodes = mat.node_tree.nodes
                    bake_node = nodes["Bake"]

                    #for node in nodes:
                    #    node.select = False
                    bake_node.select = True
                    nodes.active = bake_node

                    image = getset_image(f"0.0.bake{i}", 8, 8)
                    bake_node.image = image

                    # image = bake_node.image

                    print(image.name)
                    bpy.ops.object.bake(type='DIFFUSE')
                    images_to_save.append(image)

                    

                else:
                    print("STOPPED")
                    break
                    # return {'CANCELLED'}

            from pathlib import Path

            print("\nSaving to disk")
            for i, image in enumerate(images_to_save):
                print(image.name)
                image.save_render(f"{str(Path.home())}/Downloads/BXTools_Lightmap/bake{i}.png")
                #image.filepath = f"X:/Downloads/bx_test/lightmaps/bake{i}.png"
                #image.save()



        time_taken = round(time.time() - time_start, 5)
        print(f"Finished in {time_taken} seconds.")


        minutes = time_taken / 60

        #print(round(minutes, 4))

        time_per_cap = minutes
        time_per_object = time_per_cap / cap
        total_time = time_per_object * 4000

        print('estimated = ', round(total_time, 4), 'minutes')
        print('estimated = ', round(total_time / 60, 4), 'hours')
        return {"FINISHED"}