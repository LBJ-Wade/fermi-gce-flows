# This file is part of sbi, a toolkit for simulation-based inference. sbi is licensed
# under the Affero General Public License v3, see <https://www.gnu.org/licenses/>.


from typing import Callable

from torch import nn

from sbi.neural_nets.flow import build_maf, build_nsf

def posterior_nn(
    model: str,
    z_score_theta: bool = True,
    z_score_x: bool = True,
    hidden_features: int = 50,
    num_transforms: int = 5,
    embedding_net: nn.Module = nn.Identity(),
    num_components: int = 10,
    normalize_pixel: bool = True,
    activation: str = "relu",
) -> Callable:
    r"""
    Returns a function that builds a density estimator for learning the posterior.

    This function will usually be used for SNPE. The returned function is to be passed
    to the inference class when using the flexible interface.

    Args:
        model: The type of density estimator that will be created. One of [`mdn`,
            `made`, `maf`, `nsf`].
        z_score_theta: Whether to z-score parameters $\theta$ before passing them into
            the network.
        z_score_x: Whether to z-score simulation outputs $x$ before passing them into
            the network.
        hidden_features: Number of hidden features.
        num_transforms: Number of transforms when a flow is used. Only relevant if
            density estimator is a normalizing flow (i.e. currently either a `maf` or a
            `nsf`). Ignored if density estimator is a `mdn` or `made`.
        embedding_net: Optional embedding network for simulation outputs $x$. This
            embedding net allows to learn features from potentially high-dimensional
            simulation outputs.
        num_components: Number of mixture components for a mixture of Gaussians.
            Ignored if density estimator is not an mdn.
    """

    kwargs = dict(
        zip(
            (
                "z_score_x",
                "z_score_y",
                "hidden_features",
                "num_transforms",
                "embedding_net",
                "num_components",
                "normalize_pixel",
                "activation",
            ),
            (
                z_score_theta,
                z_score_x,
                hidden_features,
                num_transforms,
                embedding_net,
                num_components,
                normalize_pixel,
                activation,
            ),
        )
    )

    def build_fn(batch_theta, batch_x):
        if model == "maf":
            return build_maf(batch_x=batch_theta, batch_y=batch_x, **kwargs)
        elif model == "nsf":
            return build_nsf(batch_x=batch_theta, batch_y=batch_x, **kwargs)
        else:
            raise NotImplementedError

    return build_fn
