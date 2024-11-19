from flask import Flask, request
import requests
from twilio.twiml.messaging_response import MessagingResponse
import os
import logging
from twilio.rest import Client
import uuid
import cv2
from pyzbar.pyzbar import decode


app = Flask(__name__)

# Credênciais de Autenticação Twilio
account_sid = 'TOKEN-ACCOUNT'
auth_token = 'TOKEN-API'
client = Client(account_sid, auth_token)


# Diretório para salvar as mídias
DOWNLOADS_DIR = ('downloads')

# Criar o diretório se não existir
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

def processar_mensagem(numero, mensagem, midia_url, codigo, imagem):
    if midia_url:
        try:
            midia_nome = f"{uuid.uuid4()}.jpg" #Gerar um nome de arquivo aleatório e único
            baixar_midia(midia_url, midia_nome)
            carregar_imagem(midia_url)
            validar_ean(codigo)
            extrair_codigo_barras(imagem)
            resposta = f"Legal! recebemos seu produto {midia_nome}"
            logging.debug("Midia foi recebida.")
            
        except Exception as e:
            resposta += f" mas ocorreu um erro ao baixar a mídia: {e}"  

    if mensagem == "enviar código":
        resposta = "Ok! Envie o código de barra do produto."
        logging.debug("Foi solicitado o envio do código de barras")
    
    if mensagem == "outra opção":
        resposta = "Diga-me! Qual opção deseja."
        logging.debug("Foi solicitado outra opção")

    else:
        resposta = "Welcome!"
    return resposta


def baixar_midia(midia_url, nome_arquivo):
    try:
        # Fazendo a requisição com autenticação
        response = requests.get(midia_url, auth=(account_sid, auth_token))
        if response.status_code == 200:
            caminho_arquivo = os.path.join(DOWNLOADS_DIR, nome_arquivo)
            logging.debug(f"Salvando mídia em: {caminho_arquivo}")
            with open(caminho_arquivo, 'wb') as f:
                f.write(response.content)
            logging.debug(f"Mídia salva com sucesso: {caminho_arquivo}")
            return response.content
        else:
            raise Exception(f"Falha ao baixar a mídia, status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Não foi possível baixar a imagem da URL: {midia_url}. Erro: {e}")
        raise


def carregar_imagem(midia_url):
    imagem = cv2.imread(midia_url)
    if imagem is None:
        raise FileNotFoundError("Não foi possível carregar a imagem em.")
    return imagem


def extrair_codigo_barras(imagem):
  
    imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    codigos_barras = decode(imagem_cinza)
    codigos = []
    for codigo in codigos_barras:
        if 'EAN' in codigo.type:
            try:
                ean_codigo = validar_ean(codigo.data.decode('utf-8'))
                codigos.append(ean_codigo)

            except ValueError as e:
                print(e)  # Ou você pode decidir ignorar os códigos inválidos
    return codigos

def validar_ean(codigo):
    if len(codigo) == 13 and codigo.isdigit():
        return codigo  # EAN-13 válido
    elif len(codigo) == 8 and codigo.isdigit():
        return codigo  # EAN-8 válido
    else:
        raise ValueError(f"Código de barras não é um EAN válido: {codigo}")

    
@app.route("/Whatsapp", methods=['POST', 'GET'])
def webhook():
    try:
        # Log de entrada da requisição completa para depuração
        logging.debug(f"Método HTTP da requisição: {request.method}")
        logging.debug(f"Dados da requisição: {request.values}")
        
        # Extrair informações da mensagem recebida
        mensagem = request.values.get('Body', '').lower()
        numero = request.values.get('From')
        midia_url = request.values.get('MediaUrl0', '')

        # Registrar as informações da mensagem usando logging
        logging.debug(f"Mensagem recebida: {mensagem}")
        logging.debug(f"Número do remetente: {numero}")
        logging.debug(f"URL da mídia: {midia_url}")

        # Processar a mensagem recebida
        resposta = processar_mensagem(numero, mensagem, midia_url)
        
        # Enviar a resposta para o remetente
        resp = MessagingResponse()
        resp.message(resposta)
        return str(resp)

    except Exception as e:
        logging.error(f"Erro ao processar a mensagem: {e}")
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True)
