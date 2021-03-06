import torch
from torch import nn
import torch.nn.functional as F
import numpy as np

from models.healpix_pool_unpool import Healpix
from models.laplacians import get_healpix_laplacians
from models.layers import SphericalChebBNPool, SphericalChebBNPoolGeom

# pylint: disable=W0223


class SphericalGraphCNN(nn.Module):
    """Spherical GCNN Autoencoder.
    """

    def __init__(self, nside_list, indexes_list, kernel_size=4, n_neighbours=8, laplacian_type="combinatorial", fc_dims=[[-1, 2048], [2048, 512], [512, 96]], n_aux=0, n_params=0, activation="relu", nest=True, conv_source="deepsphere", conv_type="chebconv", conv_channel_config="standard", mask=None):
        """Initialization.

        Args:
            kernel_size (int): chebychev polynomial degree
        """
        super().__init__()
        self.kernel_size = kernel_size
        self.pooling_class = Healpix(mode="max")

        self.n_aux = n_aux
        self.n_params = n_params

        self.mask = mask

        # Specify convolutional part

        self.laps, self.adjs = get_healpix_laplacians(nside_list=nside_list, laplacian_type=laplacian_type, indexes_list=indexes_list, n_neighbours=n_neighbours, nest=nest)

        self.cnn_layers = []

        if activation == "relu":
            self.activation_function = nn.ReLU()
        elif activation == "selu":
            self.activation_function = nn.SELU()
        else:
            raise NotImplementedError
        
        if conv_channel_config == "standard":
            conv_config = [(1, 32), (32, 64), (64, 128), (128, 256), (256, 256), (256, 256), (256, 256)]
        elif conv_channel_config == "more_channels":
            conv_config = [(1, 32), (32, 64), (64, 128), (128, 256), (256, 512), (512, 512), (512, 512)]
        elif conv_channel_config == "fewer_layers":
            conv_config = [(1, 32), (32, 64), (64, 128), (128, 256), (256, 512), (512, 512)]
        else:
            raise NotImplementedError

        npix_final = int(len(indexes_list[len(conv_config) - 1]) / 4)  # Number of pixels in final layers

        for i, (in_ch, out_ch) in enumerate(conv_config):

            if conv_source == "deepsphere":
                layer = SphericalChebBNPool(in_ch, out_ch, self.laps[i], self.pooling_class.pooling, self.kernel_size, activation)
            elif conv_source == "geometric":
                layer = SphericalChebBNPoolGeom(in_ch, out_ch, self.adjs[i], self.pooling_class.pooling, self.kernel_size, laplacian_type=laplacian_type, indexes_list=indexes_list[i], activation=activation, conv_type=conv_type)
            else:
                raise NotImplementedError

            setattr(self, "layer_{}".format(i), layer)
            self.cnn_layers.append(layer)

        # Specify fully-connected part
        self.fc_layers = []

        if fc_dims is not None:
            # Set shape of first input of FC layers to correspond to output of conv layers + aux variables
            fc_dims[0][0] = conv_config[-1][-1] * npix_final + self.n_aux + self.n_params
        
            for i, (in_ch, out_ch) in enumerate(fc_dims):
                if i == len(fc_dims) - 1:  # No activation in final FC layer
                    layer = nn.Sequential(nn.Linear(in_ch, out_ch))
                else:
                    layer = nn.Sequential(nn.Linear(in_ch, out_ch), self.activation_function)
                setattr(self, "layer_fc_{}".format(i), layer)
                self.fc_layers.append(layer)

    def forward(self, x):
        """Forward Pass.

        Args:
            x (:obj:`torch.Tensor`): input to be forwarded.

        Returns:
            :obj:`torch.Tensor`: output
        """

        # Initialize tensor
        x = x.view(-1, 16384 + self.n_aux + self.n_params, 1)
        x_map_temp = x[:, :16384, :]

        try:
            if self.mask is not None:
                x_map = x_map_temp.clone()
                x_map[:, self.mask, :] = 0.
            else:
                x_map = x_map_temp
        except:
            x_map = x_map_temp

        # Convolutional layers
        for i_layer, layer in enumerate(self.cnn_layers):
            x_map = layer(x_map)
            # np.save("../data/feature_maps/x_map_" + str(i_layer) + ".npy", x_map.detach().numpy())  # Save intermediate feature maps for plotting

        # Concatenate auxiliary variable along last dimension
        if (self.n_aux != 0) or (self.n_params != 0):
            x_aux = x[:, 16384:16384 + self.n_aux + self.n_params, :]
            x_aux = x_aux.view(-1, 1, self.n_aux + self.n_params)
            x_map = x_map.contiguous().view(-1, 1, x_map.shape[1] * x_map.shape[2])
            x_map = torch.cat([x_map, x_aux], -1)

        # FC layers
        for layer in self.fc_layers:
            x_map = layer(x_map)

        return x_map[:, 0, :]