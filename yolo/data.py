"""
CS 6384 Homework 4 Programming
Implement the __getitem__() function in this python script
"""
import torch
import torch.utils.data as data
import csv
import os, math
import sys
import time
import random
import numpy as np
import cv2
import glob
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# The dataset class
class CrackerBox(data.Dataset):
    def __init__(self, image_set = 'train', data_path = 'yolo/data'):

        self.name = 'cracker_box_' + image_set
        self.image_set = image_set
        self.data_path = data_path
        self.classes = ('__background__', 'cracker_box')
        self.width = 640
        self.height = 480
        self.yolo_image_size = 448
        self.scale_width = self.yolo_image_size / self.width
        self.scale_height = self.yolo_image_size / self.height
        self.yolo_grid_num = 7
        self.yolo_grid_size = self.yolo_image_size / self.yolo_grid_num
        # split images into training set and validation set
        self.gt_files_train, self.gt_files_val = self.list_dataset()
        # the pixel mean for normalization
        self.pixel_mean = np.array([[[102.9801, 115.9465, 122.7717]]], dtype=np.float32)

        # training set
        if image_set == 'train':
            self.size = len(self.gt_files_train)
            self.gt_paths = self.gt_files_train
            print('%d images for training' % self.size)
        else:
            # validation set
            self.size = len(self.gt_files_val)
            self.gt_paths = self.gt_files_val
            print('%d images for validation' % self.size)


    # list the ground truth annotation files
    # use the first 100 images for training
    def list_dataset(self):
    
        filename = os.path.join(self.data_path, '*.txt')
        gt_files = sorted(glob.glob(filename))
        
        gt_files_train = gt_files[:100]
        gt_files_val = gt_files[100:]
        
        return gt_files_train, gt_files_val


    # TODO: implement this function
    def __getitem__(self, idx):  
      img_path = os.path.join(self.data_path, f"{idx+1:06}.jpg")
      # Load image
      img = cv2.imread(img_path)
      img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
      print(img_path)
      
      # Get box file path
      box_path = os.path.join(self.data_path, f"{idx+1:06}-box.txt")
      
      # Load box coordinates from file
      with open(box_path, "r") as f:
          box_coords = f.read().splitlines()
          box_coords = [float(coord) for coord in box_coords[0].split(" ")]
          
      # Get ground truth file path
      gt_path = os.path.join(self.data_path, f"{idx+1:06}-gt.jpg")
      # Load ground truth image
      gt_img = cv2.imread(gt_path)
      gt_img = cv2.cvtColor(gt_img, cv2.COLOR_BGR2RGB)
      # Normalize image pixels
      img_size = 448
      img = cv2.resize(img, (img_size, img_size))
      img = img.astype(np.float32)
      img -= self.pixel_mean
      img = img/255.0
      img = img.transpose((2, 0, 1))
      # Normalize box coordinates to (0, 1)
      cell_size = 64
      img_size = 448
      x1, y1, x2, y2 = box_coords
      x_center = (x1 + x2) / (2 *self.width)
      y_center = (y1 + y2) / (2 *self.height)
      width = (x2 - x1) / self.width
      height = (y2 - y1) / self.height
      
      # Initialize ground truth box and mask tensors
      gt_box = np.zeros((5, 7, 7))
      gt_mask = np.zeros((7, 7))
      
      # Compute cell index for ground truth box center
      #cell_row = int(y_center*7)
      #cell_col = int(x_center*7)
      cell_row = min(max(int(y_center * 7), 0), 6)
      cell_col = min(max(int(x_center * 7), 0), 6)
      # Set mask value to 1 for cell containing ground truth box center(
      gt_mask[cell_row, cell_col] = 1
      
      # Set values for ground truth box
      gt_box[0, cell_row, cell_col] = x_center
      gt_box[1, cell_row, cell_col] = y_center
      gt_box[2, cell_row, cell_col] = width
      gt_box[3, cell_row, cell_col] = height
      gt_box[4, cell_row, cell_col] = 1
      
      # Convert to PyTorch tensors
      img_tensor = torch.from_numpy(img)
      gt_box_tensor = torch.from_numpy(gt_box)
      gt_mask_tensor = torch.from_numpy(gt_mask)
      
      return {"image": img_tensor, "gt_box": gt_box_tensor, "gt_mask": gt_mask_tensor} 


    # len of the dataset
    def __len__(self):
        return self.size
        

# draw grid on images for visualization
def draw_grid(image, line_space=64):
    H, W = image.shape[:2]
    image[0:H:line_space] = [255, 255, 0]
    image[:, 0:W:line_space] = [255, 255, 0]


# the main function for testing
if __name__ == '__main__':
    dataset_train = CrackerBox('train')
    dataset_val = CrackerBox('val')
    
    # dataloader
    train_loader = torch.utils.data.DataLoader(dataset_train, batch_size=1, shuffle=False, num_workers=0)
    
    # visualize the training data
    for i, sample in enumerate(train_loader):
        
        image = sample['image'][0].numpy().transpose((1, 2, 0))
        gt_box = sample['gt_box'][0].numpy()
        gt_mask = sample['gt_mask'][0].numpy()

        y, x = np.where(gt_mask == 1)
        cx = gt_box[0, y, x] * dataset_train.yolo_grid_size + x * dataset_train.yolo_grid_size
        cy = gt_box[1, y, x] * dataset_train.yolo_grid_size + y * dataset_train.yolo_grid_size
        w = gt_box[2, y, x] * dataset_train.yolo_image_size
        h = gt_box[3, y, x] * dataset_train.yolo_image_size

        x1 = cx - w * 0.5
        x2 = cx + w * 0.5
        y1 = cy - h * 0.5
        y2 = cy + h * 0.5

        print(image.shape, gt_box.shape)
        
        # visualization
        fig = plt.figure()
        ax = fig.add_subplot(1, 3, 1)
        im = image * 255.0 + dataset_train.pixel_mean
        im = im.astype(np.uint8)
        plt.imshow(im[:, :, (2, 1, 0)])
        plt.title('input image (448x448)', fontsize = 16)

        ax = fig.add_subplot(1, 3, 2)
        draw_grid(im)
        plt.imshow(im[:, :, (2, 1, 0)])
        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1, linewidth=2, edgecolor='g', facecolor="none")
        ax.add_patch(rect)
        plt.plot(cx, cy, 'ro', markersize=12)
        plt.title('Ground truth bounding box in YOLO format', fontsize=16)
        
        ax = fig.add_subplot(1, 3, 3)
        plt.imshow(gt_mask)
        plt.title('Ground truth mask in YOLO format (7x7)', fontsize=16)
        plt.show()
