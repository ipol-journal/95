#!/usr/bin/env python3
import subprocess
import argparse
import math
from PIL import Image
import sys
from math import ceil
tabulate_path = "/usr/lib/python3/dist-packages"
sys.path.append(tabulate_path)
from tabulate import tabulate


# parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("pattern", type=str)
ap.add_argument("alpha", type=float)
args = ap.parse_args()

# showcontours_max_pixels is the max image size in pixels for showing the
# contours as a PDF.  If the image is small enough, the estimated contours
# are rendered as EPS and converted with Ghostscript to PDF.
showcontours_max_pixels = 25000
padding = 16

# Crop image if necessary
img = Image.open('input_0.png')
(sizeX, sizeY) = img.size
cropsize = (min(sizeX, 800), min(sizeY, 800))


if (sizeX, sizeY) != cropsize:
    (x0, y0) = (int(math.floor((sizeX - cropsize[0])/2)), int(math.floor((sizeY - cropsize[1])/2)))
    crop_img = img.crop((x0, y0, x0 + cropsize[0], y0 + cropsize[1]))
    crop_img.save('input_0.png')

showcontours = (cropsize[0]*cropsize[1] <= showcontours_max_pixels)

# Mosaic image with 16-pixel padding
p1 = ['mosaic', '-p', str(args.pattern), '-e', str(padding), 'input_0.png', 'mosaicked.png']
subprocess.run(p1) 

# Demosaic image, CPU times are recorded in stdout_*.txt files
with open('stdout_dmcswl1.txt', 'w') as stdout_dmcswl1:
    p2 = ['dmcswl1', '-p', str(args.pattern), '-a', str(args.alpha), 'mosaicked.png', 'dmcswl1.png']
    subprocess.run(p2, stdout=stdout_dmcswl1)

with open('stdout_bilinear.txt', 'w') as stdout_bilinear:
    p3 = ['dmbilinear', '-p', str(args.pattern), 'mosaicked.png', 'bilinear.png']
    subprocess.run(p3, stdout=stdout_bilinear)

# Display estimate image contours as EPS
if showcontours:
    p4 = ['dmcswl1', '-p', str(args.pattern), '-s', 'input_0.png', 'contours.eps']
    subprocess.run(p4) 

# Trim the padding
for m in ['mosaicked', 'bilinear', 'dmcswl1']:
    img = Image.open(m + '.png')
    crop_img = img.crop((padding, padding, padding + cropsize[0], padding + cropsize[1]))
    crop_img.save(m + '.png')


# Compute MSEs, the results are saved in files mse_*.txt
for m in ['bilinear', 'dmcswl1']:
    result = subprocess.run(['imdiff', '-mmse', 'input_0.png', m + '.png'], capture_output=True, text=True)
    mse_value = float(result.stdout.strip())
    rounded_mse_value = round(mse_value, 2)
    
    with open('mse_' + m + '.txt', 'w') as stdout:
        stdout.write(f'{rounded_mse_value}\n')


# Compute image differences
p6 = ['imdiff', 'input_0.png', 'dmcswl1.png', 'diffdmcswl1.png']
subprocess.run(p6)

p7 = ['imdiff', 'input_0.png', 'bilinear.png', 'diffbilinear.png']
subprocess.run(p7)

# Convert EPS to PDF
with open('stdout', 'w') as stdout:
    if showcontours:
        p8 = ['gs', '-dSAFER', '-q', '-P-', '-dCompatibilityLevel=1.4',
                    '-dNOPAUSE', '-dBATCH', '-sDEVICE=pdfwrite', 
                    '-sOutputFile=contours.pdf', '-c', '.setpdfwrite', 
                    '-f', 'contours.eps']
        val = subprocess.run(p8, stdout=stdout, stderr=stdout)
    
        if val.returncode != 0:
            with open('demo_failure.txt', 'w') as file:
                file.write("eps->pdf conversion failed," + " gs is probably missing on this system")
                showcontours = False
                sys.exit(0)  


# Resize for visualization (new size of the smallest dimension = 200)
zoomfactor = int(max(1, ceil(200.0/min(cropsize[0], cropsize[1]))))
(sizeX, sizeY) = (zoomfactor*cropsize[0], zoomfactor*cropsize[1])


for filename in ['input_0', 'mosaicked', 'dmcswl1', 'bilinear',
            'diffdmcswl1', 'diffbilinear']:
    img = Image.open(filename + '.png')
    resize_img = img.resize((sizeX, sizeY))
    resize_img.save(filename + '_zoom.png')


# Read Mean Squared Error values from text files
with open("mse_bilinear.txt", "r") as f:
    mse_bilinear = f.read()

with open("mse_dmcswl1.txt", "r") as f:
    mse_dmcswl1 = f.read()


# Read CPU time values from text files
with open("stdout_bilinear.txt", "r") as f:
    content = f.readlines()
    for line in content:
        if "CPU Time:" in line:
            cpu_time_bilinear = line.split(':')[1].strip()

with open("stdout_dmcswl1.txt", "r") as f:
    content = f.readlines()
    for line in content:
        if "CPU Time:" in line:
            cpu_time_dmcswl1 = line.split(':')[1].strip()
        
# Create data for the table
data = [
    ["Bilinear demosaicking", mse_bilinear, cpu_time_bilinear],
    ["Contour stencils demosaicking", mse_dmcswl1, cpu_time_dmcswl1]
]

# Table headers
headers = ["Method", "Mean squared error", "CPU time"]

#write table to a text file
with open('table.txt', 'w') as file:
  file.write(tabulate(data, headers=headers))
