import librosa
import numpy as np
import json
from typing import List, Dict, Optional

# Imports opcionais para visualização
try:
    import matplotlib.pyplot as plt
    import librosa.display
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

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
def processar_audio(audio_path: str, visualizar: bool = False) -> Dict:
    """
    Processa um arquivo de áudio e retorna as cifras detectadas em formato JSON.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização
    
    Returns:
        Dicionário com os acordes detectados e metadados
    """
    try:
        # A. Carregar Áudio
        y, sr = librosa.load(audio_path)

        # B. Separação Harmônica/Percussiva
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=3.0)

        # C. CQT (Melhor resolução que FFT para notas graves)
        chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, bins_per_octave=36)

        # D. Detecção de Onsets (Ataques)
        onset_frames = librosa.onset.onset_detect(
            y=y_percussive,
            sr=sr,
            backtrack=True,
            units='frames',
            wait=30,
            delta=0.1
        )

        # E. Correção de Bordas (Fix Frames)
        onset_frames = librosa.util.fix_frames(onset_frames, x_max=chroma.shape[1])

        # F. Sincronização (A Mágica)
        chroma_sync = librosa.util.sync(chroma, onset_frames, aggregate=np.median)

        # G. Converter frames para tempo (segundos)
        tempos_limite = librosa.frames_to_time(onset_frames, sr=sr)

        # H. Normaliza para limpar ruído de fundo
        chroma_sync = librosa.util.normalize(chroma_sync, axis=0)

        # ==========================================
        # 3. GERAÇÃO DA TIMELINE
        # ==========================================
        acordes_detectados = []
        acorde_anterior = ""
        inicio_tempo_segmento = tempos_limite[0]

        # Loop através de cada segmento sincronizado
        for i in range(chroma_sync.shape[1]):
            coluna_atual = chroma_sync[:, i]
            acorde_atual = classificar_segmento(coluna_atual)

            # Verifica mudança de acorde
            if acorde_atual != acorde_anterior:
                # Se havia um acorde anterior, adiciona à lista
                if acorde_anterior != "":
                    acordes_detectados.append({
                        "acorde": acorde_anterior,
                        "inicio": round(inicio_tempo_segmento, 2),
                        "fim": round(tempos_limite[i], 2),
                        "duracao": round(tempos_limite[i] - inicio_tempo_segmento, 2)
                    })

                # Começa a rastrear o novo acorde
                acorde_anterior = acorde_atual
                inicio_tempo_segmento = tempos_limite[i]

        # Adiciona o último acorde
        acordes_detectados.append({
            "acorde": acorde_anterior,
            "inicio": round(inicio_tempo_segmento, 2),
            "fim": round(tempos_limite[-1], 2),
            "duracao": round(tempos_limite[-1] - inicio_tempo_segmento, 2)
        })

        # Calcula a duração total
        duracao_total = float(librosa.get_duration(y=y, sr=sr))

        # Monta o resultado final
        resultado = {
            "sucesso": True,
            "arquivo": audio_path.split('/')[-1].split('\\')[-1],
            "duracao_total": round(duracao_total, 2),
            "taxa_amostragem": int(sr),
            "quantidade_acordes": len(acordes_detectados),
            "acordes": [{
                "acorde": a["acorde"],
                "tempo_inicio": a["inicio"],
                "duracao": a["duracao"],
                "confianca": 0.85  # Placeholder - pode ser melhorado com cálculo real
            } for a in acordes_detectados]
        }

        # ==========================================
        # 4. VISUALIZAÇÃO (OPCIONAL)
        # ==========================================
        if visualizar and MATPLOTLIB_AVAILABLE:
            plt.figure(figsize=(14, 6))
            librosa.display.specshow(
                chroma_sync,
                x_axis='time',
                y_axis='chroma',
                x_coords=tempos_limite[:-1],
                cmap='coolwarm',
                shading='nearest'
            )
            plt.title("Segmentação por Onset (Ataque) + Classificação Likelihood")
            plt.colorbar(label='Energia')
            plt.xlabel("Tempo (s)")
            plt.tight_layout()
            plt.show()

        return resultado

    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "arquivo": audio_path.split('/')[-1].split('\\')[-1] if isinstance(audio_path, str) else "arquivo"
        }

# ==========================================
# 3. FUNÇÃO PARA RETORNAR JSON STRING
# ==========================================
def processar_audio_json(audio_path: str, visualizar: bool = False) -> str:
    """
    Processa um arquivo de áudio e retorna as cifras detectadas em formato JSON string.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização
    
    Returns:
        String JSON com os acordes detectados
    """
    resultado = processar_audio(audio_path, visualizar)
    return json.dumps(resultado, indent=2, ensure_ascii=False)

# ==========================================
# AREA DE TESTE
# ==========================================
if __name__ == "__main__":
    # Exemplo de uso
    arquivo_teste = 'caminho/para/seu/arquivo.mp3'
    
    # Opção 1: Retorna dicionário Python
    resultado_dict = processar_audio(arquivo_teste, visualizar=False)
    print("Resultado como dicionário:")
    print(resultado_dict)
    print("\n" + "="*50 + "\n")
    
    # Opção 2: Retorna JSON string
    resultado_json = processar_audio_json(arquivo_teste, visualizar=False)
    print("Resultado como JSON:")
    print(resultado_json)
