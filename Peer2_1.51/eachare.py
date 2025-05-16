# Code by Lily and Dani (14567051 e 13659997)
# Windows 10, Python 3.11.5

import socket
import threading
import os
import time 
import sys
import base64 as b64


SELF_IP = ""
SELF_PORT = None
SELF_CLOCK = 0
SELF_PATH = ""

event = threading.Event()

vizinhos = set()

arquivos_rede = []

sair = False

#######################################################################################

#funções auxiliares de socket

def recv_eof(conn):
    buffer = b""
    while not buffer.endswith(b"\n"):
        chunk = conn.recv(1024)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode()

#######################################################################################

#classes

# Classe vizinho para armazenar os peers
class Vizinho:
    def __init__(self, iden, ip, port, status):
        self.iden = iden # Indentificador do vizinho
        self.ip = ip
        self.port = port
        self.status = status
        self.clock = 0

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

class Arquivos:
    def __init__(self, iden, nome, tamanho, peer_iden):
        self.iden = iden
        self.nome = nome
        self.tamanho = tamanho
        self.peer_iden = peer_iden

#######################################################################################

#funções auxiliares da execução do programa


# Busca de vizinho pelo identificador
# (usado para enviar mensagens para vizinhos)
def searchVizinho(vizinhos, iden):
    return next((v for v in vizinhos if v.iden == iden), None)

# Busca de vizinho pelo IP e porta
# (usado para responder mensagens de vizinhos)
def searchVizinhoIP(vizinhos, ip, port):
    return next((v for v in vizinhos if v.ip == ip and v.port == port), None)

def searchArq(arquivos_rede, iden):
    return next((a for a in arquivos_rede if a.iden == iden), None)

# Atualiza o status do vizinho (com a busca pelo iden)
def updateStatus(vizinhos, iden, newStatus):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.setStatus(newStatus)
        vizinhos.add(vizinho)
    
    print(f"Atualizando peer {vizinho.ip}:{vizinho.port} para {newStatus}")

# Update do clock para envios (sem relógio de lamport)
def addClock():
    global SELF_CLOCK
    SELF_CLOCK += 1
    print(f"=> Atualizando relogio para {SELF_CLOCK}")
    
# Update do clock para recebimentos (com relógio de lamport)
def updateClock(iden, clock):
    global SELF_CLOCK
    print(f"Comparando: {SELF_CLOCK} e {clock}")
    SELF_CLOCK = max(SELF_CLOCK, clock) + 1
    
    print(f"=> Atualizando relogio para {SELF_CLOCK}")

# Listar arquivos da rede (eu formatei isso, quero meus pontos de respeito)
def listarArquivosRede():
    global arquivos_rede

    cancelar = type('FakeEntry', (), {
        'iden': 0,
        'nome': "<Cancelar>",
        'tamanho': "",
        'peer_iden': ""
    })()
    todos = [cancelar] + arquivos_rede

    nome_width = max(len("Nome"), max(len(str(i.nome)) for i in todos))
    tamanho_width = max(len("Tamanho"), max(len(str(i.tamanho)) for i in todos))
    peer_width = max(len("Peer"), max(len(str(i.peer_iden)) for i in todos))
    id_width = max(len(str(i.iden)) for i in todos)

    print(f"{' ' * (id_width + 3)}{ 'Nome'.ljust(nome_width) } | { 'Tamanho'.rjust(tamanho_width) } | { 'Peer'.ljust(peer_width) }")

    for i in todos:
        print(
            f"[{str(i.iden).rjust(id_width)}] "
            f"{str(i.nome).ljust(nome_width)} | "
            f"{str(i.tamanho).rjust(tamanho_width)} | "
            f"{str(i.peer_iden).ljust(peer_width)}"
        )

#######################################################################################

#SEND

# Função de formatação de mensagens e envio. Padrão para TODAS AS MENSAGENS
def sendMessage(iden, tipo, arguments):
    try:
        
        event.clear()
        
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
        print(e)
        return e

#######################################################################################

# RECEIVE

# Interpreter de mensagens recebidas. Cada tipo de mensagem tem um tratamento diferente.
def interpreter(vizinhos, ip, port, clock, tipo, arguments):
    global SELF_PATH
    if not arguments:
        arguments = ""
    
    
    vizinho = searchVizinhoIP(vizinhos, ip, port) # Quem mandou a mensagem
    vizinho.clock = clock # Atualiza o clock do vizinho
    
    match tipo:
        case "HELLO":
            if vizinho:
                updateClock(vizinho.iden, clock)
                updateStatus(vizinhos, vizinho.iden, "ONLINE")

            else:
                vizinho = Vizinho(len(vizinhos)+1, ip, int(port), "ONLINE")
                vizinhos.add(vizinho)
                print(f"\nAdicionando novo peer {vizinho.ip}:{vizinho.port}")
                updateClock(vizinho.iden, int(clock))

        case "BYE":
            if vizinho:
                updateClock(vizinho.iden, clock)
                updateStatus(vizinhos, vizinho.iden, "OFFLINE")
        
        case "GET_PEERS":
            if searchVizinho(vizinhos, vizinho.iden) is None:
                v = Vizinho(len(vizinhos) + 1, ip, port, "ONLINE")
                vizinhos.add(v)
            updateClock(vizinho.iden, clock)
            lista = []
            lista.append(str(len(vizinhos)-1))
            for i in vizinhos:
                if i != vizinho:
                    lista.append(f"{i.ip}:{str(i.port)}:{i.status}:{i.clock}")
            args = " ".join(lista)
            sendMessage(vizinho.iden, "PEER_LIST", args)
        
        case "PEER_LIST":
            updateClock(vizinho.iden, clock)
            for i in arguments[1:]:
                ph = i.split(":")
                ip, port, status, temp_clock = ph[0], int(ph[1]), ph[2], int(ph[3])

                if searchVizinhoIP(vizinhos, ip, port) is not None:
                    updateClock(vizinho.iden, temp_clock)
                    updateStatus(vizinhos, vizinho.iden, status)
                    print(f"Atualizando peer {vizinho.ip}:{vizinho.port} para {status}")

                if searchVizinhoIP(vizinhos, ip, port) is None:
                    v = Vizinho(len(vizinhos) + 1, ip, port, status)
                    vizinhos.add(v)
                    print(f"Adicionando novo peer {v.ip}:{v.port} status {v.status}")
            event.set()
                
                
        
        case "LS":
            updateClock(vizinho.iden, clock)
            if os.path.exists(SELF_PATH) and os.path.isdir(SELF_PATH):
                file_list = []
                for filename in os.listdir(SELF_PATH):
                    file_path = os.path.join(SELF_PATH, filename)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        file_list.append(f"{filename}:{file_size}")
                    
                args = " ".join(file_list)
                sendMessage(vizinho.iden, "LS_LIST", args)
        
        case "LS_LIST":
            updateClock(vizinho.iden, clock)
            for l, i in enumerate(arguments, start=1):
                ph = i.split(":")
                nome, tamanho = ph[0], int(ph[1])
                arquivo = Arquivos(l, nome, tamanho, vizinho.iden)
                arquivos_rede.append(arquivo)
            event.set()
        
        case "DL":
            updateClock(vizinho.iden, clock)
            nome, int1, int2 = arguments[0], int(arguments[1]), int(arguments[2])
            with open(os.path.join(SELF_PATH, nome), 'rb') as file:
                bd = file.read()
                bd64 = b64.b64encode(bd)
                tipo = "FILE"
                sendMessage(vizinho.iden, tipo, f"{nome} {int1} {int2} {bd64.decode()}")
        
        case "FILE":
            updateClock(vizinho.iden, clock)
            nome, int1, int2, bd64 = arguments[0], int(arguments[1]), int(arguments[2]), arguments[3]
            bd = b64.b64decode(bd64)
            with open(os.path.join(SELF_PATH, nome), 'wb') as file:
                file.write(bd)
                print(f"Arquivo {nome} baixado com sucesso!")
                
                
                            
            
                
                

# Thread de escuta para receber mensagens de outros peers
def listener():
    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen.bind((SELF_IP, int(SELF_PORT)))
    listen.listen(5)
    listen.settimeout(1)
    while not sair:
        try:
            conn, addr = listen.accept()
            data = recv_eof(conn)

            vizinho_ip_port, peer_clock, tipo, *arguments = data.split()
            vizinho_ip, vizinho_port = vizinho_ip_port.split(":")
            vizinho_port = int(vizinho_port)
            peer_clock = int(peer_clock)

            if tipo == "PEER_LIST":
                print(f"Resposta recebida: \"{data}\"") # Sintaxe diferente para Obter peers (porque é uma resposta)
            else:
                print(f"Mensagem recebida: \"{data}\"")
            
            if arguments:
                interpreter(vizinhos, vizinho_ip, vizinho_port, peer_clock, tipo, arguments) # Com argumentos
            else:
                interpreter(vizinhos, vizinho_ip, vizinho_port, peer_clock, tipo, "")  # Sem argumentos
            
            if tipo == "LS_LIST" or tipo == "FILE":
                event.set()
                
            conn.close()

        except socket.timeout:
            pass


#######################################################################################

# SENDS

def sendHello(iden): # Listar peers e enviar hello para o vizinho
    tipo = "HELLO"
    vizinho = searchVizinho(vizinhos, iden)
    
    addClock()
    result = sendMessage(vizinho.iden, tipo, "")
    if result == 1:
        updateStatus(vizinhos, vizinho.iden, "ONLINE")

    else:
        print(f"Erro ao enviar mensagem para {vizinho.ip}:{str(vizinho.port)}")
        updateStatus(vizinhos, vizinho.iden, "OFFLINE")

def getPeers(vizinhos): # Obter peers e enviar mensagem para todos os vizinhos
    tipo = "GET_PEERS"
    for i in list(vizinhos):
        addClock()
        result = sendMessage(i.iden, tipo, "")
        if result == 1:
            updateStatus(vizinhos, i.iden, "ONLINE")
        else:
            print(f"Erro ao enviar mensagem para {i.ip}:{str(i.port)}")
            updateStatus(vizinhos, i.iden, "OFFLINE")
        event.wait()

def sendLS(vizinhos): # Enviar mensagem de listagem de arquivos para o vizinho
    tipo = "LS"
    for i in list(vizinhos):
        addClock()
        result = sendMessage(i.iden, tipo, "")
        if result == 1:
            updateStatus(vizinhos, i.iden, "ONLINE")
        else:
            print(f"Erro ao enviar mensagem para {i.ip}:{str(i.port)}")
            updateStatus(vizinhos, i.iden, "OFFLINE")
        event.wait()

def sendBye(iden): # Enviar mensagem de bye para o vizinho
    tipo = "BYE"
    sendMessage(iden, tipo, "")

def sendDL(arq_iden, int1, int2):
    
    tipo = "DL"
    arquivo = searchArq(arquivos_rede, arq_iden)
    vizinho = searchVizinho(vizinhos, arquivo.peer_iden)
    addClock()
    
    args = " ".join([arquivo.nome, str(int1), str(int2)])

    result = sendMessage(vizinho.iden, tipo, args)
    if result == 1:
        updateStatus(vizinhos, vizinho.iden, "ONLINE")
    else:
        print(f"Erro ao enviar mensagem para {vizinho.ip}:{str(vizinho.port)}")
        updateStatus(vizinhos, vizinho.iden, "OFFLINE")


#######################################################################################


def openFile(path):
    with open(path, 'r') as file:
        return file.read()

def console():
    print("> ")

if __name__ == "__main__":


    # Execução do programa
    if len(sys.argv) != 4:
        print("Uso: python eachare.py <selfIP> <vizinhos> <diretorio>")
        sys.exit()
    selfIP = sys.argv[1]
    SELF_IP, SELF_PORT = selfIP.split(":")
    vizinhos_filename = sys.argv[2]
    folder_name = sys.argv[3]  
    SELF_PATH = os.path.abspath(folder_name)

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
                    print(f"[{str(i.iden)}] {i.ip}:{str(i.port)} {i.status} (Clock: {str(i.clock)})")
                
                input1 = input("> ")
                if input1 == "0":
                    pass
                else:
                    sendHello(int(input1))

            case 2: #obter peers
                getPeers(vizinhos)    
            
            case 3: #Listar arquivos locais
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    contents = os.listdir(folder_path)
                    print(contents)
                else:
                    print(f"O diretório '{folder_name}' não existe ou não é um diretório.")

            case 4: #Buscar arquivos
                sendLS(vizinhos)

                listarArquivosRede()
                input4 = input("Escolha um arquivo para baixar: \n> ")
                if int(input4) == 0:
                    pass
                else:
                    sendDL(int(input4), 0, 0)
                    
            case 9: #Sair
                print("Saindo...")
                for i in vizinhos:
                    sendBye(i.iden)
                interface = 1
                sair = True
                listen_thread.join()
                sys.exit()
            

