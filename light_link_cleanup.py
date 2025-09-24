import bpy

bl_info = {
    "name": "Light Linking Cleaner",
    "blender": (4, 4, 3),
    "category": "Object",
    "author": "Antoine Claude"
}

def get_light_linking(light_obj):
    """Retourne un dict avec les receivers et blockers de la lampe donnée."""
    result = {"receivers": [], "blockers": []}
    
    if light_obj.type != 'LIGHT':
        raise TypeError(f"{light_obj.name} n'est pas une lampe")
    
    # Receivers
    recv_col = light_obj.light_linking.receiver_collection
    if recv_col:
        result["receivers"] = [obj.name for obj in recv_col.objects]
    
    # Blockers
    block_col = light_obj.light_linking.blocker_collection
    if block_col:
        result["blockers"] = [obj.name for obj in block_col.objects]
    
    return result

class EWM_OT_CleanCollections(bpy.types.Operator):
    bl_idname = "ewm.clean_light_linking"
    bl_label = "Clean Light Linking"

    def execute(self, context):
        selected_lights = [obj for obj in context.selected_objects if obj.type == "LIGHT"]

        if not selected_lights:
            self.report({'ERROR'}, "Select at least one light in the scene")
            return {'CANCELLED'}

        cleaned = 0
        to_remove = set()
        link_states = {}  # sauvegarde des états

        # --- Étape 1 : on remplace et on stocke les états ---
        for light in selected_lights:
            for link_type in ["receiver_collection", "blocker_collection"]:
                col = getattr(light.light_linking, link_type)
                if col:
                    base_name = col.name.split(".")[0]
                    target_col = bpy.data.collections.get(base_name)

                    if target_col and target_col != col:
                        # --- sauvegarde des états avant remplacement ---
                        state_data = {
                            "objects": [(obj.name, col_obj.light_linking.link_state)
                                        for obj, col_obj in zip(col.objects, col.collection_objects)],
                            "collections": [(child.name, col_child.light_linking.link_state)
                                            for child, col_child in zip(col.children, col.collection_children)]
                        }
                        link_states[(light.name, link_type)] = state_data

                        # --- remplace par la nouvelle collection ---
                        setattr(light.light_linking, link_type, target_col)

                        # marque l’ancienne pour suppression
                        to_remove.add(col)

            cleaned += 1

        # --- Étape 2 : réapplique les états sur les nouvelles collections ---
        for light in selected_lights:
            for link_type in ["receiver_collection", "blocker_collection"]:
                key = (light.name, link_type)
                if key in link_states:
                    state_data = link_states[key]
                    new_col = getattr(light.light_linking, link_type)

                    # objets
                    for obj, col_obj in zip(new_col.objects, new_col.collection_objects):
                        for saved_name, saved_state in state_data["objects"]:
                            if obj.name == saved_name[:-4]:
                                col_obj.light_linking.link_state = saved_state

                    # sous-collections
                    for child, col_child in zip(new_col.children, new_col.collection_children):
                        for saved_name, saved_state in state_data["collections"]:
                            if child.name == saved_name[:-4]:
                                col_child.light_linking.link_state = saved_state

        # --- Étape 3 : une fois toutes les lights traitées, on supprime ---
        for col in to_remove:
            for obj in list(col.objects):  # list() pour éviter de boucler sur une collection modifiée
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)


        collections_in_scene = [c for c in bpy.data.collections if bpy.context.scene.user_of_id(c)]

        # Exemple : partir de la première collection de l'objet actif
        coll = bpy.context.object.users_collection[0]

        # Trouver les collections parentes qui contiennent `coll`
        parents = [c for c in collections_in_scene if c.user_of_id(coll)]

        if parents:
            parent = parents[0]

            # Supprime objets sauf lights sélectionnées
            selected_lights = [obj for obj in bpy.context.selected_objects if obj.type == "LIGHT"]
            for obj in list(parent.objects):  # list() = éviter modification en cours de boucle
                if obj not in selected_lights:
                    bpy.data.objects.remove(obj, do_unlink=True)

            # Supprime les sous-collections
            for subcol in list(parent.children):
                if subcol != coll :
                    bpy.data.collections.remove(subcol)

        for light in selected_lights :
            parent.objects.link(light)
            coll.objects.unlink(light)
        bpy.data.collections.remove(coll)

        
        self.report({'INFO'}, f"Cleaned {cleaned} light(s), restored link states, removed {len(to_remove)} collections")
        return {'FINISHED'}


class EWM_PT_UI(bpy.types.Panel):
    bl_label = "Light Linking Tools"
    bl_idname = "EWM_PT_light_linking"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "EWM"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Sélectionne tes light append et lance ! :")
        layout.operator("ewm.clean_light_linking")


classes = (EWM_OT_CleanCollections, EWM_PT_UI)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
