from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig

def transcribe_voice(audio_path):
    speech_config = SpeechConfig(subscription="4cvYxldtAxUjSL3PL1VrF4UtYm49aQLgXGlyK48spgVcchr93ejwJQQJ99BAACrIdLPXJ3w3AAAYACOGDHDL", region="southafricanorth")
    speech_recognizer = SpeechRecognizer(speech_config=speech_config)
    audio_config = AudioConfig(filename=audio_path)
    recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = recognizer.recognize_once()
    return result.text if result.reason == result.Reason.RecognizedSpeech else None

def transcribe_voice(file_path):
    speech_config = SpeechConfig(subscription="<4cvYxldtAxUjSL3PL1VrF4UtYm49aQLgXGlyK48spgVcchr93ejwJQQJ99BAACrIdLPXJ3w3AAAYACOGDHDL>", region="southafricanorth")
    audio_input = AudioConfig(filename=file_path)
    speech_recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    result = speech_recognizer.recognize_once()
    if result.reason == ResultReason.RecognizedSpeech:
        return result.text
    else:
        return "Transcription failed."
