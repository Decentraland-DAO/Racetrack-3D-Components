bl_info = {
    # required
    'name': 'Vegas City RaceTrack Addon',
    'blender': (2, 80, 0),
    'category': 'Object',
    # optional
    'version': (1, 0, 0),
    'author': 'Karim Machlab',
    'description': 'Addon to assist in managing and exporting racetrack data.',
}

# imports
import bpy
import math
import mathutils
import re
import json

# define constants
rad_2_deg = 180 / math.pi

# define properties
PROPS = [
    (
        'track_name',
        bpy.props.StringProperty(
            name = 'Name',
            default = 'track_01',
            description='The export name for the race track.'
        )
    )
]

# class to handle the "export data" operation
class ExportDataOperator(bpy.types.Operator):
    
    # metadata
    bl_idname = 'opr.export_data_operator'
    bl_label = 'Export Data'
    
    # main method
    def execute(self, context):
        
        # construct an output filepath based on the current blender file
        filepath = bpy.data.filepath.split("\\")
        output_path = ""
        for i in range(len(filepath) - 2):
            output_path += filepath[i] + "\\"
        glb_path = "models/tracks/" + context.scene.track_name + ".glb"
        output_path += "Blender\\data\\" + context.scene.track_name + ".json"

        # Data to be written
        outputData = {
            "name": context.scene.track_name,
            "glb": glb_path,
            "track": [],
            "hotspots": []
        }

        # keep track of all objects being exported
        object_list = []

        # keep track of all dynamic objects being exported
        object_list_dynamic = []

        # find hole we want to export
        for col in bpy.data.collections:
            
            # find the collection holding the track
            if (col.name.lower() == "track"):
                
                # grab and iterate the mesh objects in the collection
                sel_objs = [obj for obj in col.objects if obj.type == 'MESH']
                for obj in sel_objs:

                    trackData = {
                        "polygon": []
                    }

                    vertices = []
                    indices = []

                    # ensure mesh data is triangulated
                    mesh = obj.data
                    mesh.calc_loop_triangles()

                    # grab the vertices
                    index = 0
                    for vert in mesh.vertices:
                        co_final = obj.matrix_world @ vert.co
                        x = -co_final.x
                        y = co_final.z
                        z = -co_final.y
                        v = mathutils.Vector((x, y, z))

                        vertices.append(v)
                        indices.append(index)
                        index = index + 1

                    polygon = sort_radial_sweep(vertices, indices)
                    for p in polygon:
                        v = vertices[p]

                        trackData["polygon"].append({
                            "x": str(v.x),
                            "y": str(v.y),
                            "z": str(v.z)
                        })

                    outputData["track"].append(trackData)

            # find the collection holding the hotspots
            if (col.name.lower() == "hotspots"):
                
                # grab and iterate the mesh objects in the collection
                sel_objs = [obj for obj in col.objects if obj.type == 'MESH']
                for obj in sel_objs:

                    hotspotData = {
                        "hotspotType": "none",
                        "polygon": []
                    }

                    if "hotspotType" in obj:
                        hotspotData["hotspotType"] = str(obj["hotspotType"])

                    vertices = []
                    indices = []

                    # ensure mesh data is triangulated
                    mesh = obj.data
                    mesh.calc_loop_triangles()

                    # grab the vertices
                    index = 0
                    for vert in mesh.vertices:
                        co_final = obj.matrix_world @ vert.co
                        x = -co_final.x
                        y = co_final.z
                        z = -co_final.y
                        v = mathutils.Vector((x, y, z))

                        vertices.append(v)
                        indices.append(index)
                        index = index + 1

                    polygon = sort_radial_sweep(vertices, indices)
                    for p in polygon:
                        v = vertices[p]

                        hotspotData["polygon"].append({
                            "x": str(v.x),
                            "y": str(v.y),
                            "z": str(v.z)
                        })

                    outputData["hotspots"].append(hotspotData)
                        
            # find the collection holding the cannon data
            elif (col.name.lower() == "obstacles"):
                
                # grab and iterate the mesh objects in the collection
                sel_objs = [obj for obj in col.objects if obj.type == 'MESH']
                for obj in sel_objs:

                    # leave a line between each mesh
                    #if not is_first:
                        #output += "\n\n"
                    is_first = False
                    
                    # grab the position
                    pos_x = -obj.location.x
                    pos_y = obj.location.z
                    pos_z = -obj.location.y
                    
                    # grab the rotation
                    rot_x = -obj.rotation_euler.x * rad_2_deg
                    rot_y = -obj.rotation_euler.z * rad_2_deg
                    rot_z = obj.rotation_euler.y * rad_2_deg

                    # grab the scale
                    sca_x = obj.scale.x
                    sca_y = obj.scale.z
                    sca_z = obj.scale.y
                    
                    # normalize the name
                    obj.name = re.sub(
                        "[^a-zA-Z0-9]",
                        "_",
                        obj.name
                    )
                    
                    # check for a plane/quad
                    if (obj.name.lower().startswith("plane") or obj.name.lower().startswith("quad")):
                        
                        # start output for the object
                        if(obj.name.lower().endswith("dynamic")):
                            object_list_dynamic.append(obj.name)
                        else:
                            object_list.append(obj.name)
                        #output += "export const " + obj.name + " = new crazygolf.shapes.PlaneShapeDefinition({\n"
                        
                        # output the sphere data
                        #output += "\tposition: new Vector3(" + str(pos_x) + ", " + str(pos_y) + ", " + str(pos_z) + "),\n"
                        #output += "\trotation: Quaternion.Euler(" + str(rot_x) + ", " + str(rot_y) + ", " + str(rot_z) + ")\n"
                        
                        # end output for the object
                        #output += "})"
                        
                    # check for a cube/box
                    elif (obj.name.lower().startswith("cube") or obj.name.lower().startswith("box")):
                        
                        # set origin to geometry
                        obj.select_set(state=True)
                        context.view_layer.objects.active = obj
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
                        
                        # check the vertices for edits - identify the bounds in local space
                        # NOTE : this won't necessarily handle well when edits other than moving faces along their normals have been made, making the shape no longer a AABB
                        min_x = 999
                        min_y = 999
                        min_z = 999
                        max_x = -999
                        max_y = -999
                        max_z = -999
                        for vert in obj.data.vertices:
                            if (vert.co.x < min_x):
                                min_x = vert.co.x
                            if (vert.co.x > max_x):
                                max_x = vert.co.x
                            if (vert.co.y < min_y):
                                min_y = vert.co.y
                            if (vert.co.y > max_y):
                                max_y = vert.co.y
                            if (vert.co.z < min_z):
                                min_z = vert.co.z
                            if (vert.co.z > max_z):
                                max_z = vert.co.z
                        
                        # work out the overall size, when combined with object scale
                        sca_x *= (max_x - min_x)
                        sca_y *= (max_z - min_z)
                        sca_z *= (max_y - min_y)
                        
                        # work out a position offset based on center point of vertices
                        off_x = (max_x + min_x) / 2
                        off_y = (max_y + min_y) / 2
                        off_z = (max_z + min_z) / 2
                        
                        # adjust the offset based on object tranform
                        off = obj.matrix_world @ mathutils.Vector((off_x, off_y, off_z))
                        
                        # apply the offset
                        #pos_x += -off.x
                        #pos_y += off.z
                        #pos_z += -off.y
                        
                        # start output for the object
                        if(obj.name.lower().endswith("dynamic")):
                            object_list_dynamic.append(obj.name)
                        else:
                            object_list.append(obj.name)
                        #output += "export const " + obj.name + " = new crazygolf.shapes.BoxShapeDefinition({\n"
                        
                        # output the sphere data
                        #output += "\tposition: new Vector3(" + str(pos_x) + ", " + str(pos_y) + ", " + str(pos_z) + "),\n"
                        #output += "\trotation: Quaternion.Euler(" + str(rot_x) + ", " + str(rot_y) + ", " + str(rot_z) + "),\n"
                        #output += "\tscale: new Vector3(" + str(sca_x) + ", " + str(sca_y) + ", " + str(sca_z) + ")\n"
                        
                        # end output for the object
                        #output += "})"

                    # check for an explicitly convex mesh
                    elif (obj.name.lower().startswith("convex")):
                        
                        # ensure mesh data is triangulated
                        mesh = obj.data
                        mesh.calc_loop_triangles()

                        # start output for the object
                        if(obj.name.lower().endswith("dynamic")):
                            object_list_dynamic.append(obj.name)
                        else:
                            object_list.append(obj.name)
                        #output += "export const " + obj.name + " = new crazygolf.shapes.ConvexShapeDefinition({\n"

                        # start the mesh data output
                        #output += "\tmeshData: {\n"
                        
                        # output the vertices
                        is_first_vert = True
                        output += "\t\tvertices: ["
                        for vert in mesh.vertices:
                            co_final = obj.matrix_world @ vert.co
                            x = -co_final.x
                            y = co_final.z
                            z = -co_final.y
                            #if not is_first_vert:
                                #output += ","
                            #else:
                                #is_first_vert = False
                            #output += "\n\t\t\t" + str(x) + ", " + str(y) + ", " + str(z)
                        #output += "\n\t\t],\n"
                        
                        # then the indices/triangles
                        is_first_index = True
                        #output += "\t\tindices: ["
                        #for tri in mesh.loop_triangles:
                            #if not is_first_index:
                            #    output += ","
                            #else:
                            #    is_first_index = False
                            #output += "\n\t\t\t" + str(tri.vertices[0]) + ", " + str(tri.vertices[1]) + ", " + str(tri.vertices[2])
                            
                        #output += "\n\t\t]\n"
                        
                        # end the mesh data output
                        #output += "\t},\n"
                        
                        # output the transform data
                        #output += "\tposition: new Vector3(" + str(pos_x) + ", " + str(pos_y) + ", " + str(pos_z) + "),\n"
                        #output += "\trotation: Quaternion.Euler(" + str(rot_x) + ", " + str(rot_y) + ", " + str(rot_z) + "),\n"
                        #output += "\tscale: new Vector3(" + str(sca_x) + ", " + str(sca_y) + ", " + str(sca_z) + ")\n"
                        
                        # end output for the object
                        #output += "})"
                                
        
        #output += "}"

        # write to the file
        print("EXPORTING DATA")
        print(output_path)
        self.report({'INFO'}, "Exported data to " + output_path)

        with open(bpy.path.abspath(output_path), 'w') as f:
            f.write(json.dumps(outputData, indent=4, sort_keys=True))
                
        # report success
        return {'FINISHED'}
        
# class to handle the "export glb" operation
class ExportGLBOperator(bpy.types.Operator):
    
    # metadata
    bl_idname = 'opr.export_glb_operator'
    bl_label = 'Export GLB'
    
    # main method
    def execute(self, context):
        
        # find the glb collection and make it active
        has_collection = False
        for layer_collection in context.view_layer.layer_collection.children:
            if (layer_collection.name.lower() == "glb"):
                context.view_layer.active_layer_collection = layer_collection
                has_collection = True
        if not has_collection:
            print("No GLB collection could be found to export")
            self.report({'ERROR'}, "No GLB collection could be found to export")
        
        # construct an output filepath based on the current blender file
        filepath = bpy.data.filepath.split("\\")
        output_path = ""
        for i in range(len(filepath) - 2):
            output_path += filepath[i] + "\\"
        output_path += "Blender\\models\\tracks\\"
        
        # construct the filename
        filename = context.scene.track_name + ".glb"
        output_path += filename
        
        # export the glb collection as the visual mesh and avatar collider
        print("EXPORTING GLB")
        print(output_path)
        self.report({'INFO'}, "Exported GLB to " + output_path)
        bpy.ops.export_scene.gltf(
            filepath = output_path,
            check_existing = False,
            export_format = "GLB",
            export_apply = True,
            export_cameras = False,
            export_selected = False,
            use_selection = False,
            use_visible = False,
            use_renderable = False,
            use_active_collection = True,
            will_save_settings = False
        )
                
        # report success
        return {'FINISHED'}
    
# class to handle custom tool panel
class RaceTrackPanel(bpy.types.Panel):
    
    # define panel data
    bl_idname = 'VIEW3D_PT_race_track'
    bl_label = 'Race Track'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    
    # method to draw the panel ui
    def draw(self, context):

        # display fields for properties
        col = self.layout.column()
        for (prop_name, _) in PROPS:
            row = col.row()
            row.prop(context.scene, prop_name)
            
        # export data button
        col.operator('opr.export_data_operator', text='Export Data')

        # export glb button
        col.operator('opr.export_glb_operator', text='Export GLB')
        
# build a list of all custom tool panels
CLASSES = [
    RaceTrackPanel,
    ExportDataOperator,
    ExportGLBOperator
]

# method to register all custom tool panels
def register():

    # register properies
    for (prop_name, prop_value) in PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)
        
    # register classes
    for klass in CLASSES:
        bpy.utils.register_class(klass)
        
# method to unregister all custom tool panels
def unregister():

    # unregister properies
    for (prop_name, _) in PROPS:
        delattr(bpy.types.Scene, prop_name)

    # unregister classes
    for klass in CLASSES:
        bpy.utils.unregister_class(klass)

# register all custom tool panels automatically as long as we're not just a dependency        
if __name__ == '__main__':
    register()

def sort_radial_sweep(vs, indices):
    """
    Given a list of vertex positions (vs) and indices
    for verts making up a circular-ish planar polygon,
    returns the vertex indices in order around that poly.
    """
    assert len(vs) >= 3
    
    # Centroid of verts
    cent = mathutils.Vector()
    for v in vs:
        cent += (1/len(vs)) * v

    # Normalized vector from centroid to first vertex
    # ASSUMES: vs[0] is not located at the centroid
    r0 = (vs[0] - cent).normalized()

    # Normal to plane of poly
    # ASSUMES: cent, vs[0], and vs[1] are not colinear
    nor = (vs[1] - cent).cross(r0).normalized()

    # Pairs of (vertex index, angle to centroid)
    vpairs = []
    for vi, vpos in zip(indices, vs):
        r1 = (vpos - cent).normalized()
        dot = r1.dot(r0)
        angle = math.acos(max(min(dot, 1), -1))
        angle *= 1 if nor.dot(r1.cross(r0)) >= 0 else -1    
        vpairs.append((vi, angle))
    
    # Sort by angle and return indices
    vpairs.sort(key=lambda v: v[1])
    return [vi for vi, angle in vpairs]