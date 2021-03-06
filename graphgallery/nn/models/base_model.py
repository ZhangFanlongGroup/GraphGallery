import random
import logging
import torch

import numpy as np
import tensorflow as tf
import os.path as osp
import scipy.sparse as sp

from tensorflow.keras import backend as K

from graphgallery.nn.models import Base
from graphgallery.data.io import makedirs_from_path
from graphgallery.utils import save
from graphgallery import POSTFIX


class BaseModel(Base):
    """Base model for semi-supervised learning and unsupervised learning."""

    def __init__(self, *graph, device="cpu:0", seed=None, name=None, **kwargs):
        """Create an Base model for semi-supervised learning and unsupervised learning.

        Parameters:
        ----------
            graph: Graph or MultiGraph.
            device: string. optional
                The device where the model running on.
            seed: interger scalar. optional
                Used in combination with `tf.random.set_seed` & `np.random.seed`
                & `random.seed` to create a reproducible sequence of tensors
                across multiple calls.
            name: string. optional
                Specified name for the model. (default: :str: `class.__name__`)
            kwargs: other customized keyword parameters.

        """
        super().__init__(*graph, device=device, seed=seed, name=name, **kwargs)
        
        self.idx_train = None
        self.idx_val = None
        self.idx_test = None
        self.backup = None

        self._model = None
        self._custom_objects = None  # used for save/load TF model

        # log path
        # add random integer to avoid duplication
        _id = np.random.RandomState(None).randint(100)
        self.weight_path = osp.join(osp.expanduser(osp.normpath("/tmp/weight")),
                                    f"{self.name}_{_id}_weights{POSTFIX}")

    def save(self, path=None, as_model=False, overwrite=True, save_format=None, **kwargs):

        if not path:
            path = self.weight_path

        makedirs_from_path(path)

        if as_model:
            if self.kind == "T":
                save.save_tf_model(self.model, path, overwrite=overwrite, save_format=save_format, **kwargs)
            else:
                save.save_torch_model(self.model, path, overwrite=overwrite, save_format=save_format, **kwargs)
        else:
            if self.kind == "T":
                save.save_tf_weights(self.model, path, overwrite=overwrite, save_format=save_format)
            else:
                save.save_torch_weights(self.model, path, overwrite=overwrite, save_format=save_format)

    def load(self, path=None, as_model=False):
        if not path:
            path = self.weight_path

        if as_model:
            if self.kind == "T":
                self.model = save.load_tf_model(
                    path, custom_objects=self.custom_objects)
            else:
                self.model = save.load_torch_model(path)
        else:
            if self.kind == "T":
                save.load_tf_weights(self.model, path)
            else:
                save.load_torch_weights(self.model, path)

    def __getattr__(self, attr):
        ##### TODO: This may cause ERROR ######
        try:
            return self.__dict__[attr]
        except KeyError:
            if hasattr(self, "_model") and hasattr(self._model, attr):
                return getattr(self._model, attr)
            raise AttributeError(
                f"'{self.name}' and '{self.name}.model' objects have no attribute '{attr}'")

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, m):
        # Back up
        if isinstance(m, tf.keras.Model) and m.weights:
            self.backup = tf.identity_n(m.weights)
        # assert m is None or isinstance(m, tf.keras.Model) or torch.nn.Module
        self._model = m

    @property
    def custom_objects(self):
        return self._custom_objects

    @custom_objects.setter
    def custom_objects(self, value):
        assert isinstance(value, dict)
        self._custom_objects = value

    @property
    def close(self):
        """Close the session of model and set `built` to False."""
        K.clear_session()
        self.model = None

    def __call__(self, *args, **kwargs):
        return self._model(*args, **kwargs)

    def __repr__(self):
        return f"GraphGallery.nn.{self.name}(device={self.device}, backend={self.backend})"
