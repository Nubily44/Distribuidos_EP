import socket
import threading
import os
import time 
import sys

CLOCK = 0

class vizinho:
    def __init__(self, ip, port, status):
        self.ip = ip
        self.port = port
        self.status = status

    def setStatus(self, status):
        self.status = status
    
    def getStatus(self):
        return self.status


def updateStatus(vizinhos, ip, port, newStatus):

    vizinho = next((v for v in vizinhos if v.ip == ip and v.port == port), None)

    if vizinho:
        vizinho.setStatus(newStatus)
    else:
        pass


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

    selfIP = "26.204.92.82"
    
    vizinhos_filename = "vizinhos.txt"
    vizinhos_ips = openFile(vizinhos_filename).split("\n")
    vizinhos = set()


    for i in vizinhos_ips:
        ph = i.split(":")
        v = vizinho(ph[0], ph[1], "OFFLINE")
        vizinhos.add(v)

    print("Vizinhos:")
    for i in vizinhos:
        print(i.ip + ":" + i.port)
    


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
        match option:

            case 1: # Listar peers
                print("Lista de peers..."
                      "[0] voltar para o menu anterior")
                
                for i in vizinhos:
                    print(i.ip + ":" + i.port + " - " + i.status)
                
                input1 = input("> ")
                
            

