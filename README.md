# NHDRRNet-pytorch
📷 NHDRRNet (TIP'20) implementation using PyTorch framework

## Introduction

This repository is the implementation of NHDRRNet [2] using PyTorch framework. The author did not open the code, therefore, we create this repository to implement NHDRRNet using PyTorch framework.

## Requirements

+ PyTorch 1.4+
+ Cuda version 10.1+
+ OpenCV
+ numpy, tqdm, scipy, etc

## Getting Started

### Download Dataset

The Kalantari Dataset can be downloaded from https://www.robots.ox.ac.uk/~szwu/storage/hdr/kalantari_dataset.zip [2].

### Dataset Model Selection

There are two dataset models provided in `dataset` folder. Using `HDRpatches.py` will generate patches in `patches` folder and will cost ~200GB spaces, but it runs faster. Using `HDR.py` (default) will open image file only when it needs to do so, thus it will save disk space. Feel free to choose the method you want.

### Configs Modifications

+ You may modify the arguments in `Configs()` to satisfy your own environment, for specific arguments descriptions, see `utils/configs.py`.
+ You may modify arguments of NHDRRNet to train a better model, for specific arguments descriptions, see config dictionary in `models/NHDRRNet.py`.

### Train

```bash
python train.py
```

### Test

First, make sure that you have models (`checkpoint.tar`) under `checkpoint_dir` (which is defined in `Configs()`).

```bash
python test.py
```

**Note**. `test.py` will dump the result images in `sample` folder.

### Tone-mapping (post-processing)

Generated HDR images are in `.hdr` format, which may not be properly displayed in your image viewer directly. You may use [Photomatix](https://www.hdrsoft.com/) for tonemapping [2]:

- Download [Photomatix](https://www.hdrsoft.com/) free trial, which won't expire.
- Load the generated `.hdr` file in Photomatix.
- Adjust the parameter settings. You may refer to pre-defined styles, such as `Detailed` and `Painterly2`.
- Save your final image in `.tif` or `.jpg`.

## Reference

[1] Yan, Qingsen, et al. "Deep hdr imaging via a non-local network." *IEEE Transactions on Image Processing* 29 (2020): 4308-4322.

[2] elliottwu/DeepHDR repository: https://github.com/elliottwu/DeepHDR