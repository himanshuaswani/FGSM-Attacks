# -*- coding: utf-8 -*-
"""MNIST_ReLU_Analysis.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1AVgJJXqKGl4ML7oUX_U5IJsn7DUnHUGM
"""

from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets
import numpy as np
import matplotlib.pyplot as plt
import torchvision.models as models
from torchvision import datasets, transforms

epsilons = [0, .05, .1, .15, .2, .25, .3]
#epsilons = [0, .01, .05, .1]
use_cuda=True

# LeNet Model definition
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
        self.conv2_drop = nn.Dropout2d()
        self.fc1 = nn.Linear(320, 50)
        self.fc2 = nn.Linear(50, 10)

    def forward(self, x):
        x = F.relu(F.max_pool2d(self.conv1(x), 2))
        x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)), 2))
        x = x.view(-1, 320)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

# MNIST Test dataset and dataloader declaration
#test_loader = torch.utils.data.DataLoader(
#    datasets.MNIST('/content/drive/MyDrive/CS726/', train=False, download=True, transform=transforms.Compose([
#            transforms.ToTensor(),
#            ])),
#        batch_size=1, shuffle=True)

# Define what device we are using
print("CUDA Available: ",torch.cuda.is_available())
device = torch.device("cuda" if (use_cuda and torch.cuda.is_available()) else "cpu")

# Initialize the network
model = Net().to(device)

# Load the pretrained model
# model.load_state_dict(torch.load(pretrained_model, map_location='cpu'))

# Set the model in evaluation mode. In this case this is for the Dropout layers
#model.eval()

# Load the datasets
trainset = datasets.MNIST(root='/content/drive/MyDrive/CS726/mnist_train', train=True, download=True, transform=transforms.Compose([
            transforms.ToTensor()]))
trainloader = torch.utils.data.DataLoader(trainset, batch_size = 16, shuffle = True)

testset = datasets.MNIST(root='/content/drive/MyDrive/CS726/mnist_test', train=False, download=True, transform=transforms.Compose([
            transforms.ToTensor()]))
testloader = torch.utils.data.DataLoader(testset, batch_size = 1, shuffle = True)

# Set the optimizer
import torch.optim as optim

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.001)

# Train the model
for epoch in range(0):  # loop over the dataset multiple times

    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        # get the inputs; data is a list of [inputs, labels]
        inputs, labels = data[0].to(device),data[1].to(device)

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        # print statistics
        running_loss += loss.item()
        if i % 1000 == 0:    # print every 100 mini-batches
            print('[%d, %5d] loss: %.3f' %
                  (epoch + 1, i + 1, running_loss / 1000))
            running_loss = 0.0

print('Finished Training')

# Save the model
PATH = '/content/drive/MyDrive/CS726/lenet_mnist.pth'
#torch.save(model.state_dict(), PATH)

# Load the model
PATH = '/content/drive/MyDrive/CS726/lenet_mnist.pth'
model.load_state_dict(torch.load(PATH))

# Test the model
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for data in testloader:
        images, labels = data[0].to(device), data[1].to(device)
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print('Accuracy of the network on test images: %d %%' % (100 * correct / total))

print(model.fc1.weight.data.shape)
print(model.fc2.weight.data.shape)
# Percentage of Pruning
p = 0.2

# Prune out the weights
W = model.fc1.weight.data
edges = []
for i in range(50):
  for j in range(320):
    edges.append([abs(W[i,j]),i,j])
print(edges)
edges.sort(key = lambda x:x[0])
print(edges)
for n in range(int(p*50*320)):
  W[edges[n][1],edges[n][2]] = 0

model.fc1.weight.data = W

# Prune out the weights
W = model.fc2.weight.data
edges = []
for i in range(10):
  for j in range(50):
    edges.append([abs(W[i,j]),i,j])
print(edges)
edges.sort(key = lambda x:x[0])
print(edges)
for n in range(int(p*10*50)):
  W[edges[n][1],edges[n][2]] = 0

model.fc2.weight.data = W

# FGSM attack code
def fgsm_attack(image, epsilon, data_grad):
    #print(image.shape)
    # Collect the element-wise sign of the data gradient
    sign_data_grad = data_grad.sign()
    # Create the perturbed image by adjusting each pixel of the input image
    perturbed_image = image + epsilon*sign_data_grad
    # Adding clipping to maintain [0,1] range
    perturbed_image = torch.clamp(perturbed_image, 0, 1)
    # Return the perturbed image
    return perturbed_image

from random import seed
from random import random
# Pruned FGSM attack code
def pruned_fgsm_attack(image, epsilon, data_grad):
    # Set percentage
    per = 0.01
    # Collect the element-wise sign of the data gradient
    sign_data_grad = data_grad.sign()
    # Create the perturbed image by adjusting each pixel of the input image
    perturbed_image = image + epsilon*sign_data_grad
    # Adding clipping to maintain [0,1] range
    perturbed_image = torch.clamp(perturbed_image, 0, 1)
    for i in range(28):
      for j in range(28):
        if random() > per:
          perturbed_image[0,0,i,j] = image[0,0,i,j]
    # Return the perturbed image
    return perturbed_image

def test( model, device, test_loader, epsilon ):

    # Accuracy counter
    correct = 0
    adv_examples = []

    # Loop over all examples in test set
    for data, target in test_loader:

        # Send the data and label to the device
        data, target = data.to(device), target.to(device)

        # Set requires_grad attribute of tensor. Important for Attack
        data.requires_grad = True

        # Forward pass the data through the model
        output = model(data)
        init_pred = output.max(1, keepdim=True)[1] # get the index of the max log-probability

        # If the initial prediction is wrong, dont bother attacking, just move on
        if init_pred.item() != target.item():
            continue

        # Calculate the loss
        loss = F.nll_loss(output, target)

        # Zero all existing gradients
        model.zero_grad()

        # Calculate gradients of model in backward pass
        loss.backward()

        # Collect datagrad
        data_grad = data.grad.data

        # Call FGSM Attack
        #perturbed_data = fgsm_attack(data, epsilon, data_grad)

        # Call Pruned FGSM Attack
        perturbed_data = pruned_fgsm_attack(data, epsilon, data_grad)

        # Re-classify the perturbed image
        output = model(perturbed_data)

        # Check for success
        final_pred = output.max(1, keepdim=True)[1] # get the index of the max log-probability
        if final_pred.item() == target.item():
            correct += 1
            # Special case for saving 0 epsilon examples
            if (epsilon == 0) and (len(adv_examples) < 5):
                adv_ex = perturbed_data.squeeze().detach().cpu().numpy()
                adv_examples.append( (init_pred.item(), final_pred.item(), adv_ex) )
        else:
            # Save some adv examples for visualization later
            if len(adv_examples) < 5:
                adv_ex = perturbed_data.squeeze().detach().cpu().numpy()
                adv_examples.append( (init_pred.item(), final_pred.item(), adv_ex) )

    # Calculate final accuracy for this epsilon
    final_acc = correct/float(len(test_loader))
    print("Epsilon: {}\tTest Accuracy = {} / {} = {}".format(epsilon, correct, len(test_loader), final_acc))

    # Return the accuracy and an adversarial example
    return final_acc, adv_examples

accuracies = []
examples = []

# Run test for each epsilon
for eps in epsilons:
    acc, ex = test(model, device, testloader, eps)
    accuracies.append(acc)
    examples.append(ex)

# No Pruning [0.9452, 0.8465, 0.6676, 0.4509, 0.2365, 0.1036, 0.0422]
# 10% of FC1 [0.9451, 0.8468, 0.6675, 0.4513, 0.237, 0.1055, 0.0423]
# 20% of FC1 [0.9452, 0.8464, 0.6653, 0.4464, 0.2286, 0.1071, 0.0424]
# 30% of FC1 [0.9441, 0.8439, 0.6631, 0.4392, 0.2269, 0.1086, 0.0448]
# 40% of FC1 [0.9435, 0.8396, 0.6543, 0.4229, 0.2214, 0.1072, 0.0446]
# 10% of FC1 and FC2 [0.9449, 0.8454, 0.6673, 0.4502, 0.2355, 0.1065, 0.0425]
# 20% of FC1 and FC2
# 30% of FC1 and FC2
# Pruned FGSM Attack
# 50% pixels changed [0.9452, 0.9061, 0.8477, 0.7672, 0.667, 0.5626, 0.4462]
# 10% pixels changed [0.9452, 0.9378, 0.9301, 0.9242, 0.9151, 0.9068, 0.8962]
# 01% pixels changed [0.9452, 0.9448, 0.9437, 0.9437, 0.9429, 0.9411, 0.9417]

print(accuracies)

plt.figure(figsize=(5,5))
plt.plot(epsilons, accuracies, "*-")
plt.yticks(np.arange(0, 1.1, step=0.1))
plt.xticks(np.arange(0, .35, step=0.05))
plt.title("Accuracy vs Epsilon")
plt.xlabel("Epsilon")
plt.ylabel("Accuracy")
plt.show()

# Plot several examples of adversarial samples at each epsilon
cnt = 0
plt.figure(figsize=(8,10))
for i in range(len(epsilons)):
    for j in range(len(examples[i])):
        cnt += 1
        plt.subplot(len(epsilons),len(examples[0]),cnt)
        plt.xticks([], [])
        plt.yticks([], [])
        if j == 0:
            plt.ylabel("Eps: {}".format(epsilons[i]), fontsize=14)
        orig,adv,ex = examples[i][j]
        plt.title("{} -> {}".format(orig, adv))
        plt.imshow(ex, cmap="gray")
plt.tight_layout()
plt.show()

# Sensitivity Map Generation
# Pick a class. Choose test images that are currently correctly classified. 
# For each of them, change one pixel according to gradient sign and check if output class changes.

# Choose class
class_chosen = 1
Xclass = []
# Test the model
model.eval()

with torch.no_grad():
    for data in testloader:
        images, labels = data[0].to(device), data[1].to(device)
        if labels == class_chosen:
          outputs = model(images)
          _, predicted = torch.max(outputs.data, 1)
          if predicted == labels:  
            Xclass.append(images)

print(len(Xclass))
print(Xclass[0].shape)

sm = np.zeros((28,28))
plt.imshow(sm, cmap='gray')
plt.show()

def generate_sensitivity_map_fgsm(model, epsilon, Xclass, chosen_class):
  sm = np.zeros((28,28))
  #with torch.no_grad():
  for image in Xclass:
    for i in range(28):
      for j in range(28):
        # Send the data and label to the device
        data = image.to(device)
        # Set requires_grad attribute of tensor. Important for Attack
        data.requires_grad = True
        # Forward pass the data through the model
        output = model(data)
        # Calculate the loss
        loss = F.nll_loss(output, torch.tensor([class_chosen]).to(device))
        # Zero all existing gradients
        model.zero_grad()
        # Calculate gradients of model in backward pass
        loss.backward()
        # Collect datagrad
        data_grad = data.grad.data
        # Calculate the sign 
        sign_data_grad = data_grad.sign()
        #print(sign_data_grad.shape)
        perturbed_image = image + 0
        #perturbed_image = torch.zeros((1,1,28,28))
        #for m in range(28):
        #  for n in range(28):
        #    perturbed_image[0,0,m,n] = image[0,0,m,n]
        # Find out sign of pixel i,j
        s = sign_data_grad[0,0,i,j]
        
        if s > 0:
          if perturbed_image[0,0,i,j] + epsilon <= 1:
            perturbed_image[0,0,i,j] += epsilon
          else:
            perturbed_image[0,0,i,j] = 1
        else:
          if perturbed_image[0,0,i,j] - epsilon >= 0:
            perturbed_image[0,0,i,j] -= epsilon
          else:
            perturbed_image[0,0,i,j] = 0
        
        perturbed_image.to(device)
        outputs = model(perturbed_image)
        _, predicted = torch.max(outputs.data, 1)

        if predicted != class_chosen:
          sm[i,j] += 1
  sm /= len(Xclass)
  plt.imshow(sm, cmap='gray')
  plt.show()

def generate_sensitivity_map(model, epsilon, Xclass, chosen_class):
  sm = np.zeros((28,28))
  #with torch.no_grad():
  for image in Xclass:
    for i in range(28):
      for j in range(28):
        prev = 0
        if image[0,0,i,j] + epsilon <= 1:
          image[0,0,i,j] += epsilon
        else:
          prev = image[0,0,i,j]
          image[0,0,i,j] = 1
        
        outputs = model(image)
        _, predicted = torch.max(outputs.data, 1)
        if predicted != class_chosen:
          sm[i,j] += 1
        
        if prev != 0:
          image[0,0,i,j] = prev
        else:
          image[0,0,i,j] -= epsilon
  sm /= len(Xclass)
  plt.imshow(sm, cmap='gray')
  plt.show()

def generate_sensitivity_map_down(model, epsilon, Xclass, chosen_class):
  sm = np.zeros((28,28))
  #with torch.no_grad():
  for image in Xclass:
    for i in range(28):
      for j in range(28):
        prev = 0
        if image[0,0,i,j] - epsilon >= 0:
          image[0,0,i,j] -= epsilon
        else:
          prev = image[0,0,i,j]
          image[0,0,i,j] = 0
        
        outputs = model(image)
        _, predicted = torch.max(outputs.data, 1)
        if predicted != class_chosen:
          sm[i,j] += 1
        
        if prev != 0:
          image[0,0,i,j] = prev
        else:
          image[0,0,i,j] += epsilon
  sm /= len(Xclass)
  plt.imshow(sm, cmap='gray')
  plt.show()

print(generate_sensitivity_map_fgsm(model,0.2,Xclass[0:10],1))

epsilons = [.2, .25, .3]
for eps in epsilons:
  print(eps)
  generate_sensitivity_map(model,eps,Xclass,1)
  #generate_sensitivity_map_fgsm(model,eps,Xclass,1)
  generate_sensitivity_map_down(model,eps,Xclass,1)

epsilons = [.2, .25, .3]
for eps in epsilons:
  print(eps)
  #generate_sensitivity_map(model,eps,Xclass,1)
  generate_sensitivity_map_fgsm(model,eps,Xclass,1)
  #generate_sensitivity_map_down(model,eps,Xclass,1)