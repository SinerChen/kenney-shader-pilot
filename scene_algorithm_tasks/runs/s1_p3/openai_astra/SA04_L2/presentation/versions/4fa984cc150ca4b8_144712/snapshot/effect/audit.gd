extends RefCounted
static func inspect(effect: Node, pixels: Array) -> void:
    var visible := 0
    var affected := 0
    for row in pixels:
        if row.visible: visible += 1
        if row.opacity > 0.0: affected += 1
    print("PIXELS step=",effect.frame," visible=",visible," affected=",affected," active=",effect.active," anchor=",effect.projector.origin)
    if effect.frame != 1: return
    var lo := Vector3(INF,INF,INF)
    var hi := -lo
    var box_overlap := 0
    var inv: Transform3D = effect.projector.affine_inverse()
    for face in effect.receiver.faces:
        if not effect.target.is_ancestor_of(face.node): continue
        var fl := Vector3(INF,INF,INF)
        var fh := -fl
        for p in face.p:
            var l: Vector3 = inv*p
            lo = lo.min(l)
            hi = hi.max(l)
            fl = fl.min(l)
            fh = fh.max(l)
        if fl.x<=0.5 and fl.y<=0.5 and fl.z<=0.5 and fh.x>=-0.5 and fh.y>=-0.5 and fh.z>=-0.5:
            box_overlap += 1
            print("BOX_CANDIDATE bounds=",fl," to ",fh," normal=",face.n[0])
    print("TARGET_PROJECTOR_BOUNDS=",lo," to ",hi," box_candidates=",box_overlap)
