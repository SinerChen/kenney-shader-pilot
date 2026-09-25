已完成实现。

- 修改文件：
  - `effect/main.gd`
  - `effect/plan.json`
- 已实现：
  - 局部命中位置与法线的目标变换
  - 贴花跟随 TargetA/TargetB 的移动和旋转
  - 投影盒范围、UV、朝向平滑衰减和材质混合
  - 单贴花生命周期与重复事件去重
  - 到期后恢复原始材质
  - 背景像素字段按要求输出
  - `active_target` 生命周期状态
- 已验证：
  - `scene/main.tscn` 成功运行，无脚本错误
  - 固定帧 1、30、60、180 生成 samples 输出
  - TargetA、TargetB、Cover 与地面均保留
  - 180 步后贴花消失并恢复原材质
  - 观察结果位于 `observations/render_20260925_034704_561b3067/`