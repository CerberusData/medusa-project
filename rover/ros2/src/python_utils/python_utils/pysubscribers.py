#!/usr/bin/env python3
# =============================================================================
"""
Code Information:
    Maintainer: Eng. John Alberto Betancourt G
	Mail: john@kiwicampus.com
	Kiwi Campus / Computer & Ai Vision Team
"""

# =============================================================================
import numpy as np
import time
import cv2
import os

from usr_msgs.msg import VisualMessage
from usr_msgs.msg import Waypoint
from usr_msgs.msg import Extrinsic as Extrinsic_msg
from std_msgs.msg import Bool

from vision.utils.vision_utils import print_text_list
from vision.utils.vision_utils import printlog
from vision.utils.vision_utils import dotline

from vision.intrinsic.intrinsic_utils import IntrinsicClass

from vision.extrinsic.extrinsic_utils import Extrinsic
from vision.extrinsic.extrinsic_utils import get_projection_point_src
from vision.extrinsic.extrinsic_utils import get_distor_point

# =============================================================================
class VisualDebuggerSubscriber():

    def __init__(self, parent_node):

        # Timer with time to show message
        self._VISUAL_DEBUGGER_TIME = int(
            os.getenv(key="VISUAL_DEBUGGER_TIME", default=10)
            )

        # Message to show in console
        self.msg = "" 
        # Type of message "info, err, warn"
        self.type = "INFO" 
        
        # Subscribers
        self._sub_visual_debugger = parent_node.create_subscription(
            msg_type=VisualMessage, topic='video_streaming/visual_debugger', 
            callback=self.cb_visual_debugger, qos_profile=5,
            callback_group=parent_node.callback_group
            )

    def cb_visual_debugger(self, msg):
        """ Draws the visual debugger message
        Args:
            msg: `VisualMessage` message for visual debugger
                data: `string` message content
                type: `string` message type
        Returns:
        """

        self.msg = msg.data
        self.type = msg.type
        
        time.sleep(self._VISUAL_DEBUGGER_TIME)
        
        self.msg = ""
        self.type = "INFO"

    def draw(self, img):
        """ Draw the visual debugger message
        Args:
            img: `cv2.math` image to draw visual
                debugger message
        Returns:
        """

        if not self.msg:
            return

        color = (255, 255, 255)
        if (self.type == "ERROR" or
            self.type == "ERR"):
            color = (0, 0, 255)
        elif (self.type == "WARNING" or
            self.type == "WARN"):
            color = (0, 255, 255)
        elif self.type == "OKGREEN":
            color = (0, 255, 0)

        print_text_list(
            img=img, tex_list=[self.msg], 
            color=color, orig=(10, int(img.shape[0]*0.95)), 
            fontScale=0.7)

class ExtrinsicSubscriber():

    def __init__(self, parent_node, cam_labels=["C"]):

        self._VIDEO_WIDTH = int(os.getenv(key="VIDEO_WIDTH", default=640))
        self._VIDEO_HEIGHT = int(os.getenv(key="VIDEO_HEIGHT", default=360))

        # Subscribers
        self._sub_extrinsic_params = parent_node.create_subscription(
            msg_type=Extrinsic_msg, 
            topic='video_calibrator/extrinsic_parameters', 
            callback=self.cb_extrinsic_params, qos_profile=2,
            callback_group=parent_node.callback_group
            )

        # Read intrinsic parameters from file
        self.intrinsic = IntrinsicClass()

        # extrinsic parameters dictionary
        self.extrinsic = Extrinsic(
            dist=self.intrinsic.distortion_coefficients,
            mtx=self.intrinsic.mtx,
            cam_labels=cam_labels
            )

    def cb_extrinsic_params(self, msg):
        """ Re-assing extrinsic calibration 
        Args:
            msg: `VisualMessage` message for visual debugger
                data: `string` message content
                type: `string` message type
        Returns:
        """

        try: 
            if msg.cam_label in self.extrinsic.cams.keys():
                self.extrinsic.load(
                    mtx=self.intrinsic.mtx, 
                    dist=self.intrinsic.distortion_coefficients,
                    FILE_NAME="Extrinsic_{}_{}_{}.yaml".format(
                        self._VIDEO_WIDTH, 
                        self._VIDEO_HEIGHT, 
                        msg.cam_label)
                        )

                for key, val in self.update.items():
                    val = True

        except Exception as e:
            printlog(msg="Error getting extrinsic calibration"
                "from topic, {}".format(e), msg_type="ERROR")
            return False
        printlog(msg="Extrinsic parameters for CAM{} updated".format(
            msg.cam_label), msg_type="INFO")

class WebclientControl():

    def __init__(self, parent_node):

        self.control_tilt = 0
        self.control_pan = 0
        self.control_throttle = 0

class WaypointSuscriber():

    def __init__(self, parent_node, extrinsic, intrinsic):

        # ---------------------------------------------------------------------
        # Enviroment variables
        self._GUI_WAYPOINT_AREA = int(os.getenv(
            key="GUI_WAYPOINT_AREA", default=1))

        # ---------------------------------------------------------------------
        self.extrinsic = extrinsic
        self.extrinsic.update["WaypointSuscriber"] = True
        self.intrinsic = intrinsic

        self.cam_label = "C" # Camera label to get extrinsic
        self.x_norm = None # Normalized X axis Waypoint coordinate 
        self.y_norm = None # Normalized Y axis Waypoint coordinate
        self.x_img = None # X axis Waypoint coordinate 
        self.y_img = None # Y axis Waypoint coordinate 
        self.incnt = False # Waypoint coordinate is inside contour

        # Subscribers
        self._sub_screen_point = parent_node.create_subscription(
            msg_type=Waypoint, 
            topic='video_streaming/waypoint_pt', 
            callback=self.cb_screen_point, qos_profile=2,
            callback_group=parent_node.callback_group
            )

        # ---------------------------------------------------------------------
        # Boot projection
        self._CURV_OFFSET = float(os.getenv("GUI_PROJECTION_BOT_CURV_OFFSET", 0.003))
        self._BOT_MARGI = float(os.getenv("GUI_PROJECTION_BOT_MARGI", 0.08))
        self._BOT_WIDTH = float(os.getenv("GUI_PROJECTION_BOT_WIDTH", 0.5))
        self._HORZL_LEN = int(os.getenv("GUI_PROJECTION_BOT_HORZL_LEN", 10))
        self._VER_THICK = int(os.getenv("GUI_PROJECTION_BOT_VER_THICK", 2))
        self._HOZ_THICK = int(os.getenv("GUI_PROJECTION_BOT_HOZ_THICK", 2))
        self._SHOW_PROJ = int(os.getenv("GUI_PROJECTION_SHOW_LOCAL", 0))
        self._COLORS = [(0, 0, 255), (32, 165, 218), (0, 255, 255), (0, 255, 0)]
        self._DISTAN_M = [1.0, 1.5, 3.0, 5.0]

        # Curve coefficients for left and right lines
        self.y_limit = 0
        self.AR = 0.0
        self.BR = 0.0
        self.CR = 0.0
        self.AL = 0.0
        self.BL = 0.0
        self.CL = 0.0
        
        self._proj_m = None
        self._cnt_line = None
        self.y_limit = None

        self.curvature = 0.0
        self.distord_lines = True

    def cb_screen_point(self, msg):

        try: 
            self.x_norm = msg.x
            self.y_norm = msg.y
            # print(self.x_norm, self.y_norm, flush=True)

            # If there's no camera calibartion
            if self.extrinsic.cams[self.cam_label] is None:
                raise Exception(f'camera {self.cam_label} no calibrated')

            # print(self.extrinsic.cams[self.cam_label].keys())
            self.x_img = int(self.x_norm*self.extrinsic.cams[self.cam_label]["image_size"][0])
            self.y_img = int(self.y_norm*self.extrinsic.cams[self.cam_label]["image_size"][1])

            # Check if the current coordinates are inside the polygon area
            # or clickable area for a valid way-point
            ValidPoint = cv2.pointPolygonTest(
                contour=self.extrinsic.cams[self.cam_label]["waypoint_area"], 
                pt=(self.x_img, self.y_img), 
                measureDist=True)

        except Exception as e:
            printlog(msg="error procesing waypoint {}".format(e), 
                msg_type="ERROR")
        
    def draw(self, img):
        
        # Draw waypoint coordinate
        if self.x_norm is not None and self.y_norm is not None:
            cv2.circle(img=img, 
                center=(
                    int(self.x_norm*img.shape[1]), 
                    int(self.y_norm*img.shape[0])), 
                radius=10, color=(255, 255, 255), thickness=1)
            cv2.circle(img=img, 
                center=(
                    int(self.x_norm*img.shape[1]), 
                    int(self.y_norm*img.shape[0])), 
                radius=2, color=(0, 0, 255), thickness=-1)
        
        # ---------------------------------------------------------------------
        # If not extrinsic calibration then continue
        if self.extrinsic.cams[self.cam_label] is None:
            return
        elif self.extrinsic.mtx is None:
            return

        #  Draw waypoint area contour
        if self._GUI_WAYPOINT_AREA:
            cv2.drawContours(
                image=img, 
                contours=[self.extrinsic.cams[self.cam_label]["waypoint_area"]], 
                contourIdx=0, color=(0, 200, 0), thickness=2)

        # ---------------------------------------------------------------------
        # Update params
        if self.extrinsic.update["WaypointSuscriber"]:
            self.y_limit = int(
                self.extrinsic.cams[self.cam_label]["view_coord"][1] - \
                self._DISTAN_M[-1]*self.extrinsic.cams[self.cam_label]["ppmy"])

            sp = get_projection_point_src(
                coords_dst=(
                    self.extrinsic.cams[self.cam_label]["view_coord"][0], 
                    self.y_limit, 1), 
                INVM=self.extrinsic.cams[self.cam_label]["M_inv"]) 
            sp = get_distor_point(
                pt=sp, 
                mtx=self.extrinsic.mtx, 
                dist=self.extrinsic.dist)
            ip = get_projection_point_src(
                coords_dst=(
                    self.extrinsic.cams[self.cam_label]["view_coord"][0], 
                    self.extrinsic.cams[self.cam_label]["unwarped_size"][1], 1), 
                INVM=self.extrinsic.cams[self.cam_label]["M_inv"])
            ip = get_distor_point(
                pt=ip, 
                mtx=self.extrinsic.mtx, 
                dist=self.extrinsic.dist)
            self._cnt_line = (sp, ip)
            self._proj_m = []; increment = 1
        
            idx_y = - (self.extrinsic.cams[self.cam_label]["view_coord"][1] - \
                self.extrinsic.cams[self.cam_label]["unwarped_size"][1])
        
            while idx_y >= -self.extrinsic.cams[self.cam_label]["view_coord"][1] + self.y_limit:
                self._proj_m.append(round(abs(idx_y)/self.extrinsic.cams[self.cam_label]["ppmy"], 2))
                idx_y -= increment; increment += 1    

            self.extrinsic.update["WaypointSuscriber"] = False

        # ---------------------------------------------------------------------
        # Variables for polynomial
        # Lines Distance from center or bot's view coordinate
        ct_dist = int(np.ceil((self._BOT_WIDTH*0.5 + \
            self._BOT_MARGI)*self.extrinsic.cams[self.cam_label]["ppmy"])) 
        self.AR = (0.01 + self._CURV_OFFSET)*self.curvature if self.curvature > 0. else (
                   0.01 - self._CURV_OFFSET)*self.curvature
        self.AL = 0.01*self.curvature
        self.CR = self.extrinsic.cams[self.cam_label]["view_coord"][0] + ct_dist
        self.CL = self.extrinsic.cams[self.cam_label]["view_coord"][0] - ct_dist
        self.AL = 0.01*self.curvature
        self.BL = 0.0

        # ---------------------------------------------------------------------
        # Get Left and right line points
        right_proj = []; left_proj = []; increment = 1
        idx_y = - (
            self.extrinsic.cams[self.cam_label]["view_coord"][1] - \
            self.extrinsic.cams[self.cam_label]["unwarped_size"][1])
        lout = False; rout = False

        while idx_y > - self.extrinsic.cams[self.cam_label][
            "view_coord"][1] + self.y_limit:

            # Left projection line
            if not lout:
                lp = get_projection_point_src(
                    coords_dst=(self.AL*(idx_y**2) + self.BL*idx_y + self.CL, 
                    self.extrinsic.cams[self.cam_label]["view_coord"][1] + idx_y, 1), 
                    INVM=self.extrinsic.cams[self.cam_label]["M_inv"])
                if self.distord_lines:
                    lp = get_distor_point(
                        pt=lp, 
                        mtx=self.extrinsic.mtx, 
                        dist=self.extrinsic.dist)
                    in_cnt = cv2.pointPolygonTest(
                        contour=self.extrinsic.cams[self.cam_label]["waypoint_area"], 
                        pt=lp, measureDist=True) 
                else:
                    in_cnt = cv2.pointPolygonTest(
                        contour=self.extrinsic.cams[self.cam_label]["undistord_cnt"], 
                        pt=lp, measureDist=True) 
                if in_cnt >= 0:
                    left_proj.append(lp)
                else:
                    lout = True
        
            # Right projection line
            if not rout:
                rp = get_projection_point_src(
                    coords_dst=(self.AR*(idx_y**2) + self.BR*idx_y + self.CR, 
                    self.extrinsic.cams[self.cam_label]["view_coord"][1] + idx_y, 1), 
                    INVM=self.extrinsic.cams[self.cam_label]["M_inv"])
                if self.distord_lines:
                    rp = get_distor_point(
                        pt=rp, 
                        mtx=self.extrinsic.mtx, 
                        dist=self.extrinsic.dist)
                    in_cnt = cv2.pointPolygonTest(
                        contour=self.extrinsic.cams[self.cam_label]["waypoint_area"], 
                        pt=rp, measureDist=True) 
                else:
                    in_cnt = cv2.pointPolygonTest(
                        contour=self.extrinsic.cams[self.cam_label]["undistord_cnt"], 
                        pt=rp, measureDist=True) 
                if in_cnt >= 0:
                    right_proj.append(rp)
                else:
                    rout = True
            
            idx_y -= increment; increment += 1

        left_proj = np.array(left_proj)
        right_proj = np.array(right_proj)

        # ---------------------------------------------------------------------
        # Draw robots projection lines
        
        # Left side
        color_idx = 0
        thickness_idx = len(self._COLORS)
        for idx in range(len(left_proj) - 1):
            if self._proj_m[idx] > self._DISTAN_M[-1]:
                break
            # Draw horizontal lines in body projection
            while self._proj_m[idx] > self._DISTAN_M[color_idx]:
                color_idx += 1 # Change Color
                thickness_idx -= 1 if thickness_idx > 0 else thickness_idx
                cv2.line(img=img, 
                    pt1=(left_proj[idx][0], left_proj[idx][1]), 
                    pt2=(left_proj[idx][0] + self._HORZL_LEN, left_proj[idx][1]), 
                    color=self._COLORS[color_idx], 
                    thickness=self._HOZ_THICK + thickness_idx)
            # Draw vertical lines in body projection
            cv2.line(img=img, 
                pt1=tuple(left_proj[idx]), pt2=tuple(left_proj[idx + 1]), 
                color=self._COLORS[color_idx], 
                thickness=self._VER_THICK + thickness_idx)

        # right side
        color_idx = 0
        thickness_idx = len(self._COLORS)
        for idx in range(len(right_proj) - 1):
            if self._proj_m[idx] > self._DISTAN_M[-1]:
                break
            # Draw horizontal lines in body projection
            while self._proj_m[idx] > self._DISTAN_M[color_idx]:
                color_idx += 1 # Change Color
                thickness_idx -= 1 if thickness_idx > 0 else thickness_idx
                cv2.line(img=img, 
                    pt1=(right_proj[idx][0], right_proj[idx][1]), 
                    pt2=(right_proj[idx][0] - self._HORZL_LEN, right_proj[idx][1]), 
                    color=self._COLORS[color_idx], 
                    thickness=self._HOZ_THICK + thickness_idx)  

            # Draw vertical lines in body projection
            cv2.line(img=img, 
                pt1=tuple(right_proj[idx]), pt2=tuple(right_proj[idx + 1]), 
                color=self._COLORS[color_idx], 
                thickness=self._VER_THICK + thickness_idx)

        # ---------------------------------------------------------------------
        # Print doted center line
        dotline(src=img, p1=self._cnt_line[0], p2=self._cnt_line[1],
            color=(255, 255, 255), thickness=self._VER_THICK, Dl=10)

    def draw_in_proj(self, img_src, curvature=0.0, 
        win_name="LOCAL_LAUNCH_IMG_PROJ"):

        # ---------------------------------------------------------------------
        # Get bird view image
        img_src = cv2.undistort(img_src, self._mtx, self._dist, None, 
            None) if img_src is not None else np.zeros((self.mono("image_size")[1], 
                self.mono("image_size")[0], 3), np.uint8)
        img_dst = cv2.warpPerspective(img_src, self._M, 
            (self._UNWARPED_SIZE[0], self._view_cord[1]))
        
        # ---------------------------------------------------------------------
        # Draw some geometries
        cv2.line(img_dst, (0, self._UNWARPED_SIZE[1]), 
            (self._UNWARPED_SIZE[0], self._UNWARPED_SIZE[1]), (0, 0, 255), 1)
        cv2.line(img_dst, (self._view_cord[0], 0), (self._view_cord[0], 
            self._view_cord[1]), (0, 255, 255), 1)
        cv2.circle(img=img_dst, center=self.mono("bot_view_cord"), radius=5, 
            color=(0, 0, 255), thickness=-1)

        # ---------------------------------------------------------------------
        # Get Left and right line points
        right_proj = []; left_proj = []; increment = 1
        idx_y = - (self._view_cord[1] - self._UNWARPED_SIZE[1])
        while idx_y >= -self._view_cord[1] + self.y_limit:
            left_proj.append((int(self.AL*(idx_y**2) + self.BL*idx_y + self.CL), 
                self._view_cord[1] + idx_y))
            right_proj.append((int(self.AR*(idx_y**2) + self.BR*idx_y + self.CR), 
                self._view_cord[1] + idx_y))
            idx_y -= increment; increment += 1            
        left_proj = np.array(left_proj)
        right_proj = np.array(right_proj)

        color_idx = 0
        thickness_idx = len(self._COLORS)
        for idx in range(len(left_proj) - 1):
            if self._proj_m[idx] > self._DISTAN_M[-1]:
                break
            # Draw horizontal lines in body projection
            while self._proj_m[idx] > self._DISTAN_M[color_idx]:
                color_idx += 1 # Change Color
                thickness_idx -= 1 if thickness_idx > 0 else thickness_idx
                cv2.line(img=img_dst, 
                    pt1=(left_proj[idx][0], left_proj[idx][1]), 
                    pt2=(left_proj[idx][0] + self._HORZL_LEN, left_proj[idx][1]), 
                    color=self._COLORS[color_idx], 
                    thickness=self._HOZ_THICK + thickness_idx)
                cv2.line(img=img_dst, 
                    pt1=(right_proj[idx][0], right_proj[idx][1]), 
                    pt2=(right_proj[idx][0] - self._HORZL_LEN, right_proj[idx][1]), 
                    color=self._COLORS[color_idx], 
                    thickness=self._HOZ_THICK + thickness_idx)

            # Draw vertical lines in body projection
            cv2.line(img=img_dst, 
                pt1=tuple(left_proj[idx]), pt2=tuple(left_proj[idx + 1]), 
                color=self._COLORS[color_idx], 
                thickness=self._VER_THICK + thickness_idx)
            cv2.line(img=img_dst, 
                pt1=tuple(right_proj[idx]), pt2=tuple(right_proj[idx + 1]), 
                color=self._COLORS[color_idx], 
                thickness=self._VER_THICK + thickness_idx)

        # ---------------------------------------------------------------------
        cv2.imshow(win_name, img_dst); cv2.waitKey(1)

class Robot():

    def __init__(self, parent_node):

        self.stream_stitch = False
        self.stream_rear_cam = False

        # Subscribers
        self._sub_extrinsic_params = parent_node.create_subscription(
            msg_type=Bool, topic='video_streaming/stitch', 
            callback=self.cb_video_streaming_stitch, qos_profile=1,
            callback_group=parent_node.callback_group)

        self._sub_extrinsic_params = parent_node.create_subscription(
            msg_type=Bool, topic='video_streaming/rear_cam', 
            callback=self.cb_video_streaming_rear_cam, qos_profile=1,
            callback_group=parent_node.callback_group)

    def cb_video_streaming_rear_cam(self, data):
        self.stream_rear_cam = not self.stream_rear_cam

    def cb_video_streaming_stitch(self, data):
        self.stream_stitch = not self.stream_stitch

# =============================================================================