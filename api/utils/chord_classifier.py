import librosa
import numpy as np
import json
import os
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Configurações de otimização de memória
LIBROSA_CACHE_ENABLED = False  # Desabilita cache de librosa
MAX_AUDIO_DURATION = 300  # 5 minutos max
MAX_FILE_SIZE_MB = 50  # 50MB max

# Imports opcionais para visualização (NUNCA usada em produção)
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')
VISUALIZAR_DISPONIVEL = ENVIRONMENT != 'production'
try:
    if VISUALIZAR_DISPONIVEL:
        import matplotlib.pyplot as plt
        import librosa.display
        MATPLOTLIB_AVAILABLE = True
    else:
        MATPLOTLIB_AVAILABLE = False
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ==========================================
# 1. MOTOR DE CLASSIFICAÇÃO COM INÉRCIA (V4)
# ==========================================
def classificar_segmento_v4(chroma_segmento, acorde_anterior=""):
    """
    Classifica um segmento de áudio com contexto temporal (inércia).
    Mantém estabilidade preferindo acordes anteriores se a confiança for similar.
    
    Args:
        chroma_segmento: Vetor de 12 notas (chroma)
        acorde_anterior: Acorde do segmento anterior (para inércia)
    
    Returns:
        Nome do acorde detectado
    """
    # 1. Gate e Normalização
    if np.sum(chroma_segmento) < 0.1:
        return ""
    
    chroma_norm = chroma_segmento / (np.max(chroma_segmento) + 1e-6)
    notas_nomes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    # 2. Definição de Templates (Apenas Tríades para estabilidade)
    tipos_acordes = {
        '':     {'idx': [0, 4, 7],     'bias': 0.15, 'required': None},  # Maior
        'm':    {'idx': [0, 3, 7],     'bias': 0.15, 'required': None},  # Menor
    }

    melhor_score = -float('inf')
    acorde_vencedor = "N/A"

    for i, root in enumerate(notas_nomes):
        for sufixo, dados in tipos_acordes.items():
            nome_atual = f"{root}{sufixo}"
            
            intervalos = dados['idx']
            bias = dados['bias']
            required_interval = dados['required']
            
            # Índices das notas do acorde
            indices_reais = [(i + interval) % 12 for interval in intervalos]
            
            # Validação de nota crítica (se configurada)
            if required_interval is not None:
                idx_critico = (i + required_interval) % 12
                if chroma_norm[idx_critico] < 0.25:
                    continue
            
            # Score baseado em energia útil vs ruído
            energia_util = np.sum(chroma_norm[indices_reais])
            mask = np.ones(12, dtype=bool)
            mask[indices_reais] = False
            energia_ruido = np.sum(chroma_norm[mask])
            
            score = energia_util - (0.6 * energia_ruido) + bias
            
            # ====================================================
            # INÉRCIA TEMPORAL: Bônus para manter acorde anterior
            # ====================================================
            if nome_atual == acorde_anterior:
                # Bônus massivo para estabilidade (evita flutuar)
                score += 0.5
            
            # (Opcional) Penalidade para trocar tríade simples por complexa
            if acorde_anterior and len(acorde_anterior) < len(nome_atual):
                score -= 0.1
            
            if score > melhor_score:
                melhor_score = score
                acorde_vencedor = nome_atual
    
    return acorde_vencedor


# ==========================================
# 2. BEAT TRACKING COM SÍNCRONIZAÇÃO
# ==========================================
def run_beat_tracking(y, sr, y_harmonic, y_percussive):
    """
    Executa beat tracking e sincroniza chroma com beats para detecção de acordes.
    Mais estável que onset detection para processamento com inércia.
    
    Args:
        y: Áudio original
        sr: Sample rate
        y_harmonic: Componente harmônica
        y_percussive: Componente percussiva
    
    Returns:
        Tupla (segmentos, tempo_BPM)
    """
    # 1. Detectar Batidas (mais robustas que onsets para acordes)
    tempo, beats = librosa.beat.beat_track(y=y_percussive, sr=sr)
    
    # 2. Processar Chroma (CQT otimizado)
    chroma = librosa.feature.chroma_cqt(
        y=y_harmonic, 
        sr=sr, 
        bins_per_octave=12,  # Otimizado para memória
        fmin=65
    )
    
    # 3. Sincronizar Chroma com Beats
    beats = librosa.util.fix_frames(beats, x_max=chroma.shape[1])
    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)
    
    # Libera memória de chroma original
    del chroma
    
    # 4. Gerar Lista de Segmentos com Inércia Temporal
    tempos = librosa.frames_to_time(beats, sr=sr)
    segmentos = []
    
    acorde_anterior = ""  # Estado para inércia
    
    for i in range(chroma_sync.shape[1]):
        # Passa o acorde anterior para manter contexto
        acorde = classificar_segmento_v4(chroma_sync[:, i], acorde_anterior)
        
        # Calcula duração até o próximo beat
        duracao = tempos[i+1] - tempos[i] if i+1 < len(tempos) else 0
        
        segmentos.append({
            'start': round(tempos[i], 2),
            'end': round(tempos[i+1] if i+1 < len(tempos) else tempos[i], 2),
            'label': acorde,
            'duracao': round(duracao, 2)
        })
        
        # Atualiza estado para próxima iteração (inércia)
        acorde_anterior = acorde
    
    return segmentos, tempo


# ==========================================
# 3. PROCESSAMENTO PRINCIPAL (Integrado)
# ==========================================
def processar_audio(audio_path: str, visualizar: bool = False) -> Dict:
    """
    Processa um arquivo de áudio com beat tracking e inércia temporal.
    OTIMIZADO para reduzir uso de memória.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização (apenas em dev)
    
    Returns:
        Dicionário com os acordes detectados e metadados
    """
    try:
        # Validação de tamanho de arquivo
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return {
                "sucesso": False,
                "erro": f"Arquivo muito grande ({file_size_mb:.1f}MB). Máximo: {MAX_FILE_SIZE_MB}MB",
                "arquivo": os.path.basename(audio_path)
            }
        
        # A. Carregar Áudio com resampling otimizado
        # 11025 Hz é suficiente para beat tracking e acordes
        y, sr = librosa.load(audio_path, sr=11025, mono=True)
        
        # Validação de duração (ANTES de deletar y)
        duracao_total = float(librosa.get_duration(y=y, sr=sr))
        if duracao_total > MAX_AUDIO_DURATION:
            return {
                "sucesso": False,
                "erro": f"Áudio muito longo ({duracao_total:.1f}s). Máximo: {MAX_AUDIO_DURATION}s",
                "arquivo": os.path.basename(audio_path)
            }

        # B. Separação Harmônica/Percussiva (HPSS)
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=3.0)
        
        # C. Beat Tracking com Síncronização
        timer_start = time.time()
        segmentos_brutos, tempo_bpm = run_beat_tracking(y, sr, y_harmonic, y_percussive)
        tempo_processamento = time.time() - timer_start
        
        # Libera memória
        del y, y_harmonic, y_percussive
        import gc
        gc.collect()
        
        # D. Consolidar Acordes (Agrupa mesmos acordes consecutivos)
        acordes_consolidados = []
        for segmento in segmentos_brutos:
            if not acordes_consolidados:
                # Primeiro segmento
                acordes_consolidados.append({
                    'acorde': segmento['label'],
                    'tempo_inicio': segmento['start'],
                    'duracao': segmento['duracao']
                })
            elif segmento['label'] == acordes_consolidados[-1]['acorde']:
                # Mesmo acorde - agrupa
                acordes_consolidados[-1]['duracao'] += segmento['duracao']
            else:
                # Novo acorde
                acordes_consolidados.append({
                    'acorde': segmento['label'],
                    'tempo_inicio': segmento['start'],
                    'duracao': segmento['duracao']
                })
        
        # Monta o resultado final
        resultado = {
            "sucesso": True,
            "arquivo": os.path.basename(audio_path),
            "duracao_total": round(duracao_total, 2),
            "taxa_amostragem": int(sr),
            "tempo_bpm": round(tempo_bpm, 1),
            "quantidade_acordes": len(acordes_consolidados),
            "tempo_processamento_ms": round(tempo_processamento * 1000, 1),
            "acordes": [{
                "acorde": a['acorde'],
                "tempo_inicio": a['tempo_inicio'],
                "duracao": a['duracao'],
                "confianca": 0.85  # Placeholder
            } for a in acordes_consolidados]
        }

        # ==========================================
        # E. VISUALIZAÇÃO (OPCIONAL)
        # ==========================================
        if visualizar and MATPLOTLIB_AVAILABLE:
            plt.figure(figsize=(14, 6))
            plt.title("Beat Tracking com Detecção de Acordes (Inércia Temporal)")
            plt.xlabel("Tempo (s)")
            plt.ylabel("Acorde")
            
            # Plot simples dos acordes
            for acorde_info in acordes_consolidados:
                plt.axvline(x=acorde_info['tempo_inicio'], color='gray', linestyle='--', alpha=0.3)
            
            plt.tight_layout()
            plt.show()

        return resultado

    except Exception as e:
        logger.error(f"Erro ao processar áudio: {e}", exc_info=True)
        return {
            "sucesso": False,
            "erro": str(e),
            "arquivo": os.path.basename(audio_path) if isinstance(audio_path, str) else "arquivo"
        }

# ==========================================
# 4. FUNÇÃO PARA RETORNAR JSON STRING
# ==========================================
def processar_audio_json(audio_path: str, visualizar: bool = False) -> str:
    """
    Processa um arquivo de áudio e retorna as cifras detectadas em formato JSON string.
    Usa beat tracking com inércia temporal para melhor estabilidade.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização
    
    Returns:
        String JSON com os acordes detectados
    """
    resultado = processar_audio(audio_path, visualizar)
    return json.dumps(resultado, indent=2, ensure_ascii=False)


# ==========================================
# 5. ÁREA DE TESTE
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
