import argparse
import os

import tensorflow as tf

from deepfake_ai import build_training_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the deepfake detector model")
    parser.add_argument("--data-dir", required=True, help="Directory with authentic/ and deepfake/ subfolders")
    parser.add_argument("--output", default=os.path.join("models", "deepfake_detector.keras"), help="Path to save the trained model")
    parser.add_argument(
        "--checkpoint-dir",
        default=os.path.join("models", "checkpoints"),
        help="Directory to save a model checkpoint after every epoch",
    )
    parser.add_argument("--image-size", type=int, default=224, help="Square image size used for training")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--validation-split", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image_size = (args.image_size, args.image_size)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        args.data_dir,
        labels="inferred",
        label_mode="binary",
        validation_split=args.validation_split,
        subset="training",
        seed=42,
        image_size=image_size,
        batch_size=args.batch_size,
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        args.data_dir,
        labels="inferred",
        label_mode="binary",
        validation_split=args.validation_split,
        subset="validation",
        seed=42,
        image_size=image_size,
        batch_size=args.batch_size,
    )

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(512).prefetch(buffer_size=autotune)
    val_ds = val_ds.cache().prefetch(buffer_size=autotune)

    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.05),
        tf.keras.layers.RandomContrast(0.1),
    ])

    inputs = tf.keras.Input(shape=(args.image_size, args.image_size, 3))
    x = augmentation(inputs)
    x = build_training_model((args.image_size, args.image_size, 3))(x)
    model = tf.keras.Model(inputs=inputs, outputs=x, name="deepfake_detector_training_wrapper")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    epoch_checkpoint_path = os.path.join(
        args.checkpoint_dir,
        "deepfake_detector_epoch_{epoch:03d}_val_auc_{val_auc:.4f}.keras",
    )
    training_log_path = os.path.join(args.checkpoint_dir, "training_log.csv")
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", patience=4, mode="max", restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(args.output, monitor="val_auc", mode="max", save_best_only=True),
        tf.keras.callbacks.ModelCheckpoint(epoch_checkpoint_path, save_best_only=False),
        tf.keras.callbacks.CSVLogger(training_log_path, append=True),
    ]

    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)
    print(f"Saved best trained model to {args.output}")
    print(f"Saved per-epoch checkpoints to {args.checkpoint_dir}")


if __name__ == "__main__":
    main()
