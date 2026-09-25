extends RefCounted
static func arr(p: Vector3) -> Array: return [p.x,p.y,p.z]

# Reverse-Z reference, near=1 far=0, independent of renderer clip conventions.
static func reverse_depth(z: float, camera: Camera3D) -> float:
    if camera.projection == Camera3D.PROJECTION_ORTHOGONAL:
        return (camera.far-z)/(camera.far-camera.near)
    return (camera.near*camera.far/z-camera.near)/(camera.far-camera.near)

static func capture(effect: Node) -> Dictionary:
    var camera: Camera3D = effect.get_viewport().get_camera_3d()
    var size: Vector2 = effect.get_viewport().get_visible_rect().size
    var pixels: Array = []
    var inv: Transform3D = effect.projector.affine_inverse()
    var settings: Dictionary = effect.test_input.projector
    var ink: Vector3 = effect.v(settings.albedo_linear)
    var projector_normal: Vector3 = (effect.projector.basis.inverse().transposed()*Vector3.BACK).normalized()
    for y in 128:
        for x in 128:
            var screen := Vector2((x+0.5)/128.0,(y+0.5)/128.0)*size
            var origin := camera.project_ray_origin(screen)
            var direction := camera.project_ray_normal(screen)
            var hit: Dictionary = effect.receiver.trace(origin,direction)
            var row := {"visible":false,"world_position":null,"projector_local_position":null,"uv":null,"opacity":0.0,"normal":null,"albedo_linear":null}
            if not hit.is_empty():
                var world: Vector3 = hit.position
                var view: Vector3 = camera.global_transform.affine_inverse()*world
                var depth := reverse_depth(-view.z,camera)
                if depth >= 0.0 and depth <= 1.0:
                    var local: Vector3 = inv*world
                    var normal: Vector3 = hit.normal
                    var opacity := 0.0
                    if effect.active and (effect.target == hit.node or effect.target.is_ancestor_of(hit.node)) and maxf(absf(local.x),maxf(absf(local.y),absf(local.z))) <= 0.5:
                        var cosine := normal.dot(projector_normal)
                        var t := clampf((cosine-float(settings.cos_reject))/maxf(0.000001,float(settings.cos_full)-float(settings.cos_reject)),0.0,1.0)
                        opacity = float(settings.opacity)*t*t*(3.0-2.0*t)
                    var base: Vector3 = effect.receiver.color_at(hit)
                    var color := base.lerp(ink,opacity)
                    row = {"visible":true,"world_position":arr(world),"projector_local_position":arr(local),"uv":[local.x+0.5,local.y+0.5],"opacity":opacity,"normal":arr(normal),"albedo_linear":arr(color)}
            pixels.append(row)
    preload("res://effect/audit.gd").inspect(effect,pixels)
    return {"step":effect.frame,"elapsed_s":effect.elapsed,"active_target":effect.test_input.hit.target if effect.active else null,"pixel_data":pixels}
