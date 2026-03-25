import psutil
import ctypes
from ..infrastructure.system_utils import SystemUtils
from ..infrastructure.persistence import PersistenceRepository

kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

class OSProcessUseCase:
    _process_cache = {}
    _process_handles = {} 
    _last_exit_codes = {} 

    @staticmethod
    def obter_processos_agrupados(termo_busca=""):
        return SystemUtils.listar_processos_agrupados(termo_busca)

    @staticmethod
    def obter_metricas_processos(lista_nomes):
        metricas = {nome: {"status": "Ausente", "cpu": 0.0, "ram": 0.0, "exit_code": OSProcessUseCase._last_exit_codes.get(nome, -1)} for nome in lista_nomes}
        processos_vivos_neste_ciclo = set()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                nome_proc = proc.info['name']
                
                if nome_proc in metricas:
                    try:
                        pid = proc.info['pid']
                        ram_mb = proc.info['memory_info'].rss / (1024 * 1024)
                        
                        if pid not in OSProcessUseCase._process_cache:
                            OSProcessUseCase._process_cache[pid] = psutil.Process(pid)
                            OSProcessUseCase._process_cache[pid].cpu_percent() 
                            cpu_pct = 0.0
                        else:
                            cpu_pct = OSProcessUseCase._process_cache[pid].cpu_percent()

                        # Prende o cabo (Handle) ao processo, sem bloquear a Thread
                        if pid not in OSProcessUseCase._process_handles:
                            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                            if handle:
                                OSProcessUseCase._process_handles[pid] = {"handle": handle, "name": nome_proc}

                        metricas[nome_proc]["status"] = "Em Execução"
                        metricas[nome_proc]["cpu"] += cpu_pct
                        metricas[nome_proc]["ram"] += ram_mb
                        metricas[nome_proc]["exit_code"] = 259 # 259 = STILL_ACTIVE no Windows
                        
                        processos_vivos_neste_ciclo.add(pid)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        if pid in OSProcessUseCase._process_cache:
                            del OSProcessUseCase._process_cache[pid]
        except Exception:
            pass 
            
        pids_para_remover = [pid for pid in OSProcessUseCase._process_cache if pid not in processos_vivos_neste_ciclo]
        for pid in pids_para_remover:
            del OSProcessUseCase._process_cache[pid]
            
        handles_para_remover = [pid for pid in OSProcessUseCase._process_handles if pid not in processos_vivos_neste_ciclo]
        for pid in handles_para_remover:
            try:
                dados_handle = OSProcessUseCase._process_handles[pid]
                handle = dados_handle["handle"]
                nome_proc = dados_handle["name"]

                exit_code_c = ctypes.c_ulong()
                # Lê o código de forma instantânea, sem esperar
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code_c)):
                    code = exit_code_c.value
                    if code != 259: # Se não estiver "STILL_ACTIVE", morreu de verdade
                        OSProcessUseCase._last_exit_codes[nome_proc] = code
                        if nome_proc in metricas and metricas[nome_proc]["status"] != "Em Execução":
                            metricas[nome_proc]["exit_code"] = code

                kernel32.CloseHandle(handle) 
            except Exception: pass
            
            del OSProcessUseCase._process_handles[pid]
            
        return metricas

class ProcessManagementUseCase:
    def __init__(self, config_data):
        self.config_data = config_data

    def adicionar_processos(self, lista_processos):
        adicionados = 0
        for proc in lista_processos:
            nome = proc['nome']
            if nome not in self.config_data.processos:
                self.config_data.processos[nome] = {'path': proc['path'], 'regra': "Não Reiniciar", 'status': "Aguardando"}
                adicionados += 1
        if adicionados > 0: PersistenceRepository.salvar(self.config_data)
        return adicionados

    def remover_processo(self, nome):
        if nome in self.config_data.processos:
            del self.config_data.processos[nome]
            PersistenceRepository.salvar(self.config_data)
            return True
        return False

    def atualizar_regra(self, nome, nova_regra):
        if nome in self.config_data.processos:
            self.config_data.processos[nome]['regra'] = nova_regra
            PersistenceRepository.salvar(self.config_data)
            return True
        return False