cmake_minimum_required(VERSION 3.8)
project(yolo_grasp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)

install (
PROGRAMS src/yolo_detect_box.py
DESTINATION lib/${PROJECT_NAME}
)




install(
DIRECTORY weights 
DESTINATION share/${PROJECT_NAME}
)

ament_package()
