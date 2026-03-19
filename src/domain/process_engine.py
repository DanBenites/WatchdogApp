# src/domain/process_engine.py
import time

class WatchdogProcessEngine:
    def __init__(self):
        self.process_states = {}

    def get_or_create_state(self, process_name):
        if process_name not in self.process_states:
            self.process_states[process_name] = {
                "cpu_start_time": 0, "ram_start_time": 0, "hb_start_time": 0,
                "last_death_time": 0, "last_crash_time": 0,
                "crash_count": 0, "perf_retry_count": 0, "hb_retry_count": 0,
                "script_executed": False, "exit_logged": False,
                "killed_by_us": False # NOVO: Diz-nos se fomos nós que puxámos a Guilhotina!
            }
        return self.process_states[process_name]

    def evaluate_process(self, process_name, os_data, config):
        now = time.time()
        state = self.get_or_create_state(process_name)
        status_real = os_data.get("status", "Fechado")
        pid = os_data.get("pid", 0)
        regra_principal = config.get("regra", "Não Reiniciar")

        # 1. REGRA: NÃO REINICIAR
        if regra_principal == "Não Reiniciar":
            return "Nada", "", None

        # 2. REGRA: SEMPRE ENCERRAR (BLACKLIST)
        if regra_principal == "Sempre Encerrar (Blacklist)":
            if status_real == "Em Execução":
                return "Parar_Forcado", "Processo na Blacklist detetado", pid
            return "Nada", "", None

        # ==========================================
        # AVALIAÇÃO DE LIMITES E INATIVIDADE
        # ==========================================
        if status_real == "Em Execução":
            state["last_death_time"] = 0 
            state["exit_logged"] = False 
            
            perf_cfg = config.get("desempenho", {})
            tol = perf_cfg.get("tolerance", 30)

            # --- LIMITE DE CPU E RAM ---
            max_cpu = perf_cfg.get("cpu_max", 0.0)
            if max_cpu > 0 and os_data.get("cpu", 0.0) > max_cpu:
                if state["cpu_start_time"] == 0: state["cpu_start_time"] = now
                elif now - state["cpu_start_time"] >= tol:
                    state["cpu_start_time"] = 0
                    return self._process_kill_limit(state, config, "perf_retry_count", perf_cfg.get("max_restarts", 3), f"CPU Alta ({max_cpu}%)", pid, regra_principal)
            else: state["cpu_start_time"] = 0

            max_ram = perf_cfg.get("ram_max", 0.0)
            if max_ram > 0 and os_data.get("ram", 0.0) > max_ram:
                if state["ram_start_time"] == 0: state["ram_start_time"] = now
                elif now - state["ram_start_time"] >= tol:
                    state["ram_start_time"] = 0
                    return self._process_kill_limit(state, config, "perf_retry_count", perf_cfg.get("max_restarts", 3), f"Memória Cheia ({max_ram}MB)", pid, regra_principal)
            else: state["ram_start_time"] = 0

            # --- LIMITE DE INATIVIDADE (HEARTBEAT) ---
            if perf_cfg.get("heartbeat_enabled", False) and os_data.get("cpu", 0.0) == 0.0:
                hb_timeout = perf_cfg.get("heartbeat_timeout", 5) * 60
                if state["hb_start_time"] == 0: state["hb_start_time"] = now
                elif now - state["hb_start_time"] >= hb_timeout:
                    state["hb_start_time"] = 0
                    return self._process_kill_limit(state, config, "hb_retry_count", perf_cfg.get("hb_max_restarts", 3), "Falha de Processo (Inativo)", pid, regra_principal)
            else: state["hb_start_time"] = 0

            return "Nada", "", None

        # ==========================================
        # AVALIAÇÃO DE QUEDA E REINÍCIO
        # ==========================================
        if status_real != "Em Execução":
            if state["last_death_time"] == 0:
                state["last_death_time"] = now

            if regra_principal in ["Sempre Reiniciar", "Reiniciar se erro Windows", "Reinício Condicional"]:
                
                exit_code = os_data.get("exit_code", -1)

                # 3. REGRA: REINICIAR SE ERRO WINDOWS
                if regra_principal == "Reiniciar se erro Windows":
                    global_cpu = os_data.get("global_cpu", 0)
                    global_ram = os_data.get("global_ram", 0)
                    sobrecarga = (global_cpu > 90 or global_ram > 90)

                    if exit_code == 0 and not sobrecarga:
                        if not state.get("exit_logged", False):
                            state["exit_logged"] = True
                            return "Log_Info", "Fechamento indevido pelo usuário (Exit Code 0)", None
                        return "Nada", "", None
                    
                    if sobrecarga:
                        regra_principal = f"{regra_principal} [SOBRECARGA SO]"

                # 4. REGRA: REINÍCIO CONDICIONAL
                elif regra_principal == "Reinício Condicional":
                    exec_cfg = config.get("execucao", {})
                    
                    if exec_cfg.get("check_exit_code", False) and exit_code == 0:
                        if not state.get("exit_logged", False):
                            state["exit_logged"] = True
                            return "Log_Info", "Fechamento ignorado pela Condição (Exit Code 0)", None
                        return "Nada", "", None

                    cooldown_enabled = exec_cfg.get("cooldown_enabled", False)
                    cooldown = exec_cfg.get("cooldown", 0)
                    if cooldown_enabled and cooldown > 0:
                        if (now - state["last_death_time"]) < cooldown:
                            return "Nada", "", None 

                # 5. AÇÕES DE EMERGÊNCIA (CRASH LOOPS NATIVOS)
                # O Crash_Count só avança se o programa morreu sozinho!
                if not state["killed_by_us"]:
                    em_cfg = config.get("emergencia", {})
                    
                    # SÓ VERIFICA AS FALHAS SE ESTIVER HABILITADO PELA UI
                    if em_cfg.get("enabled", False):
                        max_falhas = em_cfg.get("max_falhas", 3)
                        
                        if state["crash_count"] >= max_falhas:
                            if not state["script_executed"] and em_cfg.get("script_path"):
                                state["script_executed"] = True
                                return "Alerta_Critico", f"Crash Loop: Caiu sozinho {max_falhas}x", em_cfg.get("script_path")
                            return "Nada", "", None # Mantém bloqueado
                        
                        state["crash_count"] += 1 
                        state["last_crash_time"] = now
                else:
                    # Como fomos nós a matá-lo por excesso de limites, resetamos a flag 
                    # e deixamos iniciar (a falha já foi contada no Desempenho ou no Heartbeat)
                    state["killed_by_us"] = False

                return "Iniciar", f"Regra: {regra_principal}", None

        return "Nada", "", None

    def _process_kill_limit(self, state, config, counter_name, max_restarts, reason, pid, regra):
        """Lida com a contagem isolada de cada tipo de morte antes de enviar o sinal"""
        if state[counter_name] >= max_restarts:
            if not state["script_executed"] and config.get("emergencia", {}).get("script_path"):
                state["script_executed"] = True
                return "Alerta_Critico", f"Limite Excedido ({reason}): {max_restarts}x", config.get("emergencia", {}).get("script_path")
            return "Nada", "", None
        
        # Incrementa o contador EXATO do container responsável
        state[counter_name] += 1
        # Avisa o motor: "Fomos nós que matámos, não aumentem o contador de Emergência!"
        state["killed_by_us"] = True
        
        return self._handle_kill_decision(config, reason, pid, regra)

    def _handle_kill_decision(self, config, reason, pid, regra):
        if regra == "Reinício Condicional":
            graceful = config.get("execucao", {}).get("graceful_close", False)
            if graceful:
                return "Parar_Elegante", reason, pid
        return "Parar_Forcado", reason, pid