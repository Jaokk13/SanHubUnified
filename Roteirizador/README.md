# Roteirizador de Bairros V2 (BrPaving)

O **Roteirizador de Bairros V2** é uma aplicação desktop desenvolvida em Python (com interface em PyQt5) projetada para facilitar a logística de rotas e a divisão de serviços entre equipes em uma cidade configurável (por padrão Cuiabá/MT). Ele recebe uma lista de bairros ou endereços, localiza as coordenadas geográficas de forma inteligente (utilizando um banco local, cache ou APIs de geocodificação como Nominatim, ArcGIS e BrasilAPI) e otimiza a rota utilizando algoritmos clássicos de roteamento.

## 🚀 Principais Funcionalidades

- **Geocodificação Inteligente (Fallback Múltiplo)**: Tenta localizar as coordenadas primeiro através de um banco JSON local rápido. Caso não encontre, realiza buscas no Nominatim (OSM) e ArcGIS, além de buscar por CEP usando a BrasilAPI.
- **Validação de Área (Bounding Box e Raio)**: Possui travas de segurança para ignorar localizações muito distantes (ex: 100km do centro da cidade) ou que estejam fora do perímetro configurado, evitando roteamento acidental para outros estados ou países.
- **Otimização de Rota (TSP)**: Calcula e organiza a melhor ordem de visitação para os pontos informados minimizando a distância total utilizando a heurística **Nearest Neighbor (Vizinho Mais Próximo)** aliada à otimização **2-Opt** (para desembaraçar e remover cruzamentos na rota).
- **Divisão por Equipes (Algoritmo Sweep)**: Permite dividir automaticamente a lista de entregas/serviços entre várias equipes. O algoritmo varre o mapa de forma angular a partir do centro da cidade (fatias de pizza), garantindo que as equipes não cruzem os caminhos umas das outras.
- **Interface Gráfica Rica (PyQt5)**: Interface moderna com barra de progresso, opções de configuração de cidade/estado/base e relatórios em tempo real de quais bairros foram localizados.
- **Geração de Mapa Interativo**: Ao final do roteamento, o sistema gera automaticamente um arquivo `mapa_rota_otimizada.html` usando a biblioteca **Folium**, renderizando os pontos com rotas e visualizações coloridas e interativas dentro do próprio app e no navegador.

## 📂 Estrutura do Projeto

- `Localizador.py`: Arquivo principal contendo toda a lógica de interface gráfica, algoritmos de roteirização, divisão de equipes e interações no mapa.
- `processar_rotas.py`: Um script em linha de comando (CLI) simplificado que lê uma planilha Excel (`rotas.xlsx`), realiza as validações de coordenadas e cria o mapa HTML de saída. Útil para integrações ou automações sem interface gráfica.
- `atualizar_base_bairros.py`: Script focado em atualizar periodicamente a base local de dados JSON (`banco_bairros_oficial.json`) fazendo consultas dinâmicas à API do OpenStreetMap (Overpass API).
- `*.spec` e `Instalador.iss`: Arquivos de configuração do PyInstaller e Inno Setup, utilizados para transformar o código Python em um instalador executável `.exe` (Windows).

## 🛠️ Requisitos e Instalação

As principais bibliotecas necessárias para executar o projeto a partir do código-fonte são:
- `PyQt5` e `PyQtWebEngine` (Interface e navegador embutido)
- `geopy` (Geocodificação Nominatim e ArcGIS)
- `folium` (Criação de mapas HTML)
- `pandas` e `openpyxl` (Leitura de Excel)
- `requests` (Consultas a APIs)
- `qtawesome` (Ícones para a interface)

Para rodar via código fonte, você pode instalar as dependências com o `pip`:

```bash
pip install PyQt5 PyQtWebEngine geopy folium pandas openpyxl requests qtawesome
```

## ▶️ Como Usar

### 1. Pela Interface Gráfica
1. Execute `python Localizador.py`.
2. Configure a Cidade, Estado e Endereço da Base inicial (que ficará como o ponto de partida padrão).
3. Insira ou cole a lista de bairros ou endereços na caixa de texto.
4. Escolha se deseja gerar a rota para 1 equipe ou dividir para múltiplas equipes.
5. Clique em **"Localizar e Gerar Rotas"**.
6. Acompanhe a janela de log mostrando as localizações encontradas. Ao final, o mapa com a rota otimizada aparecerá na tela.

### 2. Pelo Script em Lote (Excel)
1. Preencha o arquivo `rotas.xlsx` contendo colunas como `Endereco`, `Bairro` e `CEP`.
2. Execute o script `python processar_rotas.py`.
3. O script irá ler a planilha e gerar no mesmo diretório o `mapa_rota_otimizada.html`.

## ⚙️ Compilando o Executável

O projeto é configurado para ser distribuído como um programa nativo do Windows.

1. Para gerar o binário da aplicação (usando o arquivo `.spec`):
   ```bash
   pyinstaller Localizador.spec
   ```
2. Após o build, o instalador final poderá ser montado usando o Inno Setup no arquivo `Instalador.iss`. Note que o aplicativo salva o cache e o banco de dados dinâmico na pasta `%APPDATA%\RoteirizadorBrPaving` para garantir permissão de escrita mesmo quando instalado em "Arquivos de Programas".
