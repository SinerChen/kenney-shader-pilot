extends RefCounted
static func arr(p: Vector3) -> Array:
    return [p.x,p.y,p.z]

static func capture(effect: Node) -> Dictionary:
    var camera: Camera3D = effect.get_viewport().get_camera_3d()
    var size: Vector2 = effect.get_viewport().get_visible_rect().size
    var pixels: Array = []
    var inv: Transform3D = effect.projector.affine_inverse()
    var settings: Dictionary = effect.test_input.projector
    var ink := Vector3(settings.albedo_linear[0],settings.albedo_linear[1],settings.albedo_linear[2])
    var affected := 0
    var visible := 0
    for y in 128:
        for x in 128:
            var screen := Vector2((x+0.5)/128.0, (y+0.5)/128.0)*size
            var origin := camera.project_ray_origin(screen)
            var direction := camera.project_ray_normal(screen)
            var hit: Dictionary = effect.receiver.trace(origin,direction)
            var row := {"visible":false,"world_position":null,"projector_local_position":null,"uv":null,"opacity":0.0,"normal":null,"albedo_linear":null}
            if not hit.is_empty():
                var world: Vector3 = hit.position
                var view: Vector3 = camera.global_transform.affine_inverse()*world
                var distance := -view.z
                if distance >= camera.near and distance <= camera.far:
                    # Analytical raster-equivalent reverse-Z depth, reconstructed via
                    # the inverse camera projection. CPU reference avoids GPU stalls.
                    var projection := camera.get_camera_projection()
                    var clip: Vector4 = projection * Vector4(view.x,view.y,view.z,1.0)
                    var depth := (clip.z/clip.w)*0.5+0.5
                    var reverse_depth := 1.0-depth
                    var reconstructed: Vector4 = projection.inverse()*Vector4(clip.x/clip.w,clip.y/clip.w, (1.0-reverse_depth)*2.0-1.0,1.0)
                    world = camera.global_transform*(Vector3(reconstructed.x,reconstructed.y,reconstructed.z)/reconstructed.w)
                    var local: Vector3 = inv*world
                    var normal: Vector3 = hit.normal
                    var opacity := 0.0
                    if effect.active and effect.target.is_ancestor_of(hit.node) and absf(local.x)<=0.5 and absf(local.y)<=0.5 and absf(local.z)<=0.5:
                        var cosine := normal.dot(effect.projector.basis.z.normalized())
                        var t := clampf((cosine-float(settings.cos_reject))/(float(settings.cos_full)-float(settings.cos_reject)),0.0,1.0)
                        opacity = float(settings.opacity)*t*t*(3.0-2.0*t)
                    var base: Vector3 = effect.receiver.color_at(hit)
                    var color := base.lerp(ink,opacity)
                    row = {"visible":true,"world_position":arr(world),"projector_local_position":arr(local),"uv":[local.x+0.5,local.y+0.5],"opacity":opacity,"normal":arr(normal),"albedo_linear":arr(color)}
                    visible += 1
                    if opacity > 0.0:
                        affected += 1
            pixels.append(row)
    print("PIXELS step=",effect.frame," visible=",visible," affected=",affected," active=",effect.active)
    return {"step":effect.frame,"elapsed_s":effect.elapsed,"active_target":effect.test_input.hit.target if effect.active else null,"pixel_data":pixels}
