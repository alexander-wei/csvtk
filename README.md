# csvtk

Compressive Spectrogram Visualization Toolkit

Visualize contractive dynamic range compression, noise cleaning, and clipping of mel-reduced spectrograms loaded from .wav files.  Useful for manual qualitative correction of noise and blurring due to mel down-projections.  Default parameters are permissible for sound normalized to -18dB.

Currently performs 80-dimensional mel reduction of entire .wav files inside a user-specified root directory, and accepts only 16kHz .wav files.

    usage: csvtk [-h] [--fps REFRESH] [-u LIMITS_U] [-v LIMITS_V] [-s LIMITS_S] [-t LIMITS_T] [rootdir]

    positional arguments:
      rootdir        Recursively load the sound files inside this directory

    options:
      -h, --help     show this help message and exit
      --fps REFRESH  number of plot refresh cycles per second / GUI responsiveness.  default 12
      -u LIMITS_U    default 0,5
      -v LIMITS_V    default 1,100
      -s LIMITS_S    default -2,0
      -t LIMITS_T    default 0,3

                     u, v, s, t are parameters of the compression and clipping function.
                     Use -u/v/s/t to configure the range of permissible values in the GUI.

                     Example: to limit parameters u and v to the [0,10] range, apply
                        -u 0,10 -v 0,10

                     If X is the log spectrogram of a sound, then we display approximately the following function of X:
                     f(X) = eps + ( |X - 100u| + v ) / v + s, clipped within the interval [0,t]
                     where eps is the silence floor of around log(10^-5).  Anything below eps is muted prior to application of the function f.
                     All values between zero and eps are muted following application of the function f.


#### Example applications

Cleaning of down-projected mel spectrogram
![cleaned_scale](https://user-images.githubusercontent.com/82844428/220813946-4fad30cf-f8eb-4d36-8329-7453e28ccb25.jpg)

Dynamic range compression of down-projected mel spectrogram
![compressed_scale](https://user-images.githubusercontent.com/82844428/220813954-f53b3d72-6fee-474b-a21d-a90dd67c4782.jpg)
