import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import LoadComposableNodes
from launch_ros.descriptions import ComposableNode, ParameterFile
from nav2_common.launch import RewrittenYaml


def profile_with_collision(environment, profile, use_collision_monitor):
    return PythonExpression([
        "'", environment, "' == '", profile, "' and '",
        use_collision_monitor, "'.lower() == 'true'",
    ])


def profile_without_collision(environment, profile, use_collision_monitor):
    return PythonExpression([
        "'", environment, "' == '", profile, "' and '",
        use_collision_monitor, "'.lower() != 'true'",
    ])


def controller_server(configured_params):
    return ComposableNode(
        package='nav2_controller',
        plugin='nav2_controller::ControllerServer',
        name='controller_server',
        parameters=[configured_params],
        remappings=[
            ('cmd_vel', 'cmd_vel_nav'),
        ],
    )


def smoother_server(configured_params):
    return ComposableNode(
        package='nav2_smoother',
        plugin='nav2_smoother::SmootherServer',
        name='smoother_server',
        parameters=[configured_params],
    )


def planner_server(configured_params):
    return ComposableNode(
        package='nav2_planner',
        plugin='nav2_planner::PlannerServer',
        name='planner_server',
        parameters=[configured_params],
    )


def behavior_server(configured_params):
    return ComposableNode(
        package='nav2_behaviors',
        plugin='behavior_server::BehaviorServer',
        name='behavior_server',
        parameters=[configured_params],
        remappings=[
            ('cmd_vel', 'cmd_vel_nav'),
        ],
    )


def bt_navigator(configured_params):
    return ComposableNode(
        package='nav2_bt_navigator',
        plugin='nav2_bt_navigator::BtNavigator',
        name='bt_navigator',
        parameters=[configured_params],
    )


def map_server(configured_params):
    return ComposableNode(
        package='nav2_map_server',
        plugin='nav2_map_server::MapServer',
        name='map_server',
        parameters=[configured_params],
    )


def velocity_smoother(configured_params, use_collision_monitor):
    remappings = [('cmd_vel', 'cmd_vel_nav')]

    # When collision monitor is disabled, velocity_smoother becomes the final
    # publisher to the robot base command topic.
    if not use_collision_monitor:
        remappings.append(('cmd_vel_smoothed', 'cmd_vel'))

    return ComposableNode(
        package='nav2_velocity_smoother',
        plugin='nav2_velocity_smoother::VelocitySmoother',
        name='velocity_smoother',
        parameters=[configured_params],
        remappings=remappings,
    )


def collision_monitor(configured_params):
    return ComposableNode(
        package='nav2_collision_monitor',
        plugin='nav2_collision_monitor::CollisionMonitor',
        name='collision_monitor',
        parameters=[configured_params],
    )


def route_server(configured_params):
    return ComposableNode(
        package='nav2_route',
        plugin='nav2_route::RouteServer',
        name='route_server',
        parameters=[configured_params],
    )


def lifecycle_manager(name, use_sim_time, autostart, node_names):
    return ComposableNode(
        package='nav2_lifecycle_manager',
        plugin='nav2_lifecycle_manager::LifecycleManager',
        name=name,
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': node_names,
        }],
    )


def local_navigation_nodes(configured_params, use_collision_monitor):
    # Local profile keeps the conventional Nav2 NavigateToPose stack.
    # Route server is intentionally not loaded in local mode.
    nodes = [
        map_server(configured_params),
        controller_server(configured_params),
        planner_server(configured_params),
        smoother_server(configured_params),
        behavior_server(configured_params),
        bt_navigator(configured_params),
        velocity_smoother(configured_params, use_collision_monitor),
    ]

    if use_collision_monitor:
        nodes.append(collision_monitor(configured_params))

    return nodes


def local_lifecycle_node_names(use_collision_monitor):
    node_names = [
        'map_server',
        'controller_server',
        'planner_server',
        'smoother_server',
        'behavior_server',
        'bt_navigator',
        'velocity_smoother',
    ]

    if use_collision_monitor:
        node_names.append('collision_monitor')

    return node_names


def urban_navigation_nodes(configured_params, use_collision_monitor):
    # Urban profile follows the OpenNav AMD 3D route-demo direction:
    # no BT navigator, no planner server, no map server.
    # route_navigation_executor calls route_server, Spin, and then FollowPath.
    nodes = [
        controller_server(configured_params),
        behavior_server(configured_params),
        velocity_smoother(configured_params, use_collision_monitor),
        route_server(configured_params),
    ]

    if use_collision_monitor:
        nodes.append(collision_monitor(configured_params))

    return nodes


def urban_lifecycle_node_names(use_collision_monitor):
    node_names = [
        'controller_server',
        'behavior_server',
        'velocity_smoother',
        'route_server',
    ]

    if use_collision_monitor:
        node_names.append('collision_monitor')

    return node_names


def local_navigation_bundle(
    *,
    target_container,
    condition,
    configured_params,
    use_sim_time,
    autostart,
    lifecycle_name,
    use_collision_monitor,
):
    nodes = local_navigation_nodes(configured_params, use_collision_monitor)
    nodes.append(
        lifecycle_manager(
            lifecycle_name,
            use_sim_time,
            autostart,
            local_lifecycle_node_names(use_collision_monitor),
        )
    )

    return LoadComposableNodes(
        target_container=target_container,
        condition=IfCondition(condition),
        composable_node_descriptions=nodes,
    )


def urban_navigation_bundle(
    *,
    target_container,
    condition,
    configured_params,
    use_sim_time,
    autostart,
    lifecycle_name,
    use_collision_monitor,
):
    nodes = urban_navigation_nodes(configured_params, use_collision_monitor)
    nodes.append(
        lifecycle_manager(
            lifecycle_name,
            use_sim_time,
            autostart,
            urban_lifecycle_node_names(use_collision_monitor),
        )
    )

    return LoadComposableNodes(
        target_container=target_container,
        condition=IfCondition(condition),
        composable_node_descriptions=nodes,
    )


def generate_launch_description():
    pkg_dir = get_package_share_directory('lastmile_nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    container_name = LaunchConfiguration('container_name')
    environment = LaunchConfiguration('environment')
    route_graph = LaunchConfiguration('route_graph')
    use_collision_monitor = LaunchConfiguration('use_collision_monitor')
    nav2pose_bt_xml = LaunchConfiguration('nav2pose_bt_xml')
    autostart = LaunchConfiguration('autostart')

    param_substitutions = {
        'use_sim_time': use_sim_time,
        'autostart': autostart,
        'yaml_filename': map_yaml_file,
        'graph_filepath': route_graph,
        'default_nav_to_pose_bt_xml': nav2pose_bt_xml,
    }

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key='',
            param_rewrites=param_substitutions,
            convert_types=True,
        ),
        allow_substs=True,
    )

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM',
        '1',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true.',
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_dir, 'config', 'nav2_local_params.yaml'),
        description='Full path to Nav2 parameter file.',
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Optional full path to local 2D map YAML file.',
    )

    declare_container_name_cmd = DeclareLaunchArgument(
        'container_name',
        default_value='nav2_container',
        description='Composable node container name.',
    )

    declare_environment_cmd = DeclareLaunchArgument(
        'environment',
        default_value='local',
        description='Navigation profile: local or urban.',
    )

    declare_route_graph_cmd = DeclareLaunchArgument(
        'route_graph',
        default_value='',
        description='Optional GeoJSON graph file for the urban route server.',
    )

    declare_use_collision_monitor_cmd = DeclareLaunchArgument(
        'use_collision_monitor',
        default_value='true',
        description='Enable nav2_collision_monitor in the velocity chain.',
    )

    declare_nav2pose_bt_xml_cmd = DeclareLaunchArgument(
        'nav2pose_bt_xml',
        default_value=os.path.join(
            pkg_dir,
            'behavior_trees',
            'local_navigate_to_pose.xml',
        ),
        description='Behavior Tree XML used only by the local profile.',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically transition lifecycle nodes to active.',
    )

    local_with_collision = local_navigation_bundle(
        target_container=container_name,
        condition=profile_with_collision(
            environment,
            'local',
            use_collision_monitor,
        ),
        configured_params=configured_params,
        use_sim_time=use_sim_time,
        autostart=autostart,
        lifecycle_name='lifecycle_manager_local_navigation',
        use_collision_monitor=True,
    )

    local_without_collision = local_navigation_bundle(
        target_container=container_name,
        condition=profile_without_collision(
            environment,
            'local',
            use_collision_monitor,
        ),
        configured_params=configured_params,
        use_sim_time=use_sim_time,
        autostart=autostart,
        lifecycle_name='lifecycle_manager_local_navigation',
        use_collision_monitor=False,
    )

    urban_with_collision = urban_navigation_bundle(
        target_container=container_name,
        condition=profile_with_collision(
            environment,
            'urban',
            use_collision_monitor,
        ),
        configured_params=configured_params,
        use_sim_time=use_sim_time,
        autostart=autostart,
        lifecycle_name='lifecycle_manager_urban_navigation',
        use_collision_monitor=True,
    )

    urban_without_collision = urban_navigation_bundle(
        target_container=container_name,
        condition=profile_without_collision(
            environment,
            'urban',
            use_collision_monitor,
        ),
        configured_params=configured_params,
        use_sim_time=use_sim_time,
        autostart=autostart,
        lifecycle_name='lifecycle_manager_urban_navigation',
        use_collision_monitor=False,
    )

    ld = LaunchDescription()
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_container_name_cmd)
    ld.add_action(declare_environment_cmd)
    ld.add_action(declare_route_graph_cmd)
    ld.add_action(declare_use_collision_monitor_cmd)
    ld.add_action(declare_nav2pose_bt_xml_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(local_with_collision)
    ld.add_action(local_without_collision)
    ld.add_action(urban_with_collision)
    ld.add_action(urban_without_collision)

    return ld
