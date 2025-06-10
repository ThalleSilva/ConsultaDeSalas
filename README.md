# Sistema de Consulta de Salas de Reunião e Cabines
Este projeto é uma aplicação web desenvolvida em Flask (Python) para consultar a disponibilidade de salas de reunião e cabines integradas com o Microsoft Graph API. Ele permite que os usuários busquem facilmente por espaços disponíveis em uma data e horário específicos, com a opção de filtrar por tipo de sala.

Sobre o Projeto
O objetivo principal é otimizar a gestão e a reserva de espaços, oferecendo uma ferramenta intuitiva para verificar a disponibilidade de salas de reunião e cabines em tempo real. O backend robusto em Python, aliado à flexibilidade do Flask e à integração com a API do Microsoft Graph, garante eficiência e segurança.

Funcionalidades
Autenticação OAuth 2.0: Integração com o Microsoft Graph API para autenticação e autorização, garantindo acesso seguro aos dados de calendário.
Consulta de Disponibilidade: Permite selecionar data, horário de início e fim para verificar quais salas ou cabines estão livres.
Filtragem por Tipo: Opção de buscar por "Cabine", "Sala de Reunião" ou "Todos" os tipos de espaços.
Interface Intuitiva: Formulário simples para entrada de dados e uma página de resultados clara exibindo as salas disponíveis.
Tratamento de Erros: Mensagens de erro amigáveis para datas/horas inválidas ou problemas de conexão.
Tecnologias Utilizadas
Backend: Python 3.x com Flask
Autenticação/API: Microsoft Graph API (OAuth 2.0)
Requisições HTTP: requests
Gerenciamento de Tempo: datetime, pytz
Frontend: HTML5, CSS3
Como Rodar o Projeto (Localmente)
Para configurar e executar o projeto em sua máquina local, siga os passos abaixo:

Pré-requisitos:

Python 3.x instalado.
Um registro de aplicativo no Azure AD é necessário. Configure suas credenciais (CLIENT_ID, CLIENT_SECRET, TENANT_ID, REDIRECT_URI) no arquivo main.py. As permissões mínimas exigidas para a API do Graph são User.Read e Calendars.Read.
Instalar dependências:

Bash

pip install Flask requests pytz
Configurar Credenciais Azure AD:
Abra o arquivo main.py e substitua os placeholders com suas informações de aplicativo do Azure AD:

Python

CLIENT_ID = 'YOUR_AZURE_CLIENT_ID'
CLIENT_SECRET = 'YOUR_AZURE_CLIENT_SECRET'
TENANT_ID = 'YOUR_AZURE_TENANT_ID' # Geralmente 'organizations' ou seu ID de tenant
REDIRECT_URI = 'http://localhost:9090/callback' # Deve corresponder ao configurado no Azure AD
Executar a aplicação:

Bash

python main.py
Acessar no navegador:
Abra seu navegador e acesse http://localhost:9090. Você será redirecionado para a página de login da Microsoft para autenticação inicial.
