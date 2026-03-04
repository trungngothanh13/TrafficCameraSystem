import os
import subprocess
import threading
import json
import glob
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'antigravity-frame-extractor'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEOS = [
    {"id": 1, "file": "Data_1.mp4", "output_dir": "Data_1_frame"},
    {"id": 2, "file": "Data_2.mp4", "output_dir": "Data_2_frame"},
    {"id": 3, "file": "Data_3.mp4", "output_dir": "Data_3_frame"},
    {"id": 4, "file": "Data_4.mp4", "output_dir": "Data_4_frame"},
]

extraction_status = {}
extraction_threads = {}

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_streams', '-show_format', video_path],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        return duration
    except Exception as e:
        return 0

def get_video_info(video_path):
    """Get video resolution and fps."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_streams', video_path],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = stream.get('width', 0)
                height = stream.get('height', 0)
                # Parse fps
                fps_str = stream.get('r_frame_rate', '60/1')
                num, den = fps_str.split('/')
                fps = round(float(num) / float(den), 2)
                return width, height, fps
    except Exception:
        pass
    return 0, 0, 0

def count_existing_frames(output_dir):
    frames = glob.glob(os.path.join(output_dir, '*.jpg'))
    return len(frames)

def extract_frames(video_id, video_file, output_dir_name):
    """Extract 1 frame per second from video using FFmpeg."""
    video_path = os.path.join(BASE_DIR, video_file)
    output_dir = os.path.join(BASE_DIR, output_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    # Clear existing frames
    for f in glob.glob(os.path.join(output_dir, '*.jpg')):
        os.remove(f)

    duration = get_video_duration(video_path)
    total_frames = max(1, int(duration))

    extraction_status[video_id] = {
        'status': 'running',
        'progress': 0,
        'current_frame': 0,
        'total_frames': total_frames,
        'duration': duration,
        'message': 'Starting extraction...'
    }
    socketio.emit('status_update', {'video_id': video_id, **extraction_status[video_id]})

    output_pattern = os.path.join(output_dir, 'frame_%05d.jpg')

    # FFmpeg command: extract 1 frame per second, high quality JPEG
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-vf', 'fps=1',
        '-q:v', '2',          # High quality JPEG (2 = best, 31 = worst)
        '-threads', '0',       # Use all CPU cores
        output_pattern
    ]

    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    extraction_threads[video_id] = process

    import re
    time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')

    for line in process.stderr:
        if extraction_status[video_id]['status'] == 'cancelled':
            process.terminate()
            break

        match = time_pattern.search(line)
        if match:
            h, m, s = match.groups()
            current_sec = int(h) * 3600 + int(m) * 60 + float(s)
            current_frame = int(current_sec)
            progress = min(99, int((current_sec / duration) * 100)) if duration > 0 else 0

            extraction_status[video_id].update({
                'current_frame': current_frame,
                'progress': progress,
                'message': f'Extracting frame {current_frame}/{total_frames}...'
            })
            socketio.emit('status_update', {'video_id': video_id, **extraction_status[video_id]})

    process.wait()

    if extraction_status[video_id]['status'] == 'cancelled':
        extraction_status[video_id].update({
            'status': 'cancelled',
            'progress': 0,
            'message': 'Extraction cancelled.'
        })
    elif process.returncode == 0:
        actual_frames = count_existing_frames(output_dir)
        extraction_status[video_id].update({
            'status': 'done',
            'progress': 100,
            'current_frame': actual_frames,
            'total_frames': actual_frames,
            'message': f'Done! Extracted {actual_frames} frames.'
        })
    else:
        extraction_status[video_id].update({
            'status': 'error',
            'progress': 0,
            'message': 'FFmpeg error occurred.'
        })

    socketio.emit('status_update', {'video_id': video_id, **extraction_status[video_id]})


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/videos')
def get_videos():
    result = []
    for v in VIDEOS:
        video_path = os.path.join(BASE_DIR, v['file'])
        output_dir = os.path.join(BASE_DIR, v['output_dir'])
        exists = os.path.exists(video_path)
        size = os.path.getsize(video_path) if exists else 0
        existing_frames = count_existing_frames(output_dir) if os.path.exists(output_dir) else 0

        width, height, fps = (0, 0, 0)
        duration = 0
        if exists:
            width, height, fps = get_video_info(video_path)
            duration = get_video_duration(video_path)

        status_info = extraction_status.get(v['id'], {
            'status': 'idle',
            'progress': 100 if existing_frames > 0 else 0,
            'current_frame': existing_frames,
            'total_frames': int(duration) if duration else existing_frames,
            'message': f'{existing_frames} frames already extracted' if existing_frames > 0 else 'Ready to extract'
        })

        result.append({
            **v,
            'exists': exists,
            'size_mb': round(size / (1024 * 1024), 1),
            'width': width,
            'height': height,
            'fps': fps,
            'duration': round(duration, 1),
            'existing_frames': existing_frames,
            **status_info
        })
    return jsonify(result)

@app.route('/api/extract/<int:video_id>', methods=['POST'])
def start_extraction(video_id):
    video = next((v for v in VIDEOS if v['id'] == video_id), None)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    current = extraction_status.get(video_id, {})
    if current.get('status') == 'running':
        return jsonify({'error': 'Already running'}), 400

    thread = threading.Thread(
        target=extract_frames,
        args=(video_id, video['file'], video['output_dir']),
        daemon=True
    )
    thread.start()
    return jsonify({'message': 'Started'})

@app.route('/api/extract/all', methods=['POST'])
def start_all():
    for v in VIDEOS:
        vid_id = v['id']
        current = extraction_status.get(vid_id, {})
        if current.get('status') != 'running':
            thread = threading.Thread(
                target=extract_frames,
                args=(vid_id, v['file'], v['output_dir']),
                daemon=True
            )
            thread.start()
    return jsonify({'message': 'All started'})

@app.route('/api/cancel/<int:video_id>', methods=['POST'])
def cancel_extraction(video_id):
    if video_id in extraction_threads:
        extraction_status[video_id]['status'] = 'cancelled'
        proc = extraction_threads[video_id]
        try:
            proc.terminate()
        except Exception:
            pass
    return jsonify({'message': 'Cancelled'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5055, debug=False)
