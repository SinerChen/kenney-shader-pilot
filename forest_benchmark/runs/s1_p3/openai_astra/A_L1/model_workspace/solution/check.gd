extends Node3D

func _ready() -> void:
	call_deferred("check")

func check() -> void:
	var a = get_parent().adapter
	var sample = {"points":[[0.0,0.0,0.0],[0.5,0.0,0.0],[1.0,0.0,0.0]],"origin_ref":[0.0,0.0,0.0],"time":1.0,"t0":0.0,"R0":0.0,"speed":0.5,"noise_amplitude":0.0,"width":0.1,"enabled":true}
	var result = a.query("burn_query",sample)
	if result.status == "OK":
		var data = result.device.buffer_get_data(result.buffer).to_float32_array()
		print("BURN_QUERY_CHECK shape=",result.shape," data=",data)
		assert(abs(data[1]+0.5)<0.00001 and data[2]==1.0 and data[3]==0.0)
		assert(abs(data[5])<0.00001 and abs(data[6]-0.5)<0.00001 and data[7]==1.0)
		assert(abs(data[9]-0.5)<0.00001 and data[10]==0.0 and data[11]==0.0)
		sample.enabled = false
		var off = a.query("burn_query",sample)
		var off_data = off.device.buffer_get_data(off.buffer).to_float32_array()
		for i in range(3): assert(off_data[i*4+2]==0.0 and off_data[i*4+3]==0.0)
		print("BURN_QUERY_CHECK PASS: radius, smooth masks, disabled and GPU layout")
	else:
		push_error("BURN_QUERY_CHECK "+str(result))
	print("SCENE_PROTECTION ",get_parent().protection_report().status)
