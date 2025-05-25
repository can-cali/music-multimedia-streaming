# Music and Multimedia Streaming Project

Final project for the "Music and Multimedia Streaming" class, 2025.

## Project Overview

This is a web application for processing video and audio content with various filters. The application allows users to:

1. Upload video files
2. Apply various audio and video filters
3. Stream the processed results directly in the browser

## Features

### Video Filters
- **Grayscale**: Convert video to black and white
- **Color Invert**: Invert all colors in the video
- **Frame Interpolation**: Increase the frame rate for smoother playback
- **Upscale**: Increase video resolution

### Audio Filters
- **Gain Compression**: Reduce dynamic range for clearer audio
- **Voice Enhancement**: Improve vocal clarity
- **Denoise + Delay**: Remove noise and add echo effects
- **Phone-like**: Apply telephone audio characteristics 
- **Car-like**: Simulate car audio system characteristics

## Technical Implementation

- **Backend**: FastAPI (Python)
- **Video Processing**: FFmpeg (with custom wrappers)
- **Audio Processing**: librosa, scipy.signal, soundfile
- **Frontend**: HTML/CSS/JS single page application

## Getting Started

### Prerequisites
- Python 3.10 or higher
- FFmpeg installed on your system

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the server:
   ```
   python -m uvicorn server:app --reload
   ```
4. Open your browser and visit `http://127.0.0.1:8000`

## Usage

1. Upload a video file using the "Upload Video" section
2. Select audio and/or video filters from the dropdown menus
3. Configure filter parameters as desired
4. Click "Configure Filters" and then "Apply Filters"
5. Once processing is complete, click "Play" to stream the result

## Project Structure

- `server.py`: Main FastAPI application
- `video_filters.py`: Video processing functions using FFmpeg
- `audio_filters.py`: Audio processing functions
- `static/index.html`: Web interface
- `static/media/`: Storage for uploaded and processed files