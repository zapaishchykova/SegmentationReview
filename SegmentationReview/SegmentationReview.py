import logging
import os

import vtk
import pathlib
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import ctk
import qt
from datetime import datetime
import SegmentStatistics
import logging

try:
    import pandas as pd
    import numpy as np
    import SimpleITK as sitk
except:
    slicer.util.pip_install('pandas')
    slicer.util.pip_install('numpy')
    slicer.util.pip_install('SimpleITK')
    
    import pandas as pd
    import numpy as np
    import SimpleITK as sitk
#
# SegmentationReview
#


class SegmentationReview(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegmentationReview"  
        self.parent.categories = ["Examples"]  
        self.parent.dependencies = []  
        self.parent.contributors = ["Anna Zapaishchykova, Vasco Prudente, Dr. Benjamin H. Kann (AIM-Harvard)"]  
        self.parent.helpText = """
Slicer3D extension for rating using Likert-type score Deep-learning generated segmentations, with segment editor funtionality. 
Created to speed up the validation process done by a clinician - the dataset loads in one batch with no need to load masks and volumes separately.
It is important that each nii file has a corresponding mask file with the same name and the suffix _mask.nii
"""
       
        self.parent.acknowledgementText = """
This file was developed by Anna Zapaishchykova and Vasco Prudente. 
"""
       

#
# SegmentationReviewWidget
#

class SegmentationReviewWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False
        self.volume_node = None
        self.segmentation_node = None
        self.segmentation_visible = False
        self.segmentation_color = [1, 0, 0]
        self.nifti_files = []
        self.segmentation_files = []
        self.directory=None
        self.current_index=0
        self.likert_scores = []
        self.n_files = 0
        self.seg_mask_status = [] # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
        self.with_mapper_flag = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        import qSlicerSegmentationsModuleWidgetsPythonQt
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentationReview.ui'))
        
        # Layout within the collapsible button
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Input path"
        self.layout.addWidget(parametersCollapsibleButton)

        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self.atlasDirectoryButton = ctk.ctkDirectoryButton()
        parametersFormLayout.addRow("Directory: ", self.atlasDirectoryButton)
        
        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = SlicerLikertDLratingLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        
        self.ui.PathLineEdit = ctk.ctkDirectoryButton()
        
        # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
        # (in the selected parameter node).
        self.atlasDirectoryButton.directoryChanged.connect(self.onAtlasDirectoryChanged)
        self.ui.save_and_next.connect('clicked(bool)', self.save_and_next_clicked)
        self.ui.overwrite_mask.connect('clicked(bool)', self.overwrite_mask_clicked)
        
        # add a paint brush from segment editor window
        # Create a new segment editor widget and add it to the NiftyViewerWidget
        self._createSegmentEditorWidget_()
        
        #self.editorWidget.volumes.collapsed = True
         # Set parameter node first so that the automatic selections made when the scene is set are saved
            
        
        # Make sure parameter node is initialized (needed for module reload)
        #self.initializeParameterNode()

    def _createSegmentEditorWidget_(self):
        """Create and initialize a customize Slicer Editor which contains just some the tools that we need for the segmentation"""

        import qSlicerSegmentationsModuleWidgetsPythonQt

        #advancedCollapsibleButton
        self.segmentEditorWidget = qSlicerSegmentationsModuleWidgetsPythonQt.qMRMLSegmentEditorWidget(
        )
        self.segmentEditorWidget.setMaximumNumberOfUndoStates(10)
        self.segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        self.segmentEditorWidget.unorderedEffectsVisible = False
        self.segmentEditorWidget.setEffectNameOrder([
            'No editing','Threshold',
            'Paint', 'Draw', 
            'Erase','Level tracing',
            'Grow from seeds','Fill between slices',
            'Margin','Hollow',
            'Smoothing','Scissors',
            'Islands','Logical operators',
            'Mask volume'])
        self.layout.addWidget(self.segmentEditorWidget)
    
    def overwrite_mask_clicked(self):
        # overwrite self.segmentEditorWidget.segmentationNode()
        #segmentation_node = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLSegmentationNode')

        # Get the file path where you want to save the segmentation node
        file_path = self.directory+"/t.seg.nrrd"
        # Save the segmentation node to file as nifti
        file_path_nifti = self.segmentation_files[self.current_index].split(".")[0]+f"_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.nii.gz"
        # Save the segmentation node to file
        slicer.util.saveNode(self.segmentation_node, file_path)
        
        img = sitk.ReadImage(file_path)
        sitk.WriteImage(img, file_path_nifti)
        print("Saved segmentation",file_path_nifti)

    def _is_valid_extension(self, path):
        return any(path.endswith(i) for i in [".nii", ".nii.gz", ".nrrd"])
    
    def _construct_full_path(self, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(self.directory, path)
    
    def _restore_index(self, ann_csv, files_list, mask_list, mask_status_list=None):
        #ann_csv {[self.nifti_files[self.current_index]],[likert_score],[self.ui.comment.toPlainText()]}
        statuses,unchecked_files,unchecked_masks = [],[],[]
        list_of_checked = ann_csv['file'].values
        list_of_checked = [self._construct_full_path(i) for i in list_of_checked]
        
        list_of_checked_masks = ann_csv['mask_path'].values
        # check if ['mask_path'] is empty
        if type(list_of_checked_masks[0]) == str:
            list_of_checked_masks = [self._construct_full_path(i) for i in list_of_checked_masks]
        
        #find subset of files that are not checked
        for i in range(len(files_list)):
            if files_list[i] not in list_of_checked:
                unchecked_files.append(files_list[i])
                unchecked_masks.append(mask_list[i])
                statuses.append(mask_status_list[i])

        #return list of unchecked files
        return unchecked_files, unchecked_masks, statuses
    
    def onAtlasDirectoryChanged(self, directory):
        logger = logging.getLogger('SegmentationReview')
        logger.setLevel(logging.DEBUG)

        # Set up logging to file
        fileHandler = logging.FileHandler(directory+'/segmentation_review.log')
        fileHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(fileHandler) 
        
        try:
            slicer.mrmlScene.RemoveNode(self.volume_node) 
            slicer.mrmlScene.RemoveNode(self.segmentation_node)
        except:
            pass
        self.directory = directory
        
        # case 1: mapper cvs is present
        if os.path.exists(directory+"/mapping.csv"):
            logger.info('Found mappings between files and masks') 
            print("Found mappings between files and masks")
            self.mappings = pd.read_csv(directory+"/mapping.csv")
            self.with_mapper_flag = True
            # casting to zero all nan values
            
            print("Loaded mappings between files and masks")
            for img, mask in zip(self.mappings["img_path"], self.mappings["mask_path"]):
                # counting images
                print(directory+"/"+img,mask)
                print(os.path.exists(directory+"/"+img), self._is_valid_extension(directory+"/"+img))
                if os.path.exists(directory+"/"+img) and self._is_valid_extension(directory+"/"+img):
                    self.nifti_files.append(directory+"/"+img)
                    # counting masks
                    # check if mask is 
                    if type(mask) == str:
                        if os.path.exists(directory+"/"+mask) and self._is_valid_extension(directory+"/"+mask):
                            self.segmentation_files.append(directory+"/"+mask)
                            self.seg_mask_status.append(2) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                            logger.info(f'Found mask for {img}')
                        elif self._is_valid_extension(directory+"/"+mask) and not os.path.exists(directory+"/"+mask):
                            self.segmentation_files.append("")
                            self.seg_mask_status.append(1) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                            logger.info(f'Cannot load mask for {img}, check path')
                        else:
                            self.segmentation_files.append("")
                            self.seg_mask_status.append(0) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                            logger.info(f'No mask provided for {img}')
                    else:
                        self.segmentation_files.append("")
                        self.seg_mask_status.append(0)
                        logger.info(f'No mask provided for {img}')
                else:
                    logger.info(f'File {img} does not exist or has wrong extension, skipping')
                        
                            
                # ToDo: write to log how many files were found, how many masks were found 
                
        # case 2: mapper cvs is not present; list files from file
        else:
            logger.info('No mappings between files and masks') 
            print("No mappings between files and masks")
            for file in os.listdir(directory):
                if ".nii" in file and "_mask" not in file:  
                    self.nifti_files.append(directory+"/"+file)
                    if os.path.exists(directory+"/"+file.split(".")[0]+"_mask.nii.gz"):
                        self.segmentation_files.append(directory+"/"+file.split(".")[0]+"_mask.nii.gz")
                        self.seg_mask_status.append(2) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                        logger.info(f'Found mask for {file}')
                    else:
                        self.segmentation_files.append("")
                        self.seg_mask_status.append(0) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                        logger.info(f'No mask for {file}')
                else:
                    logger.info(f'File {file} does not exist or has wrong extension, skipping')
                        
        self.current_index = 0               
        # load the .cvs file with the old annotations or create a new one
        if os.path.exists(directory+"/annotations.csv"):
            print(self.nifti_files,self.segmentation_files, self.seg_mask_status)
            ann_csv = pd.read_csv(directory+"/annotations.csv", header=None,index_col=False, names=["file","annotation","comment","mask_path","mask_status"])
            self.nifti_files, self.segmentation_files,self.seg_mask_status = self._restore_index(ann_csv, self.nifti_files,
                                                                                                 self.segmentation_files, self.seg_mask_status)
            
            print("Found session, restoring annotations")
            logger.info(f'Found session, restoring annotations {len(self.nifti_files)} files left') 
            
        self.n_files = len(self.nifti_files)
        self.ui.status_checked.setText("Checked: "+ str(self.current_index) + " / "+str(self.n_files))
        
        print("Images:",len(self.nifti_files), 
              "Masks:",len(self.segmentation_files))
        logger.info( f'Total Images Loaded: {len(self.nifti_files)}, Images with Masks: {len(self.segmentation_files)}')
        # load first file with mask
        self.load_nifti_file()
     
    def _numerical_status_to_str(self, status):
        return {0: "No mask", 1: "Cannot load mask", 2: "Mask loaded"}[status]   
    
    def _rating_to_str(self, rating):
        return {1: "Acceptable with no changes", 2: "Acceptable with minor changes", 
                3: "Unacceptable with major changes", 
                4: "Unacceptable and not visible",
                5: "Bad images"}[rating]  
    
    def save_and_next_clicked(self):
        likert_score = 0
        if self.ui.radioButton_1.isChecked():
            likert_score=1
        elif self.ui.radioButton_2.isChecked():
            likert_score=2
        elif self.ui.radioButton_3.isChecked():
            likert_score=3
        elif self.ui.radioButton_4.isChecked():
            likert_score=4
        elif self.ui.radioButton_5.isChecked():
            likert_score=5
            
            
        self.likert_scores.append([self.current_index, likert_score, self.ui.comment.toPlainText()])
        # append data frame to CSV file
        data = {'file': [self.nifti_files[self.current_index].replace(self.directory+"/","")],
                    'annotation': [self._rating_to_str(likert_score)],
                    'comment': [self.ui.comment.toPlainText()],
                    'mask_path': [self.segmentation_files[self.current_index].replace(self.directory+"/","")],
                    'mask_status': [self._numerical_status_to_str(self.seg_mask_status[self.current_index])]}
        df = pd.DataFrame(data)   
        df.to_csv(self.directory+"/annotations.csv", mode='a', index=False, header=False)
        self.ui.status_checked.setText("Checked: "+ str(self.current_index+1) + " / "+str(self.n_files))

        # go to the next file if there is one
        if self.current_index < self.n_files-1:
            self.current_index += 1
            self.load_nifti_file()
            self.ui.comment.setPlainText("")
        else:
            print("All files checked") 
    
    def load_nifti_file(self):
        
        # Reset the slice views to clear any remaining segmentations
        slicer.util.resetSliceViews()
        
        file_path = self.nifti_files[self.current_index]
        if self.volume_node:
            slicer.mrmlScene.RemoveNode(self.volume_node)
        if self.segmentation_node:
            slicer.mrmlScene.RemoveNode(self.segmentation_node)

        self.volume_node = slicer.util.loadVolume(file_path)
        slicer.app.applicationLogic().PropagateVolumeSelection(0)
        try:
            segmentation_file_path = self.segmentation_files[self.current_index]
            self.segmentation_node = slicer.util.loadSegmentation(segmentation_file_path)
            self.segmentation_node.GetDisplayNode().SetColor(self.segmentation_color)
            self.set_segmentation_and_mask_for_segmentation_editor() 
        except:
            print("no mask")       
        
        print(file_path)

    def set_segmentation_and_mask_for_segmentation_editor(self):
        slicer.app.processEvents()
        self.segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        
        #get segmentation node center and jump to it
        # this requires QuantitativeReporting installed
        # https://qiicr.gitbook.io/quantitativereporting-guide/user-guide/installation-and-upgrade
       
        segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
        #segmentationNode = segNode.GetSegmentation().GetNthSegment(0)

        # Compute centroids
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.centroid_ras.enabled", str(True))
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()
        pointListNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        pointListNode.CreateDefaultDisplayNodes()
        for segmentId in stats["SegmentIDs"]:
            centroid_ras = stats[segmentId,"LabelmapSegmentStatisticsPlugin.centroid_ras"]
            print(segmentId,centroid_ras)
            markupsLogic = slicer.modules.markups.logic()
            markupsLogic.JumpSlicesToLocation(centroid_ras[0],centroid_ras[1],centroid_ras[2], False)

        slicer.mrmlScene.AddNode(segmentEditorNode)
        self.segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        self.segmentEditorWidget.setSegmentationNode(self.segmentation_node)
        self.segmentEditorWidget.setSourceVolumeNode(self.volume_node)

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()
        #clear the scene
        slicer.mrmlScene.Clear(0)

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.GetNodeReference("InputVolume"):
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        #if inputParameterNode:
        #    self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI.
        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        # Initial GUI update
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True


        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

        self._parameterNode.EndModify(wasModified)

#
# SlicerLikertDLratingLogic
#

class SlicerLikertDLratingLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    
#
# SlicerLikertDLratingTest
#

class SlicerLikertDLratingTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_SlicerLikertDLrating1()

    def test_SlicerLikertDLrating1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        self.delayDisplay('Test passed')
