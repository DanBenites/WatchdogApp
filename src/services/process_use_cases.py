# src/services/process_use_cases.py
import psutil
from ..infrastructure.system_utils import SystemUtils
from ..infrastructure.persistence import PersistenceRepository

class OSProcessUseCase:
    """Caso de Uso para leitura e agregação de dados do Sistema Operativo."""
    
    # Cache estático para armazenar os objetos de processo e calcular a CPU corretamente
    _process_cache = {}

    @staticmethod
    def obter_processos_agrupados(termo_busca=""):
        return SystemUtils.listar_processos_agrupados(termo_busca)

    @staticmethod
    def obter_metricas_processos(lista_nomes):
        """Retorna a soma de CPU e RAM e o Status real dos processos fornecidos."""
        metricas = {nome: {"status": "Ausente", "cpu": 0.0, "ram": 0.0} for nome in lista_nomes}
        processos_vivos_neste_ciclo = set()
        
        try:
            # Varre todos os processos do Windows rapidamente
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                nome_proc = proc.info['name']
                
                # Se for um processo que estamos a monitorar
                if nome_proc in metricas:
                    try:
                        pid = proc.info['pid']
                        
                        # Calcula RAM em Megabytes
                        ram_mb = proc.info['memory_info'].rss / (1024 * 1024)
                        
                        # Lógica de CPU com Cache (vital para não retornar sempre 0.0)
                        if pid not in OSProcessUseCase._process_cache:
                            OSProcessUseCase._process_cache[pid] = psutil.Process(pid)
                            OSProcessUseCase._process_cache[pid].cpu_percent() # Descarta a 1ª leitura
                            cpu_pct = 0.0
                        else:
                            # Lê a CPU real baseada no tempo desde a última consulta
                            cpu_pct = OSProcessUseCase._process_cache[pid].cpu_percent()

                        metricas[nome_proc]["status"] = "Em Execução"
                        metricas[nome_proc]["cpu"] += cpu_pct
                        metricas[nome_proc]["ram"] += ram_mb
                        
                        processos_vivos_neste_ciclo.add(pid)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        if pid in OSProcessUseCase._process_cache:
                            del OSProcessUseCase._process_cache[pid]
        except Exception as e:
            pass # Proteção contra erros genéricos do WMI/SO
            
        # Limpeza de memória: Remove do cache os processos que foram fechados
        pids_para_remover = [pid for pid in OSProcessUseCase._process_cache if pid not in processos_vivos_neste_ciclo]
        for pid in pids_para_remover:
            del OSProcessUseCase._process_cache[pid]
            
        return metricas

class ProcessManagementUseCase:
    """Caso de Uso para gerir as configurações de monitorização (Clean Architecture)."""
    def __init__(self, config_data):
        self.config_data = config_data

    def adicionar_processos(self, lista_processos):
        """Recebe uma lista de dicionários com nome e path, e adiciona à configuração."""
        adicionados = 0
        for proc in lista_processos:
            nome = proc['nome']
            if nome not in self.config_data.processos:
                self.config_data.processos[nome] = {
                    'path': proc['path'], 
                    'regra': "Não Reiniciar", 
                    'status': "Aguardando"
                }
                adicionados += 1
        
        if adicionados > 0:
            PersistenceRepository.salvar(self.config_data)
        return adicionados

    def remover_processo(self, nome):
        """Remove um processo específico e guarda o estado."""
        if nome in self.config_data.processos:
            del self.config_data.processos[nome]
            PersistenceRepository.salvar(self.config_data)
            return True
        return False

    def atualizar_regra(self, nome, nova_regra):
        """Atualiza a regra de reinício de um processo específico."""
        if nome in self.config_data.processos:
            self.config_data.processos[nome]['regra'] = nova_regra
            PersistenceRepository.salvar(self.config_data)
            return True
        return False