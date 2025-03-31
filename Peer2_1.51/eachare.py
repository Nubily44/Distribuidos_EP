import socket
import threading
import os
import time 
import sys

SELF_IP = "127.0.0.1"
SELF_PORT = 5001

vizinhos = set()

class Vizinho:
    def __init__(self, iden, ip, port, status):
        self.iden = iden
        self.ip = ip
        self.port = port
        self.status = status
        self.clock = 0

    def setStatus(self, status):
        self.status = status
    
    def getStatus(self):
        return self.status
    
    def __hash__ (self):
        return hash((self.iden))

    def __eq__(self, other):
        if isinstance(other, Vizinho):
            return self.iden == other.iden and self.ip == other.ip and self.port == other.port
        return False


def searchVizinho(vizinhos, iden):
    return next((v for v in vizinhos if v.iden == iden), None)

def searchVizinhoIP(vizinhos, ip, port):
    return next((v for v in vizinhos if v.ip == ip and v.port == port), None)

def updateStatus(vizinhos, iden, newStatus):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.setStatus(newStatus)
        vizinhos.add(vizinho)
    
    print(f"Atualizando peer {vizinho.ip}:{vizinho.port} para {newStatus}")


def updateClock(vizinhos, iden):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.clock += 1
        vizinhos.add(vizinho)

    print(f"=> Atualizando relogio para {vizinho.clock}")


def sendMessage(iden, clock, tipo, arguments):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        vizinho = searchVizinho(vizinhos, iden)
        sock.connect((vizinho.ip, vizinho.port))

        self_ip_full = ":".join ([SELF_IP, str(SELF_PORT)])
        full_message = " ".join([self_ip_full, str(clock), tipo, arguments])

        print(f"Encaminhando mensagem \"{full_message}\" para {vizinho.ip}:{str(vizinho.port)}")

        sock.sendall(full_message.encode())

        sock.close()
        return 1
    except Exception as e:
        return e

def interpreter(vizinhos, ip, port, tipo, arguments):
    if not arguments:
        arguments = ""
    
    vizinho = searchVizinhoIP(vizinhos, ip, int(port))
    
    match tipo:
        case "HELLO":
            if vizinho:
                updateClock(vizinhos, vizinho.iden)
                updateStatus(vizinhos, vizinho.iden, "ONLINE")

            else:
                print(f"Novo peer {ip}:{port} encontrado")
                vizinho = Vizinho(len(vizinhos)+1, ip, int(port), "ONLINE")
                vizinhos.add(vizinho)
                print(f"Adicionando novo peer {vizinho.ip}:{vizinho.port}")
                updateClock(vizinhos, vizinho.iden)

        case "BYE":
            if vizinho:
                updateStatus(vizinhos, vizinho.iden, "OFFLINE")
        
        case "GET_PEERS":
            lista = []
            lista.append(str(len(vizinhos)-1))
            for i in vizinhos:
                if i != vizinho:
                    lista.append(f"{i.ip}:{str(i.port)}:{i.status}:0")
            args = " ".join(lista)
            sendMessage(vizinho.iden, vizinho.clock, "PEER_LIST", args)

            



def listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SELF_IP, int(SELF_PORT)))
    server.listen(5)

    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode()
        print(f"\nMensagem recebida: {data}")
        vizinho_ip_port, clock, tipo, *arguments = data.split()
        vizinho_ip, vizinho_port = vizinho_ip_port.split(":")
        if arguments:
            interpreter(vizinhos, vizinho_ip, vizinho_port, tipo, arguments)
        else:
            interpreter(vizinhos, vizinho_ip, vizinho_port, tipo, "")


        conn.close()


def sendHello(iden):
    vizinho = searchVizinho(vizinhos, iden)
    tipo = "HELLO"
    if sendMessage(vizinho.iden, vizinho.clock, tipo, "") == 1:

        updateClock(vizinhos, vizinho.iden)

        updateStatus(vizinhos, vizinho.iden, "ONLINE")

    else: 
        print(sendMessage(vizinho.iden, vizinho.clock, tipo, ""))
        print(f"Erro ao enviar mensagem para {vizinho.ip}:{str(vizinho.port)}")
        updateStatus(vizinhos, vizinho.iden, "OFFLINE")

def getPeers(vizinhos):
    for i in vizinhos:
        sendMessage(i.iden, i.clock, "GET_PEERS", "")

def sendBye(iden):
    vizinho = searchVizinho(vizinhos, iden)
    sendMessage(iden, vizinho.clock, "BYE", "")





def openFile(path):
    with open(path, 'r') as file:
        return file.read()

    



if __name__ == "__main__":
    print("Iniciando o programa...\n")

    #if len(sys.argv) != 3:
    #    print("Usage: python3 eachare.py <selfIP> <vizinhos> ")
    #    sys.exit
    #selfIP = sys.argv[1]
    #vizinhos_filename = sys.argv[2]
    
    listen_thread = threading.Thread(target=listener)
    listen_thread.start()

    folder_name = "dir"  
    script_dir = os.path.dirname(os.path.abspath(__file__))  
    folder_path = os.path.join(script_dir, folder_name)
    if not os.path.exists(folder_path):
        os._exit(0)


    vizinhos_filename = "vizinhos.txt"
    vizinhos_ips = openFile(vizinhos_filename).split("\n")

    temp = 1
    for i in vizinhos_ips:
        ph = i.split(":")
        v = Vizinho(temp, ph[0], int(ph[1]), "OFFLINE")
        vizinhos.add(v)
        temp += 1
        print(f"Adicionando vizinho {v.ip}:{v.port}")

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
                    print(f"[{str(i.iden)}] " + i.ip + ":" + str(i.port) + " - " + i.status + " - " + "(clock: " + str(i.clock) + ")")
                
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
                os._exit(0)
            

