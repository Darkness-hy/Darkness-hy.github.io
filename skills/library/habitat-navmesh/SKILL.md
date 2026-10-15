---
name: habitat-navmesh
description: Use when converting a 3D scene mesh (glTF/GLB, e.g. Sketchfab downloads) into a Habitat-sim NavMesh — build, debug disconnected islands, tune recast params (cell_size / agent_max_climb / agent_max_slope), validate floor connectivity with snap_point / find_path, save the .navmesh sidecar, and wire it into examples/viewer.py. Trigger on habitat、navmesh、导航网格、recompute_navmesh、Detour、recast、防穿模、楼梯上不去、sketchfab 场景.
keywords:
  - habitat
  - habitat-sim
  - navmesh
  - 导航网格
  - recast
  - detour
  - gltf
  - glb
  - sketchfab
  - 穿模
  - 楼梯
packageType: instruction-skill
instructionOnly: true
metadata:
  version: 1.0.0
---

# Habitat-sim 场景转 NavMesh

把任意场景网格（glTF/GLB，如 Sketchfab 下载的模型）转成 habitat-sim 可用的 NavMesh，并保证**各楼层通过楼梯连通、agent 行走不穿模**。

## 前置条件

```bash
python -c "import habitat_sim; print(habitat_sim.__version__, habitat_sim.built_with_bullet)"
```

- habitat-sim 可用（本流程在 0.3.3 验证；API 在不同小版本有差异，脚本里已做兼容）
- 最好 `built_with_bullet == True`（排查台阶尺寸要用 Bullet 射线）
- 场景文件：优先用**未压缩 glTF**（scene.gltf + scene.bin）。Draco 压缩的 GLB 可能因插件缺失加载失败

## 总流程

```
场景体检 → 首次构建 → 连通性验证 → (失败则按决策树调参重建) → 无头行走验证 → 保存接入
```

核心认知：**NavMesh 建不出来只是第一步，建出来各楼层互不连通才是常态**。必须用 `find_path` 验证连通性，不能只看 `is_loaded`。

---

## Step 1 场景体检（必做，5 分钟省 1 小时）

加载场景，拿包围盒和"可走高度地图"：

```python
import numpy as np, habitat_sim
from habitat_sim.utils.settings import default_sim_settings, make_cfg

SCENE = "/path/to/scene.gltf"
s = default_sim_settings.copy()
s.update({"scene": SCENE, "scene_dataset_config_file": "default",
          "enable_physics": False, "width": 320, "height": 240, "silent": True})
sim = habitat_sim.Simulator(make_cfg(s))

# 包围盒：0.3.3 用 root.cumulative_bb；新版可能是 scene_graph.calculate_bbox()
root = sim.get_active_scene_graph().get_root_node()
bb = root.cumulative_bb
print("bbox min/max:", list(bb.min), list(bb.max), "size:", list(bb.size()))
```

要点：

- **默认出生点 (0,0,0) 经常埋在实体几何里** → viewer 黑屏不是没 mesh，先算 bbox 再定出生点
- 场景超过 ~200m 时，默认 `cell_size=0.05` 的体素栅格会爆（OOM 或直接 build 失败）
- `enable_physics=False` 时 `sim.cast_ray` 不可用（报 "Not implemented in base PhysicsManager"），需要射线时开物理

## Step 2 首次构建

```python
ns = habitat_sim.nav.NavMeshSettings()
ns.set_defaults()
ns.cell_size = 0.10        # 大场景关键：0.05 → 0.1（还不够就 0.15/0.2）
ns.cell_height = 0.20
ns.agent_height = 1.5
ns.agent_radius = 0.2
ns.agent_max_climb = 0.4   # 先按正常楼梯来，后面实测再调
ns.agent_max_slope = 45.0
ok = sim.recompute_navmesh(sim.pathfinder, ns)
print(ok, sim.pathfinder.is_loaded, sim.pathfinder.num_islands)
```

## Step 3 连通性验证（关键步骤）

为每个"楼层/区域"选一个代表点（从 Step 1 的高度地图或渲染图里挑），做三件事：

```python
pf = sim.pathfinder
p = np.array([x, y, z], dtype=np.float32)
sp = pf.snap_point(p)            # 找最近可走面；返回 NaN = 附近没有可走 poly
print(sp, pf.island_radius(sp))  # island_radius：所在岛屿大小，主岛屿通常 >50

path = habitat_sim.ShortestPath()
path.requested_start = pf.snap_point(pt_a)
path.requested_end   = pf.snap_point(pt_b)
n = pf.find_path(path)
print(n, path.geodesic_distance)  # n=0 / dist=inf → 两点不连通
```

判读：

- `snap_point` 返回 NaN → 该点悬空/在实体里，或那一层根本没有可走面
- 每个楼层一个岛屿、`find_path` 全 inf → **楼梯没连上**，进入 Step 4
- `island_radius` 对比可区分"同一岛"还是"不同岛"

## Step 4 失败排查决策树

| 症状 | 原因 | 对策 |
|---|---|---|
| build 失败/OOM | 场景太大，cell_size 太小 | 0.05→0.1→0.2 |
| 各层独立岛屿，path=inf | 台阶踢面 > max_climb | **先实测台阶尺寸**，再把 `agent_max_climb` 调到 ≥ 最大踢面+0.1 |
| 同上 | 台阶口被闸门/家具挡死 | 渲染确认，接受绕行或改网格 |
| 楼梯 45° 斜坡侧面可走 | slope 阈值太松 | `agent_max_slope` 降到 40（水平踏步不受影响） |
| 岛屿数量爆炸（数百） | cell_size 过细 + 杂物 | 接受，或 cell_size 回到 0.1 |
| trimesh 加载被 kill -9 | 4K 贴图解压撑爆内存 | 别用 trimesh 加载带贴图大场景；手解 glTF（见附录 A）或 Bullet 射线 |

### 实测台阶尺寸：Bullet 射线剖面法（最可靠）

不知道台阶多高就别瞎调 climb。开物理，沿楼梯方向打一排向下的射线：

```python
# enable_physics=True 重建 sim 后
ray = habitat_sim.geo.Ray()
ray.direction = mn.Vector3(0, -1, 0)
for z in np.arange(z0, z1, 0.5):
    ray.origin = mn.Vector3(x, y_above, z)
    hits = sim.cast_ray(ray)
    print(z, hits.hits[0].point.y if hits.has_hits() else None)
```

相邻平台的高度差 = 踢面高，水平间距 = 踏面深。**风格化模型常见巨形台阶**（实测案例：1.38m 高 × 1.5m 深），`agent_max_climb` 要盖过它。注意折中：climb 调大后 agent 能翻越闸机/长椅等低矮家具。

## Step 5 无头行走验证（模拟 WASD）

```python
agent = sim.get_agent(0)
mk = habitat_sim.agent.ActionSpec; ma = habitat_sim.agent.ActuationSpec
agent.agent_config.action_space = {"move_forward": mk("move_forward", ma(0.5))}
st = agent.get_state(); st.position = pf.snap_point(start_pt)
agent.set_state(st)
for i in range(120):
    agent.act("move_forward")
    if i % 10 == 0:
        print(i, agent.get_state().position)   # y 应随上楼连续抬升
```

y 剖面连续爬升 = 楼梯真的可走；卡住不动 = 该方向被 navmesh 边缘挡住（防穿模生效）。

## Step 6 保存与接入 viewer

```python
sim.pathfinder.save_nav_mesh("/path/to/scene.navmesh")   # 与 scene.gltf 同目录同名
```

`examples/viewer.py` 接入（放在 `reconfigure_sim()` 创建 sim 之后）：

```python
navmesh_path = os.path.splitext(self.sim_settings["scene"])[0] + ".navmesh"
if not self.sim.pathfinder.is_loaded and os.path.exists(navmesh_path):
    self.sim.pathfinder.load_nav_mesh(navmesh_path)
# 出生点吸附到 navmesh（否则 tryStep 不生效）
start = self.sim.pathfinder.snap_point(np.array([x, y, z], dtype=np.float32))
```

viewer 里的 `navmesh_config_and_recompute()`（SHIFT+N 触发）用的是 `set_defaults()`，大场景/怪台阶必失败——把调好的参数同步进去。

行走约束原理：NavMesh 加载后 `agent.act()` 的水平移动走 Detour `tryStep`（≥ max_climb 的高差直接挡住），这与 Bullet 物理无关——** kinematic WASD 本来就不撞墙检测，防穿模靠的是 NavMesh，不是开物理**。

---

## 附录 A：免 trimesh 解析 glTF 几何（内存安全）

trimesh 会解压全部 4K 贴图 → OOM。只读几何就手解 JSON+bin：accessor(POSITION/indices) → 节点树世界变换 → 拼接三角形。然后用面法线做分析：

- `|normal.y| > 0.95` 的水平面按高度聚类 → 楼层清单（按面积排序）
- 中间高度的水平小面片 → 楼梯踏步候选（注意垃圾桶/栏杆/桁架会误报，需渲染确认）
- 0.35 < |normal.y| < 0.9 的斜面 → 坡道/自动扶梯

## 附录 B：参考案例（2-Floor Dirty New York Subway Station）

- 场景 616×249×97m，21.7 万面；默认参数 build 失败 → `cell_size=0.1` 后 2s 建成
- 楼层：轨道层 -22.7 / 站台 -17.5 / 夹层 9.5 / 站厅 13.6 / 屋顶 37
- 楼梯：18 级巨形台阶，踢面 1.38m → `agent_max_climb=1.7` 后站台↔站厅连通（find_path OK，行走 y 连续抬升）
- 站台→轨道层 5m 高差保持隔离（正确）；9.5m 观景层无建模楼梯，接受为独立岛屿
- 最终参数：`cell_size=0.1, cell_height=0.2, agent_radius=0.2, agent_height=1.5, agent_max_climb=1.7, agent_max_slope=40`
