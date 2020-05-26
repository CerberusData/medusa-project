#!/bin/bash
# /etc/init.d/startBot

# -----------------------------------------------------------------------------
### BEGIN INIT INFO
# Provides:          Robot
# Required-Start:    $syslog
# Required-Stop:     $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Script to start a Robot at init
# Description:       Script to start Robot at boot time
### END INIT INFO

set -e

export NO_AT_BRIDGE=1

# -----------------------------------------------------------------------------
# If you want a command to always run, put it here
# Carry out specific functions when asked to by the system 
case "$1" in
  start)
    echo  "Starting Robot"

      #  ----------------------------------------------------------------------
      #  ROS2 cv_bridge dependency
      if [ -d "${PWD%}/ros2/src/vision_opencv" ] 
      then
          echo "[INFO]: cv_bridge already exits" 
          sleep 2 && clear 
      else
          cd ${PWD%}/ros2/src
          git clone https://github.com/ros-perception/vision_opencv.git
          cd vision_opencv
          git checkout ros2
          cd .. && cd .. && cd ..
          sleep 8 && clear 
      fi

      #  ----------------------------------------------------------------------
      # Delete previous workspaces
      # echo  [WARN]: "ROS2 Removing old shit ... "
      # rm -r ${PWD%}/ros2/install || true
      # rm -r ${PWD%}/ros2/build || true
      # rm -r ${PWD%}/ros2/log || true
      # sleep 2 && clear 
      
      #  ----------------------------------------------------------------------
      #  Build ROS2 packages
      . /opt/ros/dashing/setup.bash
      clear && cd ${PWD%}/ros2    
      echo  "[INFO]: ROS2 Building new stuff ... "
      colcon build --symlink-install
      echo  "[INFO]: ROS2 Build successful ... "
      sleep 2 && clear && cd ..

      #  ----------------------------------------------------------------------
      #  Source ROS2 and local enviroment variables
      echo  "[INFO]: ROS2 Sourcing ... "
      source "${PWD%}/ros2/install/setup.bash"
      source "${PWD%}/configs/local_env_vars.sh"
      
      #  ----------------------------------------------------------------------
      #  ROS2 Launching
      # sleep 2 && clear
      echo  "[INFO]: ROS2 launching ... "
      ros2 launch "${PWD%}/configs/bot.launch.py"

      #  ----------------------------------------------------------------------
    ;;
  stop)
    echo "[WARN]: Stopping Robot"
    # kill application you want to stop
    for i in $( rosnode list ); do
      ros2 lifecycle set $i shutdown;
    done
    ;;
  *)
    echo "Usage: /etc/init.d/Robot {start|stop}"
    exit 1
    ;;
esac

exit 0

# # Topic pub
# ros2 topic pub --once /video_streaming/visual_debugger usr_msgs/msg/vision/VisualMessage '{data: "message_text", type: "INFO"}'
# ros2 topic pub --once /video_calibrator/calibrate_cam std_msgs/msg/String '{data: "C"}'
# ros2 topic pub --once /video_streaming/idle_timer_reset std_msgs/msg/Bool '{data: True}'
# ros2 topic pub --once /video_streaming/waypoint_pt usr_msgs/msg/vision/Waypoint '{x: 0.5, y:0.5}'

# # Kill a node
# ros2 lifecycle set <nodename> shutdown

# # Source ROS2 enviroment
# sudo bash configs/startBot.sh start
# source /opt/ros/dashing/setup.sh && source /workspace/rover/ros2/install/setup.sh && clear