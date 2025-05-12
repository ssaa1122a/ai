import os
import sys
import argparse
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip
from gtts import gTTS
import tempfile

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def generate_video(text, output_path, quality='high'):
    """Generate video from text with AI voiceover"""
    try:
        # 1. Generate AI voiceover
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
            tts = gTTS(text=text, lang='en')
            tts.save(audio_file.name)
            audio_clip = AudioFileClip(audio_file.name)

        # 2. Create animated text
        text_clip = TextClip(
            text,
            fontsize=70,
            color='white',
            size=(1920, 1080),
            bg_color='#0f172a',
            method='caption',
            align='center',
            font='Arial-Bold'
        ).set_duration(audio_clip.duration)

        # 3. Combine and render
        video = CompositeVideoClip([text_clip.set_audio(audio_clip)])
        
        # Quality settings
        bitrate = '8000k' if quality == 'high' else '5000k'
        threads = 4 if quality == 'high' else 2
        
        video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            bitrate=bitrate,
            threads=threads,
            preset='slow' if quality == 'high' else 'fast',
            ffmpeg_params=['-crf', '18']
        )

        # Cleanup
        os.unlink(audio_file.name)
        return True

    except Exception as e:
        print(f"Error generating video: {str(e)}")
        return False

@app.route('/generate', methods=['POST'])
def handle_generation():
    """API endpoint for video generation"""
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "Text input required"}), 400

    video_id = str(hash(data['text']))[:8]
    output_path = os.path.join(OUTPUT_FOLDER, f"{video_id}.mp4")

    if os.path.exists(output_path):
        return jsonify({"videoUrl": f"/output/{video_id}.mp4"})

    if not generate_video(data['text'], output_path):
        return jsonify({"error": "Video generation failed"}), 500

    return jsonify({"videoUrl": f"/output/{video_id}.mp4"})

@app.route('/output/<filename>')
def serve_video(filename):
    """Serve generated videos"""
    return send_from_directory(OUTPUT_FOLDER, filename)

def run_server(port=5000):
    """Run the Flask server"""
    print(f"Server running on http://localhost:{port}")
    app.run(port=port)

def run_cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='AI Video Generator')
    parser.add_argument('--text', help='Text to convert to video')
    parser.add_argument('--output', help='Output file path')
    args = parser.parse_args()

    if args.text and args.output:
        success = generate_video(args.text, args.output)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_cli()
    else:
        run_server()
