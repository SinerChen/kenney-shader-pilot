extends RefCounted
# Called synchronously inside damage(): RayCast still contains this pellet's
# spread and collision result. Never force an update or change the host ray.
static func recover(root: Node, receiver, camera: Camera3D, target: Node3D) -> Dictionary:
    var ray: RayCast3D = root.get_node_or_null("Player/Head/Camera/RayCast")
    var origin := camera.global_position
    var direction := -camera.global_basis.z
    if ray != null and ray.is_colliding():
        var collider = ray.get_collider()
        if collider != target and not target.is_ancestor_of(collider): return {}
        origin = ray.global_position
        direction = (ray.to_global(ray.target_position)-origin).normalized()
    var hit: Dictionary = receiver.trace(origin,direction)
    if hit.is_empty(): return {}
    if hit.node != target and not target.is_ancestor_of(hit.node): return {}
    return {"local_position":target.to_local(hit.position),"local_normal":(target.global_basis.transposed()*hit.normal).normalized()}
