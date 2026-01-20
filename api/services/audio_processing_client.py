"""
Cliente para processamento de áudio com detecção de acordes
Utiliza librosa para análise de chroma e onset detection
"""
import librosa
import numpy as np
from typing import Dict, List, Optional
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class ChordClassifier:
    """Classificador de acordes baseado em análise de chroma"""
    
    NOTAS_NOMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    @staticmethod
    def classificar_segmento(chroma_segmento: np.ndarray) -> str:
        """
        Analisa uma fatia de áudio (vetor de 12 notas) e decide qual o acorde.
        
        Args:
            chroma_segmento: Vetor de 12 elementos com energia de cada nota
            
        Returns:
            Nome do acorde detectado (ex: "C", "Cm", "Silêncio")
        """
        # Se o segmento for silêncio absoluto, retorna vazio
        if np.sum(chroma_segmento) < 0.05:
            return "Silêncio"

        # Normaliza para que o volume não afete a decisão, apenas a proporção das notas
        chroma_norm = chroma_segmento / (np.max(chroma_segmento) + 1e-6)

        melhor_score = -float('inf')
        acorde_vencedor = "N/A"

        for i, root in enumerate(ChordClassifier.NOTAS_NOMES):
            # Template MAIOR (Raiz + 4 + 7 semitons)
            mask_maj = np.zeros(12)
            mask_maj[[i, (i+4) % 12, (i+7) % 12]] = 1.0

            # Template MENOR (Raiz + 3 + 7 semitons)
            mask_min = np.zeros(12)
            mask_min[[i, (i+3) % 12, (i+7) % 12]] = 1.0

            # Teste Maior
            score_maj = np.sum(chroma_norm * mask_maj) - 0.6 * np.sum(chroma_norm * (1 - mask_maj))

            # Teste Menor
            score_min = np.sum(chroma_norm * mask_min) - 0.6 * np.sum(chroma_norm * (1 - mask_min))

            if score_maj > melhor_score:
                melhor_score = score_maj
                acorde_vencedor = root  # Maior

            if score_min > melhor_score:
                melhor_score = score_min
                acorde_vencedor = f"{root}m"  # Menor

        return acorde_vencedor


class AudioProcessingService:
    """
    Serviço de processamento de áudio com detecção de acordes
    """

    @staticmethod
    def processar_audio(file_path: str) -> Dict:
        """
        Processa arquivo de áudio e detecta acordes usando Onset Detection.
        
        Args:
            file_path: Caminho para o arquivo de áudio
            
        Returns:
            Dict com 'chords' (lista de acordes com timestamps) e 'success'
        """
        try:
            logger.info(f"Iniciando processamento: {file_path}")
            
            # A. Carregar Áudio
            y, sr = librosa.load(file_path, sr=None)
            duracao_total = librosa.get_duration(y=y, sr=sr)
            
            logger.info(f"Taxa de amostragem: {sr}Hz, Duração: {duracao_total:.2f}s")
            
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
            
            # E. Correção de Bordas
            onset_frames = librosa.util.fix_frames(onset_frames, x_max=chroma.shape[1])
            
            logger.info(f"{len(onset_frames)} onsets detectados")
            
            # F. Sincronização
            chroma_sync = librosa.util.sync(chroma, onset_frames, aggregate=np.median)
            
            # G. Converter frames para tempo
            tempos_limite = librosa.frames_to_time(onset_frames, sr=sr)
            
            # H. Normaliza
            chroma_sync = librosa.util.normalize(chroma_sync, axis=0)
            
            # ==========================================
            # Geração da Timeline de Acordes
            # ==========================================
            acordes_timeline = []
            acorde_anterior = ""
            inicio_tempo_segmento = tempos_limite[0]
            
            for i in range(chroma_sync.shape[1]):
                coluna_atual = chroma_sync[:, i]
                acorde_atual = ChordClassifier.classificar_segmento(coluna_atual)
                
                if acorde_atual != acorde_anterior:
                    if acorde_anterior != "":
                        acordes_timeline.append({
                            'acorde': acorde_anterior,
                            'tempo_inicio': round(inicio_tempo_segmento, 2),
                            'tempo_fim': round(tempos_limite[i], 2),
                            'duracao': round(tempos_limite[i] - inicio_tempo_segmento, 2)
                        })
                    
                    acorde_anterior = acorde_atual
                    inicio_tempo_segmento = tempos_limite[i]
            
            # Registra o último acorde
            if acorde_anterior != "":
                acordes_timeline.append({
                    'acorde': acorde_anterior,
                    'tempo_inicio': round(inicio_tempo_segmento, 2),
                    'tempo_fim': round(tempos_limite[-1], 2),
                    'duracao': round(tempos_limite[-1] - inicio_tempo_segmento, 2)
                })
            
            logger.info(f"{len(acordes_timeline)} acordes detectados")
            
            return {
                'success': True,
                'chords': acordes_timeline,
                'metadata': {
                    'duracao_total': round(duracao_total, 2),
                    'taxa_amostragem': sr,
                    'total_acordes': len(acordes_timeline),
                    'onsets_detectados': len(onset_frames)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chords': []
            }

    @staticmethod
    def processar_audio_url(file_url: str) -> Dict:
        """
        Processa arquivo de áudio a partir de uma URL (ex: Supabase)
        
        Args:
            file_url: URL do arquivo
            
        Returns:
            Dict com resultado do processamento
        """
        import requests
        try:
            logger.info(f"Baixando áudio: {file_url}")
            
            # Baixa o arquivo para um temp file
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()
            
            # Salva em arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            try:
                # Processa o arquivo
                result = AudioProcessingService.processar_audio(tmp_path)
                return result
            finally:
                # Remove arquivo temporário
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Erro ao processar URL: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chords': []
            }


# Atalho para uso
def processar_audio(file_path: str) -> Dict:
    """Atalho para processamento de áudio"""
    return AudioProcessingService.processar_audio(file_path)


def processar_audio_url(file_url: str) -> Dict:
    """Atalho para processamento de URL"""
    return AudioProcessingService.processar_audio_url(file_url)
