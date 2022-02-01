""" Standardized layers implemented in keras.
"""


from warnings import WarningMessage
from tensorflow.keras import layers
import tensorflow as tf

try:
    import tensorflow_addons as tfa

    InstanceNormalization = tfa.layers.InstanceNormalization
    GELU = layers.Lambda(lambda x: tfa.activations.gelu(x, approximate=False))
except Exception:
    import warnings

    InstanceNormalization, GELU = (layers.Layer(),) * 2
    warnings.warn(
        "DeepTrack not installed with tensorflow addons. Instance normalization will not work. Consider upgrading to tensorflow >= 2.0.",
        ImportWarning,
    )

import pkg_resources

installed_pkg = [pkg.key for pkg in pkg_resources.working_set]

BLOCKS = {}


def register(*names):
    "Register a block to a name for use in models."

    def decorator(block):
        for name in names:
            if name in BLOCKS:
                warnings.warn(
                    f"Overriding registered block {name} with a new block.",
                    WarningMessage,
                )

            BLOCKS[name] = block()
        return block

    return decorator


def as_block(x):
    """Converts input to layer block"""
    if isinstance(x, str):
        if x in BLOCKS:
            return BLOCKS[x]
        else:
            raise ValueError(
                "Invalid blockname {0}, valid names are: ".format(x)
                + ", ".join(BLOCKS.keys())
            )
    if isinstance(x, layers.Layer) or not callable(x):
        raise TypeError("Layer block should be a function that returns a keras Layer.")
    else:
        return x


def _as_activation(x):
    if x is None:
        return layers.Layer()
    elif isinstance(x, str):
        return layers.Activation(x)
    elif isinstance(x, layers.Layer):
        return x
    else:
        return layers.Layer(x)


def _get_norm_by_name(x):
    if hasattr(layers, x):
        return getattr(layers, x)
    elif "tensorflow-addons" in installed_pkg and hasattr(tfa.layers, x):
        return getattr(tfa.layers, x)
    else:
        raise ValueError(f"Unknown normalization {x}.")


def _as_normalization(x):
    if x is None:
        return layers.Layer()
    elif isinstance(x, str):
        return _get_norm_by_name(x)
    elif isinstance(x, layers.Layer) or callable(x):
        return x
    else:
        return layers.Layer(x)


def single_layer_call(x, layer, activation, normalization, norm_kwargs):
    assert isinstance(norm_kwargs, dict), "norm_kwargs must be a dict. Got {0}".format(
        type(norm_kwargs)
    )
    y = layer(x)

    if activation:
        y = _as_activation(activation)(y)

    if normalization:
        y = _as_normalization(normalization)(**norm_kwargs)(y)

    return y


@register("convolutional", "conv")
def ConvolutionalBlock(
    kernel_size=3,
    activation="relu",
    padding="same",
    strides=1,
    normalization=False,
    norm_kwargs={},
    **kwargs,
):
    """A single 2d convolutional layer.

    Accepts arguments of keras.layers.Conv2D.

    Parameters
    ----------
    kernel_size : int
        Size of the convolution kernel
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    padding : str
        How to pad the input tensor. See keras docs for accepted strings.
    strides : int
        Step length of kernel
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Conv2D arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = layers.Conv2D(
            filters,
            kernel_size=kernel_size,
            padding=padding,
            strides=strides,
            **kwargs_inner,
        )
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


@register("dense")
def DenseBlock(activation="relu", normalization=False, norm_kwargs={}, **kwargs):
    """A single dense layer.

    Accepts arguments of keras.layers.Dense.

    Parameters
    ----------
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Dense arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = layers.Dense(filters, **kwargs_inner)
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


@register("pool", "pooling")
def PoolingBlock(
    pool_size=(2, 2),
    activation=None,
    padding="same",
    strides=2,
    normalization=False,
    norm_kwargs={},
    **kwargs,
):
    """A single max pooling layer.

    Accepts arguments of keras.layers.MaxPool2D.

    Parameters
    ----------
    pool_size : int
        Size of the pooling kernel
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    padding : str
        How to pad the input tensor. See keras docs for accepted strings.
    strides : int
        Step length of kernel
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.MaxPool2D arguments
    """

    def Layer(filters=None, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = layers.MaxPool2D(
            pool_size=pool_size, padding=padding, strides=strides, **kwargs_inner
        )
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


@register("deconvolutional", "deconv")
def DeconvolutionalBlock(
    kernel_size=(2, 2),
    activation=None,
    padding="valid",
    strides=2,
    normalization=False,
    norm_kwargs={},
    **kwargs,
):
    """A single 2d deconvolutional layer.

    Accepts arguments of keras.layers.Conv2DTranspose.

    Parameters
    ----------
    kernel_size : int
        Size of the kernel
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    padding : str
        How to pad the input tensor. See keras docs for accepted strings.
    strides : int
        Step length of kernel
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Conv2DTranspose arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = layers.Conv2DTranspose(
            filters,
            kernel_size=kernel_size,
            padding=padding,
            strides=strides,
            **kwargs_inner,
        )
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


@register("upsample")
def StaticUpsampleBlock(
    size=(2, 2),
    activation=None,
    interpolation="bilinear",
    normalization=False,
    kernel_size=(1, 1),
    strides=1,
    padding="same",
    with_conv=True,
    norm_kwargs={},
    **kwargs,
):
    """A single no-trainable 2d deconvolutional layer.

    Accepts arguments of keras.layers.UpSampling2D.

    Parameters
    ----------
    size : int
        Size of the kernel
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    interpolation
        Interpolation type. Either "bilinear" or "nearest".
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    **kwargs
        Other keras.layers.Conv2DTranspose arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = layers.UpSampling2D(size=size, interpolation=interpolation)

        conv = layers.Conv2D(
            filters,
            kernel_size=kernel_size,
            strides=strides,
            padding=padding,
            **kwargs_inner,
        )

        def call(x):
            y = layer(x)
            if with_conv:
                return single_layer_call(
                    y, conv, activation, normalization, norm_kwargs
                )
            else:
                return layer(x)

        return call

    return Layer


@register("residual")
def ResidualBlock(
    kernel_size=(3, 3),
    activation="relu",
    strides=1,
    normalization="BatchNormalization",
    norm_kwargs={},
    **kwargs,
):
    """A 2d residual layer with two convolutional steps.

    Accepts arguments of keras.layers.Conv2D.

    Parameters
    ----------
    kernel_size : int
        Size of the kernel
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    strides : int
        Step length of kernel
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Conv2D arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        identity = layers.Conv2D(filters, kernel_size=(1, 1))

        conv = layers.Conv2D(
            filters,
            kernel_size=kernel_size,
            strides=strides,
            padding="same",
        )

        conv2 = layers.Conv2D(
            filters, kernel_size=kernel_size, strides=strides, padding="same"
        )

        def call(x):
            y = single_layer_call(x, conv, activation, normalization, norm_kwargs)
            y = single_layer_call(y, conv2, None, normalization, norm_kwargs)
            y = layers.Add()([identity(x), y])
            if activation:
                y = _as_activation(activation)(y)
            return y

        return call

    return Layer


@register("none", "identity", "None")
def Identity(activation=None, normalization=False, norm_kwargs={}, **kwargs):
    """Identity layer that returns the input tensor.

    Can optionally perform instance normalization or some activation function.

    Accepts arguments of keras.layers.Layer.

    Parameters
    ----------

    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Layer arguments
    """

    def Layer(filters, **kwargs_inner):
        layer = layers.Layer(**kwargs_inner)
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


class MultiHeadSelfAttention(layers.Layer):
    """Multi-head self-attention layer.
    Parameters
    ----------
    number_of_heads : int
        Number of attention heads.
    kwargs
        Other arguments for the keras.layers.Layer
    """

    def __init__(self, number_of_heads, use_bias=True, **kwargs):
        super().__init__(**kwargs)
        self.number_of_heads = number_of_heads
        self.use_bias = use_bias

    def build(self, input_shape):
        try:
            filters = input_shape[1][-1]
        except TypeError:
            filters = input_shape[-1]

        if filters % self.number_of_heads != 0:
            raise ValueError(
                f"embedding dimension = {filters} should be divisible by number of heads = {self.number_of_heads}"
            )
        self.filters = filters
        self.projection_dim = filters // self.number_of_heads

        self.query_dense = layers.Dense(filters, use_bias=self.use_bias)
        self.key_dense = layers.Dense(filters, use_bias=self.use_bias)
        self.value_dense = layers.Dense(filters, use_bias=self.use_bias)
        self.combine_dense = layers.Dense(filters, use_bias=self.use_bias)

    def SingleAttention(self, query, key, value, gate=None, **kwargs):
        """
        Single attention layer.
        Parameters
        ----------
        query : tf.Tensor
            Query tensor.
        key : tf.Tensor
            Key tensor.
        value : tf.Tensor
            Value tensor.
        gate : tf.Tensor (optional). If provided, the attention gate is applied.
            Gate tensor.
        """
        score = tf.matmul(query, key, transpose_b=True)
        dim_key = tf.cast(tf.shape(key)[-1], score.dtype)
        scaled_score = score / tf.math.sqrt(dim_key)

        weights = tf.nn.softmax(scaled_score, axis=-1)
        output = tf.matmul(weights, value)

        if gate:
            output = tf.math.multiply(output, gate)

        return output, weights

    def separate_heads(self, x, batch_size):
        """
        Parameters
        ----------
        x : tf.Tensor
            Input tensor.
        batch_size : int
            Batch size.
        projection_dim : int
            Projection dimension.
        """
        x = tf.reshape(x, (batch_size, -1, self.number_of_heads, self.projection_dim))
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def compute_attention(self, x, **kwargs):
        """
        Parameters
        ----------
        x : tf.Tensor
            Input tensor.
        kwargs
            Other arguments to pass to SingleAttention.
        """
        if not isinstance(x, list):
            x = [x]

        x = tf.concat(x, axis=-1)
        batch_size = tf.shape(x)[0]

        query = self.query_dense(x)
        key = self.key_dense(x)
        value = self.value_dense(x)

        query = self.separate_heads(query, batch_size)
        key = self.separate_heads(key, batch_size)
        value = self.separate_heads(value, batch_size)

        return (
            self.SingleAttention(query, key, value, **kwargs),
            batch_size,
        )

    def call(self, x, **kwargs):
        """
        Parameters
        ----------
        x : tuple of tf.Tensors
            Input tensors.
        """
        (attention, _), batch_size = self.compute_attention(x, **kwargs)
        attention = tf.transpose(attention, perm=[0, 2, 1, 3])
        concat_attention = tf.reshape(attention, (batch_size, -1, self.filters))
        output = self.combine_dense(concat_attention)

        return output


class MultiHeadGatedSelfAttention(MultiHeadSelfAttention):
    def build(self, input_shape):
        super().build(input_shape)
        self.gate_dense = layers.Dense(self.filters, activation="sigmoid")

    def compute_gated_attention(self, x, **kwargs):
        """
        Compute attention.
        Parameters
        ----------
        x : tf.Tensor
            Input tensor.
        kwargs
            Other arguments to pass to SingleAttention.
        """
        if not isinstance(x, list):
            x = [x]

        x = tf.concat(x, axis=-1)
        batch_size = tf.shape(x)[0]

        query = self.query_dense(x)
        key = self.key_dense(x)
        value = self.value_dense(x)
        gate = self.gate_dense(x)

        query = self.separate_heads(query, batch_size)
        key = self.separate_heads(key, batch_size)
        value = self.separate_heads(value, batch_size)
        gate = self.separate_heads(gate, batch_size)

        return (
            self.SingleAttention(query, key, value, gate, **kwargs),
            batch_size,
        )


@register("MultiHeadSelfAttention")
def MultiHeadSelfAttentionLayer(
    number_of_heads=12,
    use_bias=True,
    activation=GELU,
    normalization="LayerNormalization",
    norm_kwargs={},
    **kwargs,
):
    """Multi-head self-attention layer.
    Parameters
    ----------
    number_of_heads : int
        Number of attention heads.
    use_bias : bool
        Whether to use bias in the dense layers.
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    kwargs
        Other arguments for the keras.layers.Layer
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = MultiHeadSelfAttention(number_of_heads, use_bias, **kwargs_inner)
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


@register("MultiHeadGatedSelfAttention")
def MultiHeadGatedSelfAttentionLayer(
    number_of_heads=12,
    use_bias=True,
    activation=GELU,
    normalization="LayerNormalization",
    norm_kwargs={},
    **kwargs,
):
    """Multi-head gated self-attention layer.
    Parameters
    ----------
    number_of_heads : int
        Number of attention heads.
    use_bias : bool
        Whether to use bias in the dense layers.
    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    kwargs
        Other arguments for the keras.layers.Layer
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = MultiHeadGatedSelfAttention(number_of_heads, use_bias, **kwargs_inner)
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer


class ClassToken(tf.keras.layers.Layer):
    """ClassToken Layer."""

    def build(self, input_shape):
        cls_init = tf.zeros_initializer()
        self.hidden_size = input_shape[-1]
        self.cls = tf.Variable(
            name="cls",
            initial_value=cls_init(shape=(1, 1, self.hidden_size), dtype="float32"),
            trainable=True,
        )

    def call(self, inputs):
        batch_size = tf.shape(inputs)[0]
        cls_broadcasted = tf.cast(
            tf.broadcast_to(self.cls, [batch_size, 1, self.hidden_size]),
            dtype=inputs.dtype,
        )
        return tf.concat([cls_broadcasted, inputs], 1)


def ClassTokenLayer(activation=None, normalization=None, norm_kwargs={}, **kwargs):
    """ClassToken Layer that append a class token to the input.

    Can optionally perform instance normalization or some activation function.

    Accepts arguments of keras.layers.Layer.

    Parameters
    ----------

    activation : str or activation function or layer
        Activation function of the layer. See keras docs for accepted strings.
    normalization : str or normalization function or layer
        Normalization function of the layer. See keras and tfa docs for accepted strings.
    norm_kwargs : dict
        Arguments for the normalization function.
    **kwargs
        Other keras.layers.Layer arguments
    """

    def Layer(filters, **kwargs_inner):
        kwargs_inner.update(kwargs)
        layer = ClassToken(**kwargs_inner)
        return lambda x: single_layer_call(
            x, layer, activation, normalization, norm_kwargs
        )

    return Layer
