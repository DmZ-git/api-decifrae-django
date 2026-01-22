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
# 2. ONSET DETECTION COM SÍNCRONIZAÇÃO
# ==========================================
def run_onset_detection(y, sr, y_harmonic, y_percussive):
    """
    Executa onset detection e sincroniza chroma com onsets para detecção de acordes.
    Mais responsivo a mudanças que beat tracking.
    
    Args:
        y: Áudio original
        sr: Sample rate
        y_harmonic: Componente harmônica
        y_percussive: Componente percussiva
    
    Returns:
        Tupla (segmentos, dummy_tempo)
    """
    # 1. Detectar Onsets
    onsets = librosa.onset.onset_detect(
        y=y_percussive, 
        sr=sr, 
        backtrack=True, 
        wait=10, 
        units='frames'
    )
    
    # 2. Processar Chroma
    chroma = librosa.feature.chroma_cqt(
        y=y_harmonic, 
        sr=sr, 
        bins_per_octave=12,
        fmin=65
    )
    
    # 3. Sincronizar Chroma com Onsets
    onsets = librosa.util.fix_frames(onsets, x_max=chroma.shape[1])
    chroma_sync = librosa.util.sync(chroma, onsets, aggregate=np.median)
    
    # Libera memória
    del chroma
    
    # 4. Gerar Lista de Segmentos com Inércia
    tempos = librosa.frames_to_time(onsets, sr=sr)
    segmentos = []
    
    acorde_anterior = ""
    
    for i in range(chroma_sync.shape[1]):
        acorde = classificar_segmento_v4(chroma_sync[:, i], acorde_anterior)
        
        duracao = tempos[i+1] - tempos[i] if i+1 < len(tempos) else 0
        
        segmentos.append({
            'start': round(tempos[i], 2),
            'end': round(tempos[i+1] if i+1 < len(tempos) else tempos[i], 2),
            'label': acorde,
            'duracao': round(duracao, 2)
        })
        
        acorde_anterior = acorde
    
    return segmentos, 0  # dummy tempo


# ==========================================
# 3. AGGLOMERATIVE CLUSTERING
# ==========================================
def run_agglomerative(y, sr, y_harmonic):
    """
    Usa agglomerative clustering para segmentação baseada em similaridade de chroma.
    Menos sensível a ruído que beat tracking.
    
    Args:
        y: Áudio original
        sr: Sample rate
        y_harmonic: Componente harmônica
    
    Returns:
        Tupla (segmentos, dummy_tempo)
    """
    # 1. Processar Chroma
    chroma = librosa.feature.chroma_cqt(
        y=y_harmonic, 
        sr=sr, 
        bins_per_octave=12,
        fmin=65
    )
    
    # Stack memory para contexto temporal
    chroma_stack = librosa.feature.stack_memory(chroma, n_steps=3)
    
    # Estimar número de clusters (K)
    duracao = librosa.get_duration(y=y, sr=sr)
    k = max(2, int(duracao / 1.5))
    
    # 2. Segmentar
    bounds = librosa.segment.agglomerative(chroma_stack, k)
    bounds = librosa.util.fix_frames(bounds, x_max=chroma.shape[1])
    tempos = librosa.frames_to_time(bounds, sr=sr)
    
    # 3. Gerar Lista de Segmentos
    segmentos = []
    acorde_anterior = ""
    
    for i in range(len(bounds)-1):
        # Pega a média do chroma no bloco
        bloco = np.mean(chroma[:, bounds[i]:bounds[i+1]], axis=1)
        
        acorde = classificar_segmento_v4(bloco, acorde_anterior)
        
        duracao_seg = tempos[i+1] - tempos[i] if i+1 < len(tempos) else 0
        
        segmentos.append({
            'start': round(tempos[i], 2),
            'end': round(tempos[i+1] if i+1 < len(tempos) else tempos[i], 2),
            'label': acorde,
            'duracao': round(duracao_seg, 2)
        })
        
        acorde_anterior = acorde
    
    del chroma
    
    return segmentos, 0  # dummy tempo


# ==========================================
# 2. BEAT TRACKING COM SÍNCRONIZAÇÃO (Reformatado)
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
# 4. COMPARAÇÃO DOS TRÊS ALGORITMOS
# ==========================================
def comparar_metodos(audio_path: str) -> Dict:
    """
    Compara os três algoritmos (Beat Tracking, Onset Detection, Agglomerative)
    com visualização Gantt.
    
    Args:
        audio_path: Caminho para o arquivo de áudio
    
    Returns:
        Dicionário com resultados e tempos dos 3 métodos
    """
    try:
        print(f"\n{'='*60}")
        print(f"Comparando algoritmos para: {os.path.basename(audio_path)}")
        print(f"{'='*60}")
        
        # Carregar áudio
        y, sr = librosa.load(audio_path, sr=11025, mono=True)
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=3.0)
        
        resultados = {}
        times = {}
        
        # --- 1. Beat Tracking ---
        print("\n⏱️  Executando Beat Tracking...")
        start = time.time()
        resultados['Beat'], _ = run_beat_tracking(y, sr, y_harmonic, y_percussive)
        times['Beat'] = time.time() - start
        
        # --- 2. Onset Detection ---
        print("⏱️  Executando Onset Detection...")
        start = time.time()
        resultados['Onset'], _ = run_onset_detection(y, sr, y_harmonic, y_percussive)
        times['Onset'] = time.time() - start
        
        # --- 3. Agglomerative ---
        print("⏱️  Executando Agglomerative Clustering...")
        start = time.time()
        resultados['Agglom'], _ = run_agglomerative(y, sr, y_harmonic)
        times['Agglom'] = time.time() - start
        
        # Libera memória
        del y, y_harmonic, y_percussive
        import gc
        gc.collect()
        
        # --- TABELA DE RESULTADOS ---
        print(f"\n{'MÉTODO':<20} | {'TEMPO(s)':<12} | {'SEGMENTOS':<12}")
        print("-" * 48)
        for metodo in ['Beat', 'Onset', 'Agglom']:
            print(f"{metodo:<20} | {times[metodo]:>10.4f}s | {len(resultados[metodo]):>10}")
        
        # --- VISUALIZAÇÃO GANTT (se matplotlib disponível) ---
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            has_matplotlib = True
        except ImportError:
            has_matplotlib = False
        
        if has_matplotlib:
            print("\n📊 Gerando gráfico de comparação...")
            
            fig, ax = plt.subplots(figsize=(16, 7))
            cores_base = plt.cm.tab20.colors
            mapa_cores = {}
            y_positions = {'Beat': 3, 'Onset': 2, 'Agglom': 1}
            height = 0.7
            idx_cor = 0
            
            for metodo, segments in resultados.items():
                # Consolidar acordes consecutivos iguais
                merged = []
                if segments:
                    curr = segments[0].copy()
                    for next_seg in segments[1:]:
                        if next_seg['label'] == curr['label']:
                            curr['end'] = next_seg['end']
                        else:
                            merged.append(curr)
                            curr = next_seg.copy()
                    merged.append(curr)
                
                # Plot
                for seg in merged:
                    label = seg['label']
                    if label not in mapa_cores:
                        mapa_cores[label] = cores_base[idx_cor % len(cores_base)]
                        idx_cor += 1
                    
                    start_t = seg['start']
                    duration = seg['end'] - start_t
                    rect = mpatches.Rectangle(
                        (start_t, y_positions[metodo] - height/2),
                        duration, height,
                        color=mapa_cores[label], 
                        ec='white', 
                        linewidth=1
                    )
                    ax.add_patch(rect)
                    
                    # Adicionar label se espaço suficiente
                    if duration > 0.5:
                        ax.text(
                            start_t + duration/2, 
                            y_positions[metodo], 
                            label,
                            ha='center', 
                            va='center', 
                            color='white', 
                            fontweight='bold', 
                            fontsize=9
                        )
            
            ax.set_yticks([1, 2, 3])
            ax.set_yticklabels(['Agglomerative', 'Onset', 'Beat Tracking'], fontsize=11)
            ax.set_ylim(0.2, 3.8)
            ax.set_xlim(0, max([seg['end'] for segs in resultados.values() for seg in segs]) or 10)
            ax.set_xlabel("Tempo (segundos)", fontsize=11, fontweight='bold')
            ax.set_title(f"Comparação de Algoritmos com Inércia Temporal\n{os.path.basename(audio_path)}", 
                        fontsize=13, fontweight='bold', pad=20)
            ax.grid(axis='x', linestyle='--', alpha=0.4)
            ax.set_axisbelow(True)
            plt.tight_layout()
            plt.show()
            
            print("✅ Gráfico exibido!")
        
        return {
            'resultados': resultados,
            'tempos': times,
            'melhor_metodo': min(times, key=times.get)
        }
        
    except Exception as e:
        logger.error(f"Erro ao comparar métodos: {e}", exc_info=True)
        return {
            'erro': str(e),
            'resultados': {},
            'tempos': {}
        }


# ==========================================
# 5. PROCESSAMENTO PRINCIPAL (Com Opção de Algoritmo)
# ==========================================
def processar_audio(audio_path: str, visualizar: bool = False, metodo: str = 'beat') -> Dict:
    """
    Processa um arquivo de áudio com algoritmo selecionável.
    OTIMIZADO para reduzir uso de memória.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização (apenas em dev)
        metodo: Algoritmo a usar ('beat', 'onset', 'agglom')
    
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
        
        # A. Carregar Áudio
        y, sr = librosa.load(audio_path, sr=11025, mono=True)
        
        # Validação de duração (ANTES de deletar y)
        duracao_total = float(librosa.get_duration(y=y, sr=sr))
        if duracao_total > MAX_AUDIO_DURATION:
            return {
                "sucesso": False,
                "erro": f"Áudio muito longo ({duracao_total:.1f}s). Máximo: {MAX_AUDIO_DURATION}s",
                "arquivo": os.path.basename(audio_path)
            }

        # B. Separação Harmônica/Percussiva
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=3.0)
        
        # C. Escolher algoritmo
        timer_start = time.time()
        if metodo.lower() == 'onset':
            segmentos_brutos, tempo_bpm = run_onset_detection(y, sr, y_harmonic, y_percussive)
            nome_metodo = "Onset Detection"
        elif metodo.lower() == 'agglom':
            segmentos_brutos, tempo_bpm = run_agglomerative(y, sr, y_harmonic)
            nome_metodo = "Agglomerative Clustering"
        else:  # default: beat tracking
            segmentos_brutos, tempo_bpm = run_beat_tracking(y, sr, y_harmonic, y_percussive)
            nome_metodo = "Beat Tracking"
        
        tempo_processamento = time.time() - timer_start
        
        # Libera memória
        del y, y_harmonic, y_percussive
        import gc
        gc.collect()
        
        # D. Consolidar Acordes (Agrupa mesmos acordes consecutivos)
        acordes_consolidados = []
        for segmento in segmentos_brutos:
            if not acordes_consolidados:
                acordes_consolidados.append({
                    'acorde': segmento['label'],
                    'tempo_inicio': segmento['start'],
                    'duracao': segmento['duracao']
                })
            elif segmento['label'] == acordes_consolidados[-1]['acorde']:
                acordes_consolidados[-1]['duracao'] += segmento['duracao']
            else:
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
            "metodo_usado": nome_metodo,
            "acordes": [{
                "acorde": a['acorde'],
                "tempo_inicio": a['tempo_inicio'],
                "duracao": a['duracao'],
                "confianca": 0.85
            } for a in acordes_consolidados]
        }

        # E. VISUALIZAÇÃO (OPCIONAL)
        if visualizar:
            try:
                import matplotlib.pyplot as plt
                has_matplotlib = True
            except ImportError:
                has_matplotlib = False
            
            if has_matplotlib:
                plt.figure(figsize=(14, 6))
                plt.title(f"Detecção de Acordes - {nome_metodo}")
                plt.xlabel("Tempo (s)")
                plt.ylabel("Acorde")
                
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
# 6. FUNÇÃO PARA RETORNAR JSON STRING
# ==========================================
def processar_audio_json(audio_path: str, visualizar: bool = False, metodo: str = 'beat') -> str:
    """
    Processa um arquivo de áudio e retorna as cifras detectadas em formato JSON string.
    Usa algoritmo selecionável com inércia temporal para estabilidade.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (.mp3, .wav, etc)
        visualizar: Se True, mostra gráfico de visualização
        metodo: 'beat', 'onset' ou 'agglom'
    
    Returns:
        String JSON com os acordes detectados
    """
    resultado = processar_audio(audio_path, visualizar, metodo)
    return json.dumps(resultado, indent=2, ensure_ascii=False)


# ==========================================
# 7. ÁREA DE TESTE
# ==========================================
if __name__ == "__main__":
    # Exemplo de uso
    arquivo_teste = 'caminho/para/seu/arquivo.mp3'
    
    # Opção 1: Processar com algoritmo padrão (beat tracking)
    resultado_dict = processar_audio(arquivo_teste, visualizar=False, metodo='beat')
    print("Resultado com Beat Tracking:")
    print(resultado_dict)
    print("\n" + "="*50 + "\n")
    
    # Opção 2: Comparar os 3 algoritmos
    # comparar_metodos(arquivo_teste)
    
    # Opção 3: Retorna JSON string
    resultado_json = processar_audio_json(arquivo_teste, visualizar=False, metodo='beat')
    print("Resultado como JSON:")
    print(resultado_json)
