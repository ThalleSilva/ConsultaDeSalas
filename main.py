
from pytz import timezone
from flask import Flask, request, redirect, url_for, render_template, jsonify
import requests
import json
from datetime import datetime, date, timedelta
import os
import re
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Configurações OAuth  ---
CLIENT_ID = 'cliente_id_azure'
CLIENT_SECRET = 'cliente_secrect_azure'
TENANT_ID = 'tenant_id_azure'
REDIRECT_URI = 'http://localhost:9090/callback'
AUTHORITY_URL = 'https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize'
TOKEN_URL = 'https://login.microsoftonline.com/organizations/oauth2/v2.0/token'
SCOPE = 'https://graph.microsoft.com/.default offline_access'
AUTH_URL_PARAMS = f'{AUTHORITY_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&prompt=select_account'


def salvar_tokens(access_token, refresh_token, expires_in):
    expires_at = datetime.now().timestamp() + expires_in - 300
    with open('tokens.json', 'w') as file:
        json.dump({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }, file)
    print("Tokens salvos/atualizados.")

def carregar_tokens():
    try:
        with open('tokens.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def get_access_token():
    tokens = carregar_tokens()
    if not tokens:
        return None
    if datetime.now().timestamp() > tokens.get('expires_at', 0):
        print("Token expirado. Tentando renovar...")
        if not tokens.get('refresh_token'):
            print("Refresh token não encontrado. Login necessário.")
            if os.path.exists("tokens.json"): os.remove("tokens.json")
            return None
        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': tokens['refresh_token'],
            'scope': SCOPE
        }
        response = requests.post(TOKEN_URL, data=payload)
        if response.status_code == 200:
            new_tokens = response.json()
            salvar_tokens(new_tokens['access_token'], new_tokens.get('refresh_token', tokens['refresh_token']), new_tokens['expires_in'])
            print("Token renovado com sucesso.")
            return new_tokens['access_token']
        else:
            print(f"Erro ao renovar token: {response.status_code} - {response.text}")
            if response.status_code in [400, 401]:
                 if os.path.exists("tokens.json"): os.remove("tokens.json")
            return None
    return tokens['access_token']


def get_all_rooms(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'ConsistencyLevel': 'eventual'
    }
    filter_query = "startsWith(displayName, 'Sede BH - Sala') or startsWith(displayName, 'Cabine')"
    select_query = "id,displayName,mail,userPrincipalName"
    base_url = "https://graph.microsoft.com/v1.0/users"
    query_params = {
        '$filter': filter_query,
        '$select': select_query,
        '$count': 'true'
    }
    processed_rooms_list = []
    request_url = base_url
    print(f"DEBUG: Tentando buscar salas com filtro: {filter_query}")
    page_count = 0
    while request_url:
        page_count += 1
        print(f"DEBUG: Buscando página {page_count} de salas...")
        if page_count == 1:
            response = requests.get(request_url, headers=headers, params=query_params)
        else:
            response = requests.get(request_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            users_as_rooms = data.get('value', [])
            for room_user in users_as_rooms:
                room_email = room_user.get('mail')
                room_name = room_user.get('displayName')
                if room_email and room_name:
                    typeRoom = ''
                    room_name_clean = room_name.strip().lower()
                    if "cabine" in room_name_clean:
                        typeRoom = 'cabine'
                    elif "sala" in room_name_clean:
                        typeRoom = 'sala'
                    processed_rooms_list.append({
                        'displayName': room_name,
                        'emailAddress': room_email,
                        'id': room_user.get('id'),
                        'userPrincipalName': room_user.get('userPrincipalName'),
                        'typeRoom': typeRoom
                    })
            request_url = data.get('@odata.nextLink')
        else:
            print(f"ERRO: Falha ao buscar usuários (salas) via Directory.Read.All com filtro em displayName.")
            if page_count == 1:
                 print(f"URL Tentada: {base_url} com params: {query_params}")
            else:
                 print(f"URL Tentada (nextLink): {request_url[:request_url.find('?')]}...")
            print(f"Status: {response.status_code} - Resposta: {response.text}")
            return None
    if not processed_rooms_list:
        print(f"INFO: Nenhuma sala encontrada com o filtro atual: '{filter_query}'.")
        print(f"INFO: Verifique os prefixos no filtro da função get_all_rooms no código e os nomes das suas salas no Azure AD.")
    return processed_rooms_list


def is_room_available(access_token, room_email, start_iso, end_iso):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="America/Sao_Paulo"'
    }
    calendar_view_url = f"https://graph.microsoft.com/v1.0/users/{room_email}/calendarView"
    
    
    params = {
        'startDateTime': start_iso,
        'endDateTime': end_iso,
        '$select': 'subject,start,end,showAs,isAllDay'
    }

    response = requests.get(calendar_view_url, headers=headers, params=params)
    if response.status_code == 200:
        events = response.json().get('value', [])
        
        if not events:
            return True

        try:
            query_start_time = datetime.fromisoformat(start_iso)
            query_end_time = datetime.fromisoformat(end_iso)
            
            for event in events:
                
                if event.get('isAllDay') and event.get('showAs') == 'free':
                    continue

                event_start_obj = event.get('start', {})
                event_end_obj = event.get('end', {})

                event_start_str = event_start_obj.get('dateTime')
                event_end_str = event_end_obj.get('dateTime')
                
                if not event_start_str or not event_end_str:
                    continue 

                event_start_time = datetime.fromisoformat(event_start_str)
                event_end_time = datetime.fromisoformat(event_end_str)

                
                
                if event_start_time.tzinfo is None:
                    
                    
                    event_tz_str = event_start_obj.get('timeZone', 'UTC')
                    try:
                        event_tz = timezone(event_tz_str)
                        event_start_time = event_tz.localize(event_start_time)
                        event_end_time = event_tz.localize(event_end_time)
                    except Exception as e:
                        print(f"ERRO: Não foi possível aplicar o fuso horário '{event_tz_str}' ao evento. Pulando. Erro: {e}")
                        continue
                

                
                if event_start_time < query_end_time and event_end_time > query_start_time:
                    if event.get('showAs') == 'free':
                        continue
                    
                    print(f"DEBUG: Sala '{room_email}' está OCUPADA. Evento conflitante: '{event.get('subject')}'")
                    return False

            return True
            
        except Exception as e: 
            print(f"ERRO GERAL ao processar datas do calendário para {room_email}: {e}")
            return False

    else:
        print(f"Erro ao buscar calendário para {room_email}: {response.status_code} - {response.text}")
        return False


@app.route('/')
def index():
    return redirect(url_for('procurar_salas'))

@app.route('/login')
def login():
    return redirect(AUTH_URL_PARAMS)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return render_template('home.html', error='Erro: Código de autorização não recebido.')
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE
    }
    tokens_response = requests.post(TOKEN_URL, data=token_data)
    if tokens_response.status_code == 200:
        tokens_json = tokens_response.json()
        salvar_tokens(tokens_json['access_token'], tokens_json['refresh_token'], tokens_json['expires_in'])
        return redirect(url_for('procurar_salas'))
    else:
        error_details = f"Código: {tokens_response.status_code}, Resposta: {tokens_response.text}"
        print(f"Erro ao obter token: {error_details}")
        return render_template('home.html', error=f'Erro ao obter token: {error_details}')

@app.route('/token')
def api_retorna_token():
    access_token = get_access_token()
    if access_token:
        return jsonify({'token': access_token})
    else:
        return jsonify({"error": "Nenhum token disponível. Faça login.", 
                        "login_url": url_for('login')}), 401

@app.route('/procurar', methods=['GET', 'POST'])
def procurar_salas():
    access_token = get_access_token()
    if not access_token:
        return redirect(url_for('login'))

    default_date = date.today().strftime('%Y-%m-%d')
    default_start_time = (datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).strftime('%H:%M')
    default_end_time = (datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)).strftime('%H:%M')
    
    selected_type = request.form.get('typeRoom', 'todos')
    
    form_data = {
        'data_selecionada': request.form.get('data', default_date),
        'inicio_val': request.form.get('inicio', default_start_time),
        'fim_val': request.form.get('fim', default_end_time),
        'tipo_selecionado': selected_type
    }

    if request.method == 'POST':
        data_str = request.form.get('data')
        inicio_str = request.form.get('inicio')
        fim_str = request.form.get('fim')
        typeRoomHtml = request.form.get('typeRoom')
        
        try:
            local_tz = timezone("America/Sao_Paulo")
            naive_start = datetime.strptime(f"{data_str} {inicio_str}", "%Y-%m-%d %H:%M")
            naive_end = datetime.strptime(f"{data_str} {fim_str}", "%Y-%m-%d %H:%M")
            aware_start = local_tz.localize(naive_start)
            aware_end = local_tz.localize(naive_end)
            start_iso = aware_start.isoformat()
            end_iso = aware_end.isoformat()
        except ValueError:
            return render_template('home.html', error="Formato de data ou hora inválido.", **form_data)

        if aware_start >= aware_end:
            return render_template('home.html', error="Horário de início deve ser anterior ao de fim.", **form_data)

        all_rooms = get_all_rooms(access_token)
        
        if all_rooms is None:
            return render_template('home.html', error="Erro ao buscar salas. Verifique o console do servidor para detalhes.", **form_data)
        if not all_rooms:
            return render_template('home.html', error="Nenhuma sala de reunião encontrada com os filtros de nome atuais. Verifique o console.", **form_data)

        available_rooms = []
        for room in all_rooms:
            if typeRoomHtml == 'todos' or room.get('typeRoom') == typeRoomHtml:
                room_name = room.get('displayName')
                room_email = room.get('emailAddress')
                if not room_email or not room_name:
                    continue
                if is_room_available(access_token, room_email, start_iso, end_iso):
                    available_rooms.append({'name': room_name, 'email': room_email})
        
        return render_template('results.html', 
                               rooms=available_rooms, 
                               start_time=inicio_str, 
                               end_time=fim_str, 
                               selected_date=aware_start.strftime("%d/%m/%Y"),
                               tipo_selecionado=typeRoomHtml.capitalize())

    return render_template('home.html', **form_data)

if __name__ == '__main__':
    app.run(debug=True, port=9090)