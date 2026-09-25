extends RefCounted
var faces: Array = []
var textures: Dictionary = {}

func collect(root: Node) -> void:
    faces.clear()
    textures.clear()
    for node in root.find_children("*", "MeshInstance3D", true, false):
        # Item-camera geometry belongs to a separate viewport, not world occlusion.
        if node.mesh == null or node.get_viewport() != root.get_viewport(): continue
        for surface in node.mesh.get_surface_count():
            var arrays = node.mesh.surface_get_arrays(surface)
            var vertices = arrays[Mesh.ARRAY_VERTEX]
            var normals = arrays[Mesh.ARRAY_NORMAL]
            var uvs = arrays[Mesh.ARRAY_TEX_UV]
            var indices = arrays[Mesh.ARRAY_INDEX]
            # Snapshot the actual original binding before installing the effect.
            var material = node.get_active_material(surface)
            var count: int = indices.size() if indices != null and indices.size() > 0 else vertices.size()
            for t in range(0, count, 3):
                var ps: Array = []
                var ns: Array = []
                var ts: Array = []
                for k in 3:
                    var i: int = indices[t+k] if indices != null and indices.size() > 0 else t+k
                    ps.append(vertices[i])
                    ns.append(normals[i] if normals != null and normals.size() > 0 else Vector3.ZERO)
                    ts.append(uvs[i] if uvs != null and uvs.size() > 0 else Vector2.ZERO)
                faces.append({"lp":ps,"ln":ns,"p":[],"n":[],"uv":ts,"material":material,"node":node})
    refresh()
    print("RECEIVER triangles=", faces.size())

func refresh() -> void:
    var transforms: Dictionary = {}
    for face in faces:
        var node: MeshInstance3D = face.node
        if not is_instance_valid(node): continue
        if not transforms.has(node):
            transforms[node] = [node.global_transform, node.global_basis.inverse().transposed()]
        var transform: Transform3D = transforms[node][0]
        var normals: Basis = transforms[node][1]
        face.p = [transform * face.lp[0], transform * face.lp[1], transform * face.lp[2]]
        face.n = [(normals * face.ln[0]).normalized(), (normals * face.ln[1]).normalized(), (normals * face.ln[2]).normalized()]

func trace(origin: Vector3, direction: Vector3, only: Node = null) -> Dictionary:
    var distance := INF
    var result: Dictionary = {}
    for face in faces:
        if not is_instance_valid(face.node) or not face.node.is_visible_in_tree(): continue
        if only != null and not only.is_ancestor_of(face.node) and only != face.node: continue
        var a: Vector3 = face.p[0]
        var e1: Vector3 = face.p[1] - a
        var e2: Vector3 = face.p[2] - a
        var h := direction.cross(e2)
        var det := e1.dot(h)
        if absf(det) < 0.0000001: continue
        var s := origin - a
        var u := s.dot(h) / det
        if u < -0.000001 or u > 1.000001: continue
        var q := s.cross(e1)
        var w := direction.dot(q) / det
        if w < -0.000001 or u+w > 1.000001: continue
        var d := e2.dot(q) / det
        if d <= 0.0 or d >= distance: continue
        var normal: Vector3 = (face.n[0]*(1.0-u-w) + face.n[1]*u + face.n[2]*w).normalized()
        if normal.length_squared() < 0.1: normal = e1.cross(e2).normalized()
        var mat = face.material
        var cull := BaseMaterial3D.CULL_BACK
        if mat is BaseMaterial3D: cull = mat.cull_mode
        if cull == BaseMaterial3D.CULL_BACK and normal.dot(direction) >= 0.0: continue
        if cull == BaseMaterial3D.CULL_FRONT and normal.dot(direction) <= 0.0: continue
        distance = d
        result = {"position":origin+direction*d,"normal":normal,"uv":face.uv[0]*(1.0-u-w)+face.uv[1]*u+face.uv[2]*w,"material":face.material,"node":face.node,"distance":d}
    return result

func color_at(hit: Dictionary) -> Vector3:
    var mat = hit.material
    if not mat is BaseMaterial3D: return Vector3.ONE
    var color: Color = mat.albedo_color.srgb_to_linear()
    if mat.albedo_texture != null:
        var id: int = mat.albedo_texture.get_instance_id()
        if not textures.has(id):
            var image: Image = mat.albedo_texture.get_image()
            if image.is_compressed(): image.decompress()
            textures[id] = image
        var image: Image = textures[id]
        var uv: Vector2 = hit.uv * Vector2(mat.uv1_scale.x,mat.uv1_scale.y) + Vector2(mat.uv1_offset.x,mat.uv1_offset.y)
        var x := posmod(int(floor(uv.x*image.get_width())), image.get_width())
        var y := posmod(int(floor(uv.y*image.get_height())), image.get_height())
        color *= image.get_pixel(x,y).srgb_to_linear()
    return Vector3(color.r,color.g,color.b)
