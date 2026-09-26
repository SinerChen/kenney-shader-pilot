extends SceneTree

var evidence_dir = ""
var serial = 0

func _initialize():
	call_deferred("run")

func encode(value):
	if value is Dictionary:
		if value.get("status","") == "OK" and value.has("buffer") and value.has("device"):
			if not value.device is RenderingDevice or not value.buffer is RID:
				return {"status":"ERROR","error":"not an actual GPU resource"}
			var bytes: PackedByteArray = value.device.buffer_get_data(value.buffer)
			var expected_size = int(value.shape[0])*int(value.shape[1])*4
			if bytes.size() != expected_size:
				return {"status":"ERROR","error":"GPU buffer shape mismatch"}
			serial += 1
			var name = "gpu_%04d.f32" % serial
			var file = FileAccess.open(evidence_dir.path_join(name),FileAccess.WRITE)
			file.store_buffer(bytes)
			return {"status":"OK","file":name,"shape":value.shape,"fields":value.fields,"dtype":"<f4","time":value.get("time",0),"origin":"actual_gpu_readback"}
		if value.get("status","") == "OK" and value.has("texture") and value.texture is Texture2D:
			var image = value.texture.get_image()
			if image.get_format() not in [Image.FORMAT_RF,Image.FORMAT_RGF,Image.FORMAT_RGBF,Image.FORMAT_RGBAF]:
				return {"status":"ERROR","error":"numeric texture must have float32 channels"}
			serial += 1
			var name = "gpu_%04d.f32" % serial
			var file = FileAccess.open(evidence_dir.path_join(name),FileAccess.WRITE)
			file.store_buffer(image.get_data())
			return {"status":"OK","file":name,"shape":value.shape,"fields":value.fields,"dtype":"<f4","origin":"actual_gpu_texture_readback"}
		if value.get("status","") != "EMPTY" and (value.has("origin") or value.has("file") or value.has("shape")):
			return {"status":"ERROR","error":"Numeric evidence requires an actual GPU resource, not a file descriptor"}
		var out = {}
		for key in value:
			if key not in ["device","buffer","texture"]: out[key]=encode(value[key])
		return out
	if value is Array:
		var out: Array = []
		for item in value: out.append(encode(item))
		return out
	if value is Object or value is RID: return {"status":"ERROR","error":"unregistered resource"}
	return value

func run():
	var args = OS.get_cmdline_user_args()
	if args.size() != 2:
		push_error("runner requires request.json and output directory")
		quit(2)
		return
	evidence_dir = args[1]
	DirAccess.make_dir_recursive_absolute(evidence_dir)
	var request = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var script = load("res://solution/adapter.gd")
	if script == null:
		quit(3)
		return
	var adapter = script.new()
	root.add_child(adapter)
	var responses: Array = []
	for command in request.commands:
		var op = command.op
		var response
		match op:
			"reset": response=adapter.reset(command.config)
			"advance": response=adapter.advance(float(command.dt),command.get("events",[]))
			"query": response=adapter.query(command.name,command.get("payload",{}))
			"outputs": response=adapter.get_outputs()
			_: response={"status":"ERROR","error":"unknown command"}
		responses.append(encode(response))
		if response is Dictionary and response.get("status","OK") not in ["OK","EMPTY"]:
			break
	var report = {"responses":responses,"engine":Engine.get_version_info(),"gpu":RenderingServer.get_video_adapter_name()}
	var file = FileAccess.open(evidence_dir.path_join("result.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	adapter.dispose()
	adapter.queue_free()
	quit()
