import speech_recognition as sr
import sounddevice as sd
import numpy as np
import time
import pyaudio
from google.cloud import speech, texttospeech
from openai import OpenAI
import noisereduce as nr
import webrtcvad
import concurrent.futures
import json
import os

# OpenAIとGoogle Cloudのクライアントを初期化
client = OpenAI(api_key='Your OpenAI API Key')
stt_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)  # 事前にスレッドプールを作成

# 会話履歴のファイルパス
history_file = 'conversation_history.json'

# 会話履歴を保存するリスト
conversation_history = []

# システムメッセージを定義
system_message = {"role": "system", "content": "AIの名前は「くーにゃ」。優しく話しかける親切な心理カウンセラーの役割を持つ。記号は使わない。最初に「心理カウンセラーのくーにゃです」と自己紹介をする。ユーザに質問を積極的にして会話を続け、カウンセラーとしてアドバイスをする。"}

# 会話履歴をファイルから読み込む関数
def load_conversation_history():
    global conversation_history
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            conversation_history = json.load(f)
    if not conversation_history or conversation_history[0]['role'] != 'system':
        conversation_history.insert(0, system_message)

# 会話履歴をファイルに保存する関数
def save_conversation_history():
    with open(history_file, 'w') as f:
        json.dump(conversation_history, f, ensure_ascii=False, indent=4)

# 会話履歴を更新する関数
def update_conversation_history(role, content):
    conversation_history.append({"role": role, "content": content})
    save_conversation_history()

# デバイス選択用の関数
def select_device(device_type, p):
    if device_type == 'output':
        device_index_list = list_audio_devices(p)
        output_device_index = int(input("Enter the number of the audio output device you want to use: "))
        return device_index_list[output_device_index]
    else:
        mic_list = sr.Microphone.list_microphone_names()
        print("Available microphones:")
        for index, name in enumerate(mic_list):
            print(f"Device {index}: {name}")
        mic_index = int(input("Enter the number of the microphone you want to use: "))
        return mic_index

def list_audio_devices(p):
    info = p.get_host_api_info_by_index(0)
    num_devices = info['deviceCount']
    print("Available audio devices:")
    device_index_list = []
    for i in range(num_devices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info['maxOutputChannels'] > 0:
            print(f"Device {len(device_index_list)}: {device_info['name']}")
            device_index_list.append(i)
    return device_index_list

# 音声を聞き取る関数
def listen_for_speech(source, recognizer, vad):
    frames = []
    silence_frames = 0
    while True:
        buffer = source.stream.read(320)
        frames.append(buffer)
        if vad.is_speech(buffer, source.SAMPLE_RATE):
            silence_frames = 0
        else:
            silence_frames += 1
        if silence_frames > 7:  # 人の声が検出されないフレームが連続して10回を超えると録音終了
            break
    raw_audio_data = b''.join(frames)
    audio_data = np.frombuffer(raw_audio_data, dtype=np.int16)
    reduced_noise_audio_data = nr.reduce_noise(y=audio_data, sr=source.SAMPLE_RATE)
    return sr.AudioData(reduced_noise_audio_data.tobytes(), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

# 音声を認識する関数
def recognize_speech(audio):
    audio_config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, language_code="ja-JP")
    audio_data = speech.RecognitionAudio(content=audio.get_wav_data())
    response = stt_client.recognize(config=audio_config, audio=audio_data)
    return response

# 音声合成を並列で行うための関数
def synthesize_speech(text, client, voice_params, audio_config):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(input=synthesis_input, voice=voice_params, audio_config=audio_config)
    return response.audio_content

# ストリームからの応答を処理し、音声合成を並列で行う関数
def process_stream(client, text):
    # 音声合成のパラメータ設定
    voice_params = texttospeech.VoiceSelectionParams(language_code='ja-JP', ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
    segments = text.split('。')
    futures = [executor.submit(synthesize_speech, segment + '。', client, voice_params, audio_config) for segment in segments if segment.strip()]

    audio_segments = [future.result() for future in concurrent.futures.as_completed(futures)]
    return b''.join(audio_segments)

# 音声を再生する関数
def play_sound(audio_content, device_index):
    audio_data = np.frombuffer(audio_content, dtype=np.int16)
    sd.play(audio_data, samplerate=24000, device=device_index)
    sd.wait()

# メインループ
def main_loop(p):
    vad = webrtcvad.Vad(1)  # VADのモード設定（0-3、3が最も敏感）
    output_device_index = select_device('output', p)
    mic_index = select_device('input', p)

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=mic_index, frames_per_buffer=320)
    print("Listening... Please speak.")
    
    load_conversation_history()  # プログラム開始時に履歴を読み込み、必要であればシステムメッセージを追加

    with sr.Microphone(device_index=mic_index, sample_rate=16000, chunk_size=320) as source:
        recognizer = sr.Recognizer()
        recognizer.adjust_for_ambient_noise(source)

        while True:
            print("Listening... Please speak.")
            try:
                audio = listen_for_speech(source, recognizer, vad)

                if len(audio.frame_data) == 0:
                    print("No voice detected for a while. Exiting...")
                    break

                response = recognize_speech(audio)
                if not response.results:
                    print("No speech detected.")
                    continue

                text = response.results[0].alternatives[0].transcript
                print(f"Recognized text: {text}")

                # ユーザーの発言を履歴に追加
                update_conversation_history("user", text)

                # GPRT-4の応答をストリーム形式で取得
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=conversation_history,
                    max_tokens=220,
                    stream=True
                )

                buffer = ""
                full_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        response_text = chunk.choices[0].delta.content
                        buffer += response_text
                        sentences = buffer.split('。')
                        if len(sentences) > 1:
                            for sentence in sentences[:-1]:  # 最後のセグメントは完全でない可能性があるため保留
                                audio_content = process_stream(tts_client, sentence + '。')
                                play_sound(audio_content, output_device_index)
                                full_text += sentence + '。'
                                update_conversation_history("system", sentence + '。')  # 応答を履歴に追加
                            buffer = sentences[-1]  # 最後のセグメントを次のチャンクと連結

                if buffer:
                    # ストリーム終了後に残ったテキストを処理
                    audio_content = process_stream(tts_client, buffer + '。')
                    play_sound(audio_content, output_device_index)
                    full_text += buffer + '。'
                    update_conversation_history("system", buffer + '。')  # 応答を履歴に追加

                print("全テキスト出力:", full_text)

            except sr.UnknownValueError:
                print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"Error from speech recognition service: {e}")
            except ValueError as e:
                print(e)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

p = pyaudio.PyAudio()
try:
    main_loop(p)
finally:
    p.terminate()
