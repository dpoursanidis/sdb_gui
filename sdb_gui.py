from sklearn import metrics
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.model_selection import train_test_split
from joblib import parallel_backend
import sklearn.neighbors
import sklearn.utils._cython_blas
import sklearn.tree
import sklearn.tree._utils
import pandas as pd
import numpy as np
import rasterio as rio
import rasterio._features
import rasterio._shim
import rasterio.control
import rasterio.crs
import rasterio.sample
import rasterio.vrt
from pathlib import Path
import glob
import sys, os
import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import(QApplication, QWidget, QTextBrowser, QProgressBar, QFileDialog, QDialog,
                            QGridLayout, QMessageBox, QVBoxLayout, QComboBox, QLabel, QCheckBox,
                            QPushButton, QDoubleSpinBox, QSpinBox, QRadioButton, QTableWidgetItem,
                            QTableWidget, QScrollArea, QHeaderView)
from PyQt5.QtGui import QIcon

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# os.environ['PROJ_LIB'] = os.path.expanduser('~\\.conda\\envs\\sdb_exe\\Library\\share\\proj')
# os.environ['GDAL_DATA'] = os.path.expanduser('~\\.conda\\envs\\sdb_exe\\Library\\share')
# os.environ['PROJ_LIB'] = os.path.expanduser('~/.conda/envs/sdb_exe/Library/share/proj')
# os.environ['GDAL_DATA'] = os.path.expanduser('~/.conda/envs/sdb_exe/Library/share')
os.environ['PROJ_LIB'] = resource_path('share/proj')
os.environ['GDAL_DATA'] = resource_path('share')



class SDBWidget(QWidget):

    def __init__(self):

        super(SDBWidget, self).__init__()

####### Default Values #######
        global njobs
        njobs = -1

        global method_list
        method_list = [
            'Multiple Linear Regression',
            'Random Forest', 
            'Support Vector Machines'
        ]

        global mlr_op_list
        mlr_op_list = [
            True, # fit_intercept
            False, # normalize
            True # copy_X
        ]

        global rf_op_list
        rf_op_list = [
            300, # n_estimators
            'mse' # criterion
        ]

        global svm_op_list
        svm_op_list = [
            'rbf', # kernel
            .1, # gamma
            1000.0 # C
        ]
####### Default Values #######

        self.initUI()


    def initUI(self):

        self.setGeometry(300, 100, 480, 640)
        self.setWindowTitle('Satellite Derived Bathymetry')
        self.setWindowIcon(QIcon(resource_path('satellite.png')))

        loadImageButton = QPushButton('Load Image')
        loadImageButton.clicked.connect(self.loadImageDialog)
        self.loadImageLabel = QLabel()
        self.loadImageLabel.setAlignment(Qt.AlignCenter)

        loadSampleButton = QPushButton('Load Sample')
        loadSampleButton.clicked.connect(self.loadSampleDialog)
        self.loadSampleLabel = QLabel()
        self.loadSampleLabel.setAlignment(Qt.AlignCenter)

        depthHeaderLabel = QLabel('Depth Header:')
        self.depthHeaderCB = QComboBox()

        bandStartLabel = QLabel('First Band Column:')
        self.bandStartCB = QComboBox()
        bandEndLabel = QLabel('Last Band Column:')
        self.bandEndCB = QComboBox()

        self.table = QTableWidget()
        scroll = QScrollArea()
        scroll.setWidget(self.table)

        self.limitCheckBox = QCheckBox('Disable Depth Limitation')
        self.limitCheckBox.setChecked(False)
        self.limitCheckBox.toggled.connect(self.limitCheckBoxState)
        self.limitState = QLabel('unchecked')

        limitLabel = QLabel('Depth Limit Value:')
        self.limitSB = QSpinBox()
        self.limitSB.setRange(-100, 0)
        self.limitSB.setValue(-30)
        self.limitSB.setAlignment(Qt.AlignRight)

        methodLabel = QLabel('Regression Method:')
        self.methodCB = QComboBox()

        self.methodCB.addItems(method_list)
        self.methodCB.activated.connect(self.methodSelection)

        trainPercentLabel = QLabel('Train Data (Percent):')
        self.trainPercentDSB = QDoubleSpinBox()
        self.trainPercentDSB.setRange(10.0, 90.0)
        self.trainPercentDSB.setDecimals(2)
        self.trainPercentDSB.setValue(75.0)
        self.trainPercentDSB.setAlignment(Qt.AlignRight)

        self.optionsButton = QPushButton('Options')
        self.optionsButton.clicked.connect(self.mlrOptionDialog)
        self.optionsButton.clicked.connect(self.methodSelection)

        makePredictionButton = QPushButton('Make Prediction')
        makePredictionButton.clicked.connect(self.predict)
        saveFileButton = QPushButton('Save Into File')
        saveFileButton.clicked.connect(self.saveOptionDialog)

        resultInfo = QLabel('Result Information')
        self.resultText = QTextBrowser()
        self.resultText.setAlignment(Qt.AlignRight)

        self.progressBar = QProgressBar()
        self.progressBar.setFormat('Step %v of %m completed')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(4)

        aboutButton = QPushButton('About')
        aboutButton.clicked.connect(self.aboutDialog)


        grid = QGridLayout()
        vbox = QVBoxLayout()

        grid.addWidget(loadImageButton, 1, 1, 1, 2)
        grid.addWidget(self.loadImageLabel, 1, 3, 1, 2)

        grid.addWidget(loadSampleButton, 2, 1, 1, 2)
        grid.addWidget(self.loadSampleLabel, 2, 3, 1, 2)

        grid.addWidget(depthHeaderLabel, 3, 1, 1, 1)
        grid.addWidget(self.depthHeaderCB, 3, 2, 1, 3)

        grid.addWidget(bandStartLabel, 4, 1, 1, 1)
        grid.addWidget(self.bandStartCB, 4, 2, 1, 1)
        grid.addWidget(bandEndLabel, 4, 3, 1, 1)
        grid.addWidget(self.bandEndCB, 4, 4, 1, 1)

        grid.addWidget(self.table, 5, 1, 5, 4)

        grid.addWidget(limitLabel, 10, 1, 1, 1)
        grid.addWidget(self.limitSB, 10, 2, 1, 1)
        grid.addWidget(self.limitCheckBox, 10, 3, 1, 2)

        grid.addWidget(methodLabel, 11, 1, 1, 1)
        grid.addWidget(self.methodCB, 11, 2, 1, 3)

        grid.addWidget(trainPercentLabel, 12, 1, 1, 1)
        grid.addWidget(self.trainPercentDSB, 12, 2, 1, 1)

        grid.addWidget(self.optionsButton, 12, 3, 1, 2)

        grid.addWidget(makePredictionButton, 13, 1, 1, 2)
        grid.addWidget(saveFileButton, 13, 3, 1, 2)

        grid.addWidget(resultInfo, 14, 1, 1, 2)
        grid.addWidget(self.resultText, 15, 1, 1, 4)

        vbox.addStretch(1)
        grid.addLayout(vbox, 21, 1)

        grid.addWidget(self.progressBar, 22, 1, 1, 4)

        grid.addWidget(aboutButton, 23, 1, 1, 4)
        self.setLayout(grid)


    def str2bool(self, v):
        '''Transform string to boolean'''

        return v in ('True')


    def limitCheckBoxState(self):

        if self.limitCheckBox.isChecked() == True:
            self.limitState.setText('checked')
        else:
            self.limitState.setText('unchecked')


    def methodSelection(self):

        if self.methodCB.currentText() == method_list[0]:
            self.optionsButton.clicked.disconnect()
            self.optionsButton.clicked.connect(self.mlrOptionDialog)
        elif self.methodCB.currentText() == method_list[1]:
            self.optionsButton.clicked.disconnect()
            self.optionsButton.clicked.connect(self.rfOptionDialog)
        elif self.methodCB.currentText() == method_list[2]:
            self.optionsButton.clicked.disconnect()
            self.optionsButton.clicked.connect(self.svmOptionDialog)


    def loadImageDialog(self):

        loadImage = QDialog()
        loadImage.setWindowTitle('Load Image')
        loadImage.setWindowIcon(QIcon(resource_path('load-pngrepo-com.png')))

        openFilesButton = QPushButton('Open File')
        openFilesButton.clicked.connect(self.imageFileDialog)

        locLabel = QLabel('Location:')
        self.locList = QTextBrowser()

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(loadImage.close)
        loadButton = QPushButton('Load')
        loadButton.clicked.connect(self.loadImageAction)
        loadButton.clicked.connect(loadImage.close)

        grid = QGridLayout()
        grid.addWidget(openFilesButton, 1, 1, 1, 4)

        grid.addWidget(locLabel, 4, 1, 1, 1)

        grid.addWidget(self.locList, 5, 1, 10, 4)

        grid.addWidget(loadButton, 15, 3, 1, 1)
        grid.addWidget(cancelButton, 15, 4, 1, 1)

        loadImage.setLayout(grid)

        loadImage.exec_()


    def imageFileDialog(self):

        home_dir = str(Path.home())
        fileFilter = 'All Files (*.*) ;; GeoTIFF (*.tif)'
        selectedFilter = 'GeoTIFF (*.tif)'
        fname = QFileDialog.getOpenFileName(self, 'Open File(s)', home_dir, fileFilter, selectedFilter)

        global img_loc
        img_loc = fname[0]

        global img_size
        img_size = os.path.getsize(img_loc)

        self.locList.setText(img_loc)


    def loadImageAction(self):

        global image_raw
        image_raw = rio.open(img_loc)

        nbands = len(image_raw.indexes)
        ndata = image_raw.read(1).size
        bands_dummy = np.zeros((nbands, ndata))
        for i in range(1, nbands + 1):
            bands_dummy[i - 1, :] = np.ravel(image_raw.read(i))

        global bands_array
        bands_array = bands_dummy.T

        coord1 = np.array(image_raw.transform * (0, 0))
        coord2 = np.array(image_raw.transform * (1, 1))

        global pixel_size
        pixel_size = coord2 - coord1

        self.loadImageLabel.setText('Image Data Loaded')


    def loadSampleDialog(self):

        loadSample = QDialog()
        loadSample.setWindowTitle('Load Sample')
        loadSample.setWindowIcon(QIcon(resource_path('load-pngrepo-com.png')))

        openFilesButton = QPushButton('Open File(s)')
        openFilesButton.clicked.connect(self.sampleFilesDialog)
        openFolderButton = QPushButton('Open Folder')
        openFolderButton.clicked.connect(self.sampleFolderDialog)

        sepLabel = QLabel('Separator:')
        self.sepCB = QComboBox()
        self.sepCB.addItems(['Comma', 'Tab', 'Space', 'Semicolon'])

        textTypeLabel = QLabel('Text Type')
        self.textTypeCB = QComboBox()
        self.textTypeCB.addItems(['.csv', '.txt', '.dat'])

        headerLineLabel = QLabel('Header Starting Line:')
        self.headerLineSB = QSpinBox()
        self.headerLineSB.setMinimum(1)
        self.headerLineSB.setAlignment(Qt.AlignRight)

        dataLineLabel = QLabel('Data Starting Line:')
        self.dataLineSB = QSpinBox()
        self.dataLineSB.setMinimum(1)
        self.dataLineSB.setAlignment(Qt.AlignRight)

        locLabel = QLabel('Location:')
        self.locList = QTextBrowser()

        self.showCheckBox = QCheckBox('Show All Data to Table')
        self.showCheckBox.setChecked(False)
        self.showCheckBox.toggled.connect(self.showCheckBoxState)
        self.showState = QLabel()

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(loadSample.close)
        loadButton = QPushButton('Load')
        loadButton.clicked.connect(self.loadSampleAction)
        loadButton.clicked.connect(loadSample.close)

        grid = QGridLayout()
        grid.addWidget(openFilesButton, 1, 1, 1, 2)
        grid.addWidget(openFolderButton, 1, 3, 1, 2)

        grid.addWidget(sepLabel, 2, 1, 1, 1)
        grid.addWidget(self.sepCB, 2, 2, 1, 1)
        grid.addWidget(textTypeLabel, 2, 3, 1, 1)
        grid.addWidget(self.textTypeCB, 2, 4, 1, 1)

        grid.addWidget(headerLineLabel, 3, 1, 1, 1)
        grid.addWidget(self.headerLineSB, 3, 2, 1, 1)
        grid.addWidget(dataLineLabel, 3, 3, 1, 1)
        grid.addWidget(self.dataLineSB, 3, 4, 1, 1)

        grid.addWidget(locLabel, 4, 1, 1, 1)

        grid.addWidget(self.locList, 5, 1, 10, 4)

        grid.addWidget(self.showCheckBox, 15, 1, 1, 2)
        grid.addWidget(loadButton, 15, 3, 1, 1)
        grid.addWidget(cancelButton, 15, 4, 1, 1)

        loadSample.setLayout(grid)

        loadSample.exec_()


    def sampleFilesDialog(self):

        home_dir = str(Path.home())
        fileFilter = 'All Files (*.*) ;; Text Files (*.txt) ;; Comma Separated Value (*.csv) ;; DAT Files (*.dat)'
        selectedFilter = 'Comma Separated Value (*.csv)'
        fname = QFileDialog.getOpenFileNames(self, 'Open File(s)', home_dir, fileFilter, selectedFilter)

        global filesList
        filesList = fname[0]

        global fileListPrint
        fileListPrint = ''

        for file in filesList:
            fileListPrint += file + '\n'

        self.locList.setText(fileListPrint)


    def sampleFolderDialog(self):

        home_dir = str(Path.home())
        fname = QFileDialog.getExistingDirectory(self, 'Open Folder', home_dir)

        textTypeDict = {'.txt': '.[Tt][Xx][Tt]', '.csv': '.[Cc][Ss][Vv]', '.dat': '.[Dd][Aa][Tt]'}
        textTypeSelect = textTypeDict[self.textTypeCB.currentText()]

        pathName = fname + '/**/*' + textTypeSelect

        global filesList
        filesList = glob.glob(pathName, recursive=True)

        global fileListPrint
        fileListPrint = ''

        for file in filesList:
            fileListPrint += file + '\n'

        self.locList.setText(fileListPrint)


    def showCheckBoxState(self):

        if self.showCheckBox.isChecked() == True:
            self.showState.setText('checked')
        else:
            self.showState.setText('unchecked')


    def loadSampleDict(self):

        head = self.headerLineSB.value() - 1
        start_data = self.dataLineSB.value() - 1
        sepDict = {'Tab': '\t', 'Comma': ',', 'Space': ' ', 'Semicolon': ';'}
        sepSelect = sepDict[self.sepCB.currentText()]

        dummy = []

        global sample_size
        sample_size = np.ones(len(filesList))

        for file in filesList:
            raw_single = pd.read_csv(file, sep=sepSelect, header=head)
            raw_single = raw_single.iloc[start_data:, 0:]

            dummy.append(raw_single)

            sample_size[filesList.index(file)] = os.path.getsize(file)

        sample_size = sample_size.sum()

        global samples_raw
        samples_raw = pd.concat(dummy, ignore_index=True, sort=False)

        return samples_raw


    def loadSampleAction(self):

        raw = self.loadSampleDict()

        if self.showState.text() == 'checked':
            data = raw
        else:
            data = raw.head(100)

        self.depthHeaderCB.clear()
        self.depthHeaderCB.addItems(data.columns)
        self.bandStartCB.clear()
        self.bandStartCB.addItems(data.columns)
        self.bandStartCB.setCurrentIndex(1)
        self.bandEndCB.clear()
        self.bandEndCB.addItems(data.columns)
        self.bandEndCB.setCurrentIndex(data.columns.size - 1)

        self.table.setColumnCount(len(data.columns))
        self.table.setRowCount(len(data.index))

        for h in range(len(data.columns)):
            self.table.setHorizontalHeaderItem(
                h, QTableWidgetItem(data.columns[h]))

        for i in range(len(data.index)):
            for j in range(len(data.columns)):
                self.table.setItem(i, j, QTableWidgetItem(str(data.iloc[i, j])))

        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()

        self.loadSampleLabel.setText('Sample Data Loaded')


    def mlrOptionDialog(self):

        optionDialog = QDialog()
        optionDialog.setWindowTitle('Options (MLR)')
        optionDialog.setWindowIcon(QIcon(resource_path('setting-tool-pngrepo-com.png')))

        fitInterceptLabel = QLabel('Fit Intercept:')
        self.fitInterceptCB = QComboBox()
        self.fitInterceptCB.addItems(['True', 'False'])

        normalizeLabel = QLabel('Normalize:')
        self.normalizeCB = QComboBox()
        self.normalizeCB.addItems(['True', 'False'])
        self.normalizeCB.setCurrentIndex(1)

        copyXLabel = QLabel('Copy X:')
        self.copyXCB = QComboBox()
        self.copyXCB.addItems(['True', 'False'])

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(optionDialog.close)
        loadButton = QPushButton('Load')
        loadButton.clicked.connect(self.loadMLROptionAction)
        loadButton.clicked.connect(optionDialog.close)

        grid = QGridLayout()

        grid.addWidget(fitInterceptLabel, 1, 1, 1, 2)
        grid.addWidget(self.fitInterceptCB, 1, 3, 1, 2)

        grid.addWidget(normalizeLabel, 2, 1, 1, 2)
        grid.addWidget(self.normalizeCB, 2, 3, 1, 2)

        grid.addWidget(copyXLabel, 3, 1, 1, 2)
        grid.addWidget(self.copyXCB, 3, 3, 1, 2)

        grid.addWidget(loadButton, 4, 3, 1, 1)
        grid.addWidget(cancelButton, 4, 4, 1, 1)

        optionDialog.setLayout(grid)

        optionDialog.exec_()


    def loadMLROptionAction(self):

        global mlr_op_list
        mlr_op_list = [
            self.str2bool(self.fitInterceptCB.currentText()),
            self.str2bool(self.normalizeCB.currentText()),
            self.str2bool(self.copyXCB.currentText())
        ]


    def rfOptionDialog(self):

        optionDialog = QDialog()
        optionDialog.setWindowTitle('Options (Random Forest)')
        optionDialog.setWindowIcon(
            QIcon(resource_path('setting-tool-pngrepo-com.png')))

        ntreeLabel = QLabel('Number of Trees:')
        self.ntreeSB = QSpinBox()
        self.ntreeSB.setRange(1, 10000)
        self.ntreeSB.setValue(300)
        self.ntreeSB.setAlignment(Qt.AlignRight)

        criterionLabel = QLabel('Criterion:')
        self.criterionCB = QComboBox()
        self.criterionCB.addItems(['mse', 'mae'])

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(optionDialog.close)
        loadButton = QPushButton('Load')
        loadButton.clicked.connect(self.loadRFOptionAction)
        loadButton.clicked.connect(optionDialog.close)

        grid = QGridLayout()

        grid.addWidget(ntreeLabel, 1, 1, 1, 2)
        grid.addWidget(self.ntreeSB, 1, 3, 1, 2)

        grid.addWidget(criterionLabel, 2, 1, 1, 2)
        grid.addWidget(self.criterionCB, 2, 3, 1, 2)

        grid.addWidget(loadButton, 3, 3, 1, 1)
        grid.addWidget(cancelButton, 3, 4, 1, 1)

        optionDialog.setLayout(grid)

        optionDialog.exec_()


    def loadRFOptionAction(self):

        global rf_op_list
        rf_op_list = [
            self.ntreeSB.value(),
            self.criterionCB.currentText()
        ]


    def svmOptionDialog(self):

        optionDialog = QDialog()
        optionDialog.setWindowTitle('Options (SVM)')
        optionDialog.setWindowIcon(
            QIcon(resource_path('setting-tool-pngrepo-com.png')))

        kernelLabel = QLabel('Kernel:')
        self.kernelCB = QComboBox()
        self.kernelCB.addItems(['linear', 'poly', 'rbf', 'sigmoid', 'precomputed'])
        self.kernelCB.setCurrentIndex(2)

        gammaLabel = QLabel('Gamma:')
        self.gammaDSB = QDoubleSpinBox()
        self.gammaDSB.setRange(0, 10)
        self.gammaDSB.setDecimals(3)
        self.gammaDSB.setValue(.1)
        self.gammaDSB.setAlignment(Qt.AlignRight)

        cLabel = QLabel('C:')
        self.cDSB = QDoubleSpinBox()
        self.cDSB.setRange(.001, 10000)
        self.cDSB.setDecimals(3)
        self.cDSB.setValue(1000.0)
        self.cDSB.setAlignment(Qt.AlignRight)

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(optionDialog.close)
        loadButton = QPushButton('Load')
        loadButton.clicked.connect(self.loadSVMOptionAction)
        loadButton.clicked.connect(optionDialog.close)

        grid = QGridLayout()

        grid.addWidget(kernelLabel, 1, 1, 1, 2)
        grid.addWidget(self.kernelCB, 1, 3, 1, 2)

        grid.addWidget(gammaLabel, 2, 1, 1, 2)
        grid.addWidget(self.gammaDSB, 2, 3, 1, 2)

        grid.addWidget(cLabel, 3, 1, 1, 2)
        grid.addWidget(self.cDSB, 3, 3, 1, 2)

        grid.addWidget(loadButton, 4, 3, 1, 1)
        grid.addWidget(cancelButton, 4, 4, 1, 1)

        optionDialog.setLayout(grid)

        optionDialog.exec_()


    def loadSVMOptionAction(self):

        global svm_op_list
        svm_op_list = [
            self.kernelCB.currentText(),
            self.gammaDSB.value(),
            self.cDSB.value()
        ]


    def inputDict(self):

        samples_edit = samples_raw.copy()

        depth_label = self.depthHeaderCB.currentText()
        start_label = self.bandStartCB.currentText()
        end_label = self.bandEndCB.currentText()

        test_data_size = (100 - self.trainPercentDSB.value()) / 100

        positives_count = samples_edit[samples_edit[depth_label] > 0][depth_label].count()
        samples_count = samples_edit[depth_label].count()

        if positives_count > samples_count / 2:
            samples_edit[depth_label] = samples_edit[depth_label] * -1
        else:
            pass

        if self.limitState.text() == 'unchecked':
            print('checking input')
            samples_edit = samples_edit[samples_edit[depth_label] >= self.limitSB.value()]
            samples_edit = samples_edit[samples_edit[depth_label] <= 0]
        else:
            pass

        start_loc = samples_edit.columns.get_loc(start_label)
        end_loc = samples_edit.columns.get_loc(end_label)

        features = samples_edit.iloc[:, start_loc:end_loc+1]
        z = samples_edit[depth_label]

        features_train, features_test, z_train, z_test = train_test_split(features, z, test_size=test_data_size, random_state=0)

        samples_split = [features_train, features_test, z_train, z_test]

        self.progressBar.setValue(1)

        return samples_split


    def mlrPredict(self):
        print('mlrPredict')

        samples_split = self.inputDict()

        regressor = LinearRegression(
            fit_intercept=mlr_op_list[0],
            normalize=mlr_op_list[1],
            copy_X=mlr_op_list[2]
        )

        samples_split.append(regressor)

        global print_parameters_info
        print_parameters_info = (
            'Fit Intercept:' + '\t\t' + str(mlr_op_list[0]) + '\n' +
            'Normalize:' + '\t\t' + str(mlr_op_list[1]) + '\n' +
            'Copy X:' + '\t\t' + str(mlr_op_list[2])
        )

        return samples_split


    def rfPredict(self):
        print('rfPredict')

        samples_split = self.inputDict()

        regressor = RandomForestRegressor(
            n_estimators=rf_op_list[0],
            criterion=rf_op_list[1],
            random_state=0)

        samples_split.append(regressor)

        global print_parameters_info
        print_parameters_info = (
            'N Trees:' + '\t\t' + str(rf_op_list[0]) + '\n' +
            'Criterion:' + '\t\t' + str(rf_op_list[1])
        )

        return samples_split


    def svmPredict(self):
        print('svmPredict')

        samples_split = self.inputDict()

        regressor = SVR(
            kernel=svm_op_list[0],
            gamma=svm_op_list[1],
            C=svm_op_list[2],
            cache_size=8000)

        samples_split.append(regressor)

        global print_parameters_info
        print_parameters_info = (
            'Kernel:' + '\t\t' + str(svm_op_list[0]) +'\n' +
            'Gamma:' + '\t\t' + str(svm_op_list[1]) + '\n' +
            'C:' + '\t\t' + str(svm_op_list[2])
        )

        return samples_split


    def predict(self):
        print('prediction')

        self.resultText.setText('Fitting...\n')
        time_start = datetime.datetime.now()

        if self.methodCB.currentText() == method_list[0]:
            regressor = self.mlrPredict()
        elif self.methodCB.currentText() == method_list[1]:
            regressor = self.rfPredict()
        else:
            regressor = self.svmPredict()

        with parallel_backend('threading', n_jobs=njobs):

            regressor[4].fit(regressor[0], regressor[2])

            time_fit = datetime.datetime.now()
            self.resultText.append('Predicting...\n')
            self.progressBar.setValue(2)

            global z_predict
            z_predict = regressor[4].predict(bands_array)

            if self.limitState.text() == 'unchecked':
                print('checking prediction')
                z_predict[z_predict < self.limitSB.value()] = np.nan
                z_predict[z_predict > 0] = np.nan

                print_limit = (
                    'Depth Limit:' + '\t\t' + str(self.limitSB.value())
                )
            else:
                print_limit = (
                    'Depth Limit:' + '\t\t' + 'Disabled'
                )
                pass

            time_predict = datetime.datetime.now()
            self.resultText.append('Calculating RMSE, MAE, and R\u00B2...\n')
            self.progressBar.setValue(3)

            z_validate = regressor[4].predict(regressor[1])
            rmse = np.sqrt(metrics.mean_squared_error(regressor[3], z_validate))
            mae = metrics.mean_absolute_error(regressor[3], z_validate)
            r2 = metrics.r2_score(regressor[3], z_validate)

            time_test = datetime.datetime.now()
            self.progressBar.setValue(4)

        runtime = [
            time_fit - time_start,
            time_predict - time_fit,
            time_test - time_predict,
            time_test - time_start
        ]

        global print_result_info
        print_result_info = (
            'Image Input:' + '\t\t' + img_loc + ' (' +
            str(round(img_size / 2**10 / 2**10, 2)) + ' MB)' + '\n' +
            'Sample Data:' + '\t\t' + fileListPrint + ' (' +
            str(round(sample_size / 2**10 / 2**10, 2)) + ' MB)' + '\n\n' +
            print_limit + '\n' +
            'Train Data:' + '\t\t' + str(self.trainPercentDSB.value()) + ' %' + '\n'
            'Test Data:' + '\t\t' + str(100 - self.trainPercentDSB.value()) + ' %' + '\n\n'
            'Method:' + '\t\t' + self.methodCB.currentText() + '\n' +
            print_parameters_info + '\n\n'
            'RMSE:' + '\t\t' + str(rmse) + '\n' +
            'MAE:' + '\t\t' + str(mae) + '\n' +
            'R\u00B2:' + '\t\t' + str(r2) + '\n\n' +
            'Fitting Runtime:' + '\t\t' + str(runtime[0]) + '\n' +
            'Prediction Runtime:' + '\t' + str(runtime[1]) + '\n' +
            'Validating Runtime:' + '\t' + str(runtime[2]) + '\n' +
            'Overall Runtime:' + '\t' + str(runtime[3]) + '\n\n' +
            'CRS:' + '\t\t' + str(image_raw.crs) +'\n'
            'Dimensions:' + '\t\t' + str(image_raw.width) + ' x ' + 
            str(image_raw.height) + ' pixels' + '\n'
            'Pixel Size:' + '\t\t' + str(pixel_size[0]) + ' , ' + 
            str(pixel_size[1]) + '\n\n'
        )

        self.resultText.setText(print_result_info)


    def saveOptionDialog(self):

        saveOption = QDialog()
        saveOption.setWindowTitle('Save Options')
        saveOption.setWindowIcon(QIcon(resource_path('load-pngrepo-com.png')))

        saveFileButton = QPushButton('Save File Location')
        saveFileButton.clicked.connect(self.savePathDialog)

        global format_dict
        format_dict = {
            'GeoTIFF (*.tif)': 'GTiff',
            'Erdas Imagine image (*.img)': 'HFA',
            'ASCII Gridded XYZ (*.xyz)': 'XYZ'
        }

        format_list = list(format_dict)
        format_list.sort()

        dataTypeLabel = QLabel('Data Type:')
        self.dataTypeCB = QComboBox()
        self.dataTypeCB.addItems(format_list)
        self.dataTypeCB.setCurrentText('GeoTIFF (*.tif)')

        locLabel = QLabel('Location:')
        self.locList = QTextBrowser()

        self.reportCheckBox = QCheckBox('Save Report')
        self.reportCheckBox.setChecked(True)
        self.reportCheckBox.toggled.connect(self.reportCheckBoxState)
        self.reportState = QLabel('checked')

        cancelButton = QPushButton('Cancel')
        cancelButton.clicked.connect(saveOption.close)
        saveButton = QPushButton('Save')
        saveButton.clicked.connect(self.saveAction)
        saveButton.clicked.connect(saveOption.close)

        grid = QGridLayout()
        grid.addWidget(dataTypeLabel, 1, 1, 1, 2)
        grid.addWidget(self.dataTypeCB, 1, 3, 1, 2)

        grid.addWidget(saveFileButton, 2, 1, 1, 4)

        grid.addWidget(locLabel, 3, 1, 1, 4)
        grid.addWidget(self.locList, 4, 1, 1, 4)

        grid.addWidget(self.reportCheckBox, 5, 1, 1, 2)
        grid.addWidget(saveButton, 5, 3, 1, 1)
        grid.addWidget(cancelButton, 5, 4, 1, 1)

        saveOption.setLayout(grid)

        saveOption.exec_()


    def savePathDialog(self):

        home_dir = str(Path.home())
        fileFilter = 'All Files(*.*) ;; ' + self.dataTypeCB.currentText()
        selectedFilter = self.dataTypeCB.currentText()
        fname = QFileDialog.getSaveFileName(self, 'Save File', home_dir, fileFilter, selectedFilter)

        global save_loc
        save_loc = fname[0]

        self.locList.setText(save_loc)

    def reportCheckBoxState(self):

        if self.reportCheckBox.isChecked() == True:
            self.reportState.setText('checked')
        else:
            self.reportState.setText('unchecked')


    def saveAction(self):

        z_img_ar = z_predict.reshape(image_raw.height, image_raw.width)

        new_img = rio.open(
            save_loc,
            'w',
            driver=format_dict[self.dataTypeCB.currentText()],
            height=image_raw.height,
            width=image_raw.width,
            count=1,
            dtype=z_img_ar.dtype,
            crs=image_raw.crs,
            transform=image_raw.transform
        )

        new_img.write(z_img_ar, 1)
        new_img.close()

        if self.reportState.text() == 'checked':
            report_save_loc = os.path.splitext(save_loc)[0] + '_report.txt'
            report = open(report_save_loc, 'w')
            new_img_size = os.path.getsize(save_loc)

            report.write(
                print_result_info +
                'Output:' + '\t\t' + save_loc + ' (' +
                str(round(new_img_size / 2**10 / 2**10, 2)) + ' MB)'
            )
        else:
            pass



    def aboutDialog(self):

        about = QDialog()
        about.setWindowTitle('About')
        about.resize(500, 380)
        about.setWindowIcon(QIcon(resource_path('information-pngrepo-com.png')))

        okButton = QPushButton('OK')
        okButton.clicked.connect(about.close)

        license_file = open(resource_path('LICENSE'), 'r')
        licenseLabel = QLabel('SDB GUI')
        licenseText = QTextBrowser()
        licenseText.setText(license_file.read())

        grid = QGridLayout()

        grid.addWidget(licenseLabel, 1, 1, 1, 4)

        grid.addWidget(licenseText, 2, 1, 1, 4)

        grid.addWidget(okButton, 3, 4, 1, 1)

        about.setLayout(grid)

        about.exec_()



def main():

    global sdb
    sdb = SDBWidget()
    sdb.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main()
    sys.exit(app.exec_())
