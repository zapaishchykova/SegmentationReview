cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SegmentationReview)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/zapaishchykova/SegmentationReview")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Anna Zapaishchykova (AIM Lab, BWH), Dr. Benjamin H. Kann (AIM Lab, BWH)")
set(EXTENSION_DESCRIPTION "The SegmentationReview extension enables clinician to quickly review of Deep-learning generated segmentations using Likert-type score. The dataset loads in one batch with no need to load masks and volumes separately. The results are saved in a csv file, which can be used for further analysis.")
set(EXTENSION_ICONURL "https://raw.github.com/zapaishchykova/SegmentationReview/bd21693438a9bafed7e3a74313c0129860c9a74b/SlicerSegReview/Resources/Icons/SlicerSegReview.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/zapaishchykova/SegmentationReview/bd21693438a9bafed7e3a74313c0129860c9a74b/pics/screenshot.png")
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
