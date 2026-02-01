from abc import ABC, abstractmethod
from typing import Union
import pandas as pd
import numpy as np
from flaml import AutoML
import pickle
import warnings
warnings.filterwarnings("ignore")


class SurrogateModel(ABC):

    """
    Abstract base class for surrogate models.
    """

    @abstractmethod
    def train(self, X_train: Union[pd.DataFrame, pd.Series,np.ndarray], y_train: Union[pd.DataFrame, pd.Series,np.ndarray]) :
        """
        Trains the surrogate model.
        Args:
            X_train (pd.DataFrame): The training data.
            y_train (pd.Series): The target variable.
        Returns:
            SurrogateModel: The trained surrogate model.
        """
        pass

    @abstractmethod
    def predict(self, X_test: Union[pd.DataFrame, pd.Series, np.ndarray]) -> Union[pd.Series, np.ndarray]:
        """
        Predicts the target variable using the surrogate model.
        Args:
            X_test (pd.DataFrame): The test data.
        Returns:
            pd.Series: The predicted target variable.
        """
        pass
    
    @abstractmethod
    def load_model(self, model_file: str):
        """
        Loads the surrogate model.
        Args:
            model_file (str): The model file.
        Returns:
            SurrogateModel: The loaded surrogate model.
        """
        pass
    
    @abstractmethod
    def save_model(self, model_file: str):
        """
        Saves the surrogate model.
        Args:
            model_file (str): The model file.
        """
        pass
    

class SurrogateAutoMLModel(SurrogateModel):


    """
    Constructor for the SurrogateModel class
    Using the FLAML library to train a surrogate model
    """

    def __init__(self, model_name="surrogate", time_budget=60, **kwargs):

        """
        Initializes the SurrogateModel class.

        This class uses the FLAML library to train a surrogate model.

        Args:
            model_name (str): The name of the model for saving the model file.
            time_budget (int): The time budget for training the model.

        Keyword Args:
            metric (str): The metric to optimize.
            task (str): The type of task.
            n_splits (int): The number of splits for cross-validation.
            n_jobs (int): The number of jobs to run in parallel.
            estimator_list (list): The list of estimators to use.
        """

        self.model_name = model_name

        self.automl = AutoML()

        self.automl_settings = {
            "time_budget": time_budget,
            "metric": "mse",
            "task": "regression",
            "n_splits": 5,
            "n_jobs": 1,
            "estimator_list": [
                "lgbm",
                "xgboost",
                "rf",
                #"extra_tree",
                #"catboost",
                #"ann",
                #"svr",
                ]
        }

        if kwargs:
            self.automl_settings.update(kwargs)

    def train(self, X_train, y_train):

        """
        Trains the surrogate model.
        Args:
            X_train (pd.DataFrame): The training data.
            y_train (pd.Series): The target variable.
        Returns:
            SurrogateModel: The trained surrogate model.
        """

        self.automl.fit(X_train=X_train, y_train=y_train, **self.automl_settings)
        
        best_model = self.automl.model.estimator
        
        return best_model
    
    def predict(self, X_test):

        """
        Predicts the target variable using the surrogate model.
        Args:
            X_test (pd.DataFrame): The test data.
        Returns:
            pd.Series: The predicted target variable.
        """

        return self.automl.predict(X_test)

    def load_model(self, model_file):
        
        """
        Loads the surrogate model.
        Args:
            model_file (str): The model file.
        Returns:
            SurrogateModel: The loaded surrogate model.
        """

        with open(model_file, "rb") as f:
            self.automl = pickle.load(f)

        return self.automl
    
    def save_model(self, model_file=None):
        
        """
        Saves the surrogate model.
        Args:
            model_file (str): The model file.
        """

        model_file = f"{self.model_name}.pkl" if model_file is None else model_file
    
        # Save the model
        with open(model_file, "wb") as f:
            pickle.dump(self.automl, f, pickle.HIGHEST_PROTOCOL)
    
    
class SurrogateTabPFN(SurrogateModel):
    
    def __init__(self, model_name="tabpfnsurrogate", time_budget=None, **kwargs):
        
        self.model_name = model_name
        
        if time_budget: 
            try: 
                from tabpfn_extensions.post_hoc_ensembles.sklearn_interface import AutoTabPFNRegressor
                self.reg = AutoTabPFNRegressor(max_time=time_budget, **kwargs)
                
            except ImportError:
                raise ImportError("tabpfn is not installed. Please install it using: git clone https://github.com/priorlabs/tabpfn-extensions.git && pip install -e tabpfn-extensions")

        else:
            try:
                from tabpfn import TabPFNRegressor
                self.reg = TabPFNRegressor()
            except ImportError:
                raise ImportError("tabpfn is not installed. Please install it using: pip install tabpfn")
        
    def train(self, X_train, y_train):
        self.reg.fit(X_train, y_train)
        return self.reg
    
    def predict(self, X_test):
        return self.reg.predict(X_test)
        
    def load_model(self, model_file):
        with open(model_file, "rb") as f:
            self.reg = pickle.load(f)
        return self.reg
        
    def save_model(self, model_file=None):
        model_file = f"{self.model_name}.pkl" if model_file is None else model_file
        # Save the model
        with open(model_file, "wb") as f:
            pickle.dump(self.reg, f, pickle.HIGHEST_PROTOCOL)
        