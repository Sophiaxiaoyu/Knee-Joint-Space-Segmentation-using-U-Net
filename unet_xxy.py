# -*- coding: utf-8 -*-


import zipfile
import os
files = zipfile.ZipFile('Knee_Joint_Space_Segmentation--main.zip','r')
files.extractall(os.getcwd())

!rm -r /content/Knee_Joint_Space_Segmentation--main/Test_Y/.ipynb_checkpoints
!rm -r /content/Knee_Joint_Space_Segmentation--main/Test_X/.ipynb_checkpoints

"""Install packages"""

import os
import random
import torch
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from PIL import Image
import numpy as np
from sklearn.metrics import jaccard_score
import shutil

torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

""" create a custom dataset class for knee joint space dataset."""

class KneeJointSpaceDataset(Dataset):
  def __init__(self, image_folder, mask_folder, transform=None):
    self.image_folder = image_folder
    self.mask_folder = mask_folder
    self.transform = transform
    self.image_list = os.listdir(image_folder)

  def __len__(self):
    return len(self.image_list)

  def __getitem__(self, idx):
    img_name = self.image_list[idx]
    img_path = os.path.join(self.image_folder, img_name)
    image = Image.open(img_path).convert("L")

    if self.mask_folder:
        mask_path = os.path.join(self.mask_folder, img_name)
        mask = Image.open(mask_path).convert("L")
    else:
        mask = Image.new("L", image.size)

    if self.transform:
        image = self.transform(image)
        mask = self.transform(mask)

    return image, mask

""" UNet"""

class DoubleConv(nn.Module):
  def __init__(self, in_channels, out_channels):
    super(DoubleConv, self).__init__()
    self.conv = nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True)
    )

  def forward(self, x):
    return self.conv(x)

class UNet(nn.Module):
  def __init__(self):
    super(UNet, self).__init__()
    self.encoder = nn.Sequential(
      nn.MaxPool2d(2),
      DoubleConv(1, 64),
      nn.MaxPool2d(2),
      DoubleConv(64, 128),
      nn.MaxPool2d(2),
      DoubleConv(128, 256),
      nn.MaxPool2d(2),
      DoubleConv(256, 512)
    )
    self.middle = DoubleConv(512, 1024)
    self.decoder = nn.Sequential(
      nn.ConvTranspose2d(1024, 512, 2, stride=2),
      DoubleConv(512, 512),
      nn.ConvTranspose2d(512, 256, 2, stride=2),
      DoubleConv(256, 256),
      nn.ConvTranspose2d(256, 128, 2, stride=2),
      DoubleConv(128, 128),
      nn.ConvTranspose2d(128, 64, 2, stride=2),
      DoubleConv(64, 64)
    )
    self.final = nn.Conv2d(64, 1, 1)

  def forward(self, x):
    x1 = self.encoder(x)
    x2 = self.middle(x1)
    x3 = self.decoder(x2)
    return self.final(x3)

model = UNet()
print(model)

""" load the data and create the dataloaders"""

import torchvision.transforms as transforms
train_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
])

train_img_folder = "/content/Knee_Joint_Space_Segmentation--main/Train_X"
train_mask_folder = "/content/Knee_Joint_Space_Segmentation--main/Train_Y"

dataset = KneeJointSpaceDataset(train_img_folder, train_mask_folder, train_transform)
train_loader = DataLoader(dataset, batch_size=8, shuffle=True, num_workers=2)

# Create the train_dataset instance
train_dataset = KneeJointSpaceDataset(train_img_folder, train_mask_folder, train_transform)

# Test if the dataset can be loaded
sample_image, sample_mask = train_dataset[0]
print(f"Sample image shape: {sample_image.shape}")
print(f"Sample mask shape: {sample_mask.shape}")

""" train the modelKneeJointSpaceSegmentation."""

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

model = UNet().to(device)
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

num_epochs = 150

for epoch in range(num_epochs):
  model.train()
  epoch_loss = 0.0

  for images, masks in train_loader:
    images = images.to(device)
    masks = masks.to(device)

    optimizer.zero_grad()

    logits = model(images)
    loss = criterion(logits, masks)

    loss.backward()
    optimizer.step()

    epoch_loss += loss.item()

  print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {epoch_loss / len(train_loader):.4f}")

"""Randomly select five images from the dataset and put them at Test_X."""

test_x_folder = "Knee_Joint_Space_Segmentation--main/Test_X"
os.makedirs(test_x_folder, exist_ok=True)

all_images = os.listdir(train_img_folder)
random.shuffle(all_images)

for img_name in all_images[:5]:
    shutil.move(os.path.join(train_img_folder, img_name), os.path.join(test_x_folder, img_name))

"""Apply the model (modelKneeJointSpaceSegmentation) on five random images available at Test_X and Save the predictive masks at Test_Y. """

test_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
])

test_dataset = KneeJointSpaceDataset(test_x_folder, None, test_transform)
test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=2)

test_y_folder = "Knee_Joint_Space_Segmentation--main/Test_Y"
os.makedirs(test_y_folder, exist_ok=True)

model.eval()

with torch.no_grad():
  for idx, (images, _) in enumerate(test_loader):
    images = images.to(device)
    logits = model(images)
    preds = torch.sigmoid(logits)
    
    # Apply a threshold of 0.5
    binary_preds = (preds > 0.5).float()
    
    pred_img = Image.fromarray((binary_preds.squeeze().cpu().numpy() * 255).astype(np.uint8))
    img_name = os.listdir(test_x_folder)[idx]
    pred_img.save(os.path.join(test_y_folder, img_name))
    print(f"Prediction saved at {os.path.join(test_y_folder, img_name)}")

torch.save(model.state_dict(), "Knee_Joint_Space_Segmentation--main/modelKneeJointSpaceSegmentation.pth")

"""IoU"""

def calculate_iou(y_true, y_pred):
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    intersection = np.logical_and(y_true, y_pred)
    union = np.logical_or(y_true, y_pred)
    iou_score = np.sum(intersection) / np.sum(union)
    return iou_score

iou_scores = []

for img_name in os.listdir(test_x_folder):
    true_mask_path = os.path.join(train_mask_folder, img_name)
    pred_mask_path = os.path.join(test_y_folder, img_name)

    true_mask = np.array(Image.open(true_mask_path).convert("1").resize((256, 256)))
    pred_mask = np.array(Image.open(pred_mask_path).convert("1"))

    iou = calculate_iou(true_mask, pred_mask)
    iou_scores.append(iou)

print("Mean IoU:", np.mean(iou_scores))

