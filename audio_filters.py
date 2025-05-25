"""
Audio processing filters for the MMS project.

This module provides various audio filters and effects that can be applied to audio signals.
Functions work with numpy arrays representing audio signals and typically return processed versions.
"""
import numpy as np
import scipy.signal as sg

def pre_emphasis(x: np.ndarray, alpha: float = 0.97) -> np.ndarray:
    """y[n] = x[n] – α·x[n‑1] (voice brightening)"""
    if x.ndim == 1:
        return sg.lfilter([1, -alpha], [1], x)
    return np.vstack([pre_emphasis(ch, alpha) for ch in x])

def _butter(sr: int, low: float | None, high: float, order: int, btype: str):
    """
    Helper function to create Butterworth filter coefficients.
    
    Args:
        sr: Sample rate in Hz
        low: Lower cutoff frequency in Hz (only used for bandpass filters)
        high: Higher cutoff frequency in Hz
        order: Filter order (higher = sharper cutoff, but more processing)
        btype: Filter type ('low', 'high', 'band')
        
    Returns:
        Filter coefficients (b, a) for scipy.signal.lfilter
    """
    nyq = sr / 2
    wn = high / nyq if btype != "band" else [low / nyq, high / nyq]
    return sg.butter(order, wn, btype=btype)

def db_to_lin(db: float) -> float:
    """
    Convert decibels to linear scale.
    
    Args:
        db: Value in decibels
        
    Returns:
        Equivalent value in linear scale
    """
    return 10 ** (db / 20)

def gain_compress(x: np.ndarray, threshold_db: float = -1.0, limiter_db: float = 0.0) -> np.ndarray:
    """
    Apply gain compression to the input signal.
    
    Compresses the dynamic range of the signal by reducing the volume of louder parts
    while keeping quieter parts audible. Useful for enhancing vocal clarity.
    
    Args:
        x: Input audio signal array
        threshold_db: Threshold above which compression is applied (in dB)
        limiter_db: Hard limit to prevent clipping (in dB)
        
    Returns:
        Compressed audio signal
    """
    threshold = db_to_lin(threshold_db)
    limiter = db_to_lin(limiter_db)
    
    # region: sample‑wise shaping
    y = x.copy()
    above_threshold = np.abs(x) > threshold

    # linear below threshold
    # soft‑clip between thresh … limit (sinusoid like tanh)
    y[above_threshold] = np.sign(x[above_threshold]) * (threshold + (limiter - threshold) *
    (np.tanh((np.abs(x[above_threshold]) - threshold) / (limiter - threshold))))

    #hard limit above limit
    y = np.clip(y, -limiter, limiter)
    return y

def voice_enhancement(x: np.ndarray, sr: int, alpha: float = 0.97, order: int = 2):
    y = pre_emphasis(x, alpha)
    b, a = _butter(sr, 800, 6000, order, "band")
    return sg.lfilter(b, a, y)

def wiener_denoise(x: np.ndarray):
    if x.ndim == 1:
        return sg.wiener(x)
    return np.vstack([sg.wiener(ch) for ch in x])

def delay(x: np.ndarray, sr: int, ms: int = 100, gain: float = 0.5):
    # Calculate delay in samples
    k = int(sr * ms / 1000)
    d = np.zeros_like(x)
    
    # Handle mono audio
    if x.ndim == 1:
        # Ensure k is not larger than the audio length
        if k < len(x):
            d[k:] = x[:-k] * gain
        else:
            # For extreme delays, use a modulo approach
            # This creates a "wrap-around" effect instead of silent output
            effective_k = k % len(x) if len(x) > 0 else 0
            d[effective_k:] = x[:-effective_k] * gain if effective_k > 0 else x * gain
    # Handle multi-channel audio
    else:
        if k < x.shape[1]:  # Normal case
            for ch in range(x.shape[0]):
                d[ch, k:] = x[ch, :-k] * gain
        else:  # Extreme delay case
            effective_k = k % x.shape[1] if x.shape[1] > 0 else 0
            for ch in range(x.shape[0]):
                d[ch, effective_k:] = x[ch, :-effective_k] * gain if effective_k > 0 else x[ch] * gain
    
    return x + d

def denoise_delay(x: np.ndarray, sr: int, noise_db: float, delay_ms: int, delay_gain: float):
    return delay(wiener_denoise(x), sr, delay_ms, delay_gain / 100)

def phone_filter(x: np.ndarray, sr: int, side_gain: float = 0.0, order: int = 1):
    mono = x.mean(axis=0) if x.ndim > 1 else x
    b, a = _butter(sr, 800, 12000, order, "band")
    return sg.lfilter(b, a, mono * (1 - side_gain))

def car_filter(x: np.ndarray, sr: int, side_gain_db: float = 3.0, order: int = 1):
    g = db_to_lin(side_gain_db)
    if x.ndim == 1:
        x = np.vstack([x, x])
    mid = x.mean(axis=0)
    side = (x[0] - x[1]) / 2
    widened = np.vstack([mid + g * side, mid - g * side])
    b, a = _butter(sr, None, 10000, order, "low")
    return sg.lfilter(b, a, widened)

