extends Node3D

var source: Node
var access: Node
var adapter: Node
var task: Dictionary
var startup: Dictionary={"status":"UNIMPLEMENTED_BINDING"}
var demo: Dictionary
var tick:=0

func _ready():
	task=_host_config("task.json")
	demo=_host_config("development.json")
	source=load(task.original_entry_scene).instantiate()
	add_child(source)
	var effects=Node3D.new()
	effects.name="EffectRoot"
	add_child(effects)
	access=load("res://fixture/scene_access.gd").new()
	add_child(access)
	access.setup(source,effects,_host_config("permissions.json"))
	adapter=load("res://solution/adapter.gd").new()
	add_child(adapter)
	adapter.reset(demo.core_config)
	if not get_tree().root.has_meta("benchmark_defer_binding"):
		bind_scene()

func bind_scene():
	startup=adapter.bind_scene(access,task)

func step(dt: float, events: Array) -> Dictionary:
	if startup.get("status")!="OK":return startup
	var result=adapter.advance(dt,events)
	tick+=1
	adapter.update_display()
	return result

func _process(_delta):
	if get_tree().root.has_meta("benchmark_manual"):return
	var events=[]
	for item in demo.events:
		if item.tick==tick:events.append(item.event)
	step(demo.dt,events)

func _exit_tree():
	if is_instance_valid(adapter):
		adapter.detach_scene()
		adapter.dispose()

func _host_config(name: String) -> Dictionary:
	var project_dir = ProjectSettings.globalize_path("res://").trim_suffix("/")
	var path = project_dir.get_base_dir().path_join("public").path_join(project_dir.get_file()).path_join(name)
	return JSON.parse_string(FileAccess.get_file_as_string(path))
