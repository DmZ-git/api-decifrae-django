import librosa
import numpy as np
import json


# ===============================
# CLASSIFICADOR COM INÉRCIA
# ===============================
def classificar_segmento(chroma, acorde_anterior=""):
    if np.sum(chroma) < 0.1:
        return ""

    chroma = chroma / (np.max(chroma) + 1e-6)
    notas = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    templates = {
        '':  [0, 4, 7],   # maior
        'm': [0, 3, 7],   # menor
    }

    melhor_score = -1e9
    melhor_acorde = ""

    for i, root in enumerate(notas):
        for sufixo, intervalos in templates.items():
            idx = [(i + x) % 12 for x in intervalos]
            energia_acorde = np.sum(chroma[idx])
            energia_ruido = np.sum(chroma) - energia_acorde

            score = energia_acorde - 0.6 * energia_ruido + 0.15

            if f"{root}{sufixo}" == acorde_anterior:
                score += 0.5  # inércia

            if score > melhor_score:
                melhor_score = score
                melhor_acorde = f"{root}{sufixo}"

    return melhor_acorde


# ===============================
# PROCESSAMENTO PRINCIPAL
# ===============================
def detectar_acordes(audio_path) -> dict:
    y, sr = librosa.load(audio_path, sr=11025, mono=True)
    y_h, y_p = librosa.effects.hpss(y, margin=3.0)

    tempo, beats = librosa.beat.beat_track(y=y_p, sr=sr)

    chroma = librosa.feature.chroma_stft(
        y=y_h,
        sr=sr,
        n_chroma=12,
        n_fft=2048
    )

    beats = librosa.util.fix_frames(beats, x_max=chroma.shape[1])
    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)
    tempos = librosa.frames_to_time(beats, sr=sr)

    timestamps = []
    acorde_anterior = ""

    for i in range(chroma_sync.shape[1]):
        acorde = classificar_segmento(chroma_sync[:, i], acorde_anterior)

        start = float(round(tempos[i], 2))
        end = float(round(tempos[i + 1], 2)) if i + 1 < len(tempos) else start

        if acorde:
            timestamps.append({
                "start": start,
                "end": end,
                "chord": acorde
            })

        acorde_anterior = acorde

    # Lista única de acordes (ordem de aparecimento)
    chords = list(dict.fromkeys(t["chord"] for t in timestamps))

    return {
        "chords": chords,
        "content": "[Intro]\nC  G  Am  F\n\n[Verso]\nC              G\nLetra da música...",
        "timestamps": timestamps
    }


def detectar_acordes_json(audio_path) -> str:
    resultado = detectar_acordes(audio_path)
    return json.dumps(resultado, indent=2, ensure_ascii=False)


def processar_audio(audio_path):
    return detectar_acordes(audio_path)