extends RefCounted
## World-aligned cell-centred RGBA float field. No frame history approximation.
var origin := Vector2.ZERO
var size_m := 8.0
var width := 64
var height := 64
var values := PackedFloat32Array()
var elapsed := 0.0
var frame := 0
var player_position := Vector2.ZERO
var player_velocity := Vector2.ZERO
var active := true
var config: Dictionary
var image: Image
var texture: ImageTexture

func configure(inputs: Dictionary) -> void:
	config = inputs
	origin = Vector2(inputs.patch.origin_xz_m[0], inputs.patch.origin_xz_m[1])
	size_m = float(inputs.patch.size_m)
	width = int(inputs.patch.resolution[0])
	height = int(inputs.patch.resolution[1])
	values.resize(width * height * 4)
	values.fill(0.0)
	elapsed = 0.0
	frame = 0
	update_player()
	image = Image.create_from_data(width, height, false, Image.FORMAT_RGBAF, values.to_byte_array())
	texture = ImageTexture.create_from_image(image)

func update_player() -> void:
	var keys: Array = config.player_keyframes
	var last: Array = keys[-1].position_xz_m
	player_position = Vector2(last[0], last[1])
	player_velocity = Vector2.ZERO
	for i in range(keys.size() - 1):
		var a: Dictionary = keys[i]
		var b: Dictionary = keys[i + 1]
		if elapsed < float(b.time_s):
			var p0 := Vector2(a.position_xz_m[0], a.position_xz_m[1])
			var p1 := Vector2(b.position_xz_m[0], b.position_xz_m[1])
			var duration := float(b.time_s) - float(a.time_s)
			player_velocity = (p1 - p0) / duration
			player_position = p0.lerp(p1, clampf((elapsed - float(a.time_s)) / duration, 0.0, 1.0))
			break
	# Treat the removal boundary as exclusive, including accumulated FP roundoff.
	active = elapsed < float(config.interaction_active_until_s) - 1.0e-9

func step(dt: float) -> void:
	frame += 1
	elapsed += dt
	update_player()
	var decay := pow(float(config.interaction.persistence_per_60hz_step), dt * 60.0)
	var radius := float(config.interaction.radius_m)
	var strength := float(config.interaction.strength)
	for y in range(height):
		for x in range(width):
			var index := (y * width + x) * 4
			for c in range(3):
				values[index + c] *= decay
			if not active:
				continue
			var point := origin + Vector2((float(x) + 0.5) / width, (float(y) + 0.5) / height) * size_m
			var offset := point - player_position
			var distance := offset.length()
			if distance >= radius:
				continue
			var influence := strength * pow(1.0 - distance / radius, 2.0)
			if influence > values[index + 2]:
				var direction := offset / distance if distance > 1.0e-8 else player_velocity.normalized()
				values[index] = direction.x * influence
				values[index + 1] = direction.y * influence
				values[index + 2] = influence
	image.set_data(width, height, false, Image.FORMAT_RGBAF, values.to_byte_array())
	texture.update(image)

func cell(x: int, y: int) -> Vector3:
	if x < 0 or x >= width or y < 0 or y >= height:
		return Vector3.ZERO
	var index := (y * width + x) * 4
	return Vector3(values[index], values[index + 1], values[index + 2])

func sample_at(point: Vector2) -> Vector3:
	var uv := (point - origin) / size_m
	if uv.x < 0.0 or uv.x >= 1.0 or uv.y < 0.0 or uv.y >= 1.0:
		return Vector3.ZERO
	var grid := uv * Vector2(width, height) - Vector2(0.5, 0.5)
	var x := int(floor(grid.x))
	var y := int(floor(grid.y))
	var f := grid - Vector2(x, y)
	return cell(x, y).lerp(cell(x + 1, y), f.x).lerp(cell(x, y + 1).lerp(cell(x + 1, y + 1), f.x), f.y)

func as_rows() -> Array:
	var result: Array = []
	for i in range(width * height):
		result.append([values[i * 4], values[i * 4 + 1], values[i * 4 + 2], 0.0])
	return result
