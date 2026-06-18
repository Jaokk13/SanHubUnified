# SanHub Unified 🚀

O **SanHub Unified** é um sistema inteligente e ágil para o gerenciamento, programação e roteamento geográfico otimizado de Ordens de Serviço (OS) de manutenção e infraestrutura. Ele une um Dashboard gerencial com um poderoso motor de **Caixeiro Viajante (TSP)** para distribuir equipes em rotas inteligentes pela cidade.

## ✨ Principais Funcionalidades

1. **Dashboard Executivo:** Visualização rápida do status geral de todas as OSs (Pendentes, Executadas) divididas por Categoria (Calçada, Asfalto).
2. **Importação Automatizada Diária:** Aceita envio de planilhas do sistema Samsys em formato `.xls` e `.xlsx`. Identifica automaticamente OSs novas e atualiza as que já foram executadas com base na ausência nas planilhas recentes.
3. **Gestão e Programação de Equipes (Drag & Drop):** Permite o cadastro rápido de equipes por categoria e atribuição de OSs pendentes utilizando caixas de seleção ou o prático "Arrastar e Soltar" (Drag & Drop interativo) para organizar e programar as equipes na hora.
4. **Divisão Angular Sweep Inteligente (Roteamento por Carga):** Distribui ordens geograficamente próximas entre as equipes. Para frentes de **Asfalto e Execução**, o robô planeja o roteamento respeitando limites de peso de **8 a 10 toneladas por equipe** (calculado via área da OS), com margem de tolerância automática para manter trechos vizinhos na mesma frente.
5. **Cálculo de Massa em Tempo Real:** Exibe no painel de programação o somatório instantâneo de toneladas alocadas em cada equipe de asfalto, recalculando de forma transparente ao mover ordens de serviço.
6. **Roteirizador Geográfico com Fallback (TSP Otimizado):**
   - Rastreia a localização das OSs agrupando-as por Bairros.
   - Utiliza múltiplas camadas de geocodificação: **Banco JSON Local Ultra Rápido > OpenStreetMap (Nominatim) > ArcGIS > BrasilAPI**.
   - Calcula a melhor rota possível (fechando um ciclo da Base e retornando) usando algoritmos de *Nearest Neighbor* (Vizinho Mais Próximo) + otimização matemática *2-Opt*.
7. **Gerenciador de Banco de Bairros:** Como o tempo é dinheiro, o SanHub aprende. Cada vez que um bairro é localizado na nuvem, ele salva no `banco_bairros_compartilhar.json`. O sistema permite exportar e importar esse JSON para que a sua empresa tenha o cache sempre abastecido e rápido.
8. **Exportação Excel:** Gera planilhas mastigadas e formatadas (.xlsx) para envio das rotas e OSs diretas para os líderes das equipes.

---

## 🛠️ Tecnologias Utilizadas

- **Backend / API:** Python 3.12, FastAPI, Uvicorn, SQLite3 (Modo WAL).
- **Frontend / UI:** HTML5, CSS3 Glassmorphism (Vanilla CSS sem frameworks pesados), JavaScript (ES6+).
- **Mapas e Geocodificação:** Leaflet.js (Mapas interativos frontend), Geopy (Backend), OSM, ArcGIS.
- **Processamento de Dados:** Pandas, Openpyxl.

---

## ⚙️ Como Instalar e Rodar Localmente

**Pré-requisitos:** Certifique-se de ter o **Python 3.12** instalado na sua máquina (versões mais novas como 3.13 podem não ter bibliotecas Pandas totalmente compiladas, exigindo ferramentas de build).

1. Clone o repositório para o seu computador:
```bash
git clone https://github.com/SeuUsuario/SanHub.git
cd SanHub
```

2. Crie e ative o seu Ambiente Virtual (Recomendado):
```bash
# Windows
python -m venv venv
venv\Scripts\activate
```

3. Instale todas as dependências:
```bash
pip install -r requirements.txt
```

4. Inicialize o servidor e a aplicação:
```bash
python run.py
```
*O `run.py` inicializa o servidor web e automaticamente abre uma aba do navegador no painel administrativo local (http://localhost:8000).*

---

## 🗺️ Como Utilizar o Fluxo Principal

1. Vá em **Equipes** e cadastre as equipes do dia (escolhendo asfalto ou calçada).
2. Vá em **Importar Diária** (menu lateral inferior) e suba as planilhas pendentes retiradas do sistema matriz.
3. Acesse **Programação**. Você verá as OS na esquerda. Pode selecionar a equipe na direita e clicar na mágica **"Auto (Divisão Sweep)"** para dividir as OS de forma inteligente no mapa.
4. Vá em **Rotas (Mapa)**, selecione a equipe programada e clique em **Calcular**. O sistema mostrará no mapa a melhor ordem, agrupando os serviços pelo mesmo bairro e informando a quilometragem a ser rodada.

*Produzido com Inteligência e Precisão.*
