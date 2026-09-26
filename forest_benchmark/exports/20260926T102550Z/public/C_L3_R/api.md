# L3 接口

保留前级 reset(config)、advance(dt, events)、query(name, payload)、get_outputs()。新增 bind_scene(scene_access, task_config) 与 detach_scene()。空接入返回 UNIMPLEMENTED_BINDING。

scene_access 提供 source_node(path)、bind_material(path, surface, material)、add_effect(node)、camera()、input_texture(name)、publish_input(name, texture) 和 detach_bindings()。源节点和资源用于读取；允许修改的表面由 permissions.json 限定。输入槽不生成背景捕获。

原 L2 舞台及其节点不再存在，不能调用继承的 mount() 来假定它们存在。前级核心仍在 solution 中。public/sample_inputs/sample.json 是固定的前级开发输入输出；场景接入的配置尚未校准时不能正式投放。
