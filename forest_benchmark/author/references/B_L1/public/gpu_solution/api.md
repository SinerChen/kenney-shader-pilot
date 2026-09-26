# 公共 API

adapter.gd 继承 fixture/adapter_base.gd。reset(config) 清空状态并从 t0 开始；advance(dt, events) 在旧时刻处理事件、更新到下一时刻；query(name, payload) 的 payload 覆盖本轮配置，可显式传 time，不改变持续状态。query('state', {}) 或 get_outputs() 读取当前状态。mount(bridge) 安装材质，update_display() 更新显示。

配置字段与固定例子见 demo.json 和 sample_inputs/sample.json。二维字段按行展开，i=X 最快，j=Z 次之。grid_size=[Nx,Nz]，domain_min=[xmin,zmin]，domain_size=[Lx,Lz]。三维密度布局为 [Nz,Ny,Nx] 的展平数组。view_projection 与 cloud_world_to_local 是作用于列向量的列主序 4×4 矩阵；clip.w>0、clip.z/clip.w∈[0,1]，UV=(ndc.xy*(1,-1)+1)/2。

成功的 query 返回 Dictionary：status='OK'、device=真实 RenderingDevice、buffer=同步后的 storage buffer RID、shape=[行数,通道数]、fields=按序字段名。桥从资源读取 little-endian float32，不把普通数组当 GPU 证据。也接受 texture=真实 float32 Texture2D（RF/RGF/RGBF/RGBAF）及同样 shape/fields。布尔字段数值为 0 或 1；空粒子数组返回 status='EMPTY'、shape=[0,6]。未实现须返回 NOT_IMPLEMENTED。get_outputs 可组合资源字典与事件元数据。

纯函数查询：

- burn_query / curl_query / cloud_query：points=[[x,y,z],…]。
- particle_step：particles=[[x,y,z,age],…]，输出每行 position3、age、active、cooling。
- stamp_query：depth、contacts=[[event_id,cx,cz,angle,size_x,size_z,increment],…]；mask 为线性遮罩，mask_size=[宽,高]。
- pom_query：pom_rays=[[x,z,Vx,Vy,Vz],…] 与 depth。
- wet_step：wetness、depth、source；diffusion 对应 D。
- fog_query：view_rays=[[ox,oy,oz,dx,dy,dz,opaque_distance],…]；cloud_steps=N、view_steps=Nv。五个固定输出通道后接 Nv 个 T_cloud_at_samples，再接 Nv 个 T_fog_light。
- flow_query：uvs、flow（每单元 [vx,vz]）、period=P、phase=phi、tiling=K、texture_size、color_texture、normal_texture、normal_encoded。
- foam_step：foam、flow、sources=[[x,z,radius,rate],…]。
- optics_query：optical_rays=[[Ix,Iy,Iz,Nx,Ny,Nz,x,y,z],…]，eta_i/eta_t、ell、sigma_a、view_projection、color_texture、reflection_color、fallback_color。
- wave_step / wave_normal_query：height、height_prev、force，wave_speed=c、gamma；法线查询使用 height。

事件仅有：contact {event_id,contact}；water {event_id,contact,amount}；wave {event_id,source}；set {values}。type 字段指定类型；set 只改变给定算法参数，不自动 reset。wave 的空间核与泡沫源相同，rate 表示本 tick 加速度。重复 event_id 只处理一次。水源与外力的持续场由 source/force 输入。发射锚点顺序即 anchor_id，birth_log、particle_ids、emitted 描述真实记录。

资源接入：bridge.bind_material(target, material) 仅允许 task.json 列出的目标；bridge.add_effect(node) 将新效果放到 EffectRoot。E 题 bridge.background('rear') 给不透明输入，bridge.background('front') 给当前后景输入；后景捕获剔除前景层。绑定节点、纹理和相机由桥组织。不得改 protected 节点或以修改基础场景实现目标。

编辑器启动呈现中性场景和未实现状态。只有完成 mount/reset 后才开始固定 dt 示例推进。调试 render 可选择相机，但不改变正式采集配置。
