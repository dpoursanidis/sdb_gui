# Satellite Derived Bathymetry (SDB) GUI
This is a GUI to make a bathimetric prediction using satellite imagery and some depth samples corresponding to the imagery. If you wish to use the GUI, please download the pre-release version (version 1.0.0). Or if you want to run the source code instead, please install `python 3.6.x` and the following libraries first:

1. Numpy
2. Pandas
3. Rasterio
4. Scikit Learn
5. PyQt5

Prepare your own data before using this SDB GUI. The required data are georeferenced and corrected imagery and tabular data consisting depth sample and corresponding raster values in the form of text file (e.g. CSV, TXT, or DAT file). 

Open SDB GUI and load both data. Choose one of the methods and decide how much of the sample you're going to use as training data. If you push `Make Prediction` button right away, the software will use default hyperparameters. If you want to tweak the hyperparameters, push `Options` button.

## Methods
I am only using two methods to make the depth prediction at the time (this maybe updated in the future), [Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html#sklearn.ensemble.RandomForestRegressor "RF Regressor") and [Support Vector Machines](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVR.html#sklearn.svm.SVR "SVM Regressor").

### Random Forest
The adjustable hyperparameters for Random Forest method are the number of trees and the function to measure the quality of a split (criterion). The default values respectively are 300 and mse (Mean Square Error). The other value for the criterion is mae (Mean Absolute Error).

### Support Vector Machines
The adjustable hyperparameters for SVM method are kernel type, kernel coefficient (gamma), and regularization parameter (C). The default hyperparameter values are rbf for kernel type, 0.1 for gamma, and 1.0 for C.