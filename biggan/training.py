import tensorflow as tf

from typing import Callable, List, Tuple

from typeguard import typechecked

from .config import training as config


@typechecked
def discriminator_hinge_loss(
    *,
    logits_real: tf.Tensor,
    logits_fake: tf.Tensor,
    global_batch_size: int,
) -> tf.Tensor:
    """
    Computes the "hinge" discriminator loss given two
    discriminator outputs, `logits_real` and `logits_fake`.

    Cf. Miyato, https://arxiv.org/pdf/1802.05957.pdf,
    equation 16.
    """
    L_D = tf.reduce_sum(tf.nn.relu(1.0 - logits_real)) \
        + tf.reduce_sum(tf.nn.relu(1.0 + logits_fake))
    return L_D * (1.0 / global_batch_size)


@typechecked
def generator_hinge_loss(
    *,
    logits_fake: tf.Tensor,
    global_batch_size: int,
) -> tf.Tensor:
    """
    Computes the "hinge" generator loss given one
    discriminator output, `logits_fake`.

    Cf. Miyato, https://arxiv.org/pdf/1802.05957.pdf,
    equation 17.
    """
    L_G = -tf.reduce_sum(logits_fake)
    return L_G * (1.0 / global_batch_size)


@typechecked
def full_hinge_loss(
    *,
    logits_real: tf.Tensor,
    logits_fake: tf.Tensor,
    global_batch_size: int,
) -> Tuple[tf.Tensor, tf.Tensor]:
    """
    Represents the "hinge" GAN objective given
    discriminator outputs `logits_real` and `logits_fake`.

    Cf. https://arxiv.org/pdf/1802.05957.pdf,
    equations 16 and 17.

    Returns the generator loss and the discriminator loss,
    in that order.
    """
    return (
        generator_hinge_loss(
            logits_fake=logits_fake,
            global_batch_size=global_batch_size,
        ),
        discriminator_hinge_loss(
            logits_real=logits_real,
            logits_fake=logits_fake,
            global_batch_size=global_batch_size),
    )


@typechecked
def imperative_minimize(
    *,
    optimizer: tf.keras.optimizers.Optimizer,
    loss_fn: Callable,
    var_list: List[tf.Variable],
) -> tf.Tensor:
    """
    Like Optimizer.minimize, except it returns the loss value,
    not an Op, so it needs to be invoked imperatively, i.e.,
    in eager mode, or in a @tf.function.
    """
    with tf.GradientTape() as tape:
        loss = loss_fn()
    grad = tape.gradient(loss, var_list)
    optimizer.apply_gradients(zip(grad, var_list))
    return loss


@typechecked
def declarative_minimize(
    *,
    optimizer: tf.keras.optimizers.Optimizer,
    loss: tf.Tensor,
    var_list: List[tf.Variable],
) -> tf.Operation:
    """
    Graph-mode minimization without gradient tape
    or eager function tracing, similar to TF-1.X.
    """
    return optimizer.apply_gradients(
        zip(optimizer.get_gradients(loss, var_list), var_list)
    )


def train_model(
    *,
    model: tf.keras.Model,
    data: tf.data.Dataset,
    model_dir: str,
    num_steps: int = config.defaults.num_steps,
    log_every: int = config.defaults.log_every,
    initial_step: int = 0,
):
    """
    Train the built model on a dataset.
    """
    # Create the saving and logging callbacks.
    callbacks = model.create_callbacks(model_dir)

    # Set the global batch size for distributed training.
    model.global_batch_size = data.element_spec[0].shape[0]

    # Fit the model to the data, calling the callbacks every `log_every` steps.
    model.fit(
        data,
        callbacks=callbacks,
        epochs=num_steps//log_every,
        steps_per_epoch=log_every,
        initial_epoch=(initial_step or 0) // log_every,
    )
    # Return the trained model.
    return model
