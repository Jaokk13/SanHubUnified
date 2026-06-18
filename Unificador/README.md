# Unificador Samsys

O **Unificador Samsys** é um programa desktop com interface gráfica moderna desenvolvido para automatizar a consolidação e filtragem de Ordens de Serviço (OS) de Calçadas e Pavimento. Esta versão substitui a antiga aplicação web (Flask) por um executável *standalone* mais rápido, robusto e amigável.

## 🚀 Funcionalidades

- **Interface Gráfica Moderna**: Construída com `customtkinter`, oferecendo um design elegante em *dark mode* e feedback visual em tempo real através de um console integrado.
- **Consolidação de Dados**: Une os dados de dois relatórios gerenciais distintos do sistema Samsys (A e B).
- **Filtragem Inteligente**:
  - Filtra automaticamente serviços baseados em códigos específicos de pavimentação e calçadas (códigos: `613201`, `613202`, `613203`, `613204`, `613205` e `613206`).
  - Filtra ordens de serviço localizadas estritamente nos bairros definidos na planilha de banco (zonas Norte e Oeste).
- **Exportação Otimizada e Estilizada**:
  - Gera um arquivo `.xlsx` limpo contendo apenas as colunas essenciais: *Número da OS, Data de Solicitação, Bairro, Serviço e Data Limite de Execução*.
  - O Excel exportado já sai pré-formatado (títulos estilizados, largura de colunas ajustada com auto-fit, zebra striping e painéis congelados) para facilitar a leitura.
- **Memória de Configuração**: O programa memoriza o último "Banco de Bairros" utilizado, salvando um arquivo local (`config.json` e uma cópia do banco) para que você não precise selecioná-lo novamente no próximo uso.

## 🛠️ Tecnologias Utilizadas

- **[Python](https://www.python.org/)** (Linguagem Principal)
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** (Interface Gráfica)
- **[Pandas](https://pandas.pydata.org/)** (Limpeza, consolidação e filtragem de dados)
- **[OpenPyXL](https://openpyxl.readthedocs.io/)** (Exportação e formatação da planilha final)
- **[xlrd](https://xlrd.readthedocs.io/)** (Leitura das planilhas brutas originais `.xls`)

## 📦 Instalação e Requisitos

Certifique-se de ter o Python instalado na sua máquina. Em seguida, instale as dependências necessárias utilizando o `pip`:

```bash
pip install customtkinter pandas openpyxl xlrd
```

## 🖥️ Como Usar

1. **Inicie o programa**:
   Execute o script principal via terminal ou linha de comando:
   ```bash
   python unificador_gui.py
   ```
2. **Selecione os Arquivos no programa**:
   - **Samsys A**: Relatório extraído do Samsys em formato `.xls` (o programa ignora automaticamente as 4 primeiras linhas de cabeçalho).
   - **Samsys B**: Segundo relatório extraído do Samsys, também em formato `.xls`.
   - **Banco de Bairros**: Planilha `.xlsx` contendo a relação de bairros a serem filtrados.
3. **Processe as Planilhas**:
   - Assim que os 3 arquivos estiverem carregados corretamente, o botão **"⚡ Processar Planilhas"** ficará habilitado.
   - Clique nele para iniciar a rotina em *background*.
4. **Acompanhe pelo Console**:
   - O console na parte inferior da tela mostrará o passo a passo em tempo real (etapas concluídas, contagem de registros retidos/descartados e eventuais erros).
5. **Salve o Resultado**:
   - Ao término do processamento, uma janela padrão do Windows será aberta pedindo o local e o nome para salvar o seu novo arquivo consolidado `.xlsx`.

## 📂 Como Funciona o Processamento (Under the Hood)

A lógica do processamento foi desacoplada da interface principal usando *threads*, garantindo que a janela não "congele". Os passos executados são:
1. Leitura otimizada na memória (`io.BytesIO`) ignorando cabeçalhos não padronizados.
2. Limpeza dos códigos de serviço e concatenação com suas respectivas descrições.
3. *Merge* (Concatenação) dos relatórios em um único DataFrame Pandas.
4. Filtro iterativo excluindo serviços que não são os alvos de calçadas.
5. Cruzamento da base com o banco de bairros extraídos de forma dinâmica.
6. Isolamento das colunas de saída.
7. Instanciação e estilização das células usando os *Styles* do `openpyxl`.

---

**Desenvolvido para agilizar a triagem e otimizar a criação de cronogramas.**
