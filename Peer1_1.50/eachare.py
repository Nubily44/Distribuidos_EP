# Code by Lily and Dani (14567051 e 13659997)
# Windows 10, Python 3.11.5

import socket
import threading
import os
import time 
import sys


SELF_IP = ""
SELF_PORT = None
SELF_CLOCK = 0

vizinhos = set()

sair = False

# Classe vizinho para armazenar os peers
class Vizinho:
    def __init__(self, iden, ip, port, status):
        self.iden = iden # Indentificador do vizinho
        self.ip = ip
        self.port = port
        self.status = status

    def setStatus(self, status):
        self.status = status
    
    def getStatus(self):
        return self.status
    
    def __hash__ (self):
        return hash((self.iden)) # Hash para o set de vizinhos

    def __eq__(self, other): # Comparador para o set de vizinhos
        if isinstance(other, Vizinho):
            return self.iden == other.iden and self.ip == other.ip and self.port == other.port
        return False

# Busca de vizinho pelo identificador
# (usado para enviar mensagens para vizinhos)
def searchVizinho(vizinhos, iden):
    return next((v for v in vizinhos if v.iden == iden), None)

# Busca de vizinho pelo IP e porta
# (usado para responder mensagens de vizinhos)
def searchVizinhoIP(vizinhos, ip, port):
    return next((v for v in vizinhos if v.ip == ip and v.port == port), None)

# Atualiza o status do vizinho (com a busca pelo iden)
def updateStatus(vizinhos, iden, newStatus):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.setStatus(newStatus)
        vizinhos.add(vizinho)
    
    print(f"Atualizando peer {vizinho.ip}:{vizinho.port} para {newStatus}")

# Da update do clock proprio quando necessario
def updateClock():
    global SELF_CLOCK
    SELF_CLOCK += 1
    print(f"=> Atualizando relogio para {SELF_CLOCK}")

# Função de formatação de mensagens e envio. Padrão para TODAS AS MENSAGENS
def sendMessage(iden, tipo, arguments):
    try:

        vizinho = searchVizinho(vizinhos, iden)
        self_ip_full = ":".join ([SELF_IP, str(SELF_PORT)])
        full_message = " ".join([self_ip_full, str(SELF_CLOCK), tipo, arguments])

        print(f"Encaminhando mensagem \"{full_message}\" para {vizinho.ip}:{str(vizinho.port)}")


        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((vizinho.ip, vizinho.port))
        sock.sendall(full_message.encode())

        sock.close()
        return 1
    except Exception as e:
        return e

# Interpreter de mensagens recebidas. Cada tipo de mensagem tem um tratamento diferente.
def interpreter(vizinhos, ip, port, tipo, arguments):
    if not arguments:
        arguments = ""
    
    vizinho = searchVizinhoIP(vizinhos, ip, int(port))
    
    match tipo:
        case "HELLO":
            if vizinho:
                updateClock()
                updateStatus(vizinhos, vizinho.iden, "ONLINE")

            else:
                vizinho = Vizinho(len(vizinhos)+1, ip, int(port), "ONLINE")
                vizinhos.add(vizinho)
                print(f"\nAdicionando novo peer {vizinho.ip}:{vizinho.port}")
                updateClock()

        case "BYE":
            if vizinho:
                updateClock()
                updateStatus(vizinhos, vizinho.iden, "OFFLINE")
        
        case "GET_PEERS":
            updateClock()
            lista = []
            lista.append(str(len(vizinhos)-1))
            for i in vizinhos:
                if i != vizinho:
                    lista.append(f"{i.ip}:{str(i.port)}:{i.status}:0")
            args = " ".join(lista)
            sendMessage(vizinho.iden, "PEER_LIST", args)
        
        case "PEER_LIST":
            updateClock()
            for i in arguments[1:]:
                ph = i.split(":")
                ip, port, status = ph[0], int(ph[1]), ph[2]

                if searchVizinhoIP(vizinhos, ip, port) is None:
                    v = Vizinho(len(vizinhos) + 1, ip, port, status)
                    vizinhos.add(v)
                    print(f"Adicionando novo peer {v.ip}:{v.port} status {v.status}")

# Thread de escuta para receber mensagens de outros peers
def listener():
    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen.bind((SELF_IP, int(SELF_PORT)))
    listen.listen(5)
    listen.settimeout(1)
    while not sair:
        try:
            conn, addr = listen.accept()
            data = conn.recv(1024).decode()

            vizinho_ip_port, peer_clock, tipo, *arguments = data.split()

            if tipo == "PEER_LIST":
                print(f"Resposta recebida: \"{data}\"") # Sintaxe diferente para Obter peers (porque é uma resposta)
            else:
                print(f"Mensagem recebida: \"{data}\"")

            
            vizinho_ip, vizinho_port = vizinho_ip_port.split(":")
            if arguments:
                interpreter(vizinhos, vizinho_ip, vizinho_port, tipo, arguments) # Com argumentos
            else:
                interpreter(vizinhos, vizinho_ip, vizinho_port, tipo, "")  # Sem argumentos


            conn.close()

        except socket.timeout:
            pass



def sendHello(iden): # Listar peers e enviar hello para o vizinho
    tipo = "HELLO"
    vizinho = searchVizinho(vizinhos, iden)
    
    updateClock()
    result = sendMessage(vizinho.iden, tipo, "")
    if result == 1:
        updateStatus(vizinhos, vizinho.iden, "ONLINE")

    else:
        print(f"Erro ao enviar mensagem para {vizinho.ip}:{str(vizinho.port)}")
        updateStatus(vizinhos, vizinho.iden, "OFFLINE")

def getPeers(vizinhos): # Obter peers e enviar mensagem para todos os vizinhos
    tipo = "GET_PEERS"
    for i in list(vizinhos):
        updateClock()
        result = sendMessage(i.iden, tipo, "")
        if result == 1:
            updateStatus(vizinhos, i.iden, "ONLINE")
        else:
            print(f"Erro ao enviar mensagem para {i.ip}:{str(i.port)}")
            updateStatus(vizinhos, i.iden, "OFFLINE")
    
    time.sleep(1) # IMPROVISO (GAMBIARRA) :D / Pra esperar a resposta do peer. Se vc ta lendo isso, oie! :)

def sendBye(iden): # Enviar mensagem de bye para o vizinho
    tipo = "BYE"
    sendMessage(iden, tipo, "")

def openFile(path):
    with open(path, 'r') as file:
        return file.read()

def console():
    print("> ")

if __name__ == "__main__":


    # Execução do programa
    if len(sys.argv) != 4:
        print("Uso: python eachare.py <selfIP> <vizinhos> ")
        sys.exit()
    selfIP = sys.argv[1]
    SELF_IP, SELF_PORT = selfIP.split(":")
    vizinhos_filename = sys.argv[2]
    folder_name = sys.argv[3]  

    # Checa se o diretorio existe
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    folder_path = os.path.join(script_dir, folder_name)
    if not os.path.exists(folder_path):
        print(f"O diretório '{folder_name}' não existe.")
        sys.exit()

    # Armazena os peers atuais
    vizinhos_ips = openFile(vizinhos_filename).split("\n")

    temp = 1
    for i in vizinhos_ips:
        ph = i.split(":")
        v = Vizinho(temp, ph[0], int(ph[1]), "OFFLINE")
        vizinhos.add(v)
        temp += 1
        print(f"Adicionando vizinho {v.ip}:{v.port}")

    # Inicializa o socket e a thread de escuta
    listen_thread = threading.Thread(target=listener)
    listen_thread.start()

    print("\n\n\n")
    interface = 0
    while interface == 0:
        print(
            "Escolha um comando:\n"
            "   [1] - Listar peers\n"
            "   [2] - Obter peers\n"
            "   [3] - Listar arquivos locais\n"
            "   [4] - Buscar arquivos\n"
            "   [5] - Exibir estatisticas\n"
            "   [6] - Alterar tamanho de chunk\n"
            "   [9] - Sair\n"
        )
        option = input("> ")
        match int(option):

            case 1: # Listar peers
                print("Lista de peers...\n"
                      "[0] voltar para o menu anterior")
                
                for i in vizinhos:
                    print(f"[{str(i.iden)}] {i.ip}:{str(i.port)} {i.status}")
                
                input1 = input("> ")
                if input1 == "0":
                    pass
                else:
                    sendHello(int(input1))

            case 2: #obter peers
                getPeers(vizinhos)    
            
            case 3:
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    contents = os.listdir(folder_path)
                    print(contents)
                else:
                    print(f"O diretório '{folder_name}' não existe ou não é um diretório.")

            case 9:
                print("Saindo...")
                for i in vizinhos:
                    sendBye(i.iden)
                interface = 1
                sair = True
                listen_thread.join()
                sys.exit()
            

