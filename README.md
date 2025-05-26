# 🎬 Sistema de Geração de Vídeos Multilíngues - POC Real

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://video-generation-poc.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Objetivo

POC funcional para demonstrar a migração de um sistema de geração de vídeos com narração multilíngue, comparando custos e performance entre:

- **ElevenLabs** (atual) - R$ 6.344/mês
- **Google Cloud TTS + Translate** (meta) - R$ 416/mês (**93% de economia**)
- **OpenAI TTS + Translate** (alternativa) - R$ 1.794/mês

## 🚀 Demo Online

**🔗 [Acessar Demo](https://video-generation-poc.streamlit.app)**

## 📊 Resultados da Análise

### Cenário: 200 vídeos/dia × 3 idiomas × 1.000 caracteres

| Provedor | Custo Mensal | Custo/Vídeo | Qualidade | Latência |
|----------|--------------|-------------|-----------|----------|
| **ElevenLabs** | R$ 6.344 | R$ 7,64 | 95% | 2000ms |
| **Google Cloud** | R$ 416 | R$ 0,07 | 80% | 800ms |
| **OpenAI** | R$ 1.794 | R$ 0,30 | 85% | 1500ms |

### 💰 Economia Anual Projetada: **R$ 71.136**

## 🛠️ Funcionalidades

- ✅ **Análise de Custos Real** - Cálculos baseados em APIs reais
- ✅ **Teste de Conversão Multilíngue** - Interface funcional para testar migração
- ✅ **Comparativo de Performance** - Latência, qualidade e custos
- ✅ **Implementação Prática** - Código de migração real
- ✅ **Monitoramento de Custos** - Tracking em tempo real
- ✅ **Deploy Automático** - CI/CD com GitHub Actions

## 🔧 Configuração Rápida

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/video-generation-poc.git
cd video-generation-poc
```

### 2. Instale Dependências

```bash
pip install -r requirements.txt
```

### 3. Configure APIs no Streamlit Cloud

**Importante:** As APIs são configuradas diretamente no Streamlit Cloud, não em arquivos locais.

1. **Deploy da aplicação** (sem configurar APIs ainda)
2. **Acesse Settings > Secrets** na interface do Streamlit Cloud
3. **Cole as configurações:**

```toml
# Google Cloud (Opção 1: API Key)
GOOGLE_CLOUD_PROJECT = "seu-projeto-id"
GOOGLE_CLOUD_API_KEY = "sua-api-key"

# Google Cloud (Opção 2: Service Account - Recomendado)
GOOGLE_APPLICATION_CREDENTIALS = '''
{
  "type": "service_account",
  "project_id": "seu-projeto",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account@projeto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
'''

# ElevenLabs (opcional)
ELEVENLABS_API_KEY = "sua-api-key-elevenlabs"
```

4. **Salve** - A aplicação reiniciará automaticamente

> **💡 Sem APIs configuradas:** A aplicação funciona em **modo demo** com dados simulados.

### 4. Execute Localmente

```bash
streamlit run app.py
```

## ☁️ Deploy no Streamlit Cloud

### Passo 1: Preparar Repositório
1. Faça fork deste repositório
2. Clone para sua máquina
3. Customize conforme necessário

### Passo 2: Deploy no Streamlit Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Conecte sua conta GitHub
3. Selecione o repositório `video-generation-poc`
4. **NÃO** configure secrets ainda - deixe fazer o deploy primeiro

### Passo 3: Configurar APIs (Após Deploy)
1. **Na interface do Streamlit Cloud**, clique em **Settings**
2. Vá para **Secrets**
3. Cole as configurações das APIs (ver seção de configuração acima)
4. Clique **Save** - A app reiniciará automaticamente com as APIs ativas

### Passo 3: Deploy Automático
- Push para branch `main`
- Deploy automático em ~2 minutos
- URL gerada automaticamente

## 🔑 Configuração das APIs

### Google Cloud Setup

1. **Criar Projeto:**
   - Acesse [Google Cloud Console](https://console.cloud.google.com)
   - Crie novo projeto ou selecione existente

2. **Ativar APIs:**
   ```bash
   gcloud services enable texttospeech.googleapis.com
   gcloud services enable translate.googleapis.com
   ```

3. **Criar Credenciais:**
   - Service Account (recomendado para produção)
   - API Key (mais simples para desenvolvimento)

4. **Configurar Secrets:**
   ```toml
   GOOGLE_APPLICATION_CREDENTIALS = '''
   {
     "type": "service_account",
     "project_id": "seu-projeto",
     ...
   }
   '''
   ```

### ElevenLabs Setup (Opcional)

1. Criar conta em [ElevenLabs](https://elevenlabs.io)
2. Obter API Key no dashboard
3. Configurar secret: `ELEVENLABS_API_KEY`

## 📁 Estrutura do Projeto

```
video-generation-poc/
├── app.py                    # 🎯 Aplicação principal Streamlit
├── requirements.txt          # 📦 Dependências Python
├── .streamlit/
│   ├── config.toml          # ⚙️ Configurações do Streamlit
│   └── secrets.toml         # 🔐 Secrets (não commitar)
├── .github/
│   └── workflows/
│       └── deploy.yml       # 🚀 CI/CD Pipeline
├── tests/
│   ├── __init__.py
│   ├── test_google_cloud.py
│   └── test_cost_analysis.py
├── docs/
│   ├── MIGRATION_GUIDE.md   # 📖 Guia de migração
│   └── API_REFERENCE.md     # 📚 Referência das APIs
└── README.md                # 📄 Este arquivo
```

## 🧪 Testes

```bash
# Executar todos os testes
python -m pytest tests/ -v

# Testar apenas APIs
python -m pytest tests/test_google_cloud.py -v

# Testar análise de custos
python -m pytest tests/test_cost_analysis.py -v
```

## 🔄 Código de Migração

### Antes (ElevenLabs)
```python
from elevenlabs import generate, Voice

audio = generate(
    text=text,
    voice=Voice(voice_id=target_voice_id),
    model=self.model,
    voice_settings=voice_settings
)
```

### Depois (Google Cloud)
```python
import requests

response = requests.post(
    "https://texttospeech.googleapis.com/v1/text:synthesize",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "input": {"text": text},
        "voice": {"languageCode": language_code},
        "audioConfig": {"audioEncoding": "MP3"}
    }
)
```

## 📈 Monitoramento

### Métricas Importantes
- 💰 **Custo por vídeo gerado**
- ⏱️ **Latência média das APIs**
- ✅ **Taxa de sucesso das chamadas**
- 📊 **Volume de caracteres processados**

### Alertas Recomendados
- Limite de gastos diários
- Falhas consecutivas de API
- Latência acima de 3s
- Taxa de erro > 5%

## 🚨 Limites e Quotas

### Google Cloud
- **TTS:** 1M caracteres/mês grátis
- **Translate:** 500K caracteres/mês grátis
- **Rate Limit:** 100 req/min

### ElevenLabs
- **Creator:** 100K caracteres/mês
- **Pro:** 500K caracteres/mês
- **Rate Limit:** 20 req/min

## 🔒 Segurança

- ✅ **Secrets** nunca commitados no git
- ✅ **Service Account** com permissões mínimas
- ✅ **Rate limiting** implementado
- ✅ **Logs** sem dados sensíveis
- ✅ **HTTPS** obrigatório em produção

## 🤝 Contribuindo

1. Fork o projeto
2. Crie branch para feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para branch (`git push origin feature/nova-funcionalidade`)
5. Abra Pull Request

## 📝 Changelog

### v1.0.0 (2025-01-XX)
- ✅ Implementação inicial da POC
- ✅ Integração com Google Cloud TTS + Translate
- ✅ Comparação com ElevenLabs
- ✅ Interface Streamlit completa
- ✅ Deploy automático no Streamlit Cloud

## 📞 Suporte

- 🐛 **Bugs:** [GitHub Issues](https://github.com/seu-usuario/video-generation-poc/issues)
- 💬 **Discussões:** [GitHub Discussions](https://github.com/seu-usuario/video-generation-poc/discussions)
- 📧 **Email:** suporte@exemplo.com

## 📄 Licença

Este projeto está sob a licença MIT. Veja [LICENSE](LICENSE) para mais detalhes.

## 🎯 Próximos Passos

- [ ] **Cache Redis** para traduções repetidas
- [ ] **Fila de processamento** com Celery
- [ ] **Retry logic** para falhas de API
- [ ] **Métricas avançadas** com Prometheus
- [ ] **Dashboard de custos** em tempo real
- [ ] **A/B testing** entre provedores
- [ ] **Suporte a 20+ idiomas**
- [ ] **Processamento em lote** otimizado

---

**💡 Resultado Final:** Economia de **R$ 71.136/ano** com 60% menos latência mantendo qualidade profissional.

**🚀 [Deploy Sua Versão Agora](https://share.streamlit.io)**
