#!/usr/bin/env python
"""Feature extraction routines."""

import numpy as np
import scipy.signal

import librosa.core
import librosa.util


def centroid(y=None, sr=22050, S=None, n_fft=512, hop_length=256):
    '''Compute spectral centroid

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    - sr : int > 0
    audio sampling rate of ``S``

    :returns:
    - cent : np.ndarray
    centroid frequencies
    '''
    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    n_fft = 2 * (S.shape[0] - 1)

    # Get bin center frequencies
    freq = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    S_norm = librosa.util.normalize(S, norm=1, axis=0)
    # Calculate centroid: weighted mean of frequencies in signal
    cent = np.dot(freq, S_norm)/np.sum(S, axis=0)

    return cent

def bandwidth(y=None, sr=22050, S=None, n_fft=512, hop_length=256, centroid=None):
    '''Compute spectral bandwidth

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    - sr : int > 0
    audio sampling rate of ``S``

    - centroid : np.ndarray or None
    centroid frequencies

    :returns:
    - band : np.ndarray
    bandwidth frequencies
    '''
    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    n_fft = 2 * (S.shape[0] - 1)

    # Get bin center frequencies
    freq = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    S_norm = librosa.util.normalize(S, norm=1, axis=0)

    band = np.sum(np.multiply(S_norm, np.absolute(np.reshape(freq, (S.shape[0], 1))-centroid)), axis=0)/S.shape[0]

    return band

def rolloff(y=None, sr=22050, S=None, n_fft=512, hop_length=256, roll_percent=0.85):
    '''Compute rolloff frequency

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    - sr : int > 0
    audio sampling rate of ``S``

    - roll_percent : 0 < float < 1

    :returns:
    - roll : np.ndarray
    rolloff frequencies
    '''
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    n_fft = 2 * (S.shape[0] - 1)

    # Get bin center frequencies
    freq = librosa.fft_frequencies(sr=fs, n_fft=n_fft)
    S_norm = librosa.util.normalize(S, norm=1, axis=0)

    total_energy = np.cumsum(S_norm, axis=0)
    threshold = 0.85*total_energy[-1, :]

    ind = np.where(total_energy < np.reshape(threshold, (1, S_norm.shape[1])), np.nan, 1)

    # Remove frequencies under the threshold
    freq = ind*np.reshape(freq, (S_norm.shape[0], 1))

    # Lowest remaining frequency is the rolloff frequency
    roll = np.nanmin(freq, axis=0)

    return roll


def flux(y=None, S=None, n_fft=512, hop_length=256):
    '''Compute spectral flux

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    :returns:
    - fluxVals : np.ndarray
    spectral flux
    '''
    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    S_norm = librosa.util.normalize(S, norm=1, axis=0)

    # Create delayed spectrogram by adding zeros
    delayed_spectrogram = np.concatenate((np.zeros((S.shape[0], 1)), S_norm[:, 0:-1]), 1)
    flux = S_norm-delayed_spectrogram
    # Calculation of flux: sum of differences between spectrogram and delayed spectrogram
    fluxVals = np.sum(np.power(flux, 2), axis=0)

    return fluxVals

def spectral_contrast(y=None, sr=22050, S=None, n_fft=512, hop_length=256):
    '''Compute spectral contrast

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    - sr : int > 0
    audio sampling rate of ``S``

    :returns:
    - cont : 7 np.ndarray's
    each row of spectral contrast values corresponds to a given octave based frequency
    '''
    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    S = librosa.util.normalize(S, norm=1, axis=0)

    K, numFrames = np.shape(S)

    numBands = 6
    octa = 200*2**np.arange(0, numBands+1)
    octa = np.insert(octa, 0, 0)

    valley = np.zeros((numBands + 1, numFrames))
    peak = np.zeros((numBands + 1, numFrames))
    cont = np.zeros((numBands + 1, numFrames))

    freq = np.linspace(0, sr/2, K)

    for k in range(1, np.size(octa)):
      current_band = 1*np.logical_and(np.where(freq >= octa[k-1], 1, 0), np.where(freq <= octa[k], 1, 0))

      if k > 1:
        idx = np.nonzero(current_band == 1)[0]
        idx = idx[0] + 1
        current_band[idx-2] = 1

      if k == np.size(octa) - 1:
        idx = np.nonzero(current_band == 1)
        idx = idx[-1]
        idx = idx[-1] + 1
        current_band[idx:np.size(current_band)+1] = 1

      subBand = S[np.where(current_band == 1)]

      if k < np.size(octa - 1) - 1:
        subBand = subBand[0:-1][:]

      if np.sum(current_band) < 50:
        alph = 1
      else:
        alph = np.rint(0.02*np.sum(current_band))


      alphi = int(alph)

      sortedr = np.sort(subBand, axis=0)

      valley[k-1] = (1/alph)*np.sum(sortedr[0:alphi], axis=0)

      sortedr = sortedr[::-1]
      peak[k-1] = (1/alph)*np.sum(sortedr[0:alphi], axis=0)

    peak = np.transpose(peak)
    valley = np.transpose(valley)
    cont = peak - valley
    return cont

def rms(y=None, S=None, n_fft=512, hop_length=256):
    '''Compute rms

    :parameters:
    - S : np.ndarray or None
    stft spectrogram
    :returns:
    - rms : np.ndarray
    RMS values
    '''

    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    S_norm = librosa.util.normalize(S, norm=1, axis=0)

    #Calculate RMS value
    rms = np.sqrt(np.sum(S_norm*S_norm, axis=0)/S.shape[0])
    return rms


def line_features(y=None, sr=22050, S=None, n_fft=512, hop_length=256, order=1):
    '''Get coefficients of fitting an nth order polynomial to the data

    :parameters:
    - S : np.ndarray or None
    stft spectrogram

    - order : int > 0
    order of polynimals to fit the line to

    - sr : int > 0
    audio sampling rate of ``y``

    :returns:
    - slope : np.ndarray
    slope of polynomial

    - intercept : np.ndarray
    intercept of polynomial
    '''

    # If we don't have a spectrogram, build one
    if S is None:
      S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=scipy.signal.hamming(n_fft), center=False)

    n_fft = 2 * (S.shape[0] - 1)

    # Get bin center frequencies
    freq = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    S_norm = librosa.util.normalize(S, norm=1, axis=0)

    slope = np.zeros((1, S.shape[1]))
    intercept = np.zeros((1, S.shape[1]))

    # Get polynomial coefficients of order order
    for k in range(0, S.shape[1]):
      p = np.polyfit(freq, S_norm[:, k], order)
      slope[:, k] = p[0]
      intercept[:, k] = p[1]

    return (slope, intercept)

#-- Chroma --#
def logfsgram(y=None, sr=22050, S=None, n_fft=4096, hop_length=512, **kwargs):
    '''Compute a log-frequency spectrogram (piano roll) using a fixed-window STFT.

    :usage:
        >>> # From time-series input
        >>> S_log       = librosa.logfsgram(y=y, sr=sr)
        >>> # Or from spectrogram input
        >>> S           = np.abs(librosa.stft(y))**2
        >>> S_log       = librosa.logfsgram(S=S, sr=sr)
        >>> # Convert to chroma
        >>> chroma_map  = librosa.filters.cq_to_chroma(S_log.shape[0])
        >>> C           = chroma_map.dot(S_log)

    :parameters:
      - y : np.ndarray or None
          audio time series

      - sr : int > 0
          audio sampling rate of ``y``

      - S : np.ndarray or None
          optional power spectrogram 

      - n_fft : int > 0
          FFT window size

      - hop_length : int > 0
          hop length for STFT. See ``librosa.stft`` for details.

      - bins_per_octave : int > 0
          Number of bins per octave. 
          Defaults to 12.

      - tuning : float in [-0.5,  0.5)
          Deviation (in fractions of a bin) from A440 tuning.
          If not provided, it will be automatically estimated from ``y``.

      - kwargs : additional arguments
          See ``librosa.filters.logfrequency()`` 

    :returns:
      - P : np.ndarray, shape = (n_pitches, t)
          P(f, t) contains the energy at pitch bin f, frame t.

    .. note:: One of either ``S`` or ``y`` must be provided.
          If ``y`` is provided, the power spectrogram is computed automatically given
          the parameters ``n_fft`` and ``hop_length``.
          If ``S`` is provided, it is used as the input spectrogram, and ``n_fft`` is inferred
          from its shape.
    '''
    
    # If we don't have a spectrogram, build one
    if S is None:
        # If the user didn't specify tuning, do it ourselves
        if 'tuning' not in kwargs:
            pitches, magnitudes, S = ifptrack(y, sr, n_fft=n_fft, hop_length=hop_length)
            pitches = pitches[magnitudes > np.median(magnitudes)]
            del magnitudes

            bins_per_octave = kwargs.get('bins_per_octave', 12)
            kwargs['tuning'] = estimate_tuning(pitches, bins_per_octave=bins_per_octave)

            del pitches

        else:
            S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)

        # Retain power
        S = np.abs(S)**2

    else:
        n_fft       = (S.shape[0] -1 ) * 2

    # Build the CQ basis
    cq_basis = librosa.filters.logfrequency(sr, n_fft=n_fft, **kwargs)
    
    return cq_basis.dot(S)

def chromagram(y=None, sr=22050, S=None, norm=np.inf, n_fft=2048, hop_length=512, tuning=0.0, **kwargs):
    """Compute a chromagram from a spectrogram or waveform

    :usage:
        >>> C = librosa.chromagram(y, sr)

        >>> # Use a pre-computed spectrogram
        >>> S = np.abs(librosa.stft(y, n_fft=4096))
        >>> C = librosa.chromagram(S=S)


    :parameters:
      - y          : np.ndarray or None
          audio time series
      - sr         : int
          sampling rate of y
      - S          : np.ndarray or None
          spectrogram (STFT power)
      - norm       : float or None
          column-wise normalization. See
          ``librosa.util.normalize`` for details.
          If `None`, no normalization is performed.

      - n_fft      : int  > 0
          FFT window size if provided ``y, sr`` instead of ``S`` 

      - hop_length : int > 0
          hop length if provided ``y, sr`` instead of ``S``

      - tuning : float in [-0.5, 0.5)
          Deviation from A440 tuning in fractional bins (cents)

      - kwargs
          Parameters to build the chroma filterbank.
          See ``librosa.filters.chroma()`` for details.

    .. note:: One of either ``S`` or ``y`` must be provided.
          If y is provided, the magnitude spectrogram is computed automatically given
          the parameters ``n_fft`` and ``hop_length``.
          If S is provided, it is used as the input spectrogram, and n_fft is inferred
          from its shape.
      
    :returns:
      - chromagram  : np.ndarray
          Normalized energy for each chroma bin at each frame.

    :raises:
      - ValueError 
          if an improper value is supplied for norm

    """
    
    n_chroma = kwargs.get('n_chroma', 12)

    # Build the spectrogram, estimate tuning
    if S is None:
        pitches, magnitudes, S = ifptrack(y, sr=sr, n_fft=n_fft, hop_length=hop_length)
        tuning = estimate_tuning(pitches[magnitudes > np.median(magnitudes)], 
                                 bins_per_octave=n_chroma)

        S = np.abs(S / S.max())**2
    else:
        n_fft       = (S.shape[0] -1 ) * 2

    # Get the filter bank
    if 'A440' not in kwargs:
        kwargs['A440'] = 440.0 * 2.0**(tuning/n_chroma)

    chromafb = librosa.filters.chroma( sr, n_fft, **kwargs)

    # Compute raw chroma
    raw_chroma  = np.dot(chromafb, S)

    # Compute normalization factor for each frame
    if norm is None:
        return raw_chroma
    
    return librosa.util.normalize(raw_chroma, norm=norm, axis=0)

def perceptual_weighting(S, frequencies, ref_power=1e-12):
    '''Perceptual weighting of a power spectrogram:
    
    ``S_p[f] = A_weighting(f) + 10*log(S[f] / ref_power)``
    
    :usage:
        >>> # Re-weight a CQT representation, using peak power as reference
        >>> CQT             = librosa.cqt(y, sr, fmin=55, fmax=440)
        >>> freqs           = librosa.cqt_frequencies(CQT.shape[0], fmin=55)
        >>> percept_CQT     = librosa.feature.perceptual_weighting(CQT, freqs, 
                                                                    ref_power=CQT.max())

    :parameters:
      - S : np.ndarray, shape=(d,t)
          Power spectrogram
        
      - frequencies : np.ndarray, shape=(d,)
          Center frequency for each row of ``S``
        
      - ref_power : float > 0
          Reference power
        
    :returns:
      - S_p : np.ndarray, shape=(d,t)
          perceptually weighted version of ``S``, in dB relative to ``ref_power``
    '''
    
    offset = librosa.A_weighting(frequencies).reshape((-1, 1))
    
    return offset + librosa.logamplitude(S, ref_power=ref_power)

#-- Pitch and tuning --#
def estimate_tuning(frequencies, resolution=0.01, bins_per_octave=12):
    '''Given a collection of pitches, estimate its tuning offset
    (in fractions of a bin) relative to A440=440.0Hz.
    
    :usage:
        >>> # Generate notes at +25 cents
        >>> freqs = librosa.cqt_frequencies(24, 55, tuning=0.25)
        >>> librosa.feature.estimate_tuning(freqs)
        0.25

        >>> # Track frequencies from a real spectrogram
        >>> pitches, magnitudes, stft = librosa.feature.ifptrack(y, sr)
        >>> # Select out pitches with high energy
        >>> pitches = pitches[magnitudes > np.median(magnitudes)]
        >>> librosa.feature.estimate_tuning(pitches)

    :parameters:
      - frequencies : array-like, float
          A collection of frequencies detected in the signal.
          See ``ifptrack``.

      - resolution : float in (0, 1)
          Resolution of the tuning as a fraction of a bin.
          0.01 corresponds to cents.
        
      - bins_per_octave : int > 0
          How many frequency bins per octave
        
    :returns:
      - tuning: float in [-0.5, 0.5]
          estimated tuning deviation (fractions of a bin)                
    '''

    frequencies = np.asarray([frequencies], dtype=float).flatten()

    # Trim out any DC components
    frequencies = frequencies[frequencies > 0]

    # Compute the residual relative to the number of bins
    residual = np.mod(bins_per_octave * librosa.core.hz_to_octs(frequencies) , 1.0)

    # Are we on the wrong side of the semitone?
    # A residual of 0.95 is more likely to be a deviation of -0.05
    # from the next tone up.
    residual[residual >= 0.5] -= 1.0
    
    bins     = np.linspace(-0.5, 0.5, np.ceil(1./resolution), endpoint=False)
  
    counts, tuning = np.histogram(residual, bins)
    
    # return the histogram peak
    return tuning[np.argmax(counts)]

def ifptrack(y, sr=22050, n_fft=4096, hop_length=None, fmin=None, fmax=None, threshold=0.75):
    '''Instantaneous pitch frequency tracking.

    :usage:
        >>> pitches, magnitudes, D = librosa.feature.ifptrack(y, sr)

    :parameters:
      - y: np.ndarray
          audio signal
      
      - sr : int
          audio sampling rate of ``y``
        
      - n_fft: int
          FFT window size
        
      - hop_length : int
          Hop size for STFT.  Defaults to ``n_fft / 4``.
          See ``librosa.stft()`` for details.

      - threshold : float in (0, 1)
          Maximum fraction of expected frequency increment to tolerate
      
      - fmin : float or tuple of float
          Ramp parameter for lower frequency cutoff.
          If scalar, the ramp has 0 width.
          If tuple, a linear ramp is applied from ``fmin[0]`` to ``fmin[1]``
          Default: (150.0, 300.0)
        
      - fmax : float or tuple of float
          Ramp parameter for upper frequency cutoff.
          If scalar, the ramp has 0 width.
          If tuple, a linear ramp is applied from ``fmax[0]`` to ``fmax[1]``
          Default: (2000.0, 4000.0)

    :returns:
      - pitches : np.ndarray, shape=(d,t)
      - magnitudes : np.ndarray, shape=(d,t)
          Where ``d`` is the subset of FFT bins within ``fmin`` and ``fmax``.
        
          ``pitches[i, t]`` contains instantaneous frequencies at time ``t``
          ``magnitudes[i, t]`` contains their magnitudes.
        
      - D : np.ndarray, dtype=complex
          STFT matrix
    '''

    if fmin is None:
        fmin    = (150.0, 300.0)

    if fmax is None:
        fmax    = (2000.0, 4000.0)

    fmin = np.asarray([fmin]).squeeze()
    fmax = np.asarray([fmax]).squeeze()
    
    # Truncate to feasible region
    fmin = np.maximum(0, fmin)
    fmax = np.minimum(fmax, sr / 2)
    
    # What's our DFT bin resolution?
    fft_res = float(sr) / n_fft
    
    # Only look at bins up to 2 kHz
    max_bin = int(round(fmax[-1] / fft_res))
  
    if hop_length is None:
        hop_length = n_fft / 4

    # Calculate the inst freq gram
    if_gram, D = librosa.core.ifgram(y, sr=sr, 
                                     n_fft=n_fft, 
                                     win_length=n_fft/2, 
                                     hop_length=hop_length)

    # Find plateaus in ifgram - stretches where delta IF is < thr:
    # ie, places where the same frequency is spread across adjacent bins
    idx_above  = range(1, max_bin) + [max_bin - 1]
    idx_below  = [0] + range(0, max_bin - 1)
    
    # expected increment per bin = sr/w, threshold at 3/4 that
    matches    = abs(if_gram[idx_above] - if_gram[idx_below]) < threshold * fft_res
  
    # mask out any singleton bins (where both above and below are zero)
    matches    = matches * ((matches[idx_above] > 0) | (matches[idx_below] > 0))

    pitches    = np.zeros_like(matches, dtype=float)
    magnitudes = np.zeros_like(matches, dtype=float)

    # For each frame, extract all harmonic freqs & magnitudes
    for t in range(matches.shape[1]):
        
        # find nonzero regions in this vector
        # The mask selects out constant regions + active borders
        mask   = ~np.pad(matches[:, t], 1, mode='constant')
        
        starts = np.argwhere(matches[:, t] & mask[:-2]).astype(int)
        ends   = 1 + np.argwhere(matches[:, t] & mask[2:]).astype(int)
        
        # Set up inner loop    
        frqs = np.zeros_like(starts, dtype=float)
        mags = np.zeros_like(starts, dtype=float)
        
        for i, (start_i, end_i) in enumerate(zip(starts, ends)):

            start_i = np.asscalar(start_i)
            end_i   = np.asscalar(end_i)

            # Weight frequencies by energy
            weights = np.abs(D[start_i:end_i, t])
            mags[i] = weights.sum()
            
            # Compute the weighted average frequency.
            # FIXME: is this the right thing to do? 
            # These are frequencies... shouldn't this be a 
            # weighted geometric average?
            frqs[i] = weights.dot(if_gram[start_i:end_i, t])
            if mags[i] > 0:
                frqs[i] /= mags[i]
            
        # Clip outside the ramp zones
        idx        = (fmax[-1] < frqs) | (frqs < fmin[0])
        mags[idx]  = 0
        frqs[idx]  = 0
        
        # Ramp down at the high end
        idx        = (fmax[-1] > frqs) & (frqs > fmax[0])
        mags[idx] *= (fmax[-1] - frqs[idx]) / (fmax[-1] - fmax[0])
        
        # Ramp up from the bottom end
        idx        = (fmin[-1] > frqs) & (frqs > fmin[0])
        mags[idx] *= (frqs[idx] - fmin[0]) / (fmin[-1] - fmin[0])
        
        # Assign pitch and magnitude to their center bin
        bins                = (starts + ends) / 2
        pitches[bins, t]    = frqs
        magnitudes[bins, t] = mags

    return pitches, magnitudes, D
  
#-- Mel spectrogram and MFCCs --#
def mfcc(S=None, y=None, sr=22050, n_mfcc=20):
    """Mel-frequency cepstral coefficients

    :usage:
        >>> # Generate mfccs from a time series
        >>> mfccs = librosa.feature.mfcc(y=y, sr=sr)

        >>> # Use a pre-computed log-power Mel spectrogram
        >>> S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
        >>> mfccs = librosa.feature.mfcc(S=librosa.logamplitude(S))

        >>> # Get more components
        >>> mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)

    :parameters:
      - S     : np.ndarray or None
          log-power Mel spectrogram
      - y     : np.ndarray or None
          audio time series
      - sr    : int > 0
          sampling rate of y
      - n_mfcc: int
          number of MFCCs to return

    .. note::
        One of ``S`` or ``y, sr`` must be provided.
        If ``S`` is not given, it is computed from ``y, sr`` using
        the default parameters of ``melspectrogram``.

    :returns:
      - M     : np.ndarray, shape=(n_mfcc, S.shape[1])
          MFCC sequence

    """

    if S is None:
        S = librosa.logamplitude(melspectrogram(y=y, sr=sr))
    
    return np.dot(librosa.filters.dct(n_mfcc, S.shape[0]), S)

def melspectrogram(y=None, sr=22050, S=None, n_fft=2048, hop_length=512, **kwargs):
    """Compute a Mel-scaled power spectrogram.

    :usage:
        >>> S = librosa.feature.melspectrogram(y=y, sr=sr)

        >>> # Using a pre-computed power spectrogram
        >>> D = np.abs(librosa.stft(y))**2
        >>> S = librosa.feature.melspectrogram(S=D)

        >>> # Passing through arguments to the Mel filters
        >>> S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)

    :parameters:
      - y : np.ndarray
          audio time-series
      - sr : int
          sampling rate of y  
      - S : np.ndarray
          magnitude or power spectrogram
      - n_fft : int
          length of the FFT window
      - hop_length : int
          number of samples between successive frames.
          See ``librosa.stft()``

      - kwargs
          Mel filterbank parameters
          See librosa.filters.mel() documentation for details.

    .. note:: One of either ``S`` or ``y, sr`` must be provided.
        If the pair y, sr is provided, the power spectrogram is computed.
        If S is provided, it is used as the spectrogram, and the parameters ``y, n_fft,
        hop_length`` are ignored.

    :returns:
      - S : np.ndarray
          Mel power spectrogram

    """

    # Compute the STFT
    if S is None:
        S       = np.abs(librosa.core.stft(y,   
                                            n_fft       =   n_fft, 
                                            hop_length  =   hop_length))**2
    else:
        n_fft = 2 * (S.shape[0] - 1)

    # Build a Mel filter
    mel_basis   = librosa.filters.mel(sr, n_fft, **kwargs)

    return np.dot(mel_basis, S)

#-- miscellaneous utilities --#
def delta(data, axis=-1, order=1, pad=True):
    '''Compute delta features.

    :usage:
        >>> # Compute MFCC deltas, delta-deltas
        >>> mfccs       = librosa.feature.mfcc(y=y, sr=sr)
        >>> delta_mfcc  = librosa.feature.delta(mfccs)
        >>> delta2_mfcc = librosa.feature.delta(mfccs, order=2)

    :parameters:
      - data      : np.ndarray, shape=(d, T)
          the input data matrix (eg, spectrogram)

      - axis      : int
          the axis along which to compute deltas.
          Default is -1 (columns).

      - order     : int
          the order of the difference operator.
          1 for first derivative, 2 for second, etc.

      - pad       : bool
          set to True to pad the output matrix to the original size.

    :returns:
      - delta_data   : np.ndarray
          delta matrix of ``data``.
    '''

    delta_x  = np.diff(data, n=order, axis=axis)

    if pad:
        padding         = [(0, 0)]  * data.ndim
        padding[axis]   = (order, 0)
        delta_x              = np.pad(delta_x, padding, mode='constant')

    return delta_x

def sync(data, frames, aggregate=None):
    """Synchronous aggregation of a feature matrix

    :usage:
        >>> # Beat-synchronous MFCCs
        >>> tempo, beats    = librosa.beat.beat_track(y, sr)
        >>> S               = librosa.feature.melspectrogram(y, sr, hop_length=64)
        >>> mfcc            = librosa.feature.mfcc(S=S)
        >>> mfcc_sync       = librosa.feature.sync(mfcc, beats)

        >>> # Use median-aggregation instead of mean
        >>> mfcc_sync       = librosa.feature.sync(mfcc, beats, aggregate=np.median)
        >>> # Or max aggregation
        >>> mfcc_sync       = librosa.feature.sync(mfcc, beats, aggregate=np.max)

    :parameters:
      - data      : np.ndarray, shape=(d, T)
          matrix of features
      - frames    : np.ndarray
          ordered array of frame segment boundaries
      - aggregate : function
          aggregation function (defualt: np.mean)

    :returns:
      - Y         : ndarray 
          ``Y[:, i] = aggregate(data[:, F[i-1]:F[i]], axis=1)``

    .. note:: In order to ensure total coverage, boundary points are added to frames

    .. note:: If synchronizing a feature matrix against beat tracker output, ensure
              that the frame numbers are properly aligned and use the same hop_length.

    """
    if data.ndim < 2:
        data = np.asarray([data])
    elif data.ndim > 2:
        raise ValueError('Synchronized data has ndim=%d, must be 1 or 2.' % data.ndim)

    if aggregate is None:
        aggregate = np.mean

    (dimension, n_frames) = data.shape

    frames      = np.unique(np.concatenate( ([0], frames, [n_frames]) ))

    if min(frames) < 0:
        raise ValueError('Negative frame index.')
    elif max(frames) > n_frames:
        raise ValueError('Frame index exceeds data length.')

    data_agg    = np.empty( (dimension, len(frames)-1), order='F')

    start       = frames[0]

    for (i, end) in enumerate(frames[1:]):
        data_agg[:, i] = aggregate(data[:, start:end], axis=1)
        start = end

    return data_agg
