"""
QuadricSLAM Copyright 2020, ARC Centre of Excellence for Robotic Vision, Queensland University of Technology (QUT)
Brisbane, QLD 4000
All Rights Reserved

See LICENSE for the license information

Description: Drawing interface
Author: Lachlan Nicholson (Python)
"""

# import standard libraries
import os
import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

# import gtsam and extension
import gtsam
import quadricslam

# modify system path so file will work when run directly or as a module
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# import custom python modules
sys.dont_write_bytecode = True
from base.containers import Trajectory
from base.containers import Odometry
from base.containers import Quadrics
from base.containers import Boxes

symbolChr = lambda i: chr(gtsam.symbolChr(i))

class MPLDrawing(object):
    def __init__(self, figname):
        self._figname = figname

    def plot_system(self, graph, estimate):
        """
        Plots the trajectory and quadrics
        Color represents the sum of boundingbox factor errors at each pose
        """
        
        # extract variables and factors
        trajectory = Trajectory.from_values(estimate)
        quadrics = Quadrics.from_values(estimate)

        # collect nonlinear factors from graph
        box_factors = [quadricslam.BoundingBoxFactor.getFromGraph(graph, i) for i in range(graph.size()) if graph.at(i).keys().size() == 2 and chr(gtsam.symbolChr(graph.at(i).keys().at(1))) == 'q']
        # odom_factors = [graph.at(i) for i in range(graph.size()) if graph.at(i).keys().size() == 2 and chr(gtsam.symbolChr(graph.at(i).keys().at(1))) == 'x']

        # extract x-y positions
        xy = np.array([[pose.x(), pose.y()] for pose in trajectory.data()])

        # extract error at each pose
        errors = []
        for pose_key in trajectory.keys():

            # get factors for current pose
            bbfs = [f for f in box_factors if gtsam.symbolIndex(f.keys().at(0)) == pose_key]

            # get sum of each bbf error at pose 
            error = np.sum([np.square(bbf.unwhitenedError(estimate)).sum() for bbf in bbfs])
            errors.append(error)

        # open and clear figure
        figure = plt.figure(self._figname)
        figure.clf()

        # plot trajectory x-y
        plt.plot(xy[:,0], xy[:,1], linestyle='-', c='c', zorder=1)
        plt.scatter(xy[:,0], xy[:,1], s=25, c=errors, zorder=9)
        plt.colorbar()
        
        # plot quadrics
        for quadric in quadrics.data():
            plt.plot(quadric.pose().x(), quadric.pose().y(), marker='o', markersize=5, c='m', fillstyle='none')
            plt.plot(quadric.pose().x(), quadric.pose().y(), marker='o', markersize=5, c='m', alpha=0.5)
        
        # show plot
        plt.show()

    def plot_result(self, trajectories, maps, colors, names=None):
        """ 
        Compares a number of trajectories and maps. 

        :param - trajectories: list of Trajectory objects
        :param - maps: list of Quadrics objects
        :param - colors: list of matplotlib colors for each trajectory/map
        :param - names: list of names for legend
        """

        # open and clear figure
        figure = plt.figure(self._figname)
        figure.clf()

        # plot trajectories
        for i, trajectory in enumerate(trajectories):
            xy = np.array([[pose.x(), pose.y()] for pose in trajectory.data()])
            plt.plot(xy[:,0], xy[:,1], marker='o', markersize=3, c=colors[i], label='traj {}'.format(i))
        
        # plot quadrics
        for i, quadrics in enumerate(maps):
            for quadric in quadrics.data():
                plt.plot(quadric.pose().x(), quadric.pose().y(), marker='o', markersize=3, c=colors[i], label='quads {}'.format(i))

        # draw legend
        if names is not None:
            legend_lines = [Line2D([0], [0], color=colors[i], lw=2) for i in range(len(names))]
            figure.legend(legend_lines, names)

        # show plot
        plt.show()




class CV2Drawing(object):
    def __init__(self, image):
        self._image = image
    
    def box(self, box, color=(0,0,255), thickness=2):
        cv2.rectangle(self._image, (int(box.xmin()),int(box.ymin())), (int(box.xmax()),int(box.ymax())), color, thickness)

    def text(self, text, lower_left, color=(255,255,255), thickness=1, background=False, background_color=(0,0,255), background_margin=3):
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5

        lower_left = [lower_left[0]+background_margin, lower_left[1]-background_margin]
        text_size = cv2.getTextSize(text, font, font_scale, thickness)
        text_width = text_size[0][0] + background_margin * 2
        text_height = text_size[0][1] + background_margin * 2
        image_width = self._image.shape[1]
        image_height = self._image.shape[0]

        # lower_left = [upper_left[0], upper_left[1]+text_width]
        final_position = list(lower_left)
        final_position[1] = int(np.clip(lower_left[1], text_height, image_height))
        final_position[0] = int(np.clip(lower_left[0], 0, image_width-text_width))
        final_position = tuple(final_position)

        if (background):
            upper_left = [final_position[0], final_position[1]-text_height]
            xmin = upper_left[0]-background_margin+1
            ymin = upper_left[1]-background_margin+4
            xmax = upper_left[0]+text_width+background_margin
            ymax = upper_left[1]+text_height+background_margin+1
            cv2.rectangle(self._image, (int(xmin), int(ymin)), (int(xmax), int(ymax)), background_color, cv2.FILLED)
        cv2.putText(self._image, text, final_position, font, font_scale, color, thickness, cv2.LINE_AA)

    def box_and_text(self, box, box_color, text, text_color):
        box_thickness = 2
        self.box(box, box_color, thickness=box_thickness)
        self.text(text, (box.xmin()-box_thickness,box.ymin()-box_thickness), text_color, 1, True, box_color)

    def quadric(self, pose, quadric, calibration, color=(255,0,0), alpha=1):
        points_2D = generate_uv_spherical(quadric, pose, calibration, 10, 10)
        points_2D = np.round(points_2D).astype('int')
        # color = (0,0,255)
        color = (color[2], color[1], color[0]) # rgb to bgr

        if alpha!=1:
            full_image = self._image.copy()

        for i in range(points_2D.shape[0]):
            for j in range(points_2D.shape[1]-1):
                point_2D = points_2D[i,j]
                nextpoint_2D = points_2D[i,j+1]
                cv2.line(self._image, (point_2D[0], point_2D[1]), (nextpoint_2D[0], nextpoint_2D[1]), color, 1, cv2.LINE_AA)

        for j in range(points_2D.shape[1]):
            for i in range(points_2D.shape[0]-1):
                point_2D = points_2D[i,j]
                nextpoint_2D = points_2D[i+1,j]
                cv2.line(self._image, (point_2D[0], point_2D[1]), (nextpoint_2D[0], nextpoint_2D[1]), color, 1, cv2.LINE_AA)

        if alpha!=1:
            cv2.addWeighted(self._image, alpha, full_image, 1-alpha, 0, self._image)

    def bounds_3D(self, box3D, pose, calibration, color=(255,0,255)):
        # convert 3D box to set of 8 points
        b = box3D.vector()
        points_3D = np.array([[x,y,z] for x in b[0:2] for y in b[2:4] for z in b[4:6]])

        # ensure points infront of camera
        for point in points_3D:
            if pose.between(gtsam.Pose3(gtsam.Rot3(), gtsam.Point3(point))).translation().vector()[-1] < 0:
                return

        # project 3D points to 2D
        P = quadricslam.QuadricCamera.transformToImage(pose, calibration)
        points_3DTH = np.concatenate((points_3D.T, np.ones((1,points_3D.shape[0]))))
        points_2D = P.dot(points_3DTH)
        points_2D = points_2D[0:2,:] / points_2D[2]
        points_2D = points_2D.transpose()

        # only draw if all points project correctly
        if np.any(np.isinf(points_2D)) or np.any(np.isnan(points_2D)):
            return
        
        # draw points
        for point in points_2D:
            cv2.circle(self._image, tuple(point.astype('int')), 1, color=(0,0,255), thickness=-1, lineType=cv2.LINE_AA)

        # draw lines
        for index in [(0,1),(1,3),(3,2),(2,0),(4,5),(5,7),(7,6),(6,4),(2,6),(1,5),(0,4),(3,7)]:
            p1 = tuple(points_2D[index[0]].astype('int'))
            p2 = tuple(points_2D[index[1]].astype('int'))
            cv2.line(self._image, p1, p2, color=color, thickness=1, lineType=cv2.LINE_AA)



def generate_uv_spherical(quadric, pose, calibration, theta_points=30, phi_points=30):
    rotation = quadric.pose().rotation().matrix()
    translation = quadric.pose().translation().vector()

    # Radii corresponding to the coefficients:
    rx, ry, rz = quadric.radii()

    # Set of all spherical angles:
    u = np.linspace(0, 2 * np.pi, theta_points)
    v = np.linspace(0, np.pi, phi_points)

    # Cartesian coordinates that correspond to the spherical angles:
    x = rx * np.outer(np.cos(u), np.sin(v))
    y = ry * np.outer(np.sin(u), np.sin(v))
    z = rz * np.outer(np.ones_like(u), np.cos(v))
    # w = np.ones(x.shape)
    points = np.stack((x,y,z))

    points_2D = np.zeros((points.shape[1], points.shape[2], 2))
    transform_to_image = quadricslam.QuadricCamera.transformToImage(pose, calibration)

    # warp points to quadric (3D) and project to image (2D)
    for i in range(points.shape[1]):
        for j in range(points.shape[2]):
            # point = [x[i,j], y[i,j], z[i,j], 1.0]
            point = points[:,i,j]
            warped_point = point.dot(np.linalg.inv(rotation))
            warped_point += translation

            point_3D = np.array([warped_point[0], warped_point[1], warped_point[2], 1.0])
            point_2D = transform_to_image.dot(point_3D)
            point_2D = point_2D[:-1]/point_2D[-1]
            points_2D[i,j] = point_2D

    return points_2D