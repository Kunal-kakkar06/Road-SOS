import os
import json
from gtts import gTTS

def generate_audio():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'data', 'first_aid_tree.json')
    audio_dir = os.path.join(base_dir, 'static', 'audio')

    # Ensure audio directory exists
    os.makedirs(audio_dir, exist_ok=True)

    with open(json_path, 'r') as f:
        tree = json.load(f)

    # Dictionary to keep track of audio generation
    # audio_id -> text
    audio_map = {}

    for category, content in tree.items():
        # Generate audio for questions
        if "questions" in content:
            for q in content["questions"]:
                audio_map[f"{category}_{q['id']}"] = q["text"]
                # For options, we might want to read them out
                options_text = " Options are: " + ", or ".join(q["options"])
                audio_map[f"{category}_{q['id']}_options"] = q["text"] + options_text

        # Generate audio for outcomes/steps
        if "outcomes" in content:
            for outcome_id, outcome_data in content["outcomes"].items():
                steps = outcome_data.get("steps", [])
                audio_ids = outcome_data.get("audio_ids", [])
                
                for step_text, a_id in zip(steps, audio_ids):
                    audio_map[a_id] = step_text

    # Generate the actual MP3 files
    print(f"Generating {len(audio_map)} audio files...")
    for a_id, text in audio_map.items():
        file_path = os.path.join(audio_dir, f"{a_id}.mp3")
        if not os.path.exists(file_path):
            try:
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(file_path)
                print(f"Created: {file_path}")
            except Exception as e:
                print(f"Error generating audio for {a_id}: {e}")
        else:
            print(f"Skipped (already exists): {file_path}")

if __name__ == "__main__":
    generate_audio()
    print("Audio generation complete.")
