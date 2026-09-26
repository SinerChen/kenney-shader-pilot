# A_L2｜灼烧前沿驱动的旋涡余烬：公开数值契约 v0.1


## 继承与发射

继承 A_L1 的全部数值语义。作者提供中性表面锚点 `anchor_id, position_ref, normal_ref`，这不是已算好的发射遮罩。每个 reset 后，各锚点在某一步 t_n 第一次满足 `front_strength>=emit_threshold` 且 enable_emission=true 时出生 1 个粒子，并标记 emitted；在被关闭期间不消耗发射资格。容量大于该 run 锚点总数，不考容量溢出取舍。粒子 ID 由 anchor_id 唯一确定。出生后不会随前沿撤回，也不因原粒子死亡再发射。

出生位置由该锚点经真实实例变换得到。初始 age=0；该步新粒子也按 dt 运动；在 t_n+dt 记录 age=dt。关发射只阻止新出生，不删除已有粒子。达到 `age>=lifetime` 后 inactive；reset 清空 emitted 和全部粒子。

## Curl Noise 和积分

势场 A(x,t) 有三个分量，分别为 A_L1 的基础三维噪声 `N(f*x + drift*t + offset_i)`；三个 offset 与 drift/f 是公开输入。速度 `v(x,t)=up_speed*(0,1,0)+curl_strength*curl(A)`。

本版 curl 各偏导按统一中心差分步长 epsilon 计算；epsilon>0 由配置给出。不要拿解析导数输出与指定的离散差分参考混比。纯旋度项不再单独 normalize。

粒子位置使用显式中点 RK2：本步速度取决于位置及时间场，`x_next=x+dt*v(x+0.5*dt*v(x,t),t+0.5*dt)`。cooling=`max(0,1-age/lifetime)`，以规定温度颜色参数表达。所有 lifetime>0。

数值接口 `curl_query(points,time,params)` 输出 curl/velocity；`particle_step(states,time,dt,params)` 输出 next_position/age/active/cooling。正常运行状态查询另返回 birth_time、birth_anchor_id、emitted。CPU 可处理唯一 ID/事件记账，位置更新和场计算必须来自 GPU。
