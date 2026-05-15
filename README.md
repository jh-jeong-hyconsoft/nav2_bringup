# lastmile_nav2_bringup

Last-mile navigation용 Nav2 bringup 패키지입니다. `local`과 `urban` 두 profile을 제공합니다.

## Build

```bash
cd /home/hycon_ubuntu/workspace/nav2_route_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select lastmile_nav2_bringup --symlink-install
source install/setup.bash
```

## Run

Local profile:

```bash
ros2 launch lastmile_nav2_bringup nav2.launch.py \
  environment:=local \
  map:=/path/to/map.yaml
```

Urban profile:

```bash
ros2 launch lastmile_nav2_bringup nav2.launch.py \
  environment:=urban \
  route_graph:=/path/to/route_graph.geojson
```

RViz 포함:

```bash
ros2 launch lastmile_nav2_bringup nav2.launch.py environment:=urban rviz:=true
```

## Profiles

`local`:
- `map_server`, `bt_navigator`, `planner_server`, `controller_server`, `smoother_server`, `behavior_server`, `velocity_smoother`
- 선택적으로 `collision_monitor`
- global costmap은 `map` 인자로 받은 2D occupancy map을 사용
- costmap과 collision monitor 입력은 `/ouster/scan`
- 기본 BT: `behavior_trees/local_navigate_to_pose.xml`

`urban`:
- local profile 구성에 `nav2_route` route server 추가
- costmap 입력은 `/patchworkpp/nonground`
- collision monitor 입력은 `/ouster/scan`
- 기본 BT: `behavior_trees/urban_navigate_to_pose.xml`

## Main Arguments

```bash
environment:=local|urban
map:=/path/to/map.yaml
route_graph:=/path/to/route_graph.geojson
use_collision_monitor:=true|false
use_sim_time:=true|false
nav2pose_bt_xml:=/path/to/custom_bt.xml
params_file:=/path/to/custom_params.yaml
rviz:=true|false
rviz_config:=/path/to/custom.rviz
```

`params_file`, `nav2pose_bt_xml`, `rviz_config`을 비워두면 profile에 맞는 기본 파일을 사용합니다. `map`은 local profile에서 필요하고, `route_graph`는 urban profile에서 필요합니다.

## Required External Inputs

이 패키지는 localization을 실행하지 않습니다. 실행 전에 다음 입력이 외부에서 제공되어야 합니다.

- TF: `map -> odom`, `odom -> base_link`
- Odometry: `/odom`
- Local/urban collision scan: `/ouster/scan`
- Urban obstacle cloud: `/patchworkpp/nonground`
- Urban route graph: `route_graph` 인자로 전달하는 GeoJSON 파일
