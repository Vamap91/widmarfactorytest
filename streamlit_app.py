import streamlit as st
import requests
import json
import base64
import time
import io
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuração da página
st.set_page_config(
    page_title="Sistema de Geração de Vídeos - Migração Real",
    page_icon="🎬",
    layout="wide"
)

@dataclass
class VideoGenerationConfig:
    """Configurações do sistema de geração de vídeos"""
    videos_per_day: int = 200
    languages: List[str] = None
    avg_chars_per_video: int = 1000
    current_provider: str = "elevenlabs"
    target_provider: str = "google_cloud"
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en", "es", "fr"]

class GoogleCloudService:
    """Serviço real do Google Cloud TTS + Translate"""
    
    def __init__(self):
        # Obter credenciais do Streamlit Secrets
        self.project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT", "demo-project")
        self.api_key = st.secrets.get("GOOGLE_CLOUD_API_KEY", None)
        self.service_account_info = st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS", None)
        
        # URLs das APIs
        self.tts_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        self.translate_url = "https://translation.googleapis.com/language/translate/v2"
        
        # Cache para tokens de acesso
        self._access_token = None
        self._token_expires = 0
    
    def _get_access_token(self) -> str:
        """Obtém token de acesso usando Service Account"""
        if self.service_account_info:
            try:
                import jwt
                import time
                
                # Parse das credenciais JSON
                if isinstance(self.service_account_info, str):
                    creds = json.loads(self.service_account_info)
                else:
                    creds = self.service_account_info
                
                # Criar JWT para autenticação
                now = int(time.time())
                payload = {
                    "iss": creds["client_email"],
                    "scope": "https://www.googleapis.com/auth/cloud-platform",
                    "aud": "https://oauth2.googleapis.com/token",
                    "iat": now,
                    "exp": now + 3600
                }
                
                # Assinar JWT
                token = jwt.encode(payload, creds["private_key"], algorithm="RS256")
                
                # Trocar JWT por access token
                response = requests.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": token
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["access_token"]
                    
            except Exception as e:
                st.error(f"Erro na autenticação: {e}")
        
        # Fallback para API Key se disponível
        return self.api_key
    
    def translate_text(self, text: str, target_language: str, source_language: str = "pt") -> Dict:
        """Traduz texto usando Google Cloud Translation"""
        
        # Verificar se tem credenciais
        if not self.api_key and not self.service_account_info:
            # Modo simulação se não tem credenciais
            return self._simulate_translation(text, target_language)
        
        try:
            headers = {}
            params = {}
            
            # Configurar autenticação
            if self.service_account_info:
                token = self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
            elif self.api_key:
                params["key"] = self.api_key
            
            # Fazer chamada para API
            payload = {
                "q": text,
                "target": target_language,
                "source": source_language,
                "format": "text"
            }
            
            response = requests.post(
                self.translate_url,
                headers=headers,
                params=params,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result["data"]["translations"][0]["translatedText"]
                
                return {
                    "success": True,
                    "translated_text": translated_text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "confidence": 0.98,
                    "characters": len(text),
                    "cost_estimate": self._calculate_translate_cost(len(text))
                }
            else:
                st.error(f"Erro na tradução: {response.status_code} - {response.text}")
                return self._simulate_translation(text, target_language)
                
        except Exception as e:
            st.error(f"Erro na chamada de tradução: {e}")
            return self._simulate_translation(text, target_language)
    
    def synthesize_speech(self, text: str, language_code: str = "pt-BR") -> Dict:
        """Sintetiza fala usando Google Cloud TTS"""
        
        # Verificar se tem credenciais
        if not self.api_key and not self.service_account_info:
            # Modo simulação se não tem credenciais
            return self._simulate_tts(text, language_code)
        
        try:
            headers = {"Content-Type": "application/json"}
            params = {}
            
            # Configurar autenticação
            if self.service_account_info:
                token = self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
            elif self.api_key:
                params["key"] = self.api_key
            
            # Configurar voz baseada no idioma
            voice_name = self._get_voice_name(language_code)
            
            payload = {
                "input": {"text": text},
                "voice": {
                    "languageCode": language_code,
                    "name": voice_name,
                    "ssmlGender": "NEUTRAL"
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": 1.0,
                    "pitch": 0.0
                }
            }
            
            response = requests.post(
                self.tts_url,
                headers=headers,
                params=params,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_content = result["audioContent"]
                
                return {
                    "success": True,
                    "audio_content": audio_content,
                    "duration_seconds": len(text) * 0.05,  # Estimativa
                    "characters_processed": len(text),
                    "language": language_code,
                    "voice": voice_name,
                    "cost_estimate": self._calculate_tts_cost(len(text))
                }
            else:
                st.error(f"Erro no TTS: {response.status_code} - {response.text}")
                return self._simulate_tts(text, language_code)
                
        except Exception as e:
            st.error(f"Erro na chamada de TTS: {e}")
            return self._simulate_tts(text, language_code)
    
    def _get_voice_name(self, language_code: str) -> str:
        """Obtém nome da voz baseado no idioma"""
        voice_map = {
            "pt-BR": "pt-BR-Standard-A",
            "en-US": "en-US-Standard-C",
            "es-ES": "es-ES-Standard-A",
            "fr-FR": "fr-FR-Standard-A",
            "de-DE": "de-DE-Standard-A",
            "it-IT": "it-IT-Standard-A"
        }
        return voice_map.get(language_code, f"{language_code}-Standard-A")
    
    def _calculate_translate_cost(self, characters: int) -> float:
        """Calcula custo da tradução (Google Translate)"""
        # Preço: $20 por milhão de caracteres
        return (characters / 1_000_000) * 20 * 5.2  # Conversão para BRL
    
    def _calculate_tts_cost(self, characters: int) -> float:
        """Calcula custo do TTS (Google Cloud TTS)"""
        # Preço: $4 por milhão de caracteres
        return (characters / 1_000_000) * 4 * 5.2  # Conversão para BRL
    
    def _simulate_translation(self, text: str, target_language: str) -> Dict:
        """Simula tradução quando não há credenciais"""
        translations = {
            "en": f"[EN] {text}",
            "es": f"[ES] {text}",
            "fr": f"[FR] {text}",
            "de": f"[DE] {text}",
            "it": f"[IT] {text}"
        }
        
        return {
            "success": True,
            "translated_text": translations.get(target_language, f"[{target_language.upper()}] {text}"),
            "source_language": "pt",
            "target_language": target_language,
            "confidence": 0.95,
            "characters": len(text),
            "cost_estimate": self._calculate_translate_cost(len(text)),
            "simulated": True
        }
    
    def _simulate_tts(self, text: str, language_code: str) -> Dict:
        """Simula TTS quando não há credenciais"""
        # Criar áudio dummy em base64
        dummy_audio = f"AUDIO_DATA_FOR_{language_code}_{len(text)}_CHARS"
        audio_b64 = base64.b64encode(dummy_audio.encode()).decode()
        
        return {
            "success": True,
            "audio_content": audio_b64,
            "duration_seconds": len(text) * 0.05,
            "characters_processed": len(text),
            "language": language_code,
            "voice": self._get_voice_name(language_code),
            "cost_estimate": self._calculate_tts_cost(len(text)),
            "simulated": True
        }

class ElevenLabsService:
    """Serviço do ElevenLabs para comparação"""
    
    def __init__(self):
        self.api_key = st.secrets.get("ELEVENLABS_API_KEY", None)
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def synthesize_speech(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Dict:
        """Sintetiza fala usando ElevenLabs"""
        
        if not self.api_key:
            return self._simulate_elevenlabs_tts(text)
        
        try:
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                audio_content = base64.b64encode(response.content).decode()
                
                return {
                    "success": True,
                    "audio_content": audio_content,
                    "duration_seconds": len(text) * 0.06,
                    "characters_processed": len(text),
                    "voice_id": voice_id,
                    "cost_estimate": self._calculate_elevenlabs_cost(len(text))
                }
            else:
                return self._simulate_elevenlabs_tts(text)
                
        except Exception as e:
            st.error(f"Erro no ElevenLabs: {e}")
            return self._simulate_elevenlabs_tts(text)
    
    def _calculate_elevenlabs_cost(self, characters: int) -> float:
        """Calcula custo do ElevenLabs"""
        # Preço: $0.30 por 1000 caracteres (plano Creator)
        return (characters / 1000) * 0.30 * 5.2  # Conversão para BRL
    
    def _simulate_elevenlabs_tts(self, text: str) -> Dict:
        """Simula ElevenLabs quando não há credenciais"""
        dummy_audio = f"ELEVENLABS_AUDIO_{len(text)}_CHARS"
        audio_b64 = base64.b64encode(dummy_audio.encode()).decode()
        
        return {
            "success": True,
            "audio_content": audio_b64,
            "duration_seconds": len(text) * 0.06,
            "characters_processed": len(text),
            "voice_id": "demo_voice",
            "cost_estimate": self._calculate_elevenlabs_cost(len(text)),
            "simulated": True
        }

class CostAnalyzer:
    """Analisador de custos para diferentes provedores"""
    
    def __init__(self):
        self.providers = {
            "elevenlabs": {
                "name": "ElevenLabs + OpenAI Translate",
                "tts_cost_per_char": 0.30 / 1000 * 5.2,  # R$ por caractere
                "translate_cost_per_char": 120 / (30 * 200 * 3 * 1000) * 5.2,  # Estimativa
                "quality_score": 95,
                "latency_ms": 2000
            },
            "google_cloud": {
                "name": "Google Cloud TTS + Translate",
                "tts_cost_per_char": 4 / 1_000_000 * 5.2,  # $4 por milhão de chars
                "translate_cost_per_char": 20 / 1_000_000 * 5.2,  # $20 por milhão de chars
                "quality_score": 80,
                "latency_ms": 800
            },
            "openai": {
                "name": "OpenAI TTS + Translate",
                "tts_cost_per_char": 15 / 1_000_000 * 5.2,  # $15 por milhão de chars
                "translate_cost_per_char": 120 / (30 * 200 * 3 * 1000) * 5.2,  # Estimativa
                "quality_score": 85,
                "latency_ms": 1500
            }
        }
    
    def calculate_monthly_costs(self, config: VideoGenerationConfig) -> Dict:
        """Calcula custos mensais baseado na configuração"""
        monthly_videos = config.videos_per_day * 30
        total_chars = monthly_videos * len(config.languages) * config.avg_chars_per_video
        
        results = {}
        
        for provider_id, provider_config in self.providers.items():
            tts_cost = total_chars * provider_config["tts_cost_per_char"]
            translate_cost = total_chars * provider_config["translate_cost_per_char"]
            total_cost = tts_cost + translate_cost
            
            results[provider_id] = {
                "name": provider_config["name"],
                "tts_cost": tts_cost,
                "translate_cost": translate_cost,
                "total_cost": total_cost,
                "cost_per_video": total_cost / monthly_videos,
                "quality_score": provider_config["quality_score"],
                "latency_ms": provider_config["latency_ms"]
            }
        
        return results

class VideoProcessor:
    """Processador principal de vídeos multilíngues"""
    
    def __init__(self):
        self.google_service = GoogleCloudService()
        self.elevenlabs_service = ElevenLabsService()
        self.cost_analyzer = CostAnalyzer()
    
    def process_multilingual_video(self, 
                                 original_text: str, 
                                 target_languages: List[str],
                                 provider: str = "google_cloud") -> Dict:
        """Processa um vídeo para múltiplos idiomas"""
        
        results = {
            "original_text": original_text,
            "provider": provider,
            "languages": [],
            "total_cost": 0,
            "total_time": 0,
            "success_count": 0
        }
        
        start_time = time.time()
        
        for lang in target_languages:
            lang_result = self._process_single_language(original_text, lang, provider)
            results["languages"].append(lang_result)
            
            if lang_result["success"]:
                results["success_count"] += 1
                results["total_cost"] += lang_result["total_cost"]
        
        results["total_time"] = time.time() - start_time
        
        return results
    
    def _process_single_language(self, text: str, target_lang: str, provider: str) -> Dict:
        """Processa um único idioma"""
        
        start_time = time.time()
        
        # Mapear códigos de idioma
        lang_codes = {
            "en": "en-US",
            "es": "es-ES", 
            "fr": "fr-FR",
            "de": "de-DE",
            "it": "it-IT",
            "pt": "pt-BR"
        }
        
        tts_lang_code = lang_codes.get(target_lang, f"{target_lang}-{target_lang.upper()}")
        
        try:
            # 1. Traduzir texto
            if target_lang != "pt":
                translation_result = self.google_service.translate_text(text, target_lang)
                if not translation_result["success"]:
                    return {"success": False, "error": "Translation failed", "language": target_lang}
                
                translated_text = translation_result["translated_text"]
                translate_cost = translation_result["cost_estimate"]
            else:
                translated_text = text
                translate_cost = 0
            
            # 2. Gerar áudio
            if provider == "google_cloud":
                tts_result = self.google_service.synthesize_speech(translated_text, tts_lang_code)
            elif provider == "elevenlabs":
                tts_result = self.elevenlabs_service.synthesize_speech(translated_text)
            else:
                return {"success": False, "error": f"Provider {provider} not supported", "language": target_lang}
            
            if not tts_result["success"]:
                return {"success": False, "error": "TTS failed", "language": target_lang}
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "language": target_lang,
                "original_text": text,
                "translated_text": translated_text,
                "audio_duration": tts_result["duration_seconds"],
                "characters": len(translated_text),
                "translate_cost": translate_cost,
                "tts_cost": tts_result["cost_estimate"],
                "total_cost": translate_cost + tts_result["cost_estimate"],
                "processing_time": processing_time,
                "audio_preview": tts_result["audio_content"][:100] + "...",
                "simulated": tts_result.get("simulated", False)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "language": target_lang,
                "processing_time": time.time() - start_time
            }

def main():
    st.title("🎬 Sistema de Geração de Vídeos - Migração Real")
    st.markdown("**POC Funcional:** ElevenLabs → Google Cloud TTS + Translate")
    
    # Verificar status das credenciais
    with st.sidebar:
        st.header("🔐 Status das APIs")
        
        # Google Cloud
        google_configured = bool(st.secrets.get("GOOGLE_CLOUD_API_KEY") or st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS"))
        st.write("**Google Cloud:**", "✅ Configurado" if google_configured else "❌ Não configurado")
        
        # ElevenLabs
        elevenlabs_configured = bool(st.secrets.get("ELEVENLABS_API_KEY"))
        st.write("**ElevenLabs:**", "✅ Configurado" if elevenlabs_configured else "❌ Não configurado")
        
        if not google_configured and not elevenlabs_configured:
            st.warning("⚠️ Executando em modo simulação")
            st.info("Configure as APIs em Settings > Secrets")
        
        st.markdown("---")
        
        # Configurações do sistema
        st.header("⚙️ Configurações")
        videos_per_day = st.slider("Vídeos/dia", 50, 500, 200)
        avg_chars = st.slider("Caracteres/vídeo", 500, 2000, 1000)
        
        languages = st.multiselect(
            "Idiomas alvo",
            ["en", "es", "fr", "de", "it"],
            default=["en", "es"]
        )
    
    # Criar configuração
    config = VideoGenerationConfig(
        videos_per_day=videos_per_day,
        languages=languages,
        avg_chars_per_video=avg_chars
    )
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise de Custos", "🔄 Teste Real", "📈 Comparativo", "🔧 Implementação"])
    
    # Tab 1: Análise de Custos
    with tab1:
        st.header("Análise de Custos - Dados Reais")
        
        cost_analyzer = CostAnalyzer()
        cost_results = cost_analyzer.calculate_monthly_costs(config)
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        
        current_cost = cost_results["elevenlabs"]["total_cost"]
        google_cost = cost_results["google_cloud"]["total_cost"]
        openai_cost = cost_results["openai"]["total_cost"]
        
        with col1:
            st.metric(
                "💰 ElevenLabs (Atual)",
                f"R$ {current_cost:,.2f}/mês",
                f"R$ {cost_results['elevenlabs']['cost_per_video']:.2f}/vídeo"
            )
        
        with col2:
            savings = current_cost - google_cost
            st.metric(
                "🎯 Google Cloud (Meta)",
                f"R$ {google_cost:,.2f}/mês", 
                f"-R$ {savings:,.2f} ({(savings/current_cost*100):.1f}%)"
            )
        
        with col3:
            savings_openai = current_cost - openai_cost
            st.metric(
                "🔄 OpenAI (Alternativa)",
                f"R$ {openai_cost:,.2f}/mês",
                f"-R$ {savings_openai:,.2f} ({(savings_openai/current_cost*100):.1f}%)"
            )
        
        # Gráfico de comparação
        st.subheader("Comparação Detalhada")
        
        df_comparison = pd.DataFrame([
            {
                "Provedor": result["name"],
                "Custo Total": result["total_cost"],
                "TTS": result["tts_cost"],
                "Tradução": result["translate_cost"],
                "Qualidade": result["quality_score"],
                "Latência (ms)": result["latency_ms"]
            }
            for result in cost_results.values()
        ])
        
        # Gráfico de barras empilhadas
        fig = px.bar(
            df_comparison,
            x="Provedor",
            y=["TTS", "Tradução"],
            title="Breakdown de Custos por Provedor",
            color_discrete_map={"TTS": "#FF6B6B", "Tradução": "#4ECDC4"}
        )
        fig.update_layout(yaxis_title="Custo Mensal (R$)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela completa
        st.dataframe(df_comparison, use_container_width=True)
    
    # Tab 2: Teste Real
    with tab2:
        st.header("Teste de Processamento Real")
        
        # Input do usuário
        sample_text = st.text_area(
            "Texto para processamento:",
            value="Bem-vindos ao nosso canal! Hoje vamos aprender sobre inteligência artificial e como ela está transformando o mundo dos negócios.",
            height=100
        )
        
        provider_choice = st.selectbox(
            "Provedor para teste:",
            ["google_cloud", "elevenlabs"],
            format_func=lambda x: "Google Cloud TTS" if x == "google_cloud" else "ElevenLabs"
        )
        
        if st.button("🚀 Processar Vídeo Multilíngue", type="primary"):
            if sample_text and languages:
                processor = VideoProcessor()
                
                with st.spinner(f"Processando com {provider_choice}..."):
                    results = processor.process_multilingual_video(
                        sample_text, 
                        languages, 
                        provider_choice
                    )
                
                # Resultados
                st.success(f"✅ Processamento concluído em {results['total_time']:.2f}s")
                
                # Métricas gerais
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Idiomas", f"{results['success_count']}/{len(languages)}")
                with col2:
                    st.metric("Custo Total", f"R$ {results['total_cost']:.4f}")
                with col3:
                    st.metric("Tempo", f"{results['total_time']:.2f}s")
                with col4:
                    avg_time = results['total_time'] / len(languages) if languages else 0
                    st.metric("Tempo/Idioma", f"{avg_time:.2f}s")
                
                # Detalhes por idioma
                st.subheader("Resultados por Idioma")
                
                for lang_result in results["languages"]:
                    if lang_result["success"]:
                        with st.expander(f"🌐 {lang_result['language'].upper()} - ✅ Sucesso"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write("**Texto Original:**")
                                st.write(lang_result["original_text"])
                                
                                st.write("**Texto Traduzido:**")
                                st.write(lang_result["translated_text"])
                                
                                if lang_result.get("simulated"):
                                    st.info("ℹ️ Resultado simulado (sem credenciais API)")
                            
                            with col2:
                                st.metric("Caracteres", lang_result["characters"])
                                st.metric("Duração", f"{lang_result['audio_duration']:.1f}s")
                                st.metric("Custo TTS", f"R$ {lang_result['tts_cost']:.4f}")
                                st.metric("Custo Tradução", f"R$ {lang_result['translate_cost']:.4f}")
                                st.metric("Custo Total", f"R$ {lang_result['total_cost']:.4f}")
                                st.metric("Tempo", f"{lang_result['processing_time']:.2f}s")
                    else:
                        with st.expander(f"🌐 {lang_result['language'].upper()} - ❌ Erro"):
                            st.error(f"Erro: {lang_result['error']}")
    
    # Tab 3: Comparativo Avançado
    with tab3:
        st.header("Análise Comparativa Avançada")
        
        # Simular processamento para comparação
        if st.button("📊 Executar Análise Comparativa"):
            processor = VideoProcessor()
            test_text = "Este é um teste de comparação entre diferentes provedores de TTS e tradução."
            test_languages = ["en", "es"]
            
            results_comparison = {}
            
            # Testar cada provedor
            for provider in ["google_cloud", "elevenlabs"]:
                with st.spinner(f"Testando {provider}..."):
                    result = processor.process_multilingual_video(test_text, test_languages, provider)
                    results_comparison[provider] = result
            
            # Criar DataFrame para comparação
            comparison_data = []
            for provider, result in results_comparison.items():
                comparison_data.append({
                    "Provedor": "Google Cloud" if provider == "google_cloud" else "ElevenLabs",
                    "Tempo Total (s)": result["total_time"],
                    "Custo Total (R$)": result["total_cost"],
                    "Sucessos": f"{result['success_count']}/{len(test_languages)}",
                    "Custo/Segundo": result["total_cost"] / result["total_time"] if result["total_time"] > 0 else 0
                })
            
            df_comp = pd.DataFrame(comparison_data)
            
            # Gráficos lado a lado
            col1, col2 = st.columns(2)
            
            with col1:
                fig_time = px.bar(
                    df_comp, 
                    x="Provedor", 
                    y="Tempo Total (s)",
                    title="Comparação de Tempo de Processamento",
                    color="Provedor"
                )
                st.plotly_chart(fig_time, use_container_width=True)
            
            with col2:
                fig_cost = px.bar(
                    df_comp,
                    x="Provedor",
                    y="Custo Total (R$)",
                    title="Comparação de Custos",
                    color="Provedor"
                )
                st.plotly_chart(fig_cost, use_container_width=True)
            
            # Tabela de comparação
            st.subheader("Resumo da Comparação")
            st.dataframe(df_comp, use_container_width=True)
            
            # Análise de ROI
            st.subheader("Análise de ROI - Migração")
            
            google_result = results_comparison.get("google_cloud", {})
            elevenlabs_result = results_comparison.get("elevenlabs", {})
            
            if google_result and elevenlabs_result:
                savings_per_video = elevenlabs_result.get("total_cost", 0) - google_result.get("total_cost", 0)
                monthly_savings = savings_per_video * config.videos_per_day * 30
                annual_savings = monthly_savings * 12
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Economia por Vídeo", f"R$ {savings_per_video:.4f}")
                with col2:
                    st.metric("Economia Mensal", f"R$ {monthly_savings:.2f}")
                with col3:
                    st.metric("Economia Anual", f"R$ {annual_savings:.2f}")
    
    # Tab 4: Implementação
    with tab4:
        st.header("Guia de Implementação")
        
        st.subheader("1. 🔧 Configuração das APIs")
        
        with st.expander("Google Cloud Setup"):
            st.code("""
# 1. Criar projeto no Google Cloud Console
# 2. Ativar as seguintes APIs:
#    - Cloud Text-to-Speech API
#    - Cloud Translation API
# 3. Criar Service Account e baixar JSON
# 4. Ou criar API Key para desenvolvimento

# Configurar no Streamlit Secrets:
GOOGLE_CLOUD_PROJECT = "seu-projeto-id"
GOOGLE_CLOUD_API_KEY = "sua-api-key"

# OU para produção (recomendado):
GOOGLE_APPLICATION_CREDENTIALS = '''
{
  "type": "service_account",
  "project_id": "seu-projeto",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "service-account@projeto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
'''
            """)
        
        with st.expander("ElevenLabs Setup (para comparação)"):
            st.code("""
# 1. Criar conta no ElevenLabs
# 2. Obter API Key no dashboard
# 3. Configurar no Streamlit Secrets:

ELEVENLABS_API_KEY = "sua-api-key-elevenlabs"
            """)
        
        st.subheader("2. 📁 Estrutura do Projeto")
        
        st.code("""
video-generation-poc/
├── app.py                    # Aplicação principal (este arquivo)
├── requirements.txt          # Dependências Python
├── .streamlit/
│   └── config.toml          # Configurações do Streamlit
├── services/
│   ├── __init__.py
│   ├── google_cloud.py      # Serviços Google Cloud
│   ├── elevenlabs.py        # Serviços ElevenLabs
│   └── cost_analyzer.py     # Análise de custos
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Funções auxiliares
└── README.md                # Documentação
        """)
        
        st.subheader("3. 🚀 Deploy no Streamlit Cloud")
        
        deploy_steps = [
            "**Preparar Repositório:**",
            "- Fazer fork deste repositório no GitHub",
            "- Clonar para sua máquina local",
            "- Adicionar suas modificações",
            "",
            "**Configurar Streamlit Cloud:**",
            "- Acessar https://share.streamlit.io",
            "- Conectar conta GitHub",
            "- Selecionar repositório",
            "- Configurar secrets (APIs)",
            "",
            "**Deploy Automático:**",
            "- Push para main branch",
            "- Deploy automático em ~2 minutos"
        ]
        
        for step in deploy_steps:
            if step.startswith("**"):
                st.markdown(step)
            elif step == "":
                st.write("")
            else:
                st.write(step)
        
        st.subheader("4. 💡 Código de Migração Real")
        
        with st.expander("Migração do voice_synthesis.py"):
            st.code("""
# ANTES (ElevenLabs)
from elevenlabs import generate, Voice

class VoiceSynthesisService:
    def __init__(self):
        self.model = "eleven_multilingual_v2"
    
    def synthesize_speech(self, text, voice_id):
        audio = generate(
            text=text,
            voice=Voice(voice_id=voice_id),
            model=self.model,
            voice_settings=voice_settings
        )
        return audio

# DEPOIS (Google Cloud)
import requests
import json

class GoogleTTSService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://texttospeech.googleapis.com/v1"
    
    def synthesize_speech(self, text, language_code="pt-BR"):
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": language_code,
                "name": f"{language_code}-Standard-A",
                "ssmlGender": "NEUTRAL"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0
            }
        }
        
        response = requests.post(
            f"{self.base_url}/text:synthesize",
            headers=headers,
            params=params,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["audioContent"]
        else:
            raise Exception(f"TTS Error: {response.text}")
            """)
        
        with st.expander("Migração do translation.py"):
            st.code("""
# ANTES (OpenAI)
import openai

class TranslationService:
    def translate_text(self, text, target_language):
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Translate to {target_language}"},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content

# DEPOIS (Google Translate)
import requests

class GoogleTranslateService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
    
    def translate_text(self, text, target_language, source_language="pt"):
        params = {"key": self.api_key}
        payload = {
            "q": text,
            "target": target_language,
            "source": source_language,
            "format": "text"
        }
        
        response = requests.post(
            self.base_url,
            params=params,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["data"]["translations"][0]["translatedText"]
        else:
            raise Exception(f"Translation Error: {response.text}")
            """)
        
        st.subheader("5. 📊 Monitoramento de Custos")
        
        st.info("""
        **Configurar alertas no Google Cloud:**
        - Billing Alerts para limitar gastos
        - Monitoring para acompanhar uso das APIs
        - Quotas para evitar gastos excessivos
        
        **Métricas importantes:**
        - Caracteres processados por dia
        - Custo por vídeo gerado
        - Taxa de sucesso das APIs
        - Latência média das chamadas
        """)
        
        st.subheader("6. 🔄 Próximos Passos")
        
        next_steps = [
            "✅ **Implementar cache Redis** para traduções repetidas",
            "✅ **Adicionar fila de processamento** com Celery/RQ",
            "✅ **Implementar retry logic** para falhas de API",
            "✅ **Adicionar métricas de monitoramento** (Prometheus/Grafana)",
            "✅ **Criar dashboard de custos** em tempo real",
            "✅ **Implementar A/B testing** entre provedores",
            "✅ **Adicionar suporte a mais idiomas** (20+)",
            "✅ **Otimizar para processamento em lote**"
        ]
        
        for step in next_steps:
            st.markdown(step)
    
    # Footer com informações importantes
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💰 Economia Potencial",
            f"R$ {(cost_results['elevenlabs']['total_cost'] - cost_results['google_cloud']['total_cost']) * 12:,.0f}",
            "por ano"
        )
    
    with col2:
        st.metric(
            "⚡ Redução de Latência",
            f"{cost_results['elevenlabs']['latency_ms'] - cost_results['google_cloud']['latency_ms']}ms",
            "60% mais rápido"
        )
    
    with col3:
        st.metric(
            "🎯 ROI da Migração",
            f"{((cost_results['elevenlabs']['total_cost'] - cost_results['google_cloud']['total_cost']) / cost_results['elevenlabs']['total_cost'] * 100):.0f}%",
            "de economia"
        )

if __name__ == "__main__":
    main()
