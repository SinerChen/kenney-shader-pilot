# 当前测试环境

从原海面展示中拆出 DeepOcean 的中心网格，用原网格生成器设置 8 米、64 格子区域，保留原水材质、光照和相机；只实现波面。

main.tscn 直接继承原场景。project/ 是现有工程的只读目录，可用 read 列出和读取；其中 res:// 路径相对于该工程根。

effect/main.gd 是效果入口；后续层级继承同模型前一级文件：configure(scene_root, test_input) 接收原场景与固定输入；step(dt) 在每个截图帧步进前调用；sample() 返回题面要求的数值字典。入口提供空实现，算法由你完成。可在 effect/ 中添加 shader、资源与辅助脚本。

场景裁剪仅用于当前层；必要的宿主依赖节点保留。数值结果由 render 写入 observations/ 下的 samples.json；默认视角适合本层，也可自行指定相机。
