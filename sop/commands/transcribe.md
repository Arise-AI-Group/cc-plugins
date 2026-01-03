# Transcribe Audio
> Transcribe an audio file using OpenAI Whisper.

## Variables
audio_path: $1

## Instructions
- Run the transcription tool on the provided audio file
- Large files (>25MB) are automatically chunked
- Output is saved as `{filename}_transcript.txt` in the same directory

## Run
./run tools/transcribe_audio.py "$audio_path"

## Report
- Confirm the transcript was created
- Report the output file path
- Note the transcript length (characters)
