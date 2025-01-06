Speaker Recognition
Author: Fadi Badine
Date created: 14/06/2020
Last modified: 03/07/2020

 View in Colab • GitHub source

Description: Classify speakers using Fast Fourier Transform (FFT) and a 1D Convnet.

Introduction
This example demonstrates how to create a model to classify speakers from the frequency domain representation of speech recordings, obtained via Fast Fourier Transform (FFT).

It shows the following:

How to use tf.data to load, preprocess and feed audio streams into a model
How to create a 1D convolutional network with residual connections for audio classification.
Our process:

We prepare a dataset of speech samples from different speakers, with the speaker as label.
We add background noise to these samples to augment our data.
We take the FFT of these samples.
We train a 1D convnet to predict the correct speaker given a noisy FFT speech sample.
Note:

This example should be run with TensorFlow 2.3 or higher, or tf-nightly.
The noise samples in the dataset need to be resampled to a sampling rate of 16000 Hz before using the code in this example. In order to do this, you will need to have installed ffmpg.
Setup
import os
import shutil
import numpy as np

import tensorflow as tf
from tensorflow import keras

from pathlib import Path
from IPython.display import display, Audio

# Get the data from https://www.kaggle.com/kongaevans/speaker-recognition-dataset/download
# and save it to the 'Downloads' folder in your HOME directory
DATASET_ROOT = os.path.join(os.path.expanduser("~"), "Downloads/16000_pcm_speeches")

# The folders in which we will put the audio samples and the noise samples
AUDIO_SUBFOLDER = "audio"
NOISE_SUBFOLDER = "noise"

DATASET_AUDIO_PATH = os.path.join(DATASET_ROOT, AUDIO_SUBFOLDER)
DATASET_NOISE_PATH = os.path.join(DATASET_ROOT, NOISE_SUBFOLDER)

# Percentage of samples to use for validation
VALID_SPLIT = 0.1

# Seed to use when shuffling the dataset and the noise
SHUFFLE_SEED = 43

# The sampling rate to use.
# This is the one used in all the audio samples.
# We will resample all the noise to this sampling rate.
# This will also be the output size of the audio wave samples
# (since all samples are of 1 second long)
SAMPLING_RATE = 16000

# The factor to multiply the noise with according to:
#   noisy_sample = sample + noise * prop * scale
#      where prop = sample_amplitude / noise_amplitude
SCALE = 0.5

BATCH_SIZE = 128
EPOCHS = 100
Data preparation
The dataset is composed of 7 folders, divided into 2 groups:

Speech samples, with 5 folders for 5 different speakers. Each folder contains 1500 audio files, each 1 second long and sampled at 16000 Hz.
Background noise samples, with 2 folders and a total of 6 files. These files are longer than 1 second (and originally not sampled at 16000 Hz, but we will resample them to 16000 Hz). We will use those 6 files to create 354 1-second-long noise samples to be used for training.
Let's sort these 2 categories into 2 folders:

An audio folder which will contain all the per-speaker speech sample folders
A noise folder which will contain all the noise samples
Before sorting the audio and noise categories into 2 folders,

main_directory/
...speaker_a/
...speaker_b/
...speaker_c/
...speaker_d/
...speaker_e/
...other/
..._background_noise_/
After sorting, we end up with the following structure:

main_directory/
...audio/
......speaker_a/
......speaker_b/
......speaker_c/
......speaker_d/
......speaker_e/
...noise/
......other/
......_background_noise_/
# If folder `audio`, does not exist, create it, otherwise do nothing
if os.path.exists(DATASET_AUDIO_PATH) is False:
    os.makedirs(DATASET_AUDIO_PATH)

# If folder `noise`, does not exist, create it, otherwise do nothing
if os.path.exists(DATASET_NOISE_PATH) is False:
    os.makedirs(DATASET_NOISE_PATH)

for folder in os.listdir(DATASET_ROOT):
    if os.path.isdir(os.path.join(DATASET_ROOT, folder)):
        if folder in [AUDIO_SUBFOLDER, NOISE_SUBFOLDER]:
            # If folder is `audio` or `noise`, do nothing
            continue
        elif folder in ["other", "_background_noise_"]:
            # If folder is one of the folders that contains noise samples,
            # move it to the `noise` folder
            shutil.move(
                os.path.join(DATASET_ROOT, folder),
                os.path.join(DATASET_NOISE_PATH, folder),
            )
        else:
            # Otherwise, it should be a speaker folder, then move it to
            # `audio` folder
            shutil.move(
                os.path.join(DATASET_ROOT, folder),
                os.path.join(DATASET_AUDIO_PATH, folder),
            )
Noise preparation
In this section:

We load all noise samples (which should have been resampled to 16000)
We split those noise samples to chunks of 16000 samples which correspond to 1 second duration each
# Get the list of all noise files
noise_paths = []
for subdir in os.listdir(DATASET_NOISE_PATH):
    subdir_path = Path(DATASET_NOISE_PATH) / subdir
    if os.path.isdir(subdir_path):
        noise_paths += [
            os.path.join(subdir_path, filepath)
            for filepath in os.listdir(subdir_path)
            if filepath.endswith(".wav")
        ]

print(
    "Found {} files belonging to {} directories".format(
        len(noise_paths), len(os.listdir(DATASET_NOISE_PATH))
    )
)
Found 6 files belonging to 2 directories
Resample all noise samples to 16000 Hz

command = (
    "for dir in `ls -1 " + DATASET_NOISE_PATH + "`; do "
    "for file in `ls -1 " + DATASET_NOISE_PATH + "/$dir/*.wav`; do "
    "sample_rate=`ffprobe -hide_banner -loglevel panic -show_streams "
    "$file | grep sample_rate | cut -f2 -d=`; "
    "if [ $sample_rate -ne 16000 ]; then "
    "ffmpeg -hide_banner -loglevel panic -y "
    "-i $file -ar 16000 temp.wav; "
    "mv temp.wav $file; "
    "fi; done; done"
)

os.system(command)

# Split noise into chunks of 16000 each
def load_noise_sample(path):
    sample, sampling_rate = tf.audio.decode_wav(
        tf.io.read_file(path), desired_channels=1
    )
    if sampling_rate == SAMPLING_RATE:
        # Number of slices of 16000 each that can be generated from the noise sample
        slices = int(sample.shape[0] / SAMPLING_RATE)
        sample = tf.split(sample[: slices * SAMPLING_RATE], slices)
        return sample
    else:
        print("Sampling rate for {} is incorrect. Ignoring it".format(path))
        return None


noises = []
for path in noise_paths:
    sample = load_noise_sample(path)
    if sample:
        noises.extend(sample)
noises = tf.stack(noises)

print(
    "{} noise files were split into {} noise samples where each is {} sec. long".format(
        len(noise_paths), noises.shape[0], noises.shape[1] // SAMPLING_RATE
    )
)
6 noise files were split into 354 noise samples where each is 1 sec. long
Dataset generation
def paths_and_labels_to_dataset(audio_paths, labels):
    """Constructs a dataset of audios and labels."""
    path_ds = tf.data.Dataset.from_tensor_slices(audio_paths)
    audio_ds = path_ds.map(lambda x: path_to_audio(x))
    label_ds = tf.data.Dataset.from_tensor_slices(labels)
    return tf.data.Dataset.zip((audio_ds, label_ds))


def path_to_audio(path):
    """Reads and decodes an audio file."""
    audio = tf.io.read_file(path)
    audio, _ = tf.audio.decode_wav(audio, 1, SAMPLING_RATE)
    return audio


def add_noise(audio, noises=None, scale=0.5):
    if noises is not None:
        # Create a random tensor of the same size as audio ranging from
        # 0 to the number of noise stream samples that we have.
        tf_rnd = tf.random.uniform(
            (tf.shape(audio)[0],), 0, noises.shape[0], dtype=tf.int32
        )
        noise = tf.gather(noises, tf_rnd, axis=0)

        # Get the amplitude proportion between the audio and the noise
        prop = tf.math.reduce_max(audio, axis=1) / tf.math.reduce_max(noise, axis=1)
        prop = tf.repeat(tf.expand_dims(prop, axis=1), tf.shape(audio)[1], axis=1)

        # Adding the rescaled noise to audio
        audio = audio + noise * prop * scale

    return audio


def audio_to_fft(audio):
    # Since tf.signal.fft applies FFT on the innermost dimension,
    # we need to squeeze the dimensions and then expand them again
    # after FFT
    audio = tf.squeeze(audio, axis=-1)
    fft = tf.signal.fft(
        tf.cast(tf.complex(real=audio, imag=tf.zeros_like(audio)), tf.complex64)
    )
    fft = tf.expand_dims(fft, axis=-1)

    # Return the absolute value of the first half of the FFT
    # which represents the positive frequencies
    return tf.math.abs(fft[:, : (audio.shape[1] // 2), :])


# Get the list of audio file paths along with their corresponding labels

class_names = os.listdir(DATASET_AUDIO_PATH)
print("Our class names: {}".format(class_names,))

audio_paths = []
labels = []
for label, name in enumerate(class_names):
    print("Processing speaker {}".format(name,))
    dir_path = Path(DATASET_AUDIO_PATH) / name
    speaker_sample_paths = [
        os.path.join(dir_path, filepath)
        for filepath in os.listdir(dir_path)
        if filepath.endswith(".wav")
    ]
    audio_paths += speaker_sample_paths
    labels += [label] * len(speaker_sample_paths)

print(
    "Found {} files belonging to {} classes.".format(len(audio_paths), len(class_names))
)

# Shuffle
rng = np.random.RandomState(SHUFFLE_SEED)
rng.shuffle(audio_paths)
rng = np.random.RandomState(SHUFFLE_SEED)
rng.shuffle(labels)

# Split into training and validation
num_val_samples = int(VALID_SPLIT * len(audio_paths))
print("Using {} files for training.".format(len(audio_paths) - num_val_samples))
train_audio_paths = audio_paths[:-num_val_samples]
train_labels = labels[:-num_val_samples]

print("Using {} files for validation.".format(num_val_samples))
valid_audio_paths = audio_paths[-num_val_samples:]
valid_labels = labels[-num_val_samples:]

# Create 2 datasets, one for training and the other for validation
train_ds = paths_and_labels_to_dataset(train_audio_paths, train_labels)
train_ds = train_ds.shuffle(buffer_size=BATCH_SIZE * 8, seed=SHUFFLE_SEED).batch(
    BATCH_SIZE
)

valid_ds = paths_and_labels_to_dataset(valid_audio_paths, valid_labels)
valid_ds = valid_ds.shuffle(buffer_size=32 * 8, seed=SHUFFLE_SEED).batch(32)


# Add noise to the training set
train_ds = train_ds.map(
    lambda x, y: (add_noise(x, noises, scale=SCALE), y),
    num_parallel_calls=tf.data.AUTOTUNE,
)

# Transform audio wave to the frequency domain using `audio_to_fft`
train_ds = train_ds.map(
    lambda x, y: (audio_to_fft(x), y), num_parallel_calls=tf.data.AUTOTUNE
)
train_ds = train_ds.prefetch(tf.data.AUTOTUNE)

valid_ds = valid_ds.map(
    lambda x, y: (audio_to_fft(x), y), num_parallel_calls=tf.data.AUTOTUNE
)
valid_ds = valid_ds.prefetch(tf.data.AUTOTUNE)
Our class names: ['Julia_Gillard', 'Jens_Stoltenberg', 'Nelson_Mandela', 'Magaret_Tarcher', 'Benjamin_Netanyau']
Processing speaker Julia_Gillard
Processing speaker Jens_Stoltenberg
Processing speaker Nelson_Mandela
Processing speaker Magaret_Tarcher
Processing speaker Benjamin_Netanyau
Found 7501 files belonging to 5 classes.
Using 6751 files for training.
Using 750 files for validation.
Model Definition
def residual_block(x, filters, conv_num=3, activation="relu"):
    # Shortcut
    s = keras.layers.Conv1D(filters, 1, padding="same")(x)
    for i in range(conv_num - 1):
        x = keras.layers.Conv1D(filters, 3, padding="same")(x)
        x = keras.layers.Activation(activation)(x)
    x = keras.layers.Conv1D(filters, 3, padding="same")(x)
    x = keras.layers.Add()([x, s])
    x = keras.layers.Activation(activation)(x)
    return keras.layers.MaxPool1D(pool_size=2, strides=2)(x)


def build_model(input_shape, num_classes):
    inputs = keras.layers.Input(shape=input_shape, name="input")

    x = residual_block(inputs, 16, 2)
    x = residual_block(x, 32, 2)
    x = residual_block(x, 64, 3)
    x = residual_block(x, 128, 3)
    x = residual_block(x, 128, 3)

    x = keras.layers.AveragePooling1D(pool_size=3, strides=3)(x)
    x = keras.layers.Flatten()(x)
    x = keras.layers.Dense(256, activation="relu")(x)
    x = keras.layers.Dense(128, activation="relu")(x)

    outputs = keras.layers.Dense(num_classes, activation="softmax", name="output")(x)

    return keras.models.Model(inputs=inputs, outputs=outputs)


model = build_model((SAMPLING_RATE // 2, 1), len(class_names))

model.summary()

# Compile the model using Adam's default learning rate
model.compile(
    optimizer="Adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"]
)

# Add callbacks:
# 'EarlyStopping' to stop training when the model is not enhancing anymore
# 'ModelCheckPoint' to always keep the model that has the best val_accuracy
model_save_filename = "model.h5"

earlystopping_cb = keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True)
mdlcheckpoint_cb = keras.callbacks.ModelCheckpoint(
    model_save_filename, monitor="val_accuracy", save_best_only=True
)
Model: "model"
__________________________________________________________________________________________________
Layer (type)                    Output Shape         Param #     Connected to
==================================================================================================
input (InputLayer)              [(None, 8000, 1)]    0
__________________________________________________________________________________________________
conv1d_1 (Conv1D)               (None, 8000, 16)     64          input[0][0]
__________________________________________________________________________________________________
activation (Activation)         (None, 8000, 16)     0           conv1d_1[0][0]
__________________________________________________________________________________________________
conv1d_2 (Conv1D)               (None, 8000, 16)     784         activation[0][0]
__________________________________________________________________________________________________
conv1d (Conv1D)                 (None, 8000, 16)     32          input[0][0]
__________________________________________________________________________________________________
add (Add)                       (None, 8000, 16)     0           conv1d_2[0][0]
                                                                 conv1d[0][0]
__________________________________________________________________________________________________
activation_1 (Activation)       (None, 8000, 16)     0           add[0][0]
__________________________________________________________________________________________________
max_pooling1d (MaxPooling1D)    (None, 4000, 16)     0           activation_1[0][0]
__________________________________________________________________________________________________
conv1d_4 (Conv1D)               (None, 4000, 32)     1568        max_pooling1d[0][0]
__________________________________________________________________________________________________
activation_2 (Activation)       (None, 4000, 32)     0           conv1d_4[0][0]
__________________________________________________________________________________________________
conv1d_5 (Conv1D)               (None, 4000, 32)     3104        activation_2[0][0]
__________________________________________________________________________________________________
conv1d_3 (Conv1D)               (None, 4000, 32)     544         max_pooling1d[0][0]
__________________________________________________________________________________________________
add_1 (Add)                     (None, 4000, 32)     0           conv1d_5[0][0]
                                                                 conv1d_3[0][0]
__________________________________________________________________________________________________
activation_3 (Activation)       (None, 4000, 32)     0           add_1[0][0]
__________________________________________________________________________________________________
max_pooling1d_1 (MaxPooling1D)  (None, 2000, 32)     0           activation_3[0][0]
__________________________________________________________________________________________________
conv1d_7 (Conv1D)               (None, 2000, 64)     6208        max_pooling1d_1[0][0]
__________________________________________________________________________________________________
activation_4 (Activation)       (None, 2000, 64)     0           conv1d_7[0][0]
__________________________________________________________________________________________________
conv1d_8 (Conv1D)               (None, 2000, 64)     12352       activation_4[0][0]
__________________________________________________________________________________________________
activation_5 (Activation)       (None, 2000, 64)     0           conv1d_8[0][0]
__________________________________________________________________________________________________
conv1d_9 (Conv1D)               (None, 2000, 64)     12352       activation_5[0][0]
__________________________________________________________________________________________________
conv1d_6 (Conv1D)               (None, 2000, 64)     2112        max_pooling1d_1[0][0]
__________________________________________________________________________________________________
add_2 (Add)                     (None, 2000, 64)     0           conv1d_9[0][0]
                                                                 conv1d_6[0][0]
__________________________________________________________________________________________________
activation_6 (Activation)       (None, 2000, 64)     0           add_2[0][0]
__________________________________________________________________________________________________
max_pooling1d_2 (MaxPooling1D)  (None, 1000, 64)     0           activation_6[0][0]
__________________________________________________________________________________________________
conv1d_11 (Conv1D)              (None, 1000, 128)    24704       max_pooling1d_2[0][0]
__________________________________________________________________________________________________
activation_7 (Activation)       (None, 1000, 128)    0           conv1d_11[0][0]
__________________________________________________________________________________________________
conv1d_12 (Conv1D)              (None, 1000, 128)    49280       activation_7[0][0]
__________________________________________________________________________________________________
activation_8 (Activation)       (None, 1000, 128)    0           conv1d_12[0][0]
__________________________________________________________________________________________________
conv1d_13 (Conv1D)              (None, 1000, 128)    49280       activation_8[0][0]
__________________________________________________________________________________________________
conv1d_10 (Conv1D)              (None, 1000, 128)    8320        max_pooling1d_2[0][0]
__________________________________________________________________________________________________
add_3 (Add)                     (None, 1000, 128)    0           conv1d_13[0][0]
                                                                 conv1d_10[0][0]
__________________________________________________________________________________________________
activation_9 (Activation)       (None, 1000, 128)    0           add_3[0][0]
__________________________________________________________________________________________________
max_pooling1d_3 (MaxPooling1D)  (None, 500, 128)     0           activation_9[0][0]
__________________________________________________________________________________________________
conv1d_15 (Conv1D)              (None, 500, 128)     49280       max_pooling1d_3[0][0]
__________________________________________________________________________________________________
activation_10 (Activation)      (None, 500, 128)     0           conv1d_15[0][0]
__________________________________________________________________________________________________
conv1d_16 (Conv1D)              (None, 500, 128)     49280       activation_10[0][0]
__________________________________________________________________________________________________
activation_11 (Activation)      (None, 500, 128)     0           conv1d_16[0][0]
__________________________________________________________________________________________________
conv1d_17 (Conv1D)              (None, 500, 128)     49280       activation_11[0][0]
__________________________________________________________________________________________________
conv1d_14 (Conv1D)              (None, 500, 128)     16512       max_pooling1d_3[0][0]
__________________________________________________________________________________________________
add_4 (Add)                     (None, 500, 128)     0           conv1d_17[0][0]
                                                                 conv1d_14[0][0]
__________________________________________________________________________________________________
activation_12 (Activation)      (None, 500, 128)     0           add_4[0][0]
__________________________________________________________________________________________________
max_pooling1d_4 (MaxPooling1D)  (None, 250, 128)     0           activation_12[0][0]
__________________________________________________________________________________________________
average_pooling1d (AveragePooli (None, 83, 128)      0           max_pooling1d_4[0][0]
__________________________________________________________________________________________________
flatten (Flatten)               (None, 10624)        0           average_pooling1d[0][0]
__________________________________________________________________________________________________
dense (Dense)                   (None, 256)          2720000     flatten[0][0]
__________________________________________________________________________________________________
dense_1 (Dense)                 (None, 128)          32896       dense[0][0]
__________________________________________________________________________________________________
output (Dense)                  (None, 5)            645         dense_1[0][0]
==================================================================================================
Total params: 3,088,597
Trainable params: 3,088,597
Non-trainable params: 0
__________________________________________________________________________________________________
Training
history = model.fit(
    train_ds,
    epochs=EPOCHS,
    validation_data=valid_ds,
    callbacks=[earlystopping_cb, mdlcheckpoint_cb],
)
Epoch 1/100
53/53 [==============================] - 62s 1s/step - loss: 1.0107 - accuracy: 0.6929 - val_loss: 0.3367 - val_accuracy: 0.8640
Epoch 2/100
53/53 [==============================] - 61s 1s/step - loss: 0.2863 - accuracy: 0.8926 - val_loss: 0.2814 - val_accuracy: 0.8813
Epoch 3/100
53/53 [==============================] - 61s 1s/step - loss: 0.2293 - accuracy: 0.9104 - val_loss: 0.2054 - val_accuracy: 0.9160
Epoch 4/100
53/53 [==============================] - 63s 1s/step - loss: 0.1750 - accuracy: 0.9320 - val_loss: 0.1668 - val_accuracy: 0.9320
Epoch 5/100
53/53 [==============================] - 61s 1s/step - loss: 0.2044 - accuracy: 0.9206 - val_loss: 0.1658 - val_accuracy: 0.9347
Epoch 6/100
53/53 [==============================] - 61s 1s/step - loss: 0.1407 - accuracy: 0.9415 - val_loss: 0.0888 - val_accuracy: 0.9720
Epoch 7/100
53/53 [==============================] - 61s 1s/step - loss: 0.1047 - accuracy: 0.9600 - val_loss: 0.1113 - val_accuracy: 0.9587
Epoch 8/100
53/53 [==============================] - 60s 1s/step - loss: 0.1077 - accuracy: 0.9573 - val_loss: 0.0819 - val_accuracy: 0.9693
Epoch 9/100
53/53 [==============================] - 61s 1s/step - loss: 0.0998 - accuracy: 0.9640 - val_loss: 0.1586 - val_accuracy: 0.9427
Epoch 10/100
53/53 [==============================] - 63s 1s/step - loss: 0.1004 - accuracy: 0.9621 - val_loss: 0.1504 - val_accuracy: 0.9333
Epoch 11/100
53/53 [==============================] - 60s 1s/step - loss: 0.0902 - accuracy: 0.9695 - val_loss: 0.1016 - val_accuracy: 0.9600
Epoch 12/100
53/53 [==============================] - 61s 1s/step - loss: 0.0773 - accuracy: 0.9714 - val_loss: 0.0647 - val_accuracy: 0.9800
Epoch 13/100
53/53 [==============================] - 63s 1s/step - loss: 0.0797 - accuracy: 0.9699 - val_loss: 0.0485 - val_accuracy: 0.9853
Epoch 14/100
53/53 [==============================] - 61s 1s/step - loss: 0.0750 - accuracy: 0.9727 - val_loss: 0.0601 - val_accuracy: 0.9787
Epoch 15/100
53/53 [==============================] - 62s 1s/step - loss: 0.0629 - accuracy: 0.9766 - val_loss: 0.0476 - val_accuracy: 0.9787
Epoch 16/100
53/53 [==============================] - 63s 1s/step - loss: 0.0564 - accuracy: 0.9793 - val_loss: 0.0565 - val_accuracy: 0.9813
Epoch 17/100
53/53 [==============================] - 61s 1s/step - loss: 0.0545 - accuracy: 0.9809 - val_loss: 0.0325 - val_accuracy: 0.9893
Epoch 18/100
53/53 [==============================] - 61s 1s/step - loss: 0.0415 - accuracy: 0.9859 - val_loss: 0.0776 - val_accuracy: 0.9693
Epoch 19/100
53/53 [==============================] - 61s 1s/step - loss: 0.0537 - accuracy: 0.9810 - val_loss: 0.0647 - val_accuracy: 0.9853
Epoch 20/100
53/53 [==============================] - 62s 1s/step - loss: 0.0556 - accuracy: 0.9802 - val_loss: 0.0500 - val_accuracy: 0.9880
Epoch 21/100
53/53 [==============================] - 63s 1s/step - loss: 0.0486 - accuracy: 0.9828 - val_loss: 0.0470 - val_accuracy: 0.9827
Epoch 22/100
53/53 [==============================] - 61s 1s/step - loss: 0.0479 - accuracy: 0.9825 - val_loss: 0.0918 - val_accuracy: 0.9693
Epoch 23/100
53/53 [==============================] - 61s 1s/step - loss: 0.0446 - accuracy: 0.9834 - val_loss: 0.0429 - val_accuracy: 0.9867
Epoch 24/100
53/53 [==============================] - 61s 1s/step - loss: 0.0309 - accuracy: 0.9889 - val_loss: 0.0473 - val_accuracy: 0.9867
Epoch 25/100
53/53 [==============================] - 63s 1s/step - loss: 0.0341 - accuracy: 0.9895 - val_loss: 0.0244 - val_accuracy: 0.9907
Epoch 26/100
53/53 [==============================] - 60s 1s/step - loss: 0.0357 - accuracy: 0.9874 - val_loss: 0.0289 - val_accuracy: 0.9893
Epoch 27/100
53/53 [==============================] - 61s 1s/step - loss: 0.0331 - accuracy: 0.9893 - val_loss: 0.0246 - val_accuracy: 0.9920
Epoch 28/100
53/53 [==============================] - 61s 1s/step - loss: 0.0339 - accuracy: 0.9879 - val_loss: 0.0646 - val_accuracy: 0.9787
Epoch 29/100
53/53 [==============================] - 61s 1s/step - loss: 0.0250 - accuracy: 0.9910 - val_loss: 0.0146 - val_accuracy: 0.9947
Epoch 30/100
53/53 [==============================] - 63s 1s/step - loss: 0.0343 - accuracy: 0.9883 - val_loss: 0.0318 - val_accuracy: 0.9893
Epoch 31/100
53/53 [==============================] - 61s 1s/step - loss: 0.0312 - accuracy: 0.9893 - val_loss: 0.0270 - val_accuracy: 0.9880
Epoch 32/100
53/53 [==============================] - 61s 1s/step - loss: 0.0201 - accuracy: 0.9917 - val_loss: 0.0264 - val_accuracy: 0.9893
Epoch 33/100
53/53 [==============================] - 61s 1s/step - loss: 0.0371 - accuracy: 0.9876 - val_loss: 0.0722 - val_accuracy: 0.9773
Epoch 34/100
53/53 [==============================] - 61s 1s/step - loss: 0.0533 - accuracy: 0.9828 - val_loss: 0.0161 - val_accuracy: 0.9947
Epoch 35/100
53/53 [==============================] - 61s 1s/step - loss: 0.0258 - accuracy: 0.9911 - val_loss: 0.0277 - val_accuracy: 0.9867
Epoch 36/100
53/53 [==============================] - 60s 1s/step - loss: 0.0261 - accuracy: 0.9901 - val_loss: 0.0542 - val_accuracy: 0.9787
Epoch 37/100
53/53 [==============================] - 60s 1s/step - loss: 0.0368 - accuracy: 0.9877 - val_loss: 0.0699 - val_accuracy: 0.9813
Epoch 38/100
53/53 [==============================] - 63s 1s/step - loss: 0.0251 - accuracy: 0.9890 - val_loss: 0.0206 - val_accuracy: 0.9907
Epoch 39/100
53/53 [==============================] - 62s 1s/step - loss: 0.0220 - accuracy: 0.9913 - val_loss: 0.0211 - val_accuracy: 0.9947
Evaluation
print(model.evaluate(valid_ds))
24/24 [==============================] - 6s 244ms/step - loss: 0.0146 - accuracy: 0.9947
[0.014629718847572803, 0.9946666955947876]
We get ~ 98% validation accuracy.

Demonstration
Let's take some samples and:

Predict the speaker
Compare the prediction with the real speaker
Listen to the audio to see that despite the samples being noisy, the model is still pretty accurate
SAMPLES_TO_DISPLAY = 10

test_ds = paths_and_labels_to_dataset(valid_audio_paths, valid_labels)
test_ds = test_ds.shuffle(buffer_size=BATCH_SIZE * 8, seed=SHUFFLE_SEED).batch(
    BATCH_SIZE
)

test_ds = test_ds.map(lambda x, y: (add_noise(x, noises, scale=SCALE), y))

for audios, labels in test_ds.take(1):
    # Get the signal FFT
    ffts = audio_to_fft(audios)
    # Predict
    y_pred = model.predict(ffts)
    # Take random samples
    rnd = np.random.randint(0, BATCH_SIZE, SAMPLES_TO_DISPLAY)
    audios = audios.numpy()[rnd, :, :]
    labels = labels.numpy()[rnd]
    y_pred = np.argmax(y_pred, axis=-1)[rnd]

    for index in range(SAMPLES_TO_DISPLAY):
        # For every sample, print the true and predicted label
        # as well as run the voice with the noise
        print(
            "Speaker: {} - Predicted: {}".format(
                class_names[labels[index]],
                class_names[y_pred[index]],
            )
        )
        display(Audio(audios[index, :, :].squeeze(), rate=SAMPLING_RATE))