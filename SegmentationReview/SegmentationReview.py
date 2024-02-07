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
#from qt import QtCore, QtGui


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
#remove warnings
import warnings
warnings.filterwarnings("ignore")

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
        self.seg_mask_status = [] # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded, 3- mask edited
        self.with_mapper_flag = False
        self.id_subs = []
        self.id_subs_checked = []
        self.unique_case_flag=False
        self.finish_flag = False
        self.save_new_mask = False
        self.pointListNode = None


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
        #shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+e"), slicer.util.mainWindow())
        #shortcut.connect("clicked(bool)", lambda: slicer.ui.radioButton_1.isChecked())
        # Get reference to the radio button widget 
        '''self.radioButton = self.ui.radioButton_1 
            # Create keyboard event handler
        def onKeyPress(event):
            key = event.key()
            if key == QtCore.Qt.Key_1:
                # Check the radio button
                self.radioButton.setChecked(True)
                    
        
        # Connect the keyboard handler 
        shortcut = QtGui.QShortcut(QtGui.QKeySequence("1"), self)
        shortcut.activated.connect(onKeyPress)'''


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
        
        #self.segmentEditorWidgetWidget.volumes.collapsed = True
         # Set parameter node first so that the automatic selections made when the scene is set are saved
            
        
        # Make sure parameter node is initialized (needed for module reload)
        #self.initializeParameterNode()

    def _createSegmentEditorWidget_(self):
        """Create and initialize a customize Slicer Editor which contains just some the tools that we need for the segmentation"""

        import qSlicerSegmentationsModuleWidgetsPythonQt

        #advancedCollapsibleButton
        self.segmentEditorWidget = qSlicerSegmentationsModuleWidgetsPythonQt.qMRMLSegmentEditorWidget()
        #enable the "add" button
        #self.segmentEditorWidget.setAddSegmentShortcutEnabled(True)
        
        self.segmentEditorWidget.setMaximumNumberOfUndoStates(10)
        self.selectParameterNode()
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
        
        # Observe editor effect registrations to make sure that any effects that are registered
        # later will show up in the segment editor widget. For example, if Segment Editor is set
        # as startup module, additional effects are registered after the segment editor widget is created.
        #self.effectFactorySingleton = slicer.qSlicerSegmentEditorEffectFactory.instance()
        #self.effectFactorySingleton.connect("effectRegistered(QString)", self.editorEffectRegistered)

        # Connect observers to scene events
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)
        
    def enter(self):
        """Runs whenever the module is reopened"""
        #print("Enter")
        
        # Set parameter set node if absent
        self.selectParameterNode()
        self.segmentEditorWidget.updateWidgetFromMRML()

        # If no segmentation node exists then create one so that the user does not have to create one manually
        if not self.segmentEditorWidget.segmentationNodeID():
            #print("No segmentation node, creating one")
            self.segmentation_node = slicer.mrmlScene.GetFirstNode(None, "vtkMRMLSegmentationNode")
            if not self.segmentation_node:
                self.segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            self.segmentEditorWidget.setSegmentationNode(self.segmentation_node)
            if not self.segmentEditorWidget.sourceVolumeNodeID():
                self.sourceVolumeNodeID = self.getDefaultSourceVolumeNodeID()
                self.segmentEditorWidget.setSourceVolumeNodeID(self.sourceVolumeNodeID)
        self.initializeParameterNode()
    
    def overwrite_mask_clicked(self):
        # overwrite self.segmentEditorWidget.segmentationNode()
        self.segmentation_node = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLSegmentationNode')
        file_path = os.path.join(self.directory,"t.seg.nrrd")
        # Save the segmentation node to file as nifti
        self.file_path_nifti = self.nifti_files[self.current_index].split(".")[0]+f"_mask_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.nii.gz"
        self.seg_mask_status[self.current_index] = 3
        # add to the list of segmentation files
        self.segmentation_files[self.current_index] = self.file_path_nifti
        
        # Save the segmentation node to file
        slicer.util.saveNode(self.segmentation_node, file_path)
        img = sitk.ReadImage(file_path)
        sitk.WriteImage(img, self.file_path_nifti)
        
        #delete the temporary file
        try:
            os.remove(file_path)
        except:
            pass
        
        #print("Saved segmentation",self.file_path_nifti)

    def _is_valid_extension(self, path):
        return any(path.endswith(i) for i in [".nii", ".nii.gz", ".nrrd"])
    
    def _construct_full_path(self, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(self.directory, path)
    
    def _restore_index(self, ann_csv, files_list, mask_list, mask_status_list=None):
        #print(files_list,mask_list)
        #print(self.unique_case_flag)
        #ann_csv {[self.nifti_files[self.current_index]],[likert_score],[self.ui.comment.toPlainText()]}
        statuses, unchecked_files, unchecked_masks, checked_ids, id_subs_list = [], [], [], [], []
        list_of_checked = ann_csv['file'].values
        list_of_checked = [self._construct_full_path(i) for i in list_of_checked]
        
        list_of_checked_masks = ann_csv['mask_path'].values
        #print(list_of_checked)
        # check if ['mask_path'] is empty
        if type(list_of_checked_masks[0]) == str:
            list_of_checked_masks = [self._construct_full_path(i) for i in list_of_checked_masks]
        
        #find subset of files that are not checked
        if self.unique_case_flag:
            # read what ids were checked by finding the corresponding ids
            checked_ids = []
            list_of_checked = ann_csv['file'].values
            # first, check what ids were checked
            for id_subj, img, _ in zip(self.mappings["subj_id"], self.mappings["img_path"], self.mappings["mask_path"]):
                if img in list_of_checked:
                    checked_ids.append(id_subj)
            # second, find the files that were not checked       
            for id_subj, img, mask in zip(self.mappings["subj_id"], self.mappings["img_path"], self.mappings["mask_path"]):
                if id_subj not in checked_ids:
                    id_subs_list.append(id_subj)
                    unchecked_files.append(self._construct_full_path(img))
                    # check if mask is empty or nan 
                    if type(mask) == str:
                        unchecked_masks.append(self._construct_full_path(mask))
                        statuses.append(2)
                    else:
                        unchecked_masks.append("")
                        statuses.append(0)
                        
            #print("Checked ids",checked_ids)
            #print("Unchecked files",unchecked_files)
            #print("Unchecked masks",unchecked_masks)
            
        else:
            for i in range(len(files_list)):
                if files_list[i] not in list_of_checked:
                    unchecked_files.append(files_list[i])
                    unchecked_masks.append(mask_list[i])
                    statuses.append(mask_status_list[i])
        
        
        #return list of unchecked files
        return unchecked_files, unchecked_masks, statuses, id_subs_list, checked_ids
    
    def getDefaultSourceVolumeNodeID(self):
        layoutManager = slicer.app.layoutManager()
        firstForegroundVolumeID = None
        # Use first background volume node in any of the displayed layouts.
        # If no beackground volume node is in any slice view then use the first
        # foreground volume node.
        for sliceViewName in layoutManager.sliceViewNames():
            sliceWidget = layoutManager.sliceWidget(sliceViewName)
            if not sliceWidget:
                continue
            compositeNode = sliceWidget.mrmlSliceCompositeNode()
            if compositeNode.GetBackgroundVolumeID():
                return compositeNode.GetBackgroundVolumeID()
            if compositeNode.GetForegroundVolumeID() and not firstForegroundVolumeID:
                firstForegroundVolumeID = compositeNode.GetForegroundVolumeID()
        # No background volume was found, so use the foreground volume (if any was found)
        return firstForegroundVolumeID 
   
    def editorEffectRegistered(self):
        self.segmentEditorWidget.updateEffectList()
        
    def selectParameterNode(self):
        # Select parameter set node if one is found in the scene, and create one otherwise
        segmentEditorSingletonTag = "SegmentEditor"
        segmentEditorNode = slicer.mrmlScene.GetSingletonNode(segmentEditorSingletonTag, "vtkMRMLSegmentEditorNode")
        if segmentEditorNode is None:
            segmentEditorNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLSegmentEditorNode")
            segmentEditorNode.UnRegister(None)
            segmentEditorNode.SetSingletonTag(segmentEditorSingletonTag)
            segmentEditorNode = slicer.mrmlScene.AddNode(segmentEditorNode)
        #if self.parameterSetNode == segmentEditorNode:
        #    # nothing changed
        #    return
        self.parameterSetNode = segmentEditorNode
        self.segmentEditorWidget.setMRMLSegmentEditorNode(self.parameterSetNode)
   
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
        
        self.unique_case_flag=False
        # case 0: searching for one unique nifti file for id
        # they 
        if os.path.exists(os.path.join(directory,"mapping_unique.csv")):
            case_flag = True
            # mapping file contains id and nifti file name
            id_subs = []
            self.mappings = pd.read_csv(os.path.join(directory,"mapping_unique.csv"))
            self.unique_case_flag = True
            for id_subj, img, mask in zip(self.mappings["subj_id"], self.mappings["img_path"], self.mappings["mask_path"]):
                # counting images
                if os.path.exists(os.path.join(directory,img)) and self._is_valid_extension(os.path.join(directory,img)):
                    self.nifti_files.append(os.path.join(directory,img))
                    id_subs.append(id_subj)
                    # counting masks
                    # check if mask is 
                    if type(mask) == str:
                        if os.path.exists(os.path.join(directory,mask)) and self._is_valid_extension(os.path.join(directory,mask)):
                            
                            self.segmentation_files.append(os.path.join(directory,mask))
                            self.seg_mask_status.append(2) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                            logger.info(f'Found mask for {img}')
                        elif self._is_valid_extension(os.path.join(directory,mask)) and not os.path.exists(os.path.join(directory,mask)):
                           
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
            #get unique ids
            self.id_subs = id_subs
            #print("Unique:",len(np.unique(self.id_subs)),id_subs)   
        
        # case 1: mapper cvs is present
        elif os.path.exists(os.path.join(directory,"mapping.csv")):
            logger.info('Found mappings between files and masks') 
            #print("Found mappings between files and masks")
            self.mappings = pd.read_csv(os.path.join(directory,"mapping.csv"))
            self.with_mapper_flag = True
            # casting to zero all nan values
            
            #print("Loaded mappings between files and masks")
            for img, mask in zip(self.mappings["img_path"], self.mappings["mask_path"]):
                # counting images
                if os.path.exists(os.path.join(directory,img)) and self._is_valid_extension(os.path.join(directory,img)):
                    self.nifti_files.append(os.path.join(directory,img))
                    # counting masks
                    # check if mask is 
                    if type(mask) == str:
                        if os.path.exists(os.path.join(directory,mask)) and self._is_valid_extension(os.path.join(directory,mask)):
                            self.segmentation_files.append(os.path.join(directory,mask))
                            self.seg_mask_status.append(2) # 0 - no mask, 1 - mask path, cannot load , 2 - mask loaded
                            logger.info(f'Found mask for {img}')
                        elif self._is_valid_extension(os.path.join(directory,mask)) and not os.path.exists(os.path.join(directory,mask)):
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
            #print("No mappings between files and masks")
            for file in os.listdir(directory):
                if ".nii" in file and "_mask" not in file:  
                    self.nifti_files.append(os.path.join(directory,file)) #
                    if os.path.exists(os.path.join(directory,file.split(".")[0]+"_mask.nii.gz")):
                        self.segmentation_files.append(os.path.join(directory,file.split(".")[0]+"_mask.nii.gz"))
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
        #print("Path exists",os.path.exists(os.path.join(directory,"annotations.csv")))
        if os.path.exists(os.path.join(directory,"annotations.csv")):
        
            ann_csv = pd.read_csv(os.path.join(directory,"annotations.csv"), header=None,index_col=False, names=["file","annotation","comment","mask_path","mask_status"])
            #print(ann_csv)
            if self.unique_case_flag:
                self.nifti_files, self.segmentation_files, self.seg_mask_status, self.id_subs, self.id_subs_checked = self._restore_index(ann_csv, self.nifti_files,
                                                                                                 self.segmentation_files, self.seg_mask_status)
            else:
                self.nifti_files, self.segmentation_files, self.seg_mask_status, _,_ = self._restore_index(ann_csv, self.nifti_files, self.segmentation_files, self.seg_mask_status)
            
            logger.info(f'Found session, restoring annotations {len(self.nifti_files)} files left') 
            
        self.n_files = len(self.nifti_files)
        self.ui.status_checked.setText("Checked: "+ str(self.current_index) + " / "+str(self.n_files))
        
        #print("Images:",len(self.nifti_files), 
        #      "Masks:",len(self.segmentation_files))
        logger.info( f'Total Images Loaded: {len(self.nifti_files)}, Images with Masks: {len(self.segmentation_files)}')
        
        # load first file with mask
        if self.unique_case_flag==False:
            self.load_nifti_file()
        else: 
            #print("Loading unique pipeline")
            self.load_nifti_file_unique()
     
    def _numerical_status_to_str(self, status):
        return {0: "No mask found", 1: "Cannot load mask", 2: "Mask loaded, no edits", 3:"Mask edited"}[status]   
    
    def _rating_to_str(self, rating):
        return {1: "Acceptable with no changes", 2: "Acceptable with minor changes", 
                3: "Unacceptable with major changes", 
                4: "Unacceptable and not visible",
                5: "Bad images"}[rating]  
    
    def save_and_next_clicked(self):
        likert_score = 0
        
        if self.ui.radioButton_1.isChecked():
            likert_score=1
            if self.unique_case_flag:
                self.id_subs_checked.append(self.id_subs[self.current_index])
                #print("found the file for this id",self.current_index,self.id_subs[self.current_index])
                # update current index display
                #self.ui.status_checked.setText("Checked: "+ str(self.current_index) + " / "+str(self.n_files))
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
        if  self.finish_flag == False:
            head, tail = os.path.split(self.nifti_files[self.current_index])
            print("Head, tail", head, tail)
            data = {'file': [self.nifti_files[self.current_index].replace(head,"")],
                        'annotation': [self._rating_to_str(likert_score)],
                        'comment': [self.ui.comment.toPlainText()],
                        'mask_path': [self.segmentation_files[self.current_index].replace(head,"")],
                        'mask_status': [self._numerical_status_to_str(self.seg_mask_status[self.current_index])]}
            df = pd.DataFrame(data)   
            df.to_csv(os.path.join(self.directory,"annotations.csv"), mode='a', index=False, header=False)
        
        # go to the next file if there is one
        ret = 0
        if self.current_index <= self.n_files:#-1:
            if self.volume_node:
                slicer.mrmlScene.RemoveNode(self.volume_node)
            if self.segmentation_node:
                slicer.mrmlScene.RemoveNode(self.segmentation_node)
                slicer.mrmlScene.RemoveNode(self.pointListNode)
                #slicer.mrmlScene.Clear(0)
            if self.unique_case_flag:
                while ret == 0 and self.current_index <= self.n_files:#-1:
                    self.current_index += 1
                    
                    ret = self.load_nifti_file_unique()
                    #print("skip, load next",self.id_subs[self.current_index])
                    
                    if self.current_index == self.n_files:
                    
                        print("*All files checked", self.current_index, self.n_files)
                        self.finish_flag = True
                        break
                    
                    #self.current_index += 1
                    
            else:
                self.current_index += 1
                self.load_nifti_file()

            self.ui.comment.setPlainText("")
            self.ui.status_checked.setText("Checked: "+ str(self.current_index) + " / "+str(self.n_files))

        else:
            #print("_All files checked") 
            self.finish_flag = True
    
    def load_nifti_file(self):
        
        # Reset the slice views to clear any remaining segmentations
        file_path = self.nifti_files[self.current_index]
        if self.volume_node:
            slicer.mrmlScene.RemoveNode(self.volume_node)
        if self.segmentation_node:
            slicer.mrmlScene.RemoveNode(self.segmentation_node)
            slicer.mrmlScene.RemoveNode(self.segmentEditorWidget.segmentationNode())
        if self.pointListNode:
            slicer.mrmlScene.RemoveNode(self.pointListNode)
            #slicer.mrmlScene.Clear(0)
        slicer.util.resetSliceViews()
        
        self.volume_node = slicer.util.loadVolume(file_path)
        slicer.app.applicationLogic().PropagateVolumeSelection(0)
        try:
            segmentation_file_path = self.segmentation_files[self.current_index]
            self.segmentation_node = slicer.util.loadSegmentation(segmentation_file_path)
            self.segmentation_node.GetDisplayNode().SetColor(self.segmentation_color)
            self.set_segmentation_and_mask_for_segmentation_editor() 
        except:
            #print("no mask, creating one")  
            # Create or get the segmentation node
            self.enter()
     
    def load_nifti_file_unique(self): 
        # Reset the slice views to clear any remaining segmentations
        slicer.util.resetSliceViews()
        # check if for this id we already found a file
        # if yes, load it
        # if no, load the first file
        if self.current_index <= self.n_files-1 and self.id_subs[self.current_index] in self.id_subs_checked: 
            #print("Skipping since already found a good file for this id",self.id_subs[self.current_index])
            return 0
        elif self.current_index == self.n_files:
            #print("+All files checked")
            return 1
        else:
            file_path = self.nifti_files[self.current_index]
            if self.volume_node:
                slicer.mrmlScene.RemoveNode(self.volume_node)
            if self.segmentation_node:
                slicer.mrmlScene.RemoveNode(self.segmentation_node)
                slicer.mrmlScene.RemoveNode(self.segmentEditorWidget.segmentationNode())
            if self.pointListNode:
                slicer.mrmlScene.RemoveNode(self.pointListNode)

            self.volume_node = slicer.util.loadVolume(file_path)
            slicer.app.applicationLogic().PropagateVolumeSelection(0)
            
            try:
                segmentation_file_path = self.segmentation_files[self.current_index]
                self.segmentation_node = slicer.util.loadSegmentation(segmentation_file_path)
                self.segmentation_node.GetDisplayNode().SetColor(self.segmentation_color)
                self.set_segmentation_and_mask_for_segmentation_editor() 
            except:
                pass   
        
            

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
        self.pointListNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        self.pointListNode.CreateDefaultDisplayNodes()
        for segmentId in stats["SegmentIDs"]:
            centroid_ras = stats[segmentId,"LabelmapSegmentStatisticsPlugin.centroid_ras"]
            #print(segmentId,centroid_ras)
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
        #self.effectFactorySingleton.disconnect("effectRegistered(QString)", self.editorEffectRegistered)

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
        try:
            self.setParameterNode(None)
            self.segmentEditorWidget.setSegmentationNode(None)
            self.segmentEditorWidget.removeViewObservations()
        except:
            pass

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()
            self.selectParameterNode()
            self.segmentEditorWidget.updateWidgetFromMRML()  
        
    def onSceneEndImport(self, caller, event):
        if self.parent.isEntered:
            self.selectParameterNode()
            self.segmentEditorWidget.updateWidgetFromMRML()

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
