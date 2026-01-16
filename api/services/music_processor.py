import librosa
import librosa.display
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import scipy.ndimage

# ==========================================
# 1. MOTOR DE CLASSIFICAÇÃO (Likelihood)
# ==========================================
def classificar_segmento(chroma_segmento):
    """
    Analisa uma fatia de áudio (vetor de 12 notas) e decide qual o acorde.
    """
    # Se o segmento for silêncio absoluto, retorna vazio
    if np.sum(chroma_segmento) < 0.05:
        return "Silêncio"

    # Normaliza para que o volume não afete a decisão, apenas a proporção das notas
    chroma_norm = chroma_segmento / (np.max(chroma_segmento) + 1e-6)

    notas_nomes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    melhor_score = -float('inf')
    acorde_vencedor = "N/A"

    for i, root in enumerate(notas_nomes):
        # Template MAIOR (Raiz + 4 + 7 semitons)
        # Ex: Dó Maior = C, E, G
        mask_maj = np.zeros(12)
        mask_maj[[i, (i+4)%12, (i+7)%12]] = 1.0

        # Template MENOR (Raiz + 3 + 7 semitons)
        # Ex: Dó Menor = C, Eb, G
        mask_min = np.zeros(12)
        mask_min[[i, (i+3)%12, (i+7)%12]] = 1.0

        # Template Diminuto (Raiz + 3 + 7 semitons)
        # Ex: Dó Menor = C, Eb, G
        mask_min = np.zeros(12)
        mask_min[[i, (i+3)%12, (i+7)%12]] = 1.0

        # CÁLCULO DE LIKELIHOOD (Pontuação)
        # Ganha pontos se tiver as notas certas, perde pontos se tiver notas erradas

        # Teste Maior
        score_maj = np.sum(chroma_norm * mask_maj) - 0.6 * np.sum(chroma_norm * (1-mask_maj))

        # Teste Menor
        score_min = np.sum(chroma_norm * mask_min) - 0.6 * np.sum(chroma_norm * (1-mask_min))

        if score_maj > melhor_score:
            melhor_score = score_maj
            acorde_vencedor = root # Maior

        if score_min > melhor_score:
            melhor_score = score_min
            acorde_vencedor = f"{root}m" # Menor

    return acorde_vencedor

# ==========================================
# 2. ALGORITMO PRINCIPAL COM ONSET
# ==========================================
def analisar_com_onset(audio_path):
    print(f"Processando com Onset Detection: {audio_path.split('/')[-1]}...")

    # A. Carregar Áudio
    y, sr = librosa.load(audio_path)

    # B. Separação Harmônica/Percussiva
    # Usamos 'y_percussive' para achar ONDE mudar (ritmo)
    # Usamos 'y_harmonic' para saber QUAL nota é (harmonia)
    y_harmonic, y_percussive = librosa.effects.hpss(y, margin=3.0)

    # C. CQT (Melhor resolução que FFT para notas graves)
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, bins_per_octave=36)

    # D. Detecção de Onsets (Ataques)
    # wait=10 -> Espera ~230ms entre detecções (evita picotar dedilhados)
    # backtrack=True -> Ajusta o corte para o início exato do som
    onset_frames = librosa.onset.onset_detect(
        y=y_percussive,
        sr=sr,
        backtrack=True,
        units='frames',
        wait=30,
        delta=0.1
    )

    # E. Correção de Bordas (Fix Frames)
    # Adiciona o frame 0 e o frame final para cobrir a música toda
    onset_frames = librosa.util.fix_frames(onset_frames, x_max=chroma.shape[1])

    # F. Sincronização (A Mágica)
    # Tira a MEDIANA do chroma entre cada ataque detectado
    # Note: If onset_frames has K elements, chroma_sync will have K-1 columns.
    chroma_sync = librosa.util.sync(chroma, onset_frames, aggregate=np.median)

    # G. Converter frames para tempo (segundos) para o gráfico e print
    # Note: tempos_limite will have K elements (from onset_frames)
    tempos_limite = librosa.frames_to_time(onset_frames, sr=sr)

    # ==========================================
    # 3. GERAÇÃO DA TIMELINE
    # ==========================================
    print("\n--- RESULTADO DA TRANSCRIÇÃO ---")

    acorde_anterior = ""
    # The first segment starts at tempos_limite[0]
    inicio_tempo_segmento = tempos_limite[0]

    # Normaliza para limpar ruído de fundo antes de classificar
    chroma_sync = librosa.util.normalize(chroma_sync, axis=0)

    # Loop through each synchronized segment. chroma_sync.shape[1] is N_segments
    # tempos_limite has N_segments + 1 elements, corresponding to edges.
    # The loop should go up to chroma_sync.shape[1]
    for i in range(chroma_sync.shape[1]):
        coluna_atual = chroma_sync[:, i]
        acorde_atual = classificar_segmento(coluna_atual)

        # Check for chord change
        if acorde_atual != acorde_anterior:
            # If there was a previous chord, print its duration.
            # The previous chord ended at tempos_limite[i] (which is the start of the current segment)
            if acorde_anterior != "": # Avoid printing for the very first 'empty' chord
                print(f"{inicio_tempo_segmento:5.2f}s -> {tempos_limite[i]:5.2f}s : {acorde_anterior}")

            # Start tracking the new chord. It begins at tempos_limite[i]
            acorde_anterior = acorde_atual
            inicio_tempo_segmento = tempos_limite[i]

    # Print the very last chord segment. It ends at tempos_limite[-1]
    print(f"{inicio_tempo_segmento:5.2f}s -> {tempos_limite[-1]:5.2f}s : {acorde_anterior}")

    # ==========================================
    # 4. VISUALIZAÇÃO
    # ==========================================
    plt.figure(figsize=(14, 6))

    # Plota o Chroma Sincronizado
    # We use tempos_limite[:-1] because chroma_sync has N columns,
    # and tempos_limite (from onset_frames) has N+1 elements.
    # For shading='nearest', x_coords should have N elements.
    librosa.display.specshow(chroma_sync,
                             x_axis='time',
                             y_axis='chroma',
                             x_coords=tempos_limite[:-1], # <-- FIX: Use tempos_limite without the last element
                             cmap='coolwarm',
                             shading='nearest')

    plt.title("Segmentação por Onset (Ataque) + Classificação Likelihood")
    plt.colorbar(label='Energia')
    plt.xlabel("Tempo (s)")
    plt.tight_layout()
    plt.show()

