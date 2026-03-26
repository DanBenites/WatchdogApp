# src/infrastructure/service_adapter.py
import psutil
import subprocess

class ServiceAdapter:
    """Adaptador responsável exclusivo por interagir com os Serviços do Windows."""

    @staticmethod
    def get_all_services():
        """Retorna uma lista de todos os serviços instalados no Windows."""
        services = []
        for svc in psutil.win_service_iter():
            try:
                nome = svc.name()
                
                # Tenta obter o nome de exibição (fallback para o próprio nome)
                try:
                    display = svc.display_name()
                except Exception:
                    display = nome
                    
                # Tenta obter a descrição (ignora erros de FileNotFoundError do Windows)
                try:
                    desc = svc.description() or "Sem descrição disponível."
                except Exception:
                    desc = "Sem descrição disponível."

                services.append({
                    "name": nome,
                    "display_name": display,
                    "desc": desc
                })
            except Exception:
                # Ignora completamente serviços restritos (AccessDenied) ou que sumiram na hora da leitura
                continue
                
        # Ordena alfabeticamente pelo nome de exibição
        return sorted(services, key=lambda x: x["name"].lower())

    @staticmethod
    def get_service_info(name):
        """Retorna os dados detalhados em tempo real de um serviço."""
        data = {
            "name": name, "status": "Ausente", "pid": "-", 
            "desc": "N/D", "display_name": "N/D"
        }
        try:
            svc = psutil.win_service_get(name)
            data["status"] = svc.status() # running, stopped, start_pending, etc.
            
            try:
                pid = svc.pid()
                data["pid"] = str(pid) if pid else "-"
            except Exception: pass
            
            try:
                data["desc"] = svc.description() or "Sem descrição."
            except Exception: pass
            
            try:
                data["display_name"] = svc.display_name()
            except Exception: pass
            
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
        """Define se o serviço inicia com o Windows (auto, demand, disabled, delayed-auto)."""
        return ServiceAdapter._run_sc_command(f'sc config "{name}" start= {startup_type}')

    @staticmethod
    def _run_sc_command(command):
        """Executa comandos ocultos no sistema e retorna sucesso ou erro."""
        try:
            # creationflags=0x08000000 esconde a janela do terminal no Windows
            result = subprocess.run(command, shell=True, capture_output=True, text=True, creationflags=0x08000000)
            if result.returncode == 0:
                return True, "Comando executado com sucesso."
            else:
                return False, result.stderr.strip() or result.stdout.strip()
        except Exception as e:
            return False, str(e)