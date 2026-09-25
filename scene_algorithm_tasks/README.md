# 五组场景算法递进任务（15 题）

[HTML 实验结果页](http://127.0.0.1:8770/scene_algorithm_tasks/index.html) · [独立展示服务](http://127.0.0.1:8771/index.html)

依据用户提供的《Shader 算法 × 应用场景》、本地已实现算法及现有 Godot 工程制作。每组各含 L1 算法正确性、L2 模块关系、L3 场景影响与设计作用。

**当前交付：题面、read/write/render 工具、结构化任务和评测侧协议。render 已接入原生 Godot，支持自由相机并通过独立小场景作真实 GPU 验证；15 题均复用现有宿主：L1 为完整场景的相关子集，L2 按交互需求裁剪，L3 为完整场景。未调用模型或执行正式效果评分。** 原 15 题和 FG01 题目/实验保持原样。

[分级与验收协议](EVALUATION.md) · [算法实现证据](ALGORITHM_MAP.md) · [环境分层](ENVIRONMENTS.md) · [环境细节](FIXTURES.md) · [机器清单](manifest.json)

| 组 | 现有场景 | L1：模块 | L2：关系 | L3：场景作用 |
|---|---|---|---|---|
| SA01 草地通行：局部踩踏与自然风动 | [场景](../forest_grass_lab/project/scenes/GrassPatch.tscn) | [交互场与固定根部变形](tasks/SA01_L1/prompt.md) | [压草、风动与阴影的关系](tasks/SA01_L2/prompt.md) | [通行痕迹的覆盖与场景保留](tasks/SA01_L3/prompt.md) |
| SA02 海面展示：Gerstner 波与波峰泡沫 | [场景](../realistic/projects/water/example/boujie_water_shader/water_shader_examples.tscn) | [完整 Gerstner 波面](tasks/SA02_L1/prompt.md) | [波面压缩驱动泡沫历史](tasks/SA02_L2/prompt.md) | [完整海面覆盖与展览保留](tasks/SA02_L3/prompt.md) |
| SA03 Bistro 雨后路面：湿区覆盖与材质保留 | [场景](../realistic/projects/bistro/MainScene.tscn) | [四层高度材质混合](tasks/SA03_L1/prompt.md) | [湿区权重、细节法线与受光一致](tasks/SA03_L2/prompt.md) | [湿路面的作用边界与街道用途](tasks/SA03_L3/prompt.md) |
| SA04 FPS 命中反馈：有边界的投影贴花 | [场景](../projects/fps/pilot/F01.tscn) | [深度重建与完整投影贴花](tasks/SA04_L1/prompt.md) | [命中事件、移动受体与遮挡](tasks/SA04_L2/prompt.md) | [有效命中覆盖与射击流程保留](tasks/SA04_L3/prompt.md) |
| SA05 森林晨雾：高度层次与景观可读性 | [场景](../realistic/projects/forest/Main.tscn) | [指数高度雾积分](tasks/SA05_L1/prompt.md) | [高度雾与深度、植被和颜色合成](tasks/SA05_L2/prompt.md) | [晨雾的完整覆盖与景观可读性](tasks/SA05_L3/prompt.md) |


## 使用方式

先打开上表题面审阅；各层复用现有宿主，按场景范围配置执行。基础输入为当前 prompt.md 和 read/write/render 工具定义。本次 [串行 S1/P3 实验](experiment/README.md) 另加入共用 P3 系统文本，[完整输入预览](experiment/review/INDEX.md) 待用户审阅后再调用模型；不追加算法契约、通用接口或 cases.json。模型工具根为该题 model_workspace/，四个可读目录与仅 effect/ 可写的权限已实现。详见 [模型输入说明](MODEL_INPUT.md)。

内部评测材料保留在模型可读目录之外。后续评分须按当前题面明确的固定输入、输出和效果要求校准；渲染工具独立验证与正式任务评分分开记录。

生成与结构校验（在工作区根目录）：

```powershell
& '..\.venv\Scripts\python.exe' scene_algorithm_tasks/tools/build_pack.py
& '..\.venv\Scripts\python.exe' scene_algorithm_tasks/tools/validate_pack.py
```

生成器只写本包文档、场景入口、空候选和 JSON，不启动 Godot、不复制完整算法实现、不调用模型。来源文档快照位于 `sources/`；已读取它作为设计资料，没有执行其中的命令或把文档描述当作已实现事实。

展示页默认播放 30 fps 连续效果视频，支持慢放、全屏和 MP4 下载。视频由实际候选重新运行生成，后台自动补录；详见 [连续效果视频](experiment/STATUS.md#连续效果视频)。

[Prompt、调用轨迹与修改文件展示](experiment/CASE_VIEWER.md)：每个模型×任务均可在页面内查看实际输入、事件详情及代码差异。
