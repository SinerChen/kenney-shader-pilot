# Forest 叶面露珠试作

在原 Forest Benchmark 工程中实例化 `Main.tscn`，加入独立的露珠场景。没有修改原场景文件、植被布局、网格、贴图或原材质文件，没有调用模型 API。

## 查看

- 项目根目录双击 `Forest_Dew.cmd`：直接运行露珠场景，默认叶面近景。
- 双击 `Edit_Forest_Dew.cmd`：打开编辑器中的 `dew/ForestDew.tscn`，按 F6 运行当前场景。F5 仍按原工程的主场景运行。
- [HTML 前后对比](../../../forest-dew.html)：实际 GPU 渲染截图，可比较露珠开关、局部森林/天空反射和两个风动时刻。
- [验证记录](../../../verification/forest/dew/verification.json)、[退出状态与日志摘要](../../../verification/forest/dew/capture-status.json)。

控制：1 近景、2 整株、3 原森林视角；D 切换露珠，L 切换局部森林/仅天空反射；空格暂停风动。按住右键转动视角，右键按住时 WASD/QE 移动，Shift 加速，R 重置当前镜头。

## 实现

`ForestDew.tscn` 是变体入口，`forest_dew.gd` 负责采样、附着、相机和开关，`water.gdshader` 负责透明水滴。原工程的主场景设置保持不变。

1. 从已有 Groundcover 的蕨类 MultiMesh 中选取邻近 7 株，在三角形上按面积采样。采样 UV 的 Alpha 必须超过 0.92，并检查周围 4 个贴图点，避免在透明的叶片空隙中放水滴。水滴间保持间距，半径在 2–4.7 mm 之间；尺度按照场景世界单位理解。
2. 7 株各 650 颗，加上近景叶面的 140 颗，共 4,690 颗。使用一个 MultiMesh，共享水滴球冠形状和材质；仅加密近景，尚未铺到整片森林的树冠上。
3. 每颗水滴保留承载三角形的三个顶点、顶点颜色和重心坐标。运行时叶片材质使用独立 `dew_time`，CPU 使用同一风动公式计算三个顶点再插值，随之更新水滴位置和朝向。
4. 为原蕨类材质创建运行时副本。灰度 `fern_02_rough_4k.png` 仅用于粗糙度，金属度设为 0，AO 设为 1；修复旧 `.tres` 中 Vector3 与 Shader 的 vec2 UV 参数不匹配。前后对比的两侧都使用此副本，不将这些修正混作露珠效果。
5. 水滴是无漫反射、非金属的透明电介质。折射率 1.333，法向入射反射率约 0.0204，粗糙度 0.055。Godot 4.6 的实现为 `F0 = 0.16 * SPECULAR²`，这里设置 `SPECULAR = sqrt(F0 / 0.16)`，并用 Fresnel 系数分配透射。
6. 不透明场景颜色和深度用于有厚度近似的屏幕空间折射，拒绝屏外坐标和前景深度。透射在 `EMISSION` 通道中传递已经照亮的背景，并不额外加常量发光；反射使用 Godot 的 PBR 太阳光和环境光照。合成在 HDR 线性空间完成，曝光与色调映射沿用场景的最终显示阶段。
7. 局部 ReflectionProbe 捕获周围森林、天空及阴影。只影响露珠的 layer 2，捕获时只包含原场景 layer 1，避免自反射，也不改变原森林材质的反射。探针启动时更新一次，适合此处相对静态的周围环境。
8. L 是诊断开关：通过探针的 reflection_mask 在局部森林反射与原天空反射之间切换。两种模式都保留透明度、太阳光、叶片和背景，不改变曝光。仅天空模式忽略了局部树木的反射遮挡，因此可能出现不合环境的明亮天光边缘。

## 检查与限制

检查在 AMD Radeon 780M、Godot 4.6.1、Forward+ 下执行，保留六张 1280×720 截图和 JSON 记录。固定相机与蕨类风动时间比较露珠开关，额外改变风动时间确认附着位置更新，并比较局部森林/仅天空反射。原背景树木与云仍按场景时间运行，截图不是逐像素一致性的测试。

原森林使用浓密树冠遮挡，阴影中的露珠反光较弱；远景的毫米级水滴也不会始终显示为亮点。

这是实时近似：屏幕空间折射无法看见屏幕外物体或其他透明层，不计算焦散、多次内部反射或水滴流动/合并。反射探针在近景区域最准确，并非每颗露珠单独进行光线追踪。水滴不投射不透明的黑色实体阴影。透射背景已包含场景雾，因此水滴材质关闭重复雾处理，适用于当前近距离观察；不用于精确的远距离浓雾合成。

运行日志仍保留上游旧网格格式与纹理 UID 的警告；退出时另有 7 个纹理 RID 的资源释放警告，其来源尚未进一步定位。当前截图生成无 Shader/GDScript 运行错误；这不等同于对所有视角或长期运行的完整测试。

重新检查（从 `D:\shaderagent17_s0_s1` 运行）：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\dew_check.py capture
```

参考：[Godot Spatial Shader](https://docs.godotengine.org/en/4.6/tutorials/shaders/shader_reference/spatial_shader.html)、[ReflectionProbe](https://docs.godotengine.org/en/4.6/classes/class_reflectionprobe.html)、[4.6 PBR F0 实现](https://github.com/godotengine/godot/blob/4.6/servers/rendering/renderer_rd/shaders/scene_forward_lights_inc.glsl)。资产署名与许可证见上一级原工程文件。
