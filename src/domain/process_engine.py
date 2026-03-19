# src/domain/process_engine.py
import time

class WatchdogProcessEngine:
    """Motor que avalia as regras de negócio e decide as ações (Clean Architecture)"""
    def __init__(self):
        # Memória de curto prazo para cada processo
        self.process_states = {}

    def get_or_create_state(self, process_name):
        if process_name not in self.process_states:
            self.process_states[process_name] = {
                "cpu_start_time": 0,
                "ram_start_time": 0,
                "hb_start_time": 0,
                "last_death_time": 0, # Para calcular o Cooldown
                "crash_count": 0,
                "last_crash_time": 0,
                "script_executed": False
            }
        return self.process_states[process_name]

    def evaluate_process(self, process_name, os_data, config):
        """
        Avalia o status atual do processo contra as regras da UI.
        Retorna uma tupla: (Ação, Motivo, PID_Alvo)
        Ações possíveis: "Nada", "Iniciar", "Parar_Forcado", "Parar_Elegante", "Alerta_Critico"
        """
        now = time.time()
        state = self.get_or_create_state(process_name)
        status_real = os_data.get("status", "Fechado")
        pid = os_data.get("pid", 0)

        # --- 1. MODO DE MANUTENÇÃO (SNOOZE) ---
        snooze = config.get("snooze", {})
        if snooze.get("active", False):
            until = snooze.get("until", 0)
            if until == -1 or now < until:
                return "Nada", "", None

        regra_principal = config.get("regra", "Não Reiniciar")

        # --- 2. BLACKLIST (SEMPRE ENCERRAR) ---
        if regra_principal == "Sempre Encerrar (Blacklist)":
            if status_real == "Em Execução":
                # Como é Blacklist, ignoramos a elegância e disparamos a Guilhotina
                return "Parar_Forcado", "Processo na Blacklist detetado", pid
            return "Nada", "", None

        # --- 3. PROCESSO ESTÁ RODANDO (AVALIAR DESEMPENHO) ---
        if status_real == "Em Execução":
            state["last_death_time"] = 0 # Reseta o timer de morte
            
            perf_cfg = config.get("desempenho", {})
            tol = perf_cfg.get("tolerance", 30)

            # Avaliar CPU
            max_cpu = perf_cfg.get("cpu_max", 0.0)
            if max_cpu > 0 and os_data.get("cpu", 0.0) > max_cpu:
                if state["cpu_start_time"] == 0: state["cpu_start_time"] = now
                elif now - state["cpu_start_time"] >= tol:
                    state["cpu_start_time"] = 0
                    return self._handle_kill_decision(config, f"CPU excedeu {max_cpu}% por {tol}s", pid)
            else: state["cpu_start_time"] = 0

            # Avaliar RAM
            max_ram = perf_cfg.get("ram_max", 0.0)
            if max_ram > 0 and os_data.get("ram", 0.0) > max_ram:
                if state["ram_start_time"] == 0: state["ram_start_time"] = now
                elif now - state["ram_start_time"] >= tol:
                    state["ram_start_time"] = 0
                    return self._handle_kill_decision(config, f"RAM excedeu {max_ram}MB por {tol}s", pid)
            else: state["ram_start_time"] = 0

            # Avaliar Heartbeat (0% CPU)
            if perf_cfg.get("heartbeat_enabled", False) and os_data.get("cpu", 0.0) == 0.0:
                hb_timeout = perf_cfg.get("heartbeat_timeout", 5) * 60
                if state["hb_start_time"] == 0: state["hb_start_time"] = now
                elif now - state["hb_start_time"] >= hb_timeout:
                    state["hb_start_time"] = 0
                    return self._handle_kill_decision(config, f"Inatividade detetada ({hb_timeout/60} min)", pid)
            else: state["hb_start_time"] = 0

            return "Nada", "", None

        # --- 4. PROCESSO ESTÁ FECHADO/AUSENTE (AVALIAR REINÍCIO E COOLDOWN) ---
        if status_real != "Em Execução":
            # Regista a hora exata que notou a morte para calcular o Cooldown
            if state["last_death_time"] == 0:
                state["last_death_time"] = now

            if regra_principal in ["Sempre Reiniciar", "Reiniciar se erro Windows"]:
                
                # Tratar Emergência (Crash Loops)
                em_cfg = config.get("emergencia", {})
                max_falhas = em_cfg.get("max_falhas", 3)
                
                # Se falhou mais vezes que o permitido, aborta o reinício
                if state["crash_count"] >= max_falhas:
                    if not state["script_executed"] and em_cfg.get("script_path"):
                        state["script_executed"] = True
                        return "Alerta_Critico", f"Crash Loop: Falhou {max_falhas}x", em_cfg.get("script_path")
                    return "Nada", "", None

                # Avaliar Cooldown
                exec_cfg = config.get("execucao", {})
                cooldown_enabled = exec_cfg.get("cooldown_enabled", False)
                cooldown = exec_cfg.get("cooldown", 10)
                
                if cooldown_enabled and (now - state["last_death_time"] < cooldown):
                    return "Nada", "", None
                state["crash_count"] += 1 
                state["last_crash_time"] = now
                return "Iniciar", f"Regra: {regra_principal}", None

        return "Nada", "", None

    def _handle_kill_decision(self, config, reason, pid):
        """Decide se o kill deve ser elegante ou forçado baseado na UI"""
        graceful = config.get("execucao", {}).get("graceful_close", False)
        if graceful:
            return "Parar_Elegante", reason, pid
        return "Parar_Forcado", reason, pid