# src/infrastructure/service_adapter.py
import psutil
import subprocess
import winreg

class ServiceAdapter:
    """Adaptador responsável exclusivo por interagir com os Serviços do Windows."""
    
    _process_cache = {} # Cache essencial para ler a CPU corretamente em intervalos

    @staticmethod
    def _get_service_group(service_name):
        """Lê o Grupo do serviço nativamente pelo Registo do Windows ou pelo parâmetro do svchost."""
        try:
            chave_caminho = f"SYSTEM\\CurrentControlSet\\Services\\{service_name}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chave_caminho) as key:
                # 1. Tenta obter o Load Order Group (Grupo Oficial de Inicialização)
                try:
                    group, _ = winreg.QueryValueEx(key, "Group")
                    if group and group.strip(): 
                        return group
                except FileNotFoundError:
                    pass # Não tem grupo oficial, vamos tentar o plano B
                
                # 2. Tenta extrair o Svchost Group do caminho do executável (ImagePath)
                try:
                    image_path, _ = winreg.QueryValueEx(key, "ImagePath")
                    # Procura pelo parâmetro "-k" que define o grupo do svchost
                    if "-k " in image_path.lower():
                        # Ex: "%SystemRoot%\system32\svchost.exe -k netsvcs" -> pega o "netsvcs"
                        partes = image_path.lower().split("-k ")
                        if len(partes) > 1:
                            svchost_group = partes[1].split()[0].strip()
                            # Capitaliza a primeira letra para ficar bonito (ex: Netsvcs)
                            return svchost_group.capitalize()
                except FileNotFoundError:
                    pass

                return "N/D"
        except (FileNotFoundError, OSError):
            return "N/D"
        except Exception:
            return "N/D"

    @staticmethod
    def get_all_services():
        """Retorna uma lista de todos os serviços instalados no Windows."""
        services = []
        for svc in psutil.win_service_iter():
            try:
                nome = svc.name()
                
                try: display = svc.display_name()
                except Exception: display = nome
                
                # Usa o display_name como 'desc' para replicar o Gerenciador de Tarefas
                services.append({
                    "name": nome,
                    "display_name": display,
                    "desc": display 
                })
            except Exception:
                continue
                
        return sorted(services, key=lambda x: x["name"].lower())

    @staticmethod
    def get_service_info(name):
        """Retorna os dados detalhados em tempo real de um serviço (incluindo CPU, RAM e Disco)."""
        import time # Certifique-se de que o time está importado
        data = {
            "name": name, "status": "Ausente", "pid": "-", 
            "desc": "N/D", "display_name": "N/D", "group": "N/D",
            "cpu": 0.0, "ram": 0.0, "disk": 0.0
        }
        try:
            svc = psutil.win_service_get(name)
            data["status"] = svc.status()
            
            try: data["display_name"] = svc.display_name()
            except Exception: pass
            
            data["desc"] = data["display_name"]
            data["group"] = ServiceAdapter._get_service_group(name)

            if data["status"] == 'running':
                pid = svc.pid()
                if pid:
                    data["pid"] = str(pid)
                    try:
                        pid_int = int(pid)
                        if pid_int not in ServiceAdapter._process_cache:
                            p = psutil.Process(pid_int)
                            ServiceAdapter._process_cache[pid_int] = {
                                "proc": p,
                                "last_io": p.io_counters() if hasattr(p, 'io_counters') else None,
                                "last_time": time.time()
                            }
                            p.cpu_percent(interval=None) # Inicializa a leitura de CPU
                        else:
                            cache = ServiceAdapter._process_cache[pid_int]
                            p = cache["proc"]
                            
                            # 1. Leitura de CPU e RAM
                            data["cpu"] = p.cpu_percent(interval=None)
                            data["ram"] = round(p.memory_info().rss / (1024 * 1024), 2)
                            
                            # 2. Leitura de Disco (Cálculo de MB/s real)
                            if hasattr(p, 'io_counters'):
                                current_io = p.io_counters()
                                current_time = time.time()
                                if cache["last_io"] and current_time > cache["last_time"]:
                                    # Soma os bytes lidos e escritos desde a última checagem
                                    bytes_read = current_io.read_bytes - cache["last_io"].read_bytes
                                    bytes_write = current_io.write_bytes - cache["last_io"].write_bytes
                                    total_mb = (bytes_read + bytes_write) / (1024 * 1024)
                                    time_diff = current_time - cache["last_time"]
                                    
                                    # Calcula os Megabytes por segundo
                                    data["disk"] = round(total_mb / time_diff, 2)
                                
                                # Atualiza o cache para a próxima volta do loop
                                cache["last_io"] = current_io
                                cache["last_time"] = current_time
                                
                    except Exception:
                        if int(pid) in ServiceAdapter._process_cache:
                            del ServiceAdapter._process_cache[int(pid)]
        except Exception:
            pass
        return data

    @staticmethod
    def start_service(name):
        return ServiceAdapter._run_sc_command(f'sc start "{name}"')

    @staticmethod
    def stop_service(name):
        return ServiceAdapter._run_sc_command(f'sc stop "{name}"')

    @staticmethod
    def pause_service(name):
        return ServiceAdapter._run_sc_command(f'sc pause "{name}"')

    @staticmethod
    def continue_service(name):
        return ServiceAdapter._run_sc_command(f'sc continue "{name}"')

    @staticmethod
    def set_startup_type(name, startup_type):
        """Altera o tipo de inicialização do serviço no Windows (exige espaço após 'start=')."""
        return ServiceAdapter._run_sc_command(f'sc config "{name}" start= {startup_type}')

    @staticmethod
    def force_kill_service(name):
        """Mata o processo à força. Possui radar contra PIDs partilhados (svchost)."""
        try:
            # 1. Obtém o PID real
            pid = 0
            query_result = subprocess.run(f'sc queryex "{name}"', shell=True, capture_output=True, text=True, creationflags=0x08000000)
            for line in query_result.stdout.split('\n'):
                if "PID" in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        try: pid = int(parts[1].strip())
                        except ValueError: pass
                        break
                        
            if pid > 0:
                # 2. Radar de Segurança (Verifica quem mais partilha o PID)
                check_result = subprocess.run(f'tasklist /SVC /FI "PID eq {pid}"', shell=True, capture_output=True, text=True, creationflags=0x08000000)
                is_shared = False
                for line in check_result.stdout.split('\n'):
                    if str(pid) in line and "," in line:
                        is_shared = True
                        break
                
                if not is_shared:
                    # Tiro isolado! Seguro matar o processo inteiro.
                    cmd = f'taskkill /F /PID {pid} /T'
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
                    if res.returncode == 0 or "sucesso" in res.stdout.lower() or "success" in res.stdout.lower():
                        return True, f"Processo isolado (PID {pid}) encerrado à força."
            
            # 3. Fallback Seguro (Se for partilhado, mata pelo nome do serviço para proteger o SO)
            cmd = f'taskkill /F /FI "SERVICES eq {name}" /T'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
            out = res.stdout.lower() + res.stderr.lower()
            
            if "nenhuma tarefa" in out or "no tasks" in out:
                return False, "Nenhum processo correspondente encontrado."
            if res.returncode == 0 or "sucesso" in out or "success" in out:
                return True, "Serviço encerrado de forma segura via filtro nativo."
            
            return False, f"O serviço não pôde ser morto."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _run_sc_command(command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, creationflags=0x08000000)
            if result.returncode == 0 or result.returncode in [1056, 1062]:
                return True, "Comando executado com sucesso."
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception as e:
            return False, str(e)