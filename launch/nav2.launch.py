import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def launch_setup(context, *args, **kwargs):
    pkg_dir = get_package_share_directory('lastmile_nav2_bringup')
    launch_dir = os.path.join(pkg_dir, 'launch')

    environment_value = LaunchConfiguration('environment').perform(context)
    params_file_value = LaunchConfiguration('params_file').perform(context)
    nav2pose_bt_xml_value = LaunchConfiguration('nav2pose_bt_xml').perform(
        context
    )
    rviz_config_value = LaunchConfiguration('rviz_config').perform(context)

    if environment_value not in ('local', 'urban'):
        raise RuntimeError(
            "environment must be either 'local' or 'urban', "
            f"got '{environment_value}'"
        )

    if not params_file_value:
        params_file_value = os.path.join(
            pkg_dir,
            'config',
            f'nav2_{environment_value}_params.yaml',
        )

    # BT XML is used only in the local profile. Urban does not load bt_navigator.
    if not nav2pose_bt_xml_value and environment_value == 'local':
        nav2pose_bt_xml_value = os.path.join(
            pkg_dir,
            'behavior_trees',
            'local_navigate_to_pose.xml',
        )

    if not rviz_config_value:
        rviz_filename = (
            'urban_nav2.rviz'
            if environment_value == 'urban'
            else 'local_nav2.rviz'
        )
        rviz_config_value = os.path.join(pkg_dir, 'rviz', rviz_filename)

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml_file = LaunchConfiguration('map')
    route_graph = LaunchConfiguration('route_graph')
    use_collision_monitor = LaunchConfiguration('use_collision_monitor')
    container_name = LaunchConfiguration('container_name')
    autostart = LaunchConfiguration('autostart')
    rviz = LaunchConfiguration('rviz')

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file_value,
            root_key='',
            param_rewrites={
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'yaml_filename': map_yaml_file,
                'graph_filepath': route_graph,
                'default_nav_to_pose_bt_xml': nav2pose_bt_xml_value,
            },
            convert_types=True,
        ),
        allow_substs=True,
    )

    bringup_cmd_group = GroupAction([
        Node(
            name=container_name,
            package='rclcpp_components',
            executable='component_container_isolated',
            parameters=[configured_params],
            arguments=['--ros-args', '--log-level', 'info'],
            output='screen',
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(launch_dir, 'include', 'navigation.launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': params_file_value,
                'container_name': container_name,
                'environment': environment_value,
                'map': map_yaml_file,
                'route_graph': route_graph,
                'use_collision_monitor': use_collision_monitor,
                'nav2pose_bt_xml': nav2pose_bt_xml_value,
                'autostart': autostart,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(launch_dir, 'rviz.launch.py')
            ),
            condition=IfCondition(rviz),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'rviz_config': rviz_config_value,
            }.items(),
        ),
    ])

    return [bringup_cmd_group]


def generate_launch_description():
    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM',
        '1',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true.',
    )

    declare_environment_cmd = DeclareLaunchArgument(
        'environment',
        default_value='local',
        description='Navigation profile: local or urban.',
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value='',
        description='Optional full path to Nav2 parameter file.',
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Optional full path to local 2D map YAML file.',
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
        default_value='',
        description='Optional Behavior Tree XML used only by local profile.',
    )

    declare_container_name_cmd = DeclareLaunchArgument(
        'container_name',
        default_value='nav2_container',
        description='Composable node container name.',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically transition lifecycle nodes to active.',
    )

    declare_rviz_cmd = DeclareLaunchArgument(
        'rviz',
        default_value='false',
        description='Launch RViz2.',
    )

    declare_rviz_config_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value='',
        description='Optional full path to RViz2 config file.',
    )

    ld = LaunchDescription()
    ld.add_action(stdout_linebuf_envvar)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_environment_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_route_graph_cmd)
    ld.add_action(declare_use_collision_monitor_cmd)
    ld.add_action(declare_nav2pose_bt_xml_cmd)
    ld.add_action(declare_container_name_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_rviz_cmd)
    ld.add_action(declare_rviz_config_cmd)
    ld.add_action(OpaqueFunction(function=launch_setup))

    return ld
