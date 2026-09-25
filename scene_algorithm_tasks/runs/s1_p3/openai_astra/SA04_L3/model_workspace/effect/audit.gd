extends RefCounted
static func inspect(effect: Node, pixels: Array) -> void:
    var visible := 0
    var affected := 0
    var malformed := 0
    for row in pixels:
        if row.visible: visible += 1
        if row.opacity > 0.0: affected += 1
        if not row.visible and (row.world_position != null or row.projector_local_position != null or row.uv != null or row.normal != null or row.opacity != 0.0): malformed += 1
    print("PIXELS step=",effect.frame," count=",pixels.size()," visible=",visible," affected=",affected," bad_background=",malformed," active=",effect.active," anchor=",effect.projector.origin)
    if effect.frame != 1: return
    for name_string in ["TargetA","TargetB","TargetC","Cover"]:
        var node = effect.scene_root.get_node_or_null("World/"+name_string)
        if node == null: continue
        var meshes: Array = node.find_children("*","MeshInstance3D",true,false)
        if node is MeshInstance3D: meshes.append(node)
        var count := 0
        var bound := 0
        for mesh in meshes:
            if mesh.mesh == null: continue
            count += mesh.mesh.get_surface_count()
            for s in mesh.mesh.get_surface_count():
                var mat: Material = mesh.get_active_material(s)
                while mat != null:
                    if mat in effect.materials: bound += 1
                    mat = mat.next_pass
        print("BINDING ",name_string," surfaces=",count," ink_passes=",bound)
    var overlaps := 0
    var inv: Transform3D = effect.projector.affine_inverse()
    for face in effect.receiver.faces:
        if not effect.target.is_ancestor_of(face.node): continue
        var lo := Vector3(INF,INF,INF)
        var hi := -lo
        for p in face.p:
            var local: Vector3 = inv*p
            lo = lo.min(local)
            hi = hi.max(local)
        if lo.x<=0.5 and lo.y<=0.5 and lo.z<=0.5 and hi.x>=-0.5 and hi.y>=-0.5 and hi.z>=-0.5:
            overlaps += 1
            print("BOX_CANDIDATE normal=",face.n[0])
    print("BOX_CANDIDATES=",overlaps)
