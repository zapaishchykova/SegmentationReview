cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SegmentationReview)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/SegmentationReview")
set(EXTENSION_CATEGORY "Examples")
set(EXTENSION_CONTRIBUTORS "Anna Zapaishchykova (AIM-lab (BWH)), Dr. Benjamin H. Kann (AIM-lab (BWH))")
set(EXTENSION_DESCRIPTION "Slicer3D extension for rating using Likert-type(4 Scale, 1: Acceptable, no changes; 2: Acceptable, minor changes; 3: Unacceptable, major changes; 4: Unacceptable, not visible/wrong location) score Deep-learning generated segmentations, with segment editor. Created to speed up the validation process done by a clinician - the dataset loads in one batch with no need to load masks and volumes separately. The results are saved in a csv file, which can be used for further analysis.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/SegmentationReview.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/SegmentationReview/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentationReview)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
