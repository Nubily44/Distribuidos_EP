# Code by Lily and Dani (14567051 e 13659997)
# Windows 11, Python 3.12.10

import socket
import threading
import os
import time 
import sys
import base64 as b64
from operator import attrgetter


SELF_IP = ""
SELF_PORT = None
SELF_CLOCK = 0
SELF_PATH = ""
SELF_CHUNK = 256

event = threading.Event() # Eventos para sincronização de threads

vizinhos = set() # Set de vizinhos

arquivos_rede = [] # Lista de arquivos na rede

Buffer = [] # Buffer de chunks recebidos
BufferCount = 0 # Contador de chunks no buffer (para saber quando o ultimo chunk foi recebido)

statistics = [] # Lista de estatísticas do download (lista de StatisticItem, cada um com uma lista de Metric)

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


# Classe para armazenar os chunks recebidos
class BufferItem:
    def __init__(self, index, data):
        self.index = index
        self.data = data

# Classe para armazenar as métricas de cada chunk
class Metric:
    def __init__(self, index, tamanho, n_peers, tempo):
        self.index = index
        self.tamanho = tamanho
        self.n_peers = n_peers
        self.tempo = tempo

# Classe para armazenar as estatísticas de download
class StatisticItem:
    def __init__(self, chunk, n_peers, tamanho):
        self.Metrics = []
        self.status = "Pendente" # Finalizada ou Pendente
        self.chunk = chunk
        self.n_peers = n_peers
        self.tamanho = tamanho
        self.quant = 0
        self.tempo = 0
        self.desvio = 0
    
    def sortMetrics(self):
        self.Metrics = sorted(self.Metrics, key=attrgetter('index'))
    
    def addMetric(self, metric):
        #print(f"Adicionando métrica {metric.index} de tamanho {metric.tamanho} bytes e tempo {metric.tempo} segundos")
        self.Metrics.append(metric)
        self.sortMetrics()
    
    def searchMetric(self, index):
        return next((m for m in self.Metrics if m.index == index), None)
    
    def updateMetric(self, index, tempo):
        metric = self.searchMetric(index)
        #print(f"Tempo antigo: {metric.tempo}, index: {index}")
        if metric:
            metric.tempo = tempo - metric.tempo
        #print(f"Tempo antigo: {metric.tempo}, index: {index}")

    # Consolidate para calcular a média e desvio padrão dos tempos, após armazenar todos as métricas
    def consolidate(self):
        self.tempo = sum(m.tempo for m in self.Metrics)/len(self.Metrics)
        self.desvio = (sum((m.tempo - self.tempo) ** 2 for m in self.Metrics) / len(self.Metrics)) ** 0.5
        self.status = "Finalizada"
        #print("QUANT ATUALIZADO")
        self.quant += 1
        #print(f"Consolidando estatísticas: Tempo médio {self.tempo:.5f} segundos, Desvio padrão {self.desvio:.5f} segundos")
    
    


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
    def __init__(self, iden, nome, tamanho):
        self.iden = iden
        self.nome = nome
        self.tamanho = tamanho
        self.peer_iden = []
        
    def addPeer(self, peer_iden):
        if peer_iden not in self.peer_iden:
            self.peer_iden.append(peer_iden)

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

def searchArqNome(arquivos_rede, nome):
    return next((a for a in arquivos_rede if a.nome == nome), None)

def searchArqNomeETam(arquivos_rede, nome, tamanho):
    return next((a for a in arquivos_rede if a.nome == nome and a.tamanho == tamanho), None)

def sortBuffer(buffer):
    return sorted(buffer, key=attrgetter('index'))

def searchStat(statistics, chunk, n_peers, tamanho):
    return next((s for s in statistics if s.chunk == chunk and s.n_peers == n_peers and s.tamanho == tamanho), None)

def addStat(statistics, stat):
    existing_stat = searchStat(statistics, stat.chunk, stat.n_peers, stat.tamanho)
    
    if existing_stat:
        existing_stat.status = "Pendente"
        return existing_stat
        
    else:
        statistics.append(stat)
        return stat

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
    peer_width = max(len("Peer"), max(len(", ".join(str(p) for p in i.peer_iden)) for i in todos))
    id_width = max(len(str(i.iden)) for i in todos)

    print(f"{' ' * (id_width + 3)}{ 'Nome'.ljust(nome_width) } | { 'Tamanho'.rjust(tamanho_width) } | { 'Peer'.ljust(peer_width) }")



    for i in todos:
        if i.iden == 0:
            temp = ""
        else:
            temp_list = []
            for pid in i.peer_iden:
                vizinho = searchVizinho(vizinhos, pid)
                temp_list.append(f"{vizinho.ip}:{vizinho.port}")
            temp = ", ".join(temp_list)
        print(
            f"[{str(i.iden).rjust(id_width)}] "
            f"{str(i.nome).ljust(nome_width)} | "
            f"{str(i.tamanho).rjust(tamanho_width)} | "
            f"{str(temp).ljust(peer_width)}"
        )
        

def display_statistics(statistics):
        headers = ["Tam. chunk", "N peers", "Tam. arquivo", "N", "Tempo [s]", "Desvio"]
        rows = [
            [
                str(stat.chunk),
                str(stat.n_peers),
                str(stat.tamanho),
                str(stat.quant),
                f"{stat.tempo:.5f}",
                f"{stat.desvio:.5f}"
            ]
            for stat in statistics
        ]

        # Include headers in the data to compute max width
        columns = list(zip(*([headers] + rows)))
        col_widths = [max(len(item) for item in col) for col in columns]

        # Format string
        row_format = " | ".join(f"{{:<{w}}}" for w in col_widths)

        # Print header
        print(row_format.format(*headers))
        print("-" * (sum(col_widths) + 3 * (len(headers) - 1)))

        # Print each row
        for row in rows:
            print(row_format.format(*row))

#######################################################################################

#SEND

# Função de formatação de mensagens e envio. Padrão para TODAS AS MENSAGENS
def sendMessage(iden, tipo, arguments):
    try:
        
        event.clear()
        
        vizinho = searchVizinho(vizinhos, iden)
        self_ip_full = ":".join ([SELF_IP, str(SELF_PORT)])
        full_message = " ".join([self_ip_full, str(SELF_CLOCK), tipo, arguments])

        if tipo == "FILE":
            truncated = full_message if len(full_message) <= 40 else full_message[:40] + "..."
            print(f"Enviando resposta \"{truncated}\" para {vizinho.ip}:{str(vizinho.port)}")
        elif tipo == "PEER_LIST" or tipo == "LS_LIST":
            print(f"Enviando resposta \"{full_message}\" para {vizinho.ip}:{str(vizinho.port)}")
        else:
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
    global SELF_PATH, arquivos_rede, BufferCount
    if not arguments:
        arguments = ""
    
    # Quem mandou a mensagem
    if searchVizinhoIP(vizinhos, ip, port) is not None: 
        vizinho = searchVizinhoIP(vizinhos, ip, port)
        vizinho.clock = clock
    
    else:
        vizinho = Vizinho(len(vizinhos) + 1, ip, int(port), "ONLINE")
        vizinhos.add(vizinho)
        vizinho.clock = clock
    
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
                    vizinho_exis = searchVizinhoIP(vizinhos, ip, port)
                    if vizinho_exis.clock < temp_clock:
                        updateClock(vizinho_exis.iden, temp_clock)
                        updateStatus(vizinhos, vizinho_exis.iden, status)
                    else:
                        updateClock(vizinho_exis.iden, temp_clock)

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
            for l, i in enumerate(arguments, start=1): #Esse l é simplesmente o salvador de todos. NÃO TIRE ELE. ELE É SAGRADO.
                ph = i.split(":")
                nome, tamanho = ph[0], int(ph[1])
                
                if (searchArqNomeETam(arquivos_rede, nome, tamanho) is None):  
                    arquivo = Arquivos((1 + len(arquivos_rede)), nome, tamanho)
                    arquivo.addPeer(vizinho.iden)
                    arquivos_rede.append(arquivo)
                    
                else:
                    arquivo = searchArqNomeETam(arquivos_rede, nome, tamanho)
                    arquivo.tamanho = tamanho
                    arquivo.addPeer(vizinho.iden)

            event.set()
        
        case "DL":
            updateClock(vizinho.iden, clock)
            nome, chunk, index = arguments[0], int(arguments[1]), int(arguments[2])
            start = index * chunk
            
            with open(os.path.join(SELF_PATH, nome), 'rb') as file:
                
                file.seek(start)
                bd = file.read(chunk)
                bd64 = b64.b64encode(bd).decode()
                tipo = "FILE"
                args = " ".join([nome, str(chunk), str(index), bd64])
                sendMessage(vizinho.iden, tipo, args)
        
        case "FILE":
            
            updateClock(vizinho.iden, clock)
            nome, chunk, index, bd64 = arguments[0], int(arguments[1]), int(arguments[2]), arguments[3]
            
            Buffer.append(BufferItem(index, bd64))
            #print(f"-------------REC----------BufferCount: {BufferCount}")
            BufferCount -= 1
            #print(f"-------------REC----------BufferCount: {BufferCount}")
            arq = searchArqNome(arquivos_rede, nome)
            stat = searchStat(statistics, chunk, len(arq.peer_iden), arq.tamanho)
            stat.searchMetric(index)
            stat.updateMetric(index, round(time.time(), 2))
            
            if BufferCount == 0:
                path = os.path.join(SELF_PATH, nome)
                
                if not os.path.exists(path):
                    with open(path, 'wb') as f:
                        pass

                sortBuffer(Buffer)
                full_bytes = b"".join(b64.b64decode(item.data) for item in Buffer)
                with open(path, 'wb') as file:
                    file.write(full_bytes)
                
                stat.consolidate() # Consolidar depois de escrever NÃO INCLUI O TEMPO DE ESCRITA (os chunks ja foram recebidos, as métricas já foram atualizadas)
                # EU TO TE VENDO RENAN
                
                Buffer.clear()
                
                event.set()
                    
            
                    

                
                
                            
            
                
                

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

            if tipo == "FILE":
                truncated = data if len(data) <= 45 else data[:45] + "..."
                print(f"Resposta recebida: \"{truncated}\"")
                
            elif tipo == "PEER_LIST" or tipo == "LS_LIST":
                print(f"Resposta recebida: \"{data}\"")
            else:
                print(f"Mensagem recebida: \"{data}\"")
            
            
            if arguments:
                interpreter(vizinhos, vizinho_ip, vizinho_port, peer_clock, tipo, arguments) # Com argumentos
            else:
                interpreter(vizinhos, vizinho_ip, vizinho_port, peer_clock, tipo, "")  # Sem argumentos
            
            if tipo == "PEER_LIST" or tipo == "LS_LIST":
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
            event.wait()
        else:
            print(f"Erro ao enviar mensagem para {i.ip}:{str(i.port)}")
            updateStatus(vizinhos, i.iden, "OFFLINE")
        

def sendLS(vizinhos): # Enviar mensagem de listagem de arquivos para o vizinho
    tipo = "LS"
    for i in (v for v in vizinhos if v.status == "ONLINE"):
        addClock()
        result = sendMessage(i.iden, tipo, "")
        if result == 1:
            updateStatus(vizinhos, i.iden, "ONLINE")
            event.wait()
        else:
            print(f"Erro ao enviar mensagem para {i.ip}:{str(i.port)}")
            updateStatus(vizinhos, i.iden, "OFFLINE")
        

def sendBye(iden): # Enviar mensagem de bye para o vizinho
    tipo = "BYE"
    sendMessage(iden, tipo, "")

def sendDL(arq_iden):
    global SELF_CHUNK, BufferCount
    tipo = "DL"
    arquivo = searchArq(arquivos_rede, arq_iden)
    
    vizinhos_para_download = []
    
    for i in arquivo.peer_iden:
        vizinho = searchVizinho(vizinhos, i)
        vizinhos_para_download.append(vizinho)
    
    n_de_peers = len(vizinhos_para_download)
    n_de_iters = (arquivo.tamanho // SELF_CHUNK) + (1 if arquivo.tamanho % SELF_CHUNK > 0 else 0)
    
    #Cria a instancia final de Statistic
    stats = StatisticItem(SELF_CHUNK, n_de_peers, arquivo.tamanho)
    
    stats = addStat(statistics, stats)
    
    #print(f"-------------SND----------BufferCount: {BufferCount}")
    BufferCount += 1
    #print(f"-------------SND----------BufferCount: {BufferCount}")
            
    
    for i in range(n_de_iters):
        addClock()
        
        peer_index = i % n_de_peers
        vizinho = vizinhos_para_download[peer_index]
        
        args = " ".join([arquivo.nome, str(SELF_CHUNK), str(i)])

        result = sendMessage(vizinho.iden, tipo, args)
        
        
        
        stats.addMetric(Metric(i, arquivo.tamanho, n_de_peers, round(time.time(), 2)))
        
        
        if result == 1:
            updateStatus(vizinhos, vizinho.iden, "ONLINE")
            #print(f"-------------SND----------BufferCount: {BufferCount}")
            BufferCount += 1
            #print(f"-------------SND----------BufferCount: {BufferCount}")
            
            
        else:
            print(f"Erro ao enviar mensagem para {vizinho.ip}:{str(vizinho.port)}")
            updateStatus(vizinhos, vizinho.iden, "OFFLINE")
        
    #print(f"-------------SND----------BufferCount: {BufferCount}")
    BufferCount -= 1
    #print(f"-------------SND----------BufferCount: {BufferCount}")
    event.wait()
    time.sleep(1) # Espera o calculo do consolidate

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
    if os.path.isabs(folder_name):
        folder_path = folder_name
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, folder_name)

    if not os.path.exists(folder_path):
        print(f"O diretório '{folder_path}' não existe.")
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
                    print(f"arquivo escolhido {searchArq(arquivos_rede, int(input4)).nome}")
                    sendDL(int(input4))
                    arq = searchArq(arquivos_rede, int(input4))
                    if arq.tamanho == os.path.getsize(os.path.join(SELF_PATH, arq.nome)): # Verifica se o arquivo foi baixado corretamente
                        print(f"Arquivo {searchArq(arquivos_rede, int(input4)).nome} foi baixado com sucesso!")
            
            case 5: #Exibir estatisticas
                display_statistics(statistics)
                
            case 6: #Alterar tamanho de chunk
                input6 = input("Digite novo tamanho de chunk: \n> ")
                SELF_CHUNK = int(input6)
                print(f"    Tamanho de chunk alterado: {SELF_CHUNK}")
            
            case 9: #Sair
                print("Saindo...")
                for i in vizinhos:
                    sendBye(i.iden)
                interface = 1
                sair = True
                listen_thread.join()
                sys.exit()
            

