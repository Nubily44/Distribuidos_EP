import socket
import threading
import os
import time 
import sys

CLOCK = 0

SELF_IP = None
SELF_PORT = None

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

def updateStatus(vizinhos, iden, newStatus):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.setStatus(newStatus)
        vizinhos.add(vizinho)

def updateClock(vizinhos, iden):
    vizinho = searchVizinho(vizinhos, iden)
    if vizinho:
        vizinhos.remove(vizinho)
        vizinho.clock += 1
        vizinhos.add(vizinho)


def sendMessage(ip, port, clock, message):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, int(port)))

        self_ip_full = ":".join ([SELF_IP, SELF_PORT])
        full_message = " ".join([self_ip_full, str(clock), message])

        print(f"Encaminhando mensagem {full_message} para {ip}:{port}")
        sock.sendall(full_message.encode())

        sock.close()
    except Exception as e:
        print(f"Erro ao enviar mensagem para {ip}:{port} - {e}")


def listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SELF_IP, int(SELF_PORT)))
    server.listen(5)

    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode()
        peer_ip_port, clock, *arguments  = data.split(" ")
        peer_ip, peer_port = peer_ip_port.split(":")
        
        print("Mensagem recebida: ")

        conn.close()

def openFile(path):
    with open(path, 'r') as file:
        return file.read()

    



if __name__ == "__main__":
    print("Iniciando o programa...")

    #if len(sys.argv) != 3:
    #    print("Usage: python3 eachare.py <selfIP> <vizinhos> ")
    #    sys.exit
    #selfIP = sys.argv[1]
    #vizinhos_filename = sys.argv[2]

    SELF_IP = "127.0.0.1"
    SELF_PORT = "5000"
    
    vizinhos_filename = "vizinhos.txt"
    vizinhos_ips = openFile(vizinhos_filename).split("\n")
    vizinhos = set()

    temp = 1
    for i in vizinhos_ips:
        ph = i.split(":")
        v = Vizinho(temp, ph[0], int(ph[1]), "OFFLINE")
        vizinhos.add(v)
        temp += 1

    print("Vizinhos:")
    for i in vizinhos:
        print(f"[{str(i.iden)}] " + i.ip + ":" + str(i.port) + " - " + i.status + " - " + str(i.clock))
    
    updateStatus(vizinhos, 1, "ONLINE")
    updateClock(vizinhos, 2)
    
    print("Vizinhos:")
    for i in vizinhos:
        print(f"[{str(i.iden)}] "  + i.ip + ":" + str(i.port) + " - " + i.status + " - " + str(i.clock))

    

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
        print("aaaaaaaaa" + option)
        match option:

            case 1: # Listar peers
                print("Lista de peers..."
                      "[0] voltar para o menu anterior")
                
                for i in vizinhos:
                    print(i.ip + ":" + i.port + " - " + i.status)
                
                input1 = input("> ")
                
            

