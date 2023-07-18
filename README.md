# SegmentationReview

The SegmentationReview extension is a powerful tool for clinicians who need to quickly and efficiently review deep-learning generated segmentations. With this extension, you can use a Likert-type rating system that scores segmentations on a four-point scale, ranging from "Acceptable with no changes" to "Unacceptable, not visible/wrong location".

One of the key benefits of SegmentationReview is the ability to load the entire dataset with all masks and volumes in one batch. This simplifies the workflow and eliminates the need to load masks and volumes separately. Additionally, the results of the review are saved as a csv file, which can be easily used for further analysis.

Overall, SegmentationReview provides a streamlined solution for clinicians who want to speed up the validation process of deep-learning generated segmentations. It is a valuable tool that can help to improve workflow efficiency and reduce the burden associated with segmentation validation.

## Installing the extension

You can install `SegmentationReview` from the 3D Slicer [extensions manager](https://slicer.readthedocs.io/en/latest/user_guide/extensions_manager.html).

To open the extension manager, go to `View -> Extensions Manager` in the main menu. In the extensions manager, search for `SegmentationReview` and click  `Install` to install the extension. Once the extension is installed, switch to the `SegmentationReview` module by clicking `Modules -> SegmentationReview` in the main menu.

## Interface

<p align="center">
  <img width="75%" src="pics/main_readme.png" alt="SegmentationReview Screenshot">
</p>

**Panel Overview:**

The interface displays three main panels:
- **Likert-type segmentation assessment**: Ratings are provided on a scale of 1 to 4, representing levels of (1) Acceptable with no changes, (2) Acceptable with minor changes, (3) Unacceptable with major changes, and (4) Unacceptable and not visible. A 5th option for bad images is also available.
- **Segmentation Editor**: The editor panel allows for fine-tuning of the segmentation.
- **2D/3D Segmentation View**: The 2D/3D view allows for visualization and comparison of the original image and the segmentation.

**Results:**

AI-generated segmentation ratings are automatically saved as a .csv file, which can be further analyzed using any tool of choice. The example above presents a dummy dataset using MS Office, but any other analysis tool can be used. 

<p align="center">
  <img width="50%" src="pics/example.png" alt="Example Analysis in MS Office">
</p>

The `annotation.csv` has a following structure (with no header):

| Filename | Rating | Comments |
| ---         |     ---      |          --- |
| image1.nii.gz   | 1     |     |
| image2.nii.gz     | 5       | wrong sequence     | 
| ...    | ...      | ...    | 

"Rating" (2nd column) has the following encoding: (1) Acceptable with no changes, (2) Acceptable with minor changes, (3) Unacceptable with major changes, (4) Unacceptable and not visible, and (5) Bad images.


## Tutorial

1. **Prepare the dataset:** To get started, create a folder with the following file structure:

    ```
    - image1.nii.gz
    - image1_mask.nii.gz
    - image2.nii.gz
    - image2_mask.nii.gz
    ...
    ```
    The images should be in NIfTI format (`.nii.gz`), with corresponding segmentation masks labeled `_mask.nii.gz`.

An example dataset of T1w brain scans and their corresponding brain segmentations is provided in the `example_data` folder with already reviewed images. You can use this dataset to test the extension. If you want to review the images yourself, you can delete the `annotations.csv` file and start the review process from scratch.

2. **Load the dataset into 3D Slicer:** After starting 3D Slicer, open `File -> Add Data` from the main menu, then select the folder containing the images and masks and press `OK`. After loading, you will see how many images are loaded under the _Checked_ status. If the path is opened for the first time, an `annotations.csv` file will be created in the same folder. This file will contain the results of the rating and will be automatically updated after each rating. Additionally, the `annotations.csv` file allows you to restore the annotation process in case of a crash or if there are too many images to rate in one session.

3. **Assign a Likert score to each image:** In the "SegmentationReview" module, click on the `Likert rating` tab, select the image, and then select a rating from the drop-down menu (ranging from _Acceptable with no changes_ to _Unacceptable and not visible_). When you're done, click `Save and Next` to move to the next image. The results will be automatically saved in the `annotations.csv` file.

4. **Optional: Edit the mask of an image:** If you want to change the segmentation mask of any image, you can use the "Segment Editor" module that is added to the extension. Select the `Segment editor` tab, edit the mask using the brushes or eraser, and then click `Overwrite edited mask` to save the new mask. The new mask will be saved in the same folder as the original mask, with `_upd` added to the end of the name.


## Maintainers

Here are the steps to install the extension from source and develop the extension locally. This is useful for testing and contributing changes leveraging the GitHub pull request contribution workflow.

1. Download the source code using `git`

  ```
  git clone git@github.com:zapaishchykova/SegmentationReview.git
  ```

2. After starting 3D Slicer, [install the module by drag&drop](https://discourse.slicer.org/t/new-feature-install-modules-by-drag-and-drop-python-files/28311) the extension source directory.

3. Enabling the [developer mode](https://slicer.readthedocs.io/en/latest/user_guide/settings.html#developer-mode) will allow to reload the module from source without having to restart the application.

## Example Dataset

The example data was obtained from the [OpenfMRI databaset](https://openfmri.org/dataset/ds000228/). Its accession number is ds000228. Brains were segmented using [HD Brain Extraction tool](https://github.com/lassoan/SlicerHDBrainExtraction#hdbrainextraction). 


## Citation
Anna Zapaishchykova, Divyanshu Tak, Aidan Boyd, Zezhong Ye, Hugo J.W.L. Aerts, Benjamin H. Kann
"SegmentationReview: A Slicer3D extension for fast review of AI-generated segmentations"
[https://doi.org/10.1016/j.simpa.2023.100536]https://doi.org/10.1016/j.simpa.2023.100536


## License

This extension is distributed under the terms of the MIT license.

