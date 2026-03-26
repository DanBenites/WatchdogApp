# src/domain/service_engine.py
import time
from datetime import datetime

class WatchdogServiceEngine:
    """Motor de regras focado exclusivamente na lógica de Serviços do Windows."""
    
    def __init__(self):
        self.service_states = {}
        self.dias_pt = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }

    def get_or_create_state(self, service_name):
        """Garante a memória de curto prazo para cada serviço."""
        if service_name not in self.service_states:
            self.service_states[service_name] = {
                "cpu_start_time": 0, "ram_start_time": 0, "disk_start_time": 0, "hb_start_time": 0,
                "retry_count": 0, "perf_retry_count": 0, "hb_retry_count": 0,
                "last_state_action": 0, "last_perf_action": 0, "last_hb_action": 0,
                "script_executed": False, "last_schedule_run": "",
                "pending_status": "", "pending_start": 0,
                "domino_effect": False, # CORREÇÃO 2: Memória do Efeito Dominó
                "notified_status": ""   # CORREÇÃO 4: Prevenção de Spam de Alertas
            }
        return self.service_states[service_name]

    def remove_state(self, service_name):
        if service_name in self.service_states:
            del self.service_states[service_name]

    def _verificar_reset_falhas(self, state, cfg):
        """Reseta os contadores se o tempo de 'reset_days' já tiver passado."""
        now = time.time()
        
        em_reset = cfg.get("emergency", {}).get("reset_days", 0)
        if em_reset > 0 and state["last_state_action"] > 0:
            if (now - state["last_state_action"]) > (em_reset * 86400):
                state["retry_count"] = 0
                state["script_executed"] = False
                state["last_state_action"] = 0
                
        perf_reset = cfg.get("perf_limits", {}).get("reset_days", 0)
        if perf_reset > 0 and state["last_perf_action"] > 0:
            if (now - state["last_perf_action"]) > (perf_reset * 86400):
                state["perf_retry_count"] = 0
                state["last_perf_action"] = 0
                
        hb_reset = cfg.get("heartbeat", {}).get("reset_days", 0)
        if hb_reset > 0 and state["last_hb_action"] > 0:
            if (now - state["last_hb_action"]) > (hb_reset * 86400):
                state["hb_retry_count"] = 0
                state["last_hb_action"] = 0

    def _check_emergency(self, state, cfg, fail_type):
        """Verifica se a quantidade de falhas excedeu o limite."""
        now = time.time()
        em_cfg = cfg.get("emergency", {})
        
        if fail_type == "state" and not em_cfg.get("enabled", False):
            state["retry_count"] += 1
            state["last_state_action"] = now
            return False, None

        if fail_type == "state":
            max_retries = em_cfg.get("max_retries", 3)
            current_fails = state["retry_count"]
            script_path = em_cfg.get("run_script", "")
        elif fail_type == "perf":
            max_retries = cfg.get("perf_limits", {}).get("max_restarts", 3)
            current_fails = state["perf_retry_count"]
            script_path = ""
        elif fail_type == "hb":
            max_retries = cfg.get("heartbeat", {}).get("max_restarts", 3)
            current_fails = state["hb_retry_count"]
            script_path = ""

        if current_fails >= max_retries:
            if fail_type == "state": state["last_state_action"] = now
            elif fail_type == "perf": state["last_perf_action"] = now
            elif fail_type == "hb": state["last_hb_action"] = now

            script_to_run = None
            if fail_type == "state" and em_cfg.get("enabled", False) and script_path and not state["script_executed"]:
                state["script_executed"] = True
                script_to_run = script_path
            return True, script_to_run
        
        if fail_type == "state":
            state["retry_count"] += 1
            state["last_state_action"] = now
        elif fail_type == "perf":
            state["perf_retry_count"] += 1
            state["last_perf_action"] = now
        elif fail_type == "hb":
            state["hb_retry_count"] += 1
            state["last_hb_action"] = now
            
        return False, None

    def evaluate_service(self, name, info, cfg, get_info_callback):
        state = self.get_or_create_state(name)
        self._verificar_reset_falhas(state, cfg)
        
        status = info.get("status", "Ausente")
        now = time.time()

        # 1. SNOOZE
        snooze = cfg.get("snooze", {})
        if snooze.get("active", False):
            until = snooze.get("until", 0)
            if until == -1 or until > now:
                return "Nada", "Modo Manutenção (Snooze) Ativo", None
            else:
                cfg["snooze"]["active"] = False 

        # 2. SMART SCHEDULE
        sched = cfg.get("schedule", {})
        if sched.get("enabled", False) and status == "running":
            hoje = datetime.now()
            dia_cfg = sched.get("days", "Todos os Dias")
            
            if dia_cfg == "Todos os Dias" or dia_cfg == self.dias_pt[hoje.weekday()]:
                hora_cfg = sched.get("time", "03:00")
                if hoje.strftime("%H:%M") == hora_cfg and state["last_schedule_run"] != hoje.strftime("%Y-%m-%d"):
                    state["last_schedule_run"] = hoje.strftime("%Y-%m-%d")
                    return "Reiniciar", f"Smart Schedule: Reinício agendado para {hora_cfg}.", None

        # 3. DEADLOCKS (Transições)
        if "pending" in status.lower():
            pend_cfg = cfg.get("pending_timeouts", {})
            if pend_cfg.get("enabled", False):
                if state["pending_status"] != status:
                    state["pending_status"] = status
                    state["pending_start"] = now
                else:
                    elapsed = now - state["pending_start"]
                    limit = pend_cfg.get("start", 60) if status == "start_pending" else pend_cfg.get("stop_others", 30)
                    if elapsed > limit:
                        state["pending_status"] = ""
                        state["pending_start"] = 0
                        return "Forcar_Encerramento", f"Deadlock: Travado em '{status}' por > {limit}s.", None
            return "Nada", f"Aguardando Windows processar '{status}'...", None
        else:
            state["pending_status"] = ""
            state["pending_start"] = 0

        # 4. DEPENDÊNCIAS CUSTOMIZADAS (ÓRFÃOS) - COM CORREÇÃO 2
        deps = cfg.get("custom_deps", {})
        dep_name = deps.get("services", "").strip()
        dep_behavior = deps.get("behavior", "Não Fazer Nada")

        if dep_name and dep_behavior != "Não Fazer Nada":
            dep_status = get_info_callback(dep_name).get("status", "Ausente")

            if dep_status != "running":
                if dep_behavior == "Ordem de Inicialização" and status in ["stopped", "paused"]:
                    return "Iniciar_Outro", f"Dependência '{dep_name}' parada. Iniciando ela primeiro.", dep_name
                elif dep_behavior == "Efeito Dominó (Queda)" and status == "running":
                    state["domino_effect"] = True # Memoriza o desligamento forçado
                    return "Parar", f"Efeito Dominó: Dependência '{dep_name}' caiu!", None
            else:
                # Efeito Dominó Reverso (A dependência voltou!)
                if dep_behavior == "Efeito Dominó (Queda)" and status in ["stopped", "paused"] and state.get("domino_effect"):
                    state["domino_effect"] = False
                    return "Iniciar", f"A dependência '{dep_name}' voltou a funcionar. Religando serviço.", None

        # Se o serviço estiver rodando, limpa a memória do dominó
        if status == "running" and state.get("domino_effect"):
            state["domino_effect"] = False

        # 5. DESEMPENHO & HEARTBEAT (CORREÇÕES 1 e 3)
        if status == "running":
            # Heartbeat
            hb_cfg = cfg.get("heartbeat", {})
            if hb_cfg.get("enabled", False) and info.get("cpu", 0.0) == 0.0:
                if state["hb_start_time"] == 0: state["hb_start_time"] = now
                elif (now - state["hb_start_time"]) > (hb_cfg.get("timeout", 5) * 60):
                    state["hb_start_time"] = 0
                    is_crit, script = self._check_emergency(state, cfg, "hb")
                    if is_crit: return "Alerta_Critico", f"Heartbeat Falhou {state['hb_retry_count']}x.", script
                    return "Reiniciar", "Heartbeat: CPU em 0% (Travamento).", None
            elif info.get("cpu", 0.0) > 0.0:
                state["hb_start_time"] = 0

            # Performance Limits (Timers Separados e Disco Incluído)
            perf = cfg.get("perf_limits", {})
            tolerance = perf.get("tolerance", 30)
            
            # CPU Limit
            cpu_lim = perf.get("cpu", 0.0)
            if cpu_lim > 0 and info.get("cpu", 0.0) >= cpu_lim:
                if state["cpu_start_time"] == 0: state["cpu_start_time"] = now
                elif (now - state["cpu_start_time"]) > tolerance:
                    state["cpu_start_time"] = 0
                    is_crit, script = self._check_emergency(state, cfg, "perf")
                    if is_crit: return "Alerta_Critico", "Sobrecarga Crítica de CPU.", script
                    return "Reiniciar", "Limite de CPU excedido.", None
            else: state["cpu_start_time"] = 0

            # RAM Limit
            ram_lim = perf.get("ram", 0.0)
            if ram_lim > 0 and info.get("ram", 0.0) >= ram_lim:
                if state["ram_start_time"] == 0: state["ram_start_time"] = now
                elif (now - state["ram_start_time"]) > tolerance:
                    state["ram_start_time"] = 0
                    is_crit, script = self._check_emergency(state, cfg, "perf")
                    if is_crit: return "Alerta_Critico", "Sobrecarga Crítica de RAM.", script
                    return "Reiniciar", "Limite de RAM excedido.", None
            else: state["ram_start_time"] = 0
            
            # DISK Limit
            disk_lim = perf.get("disk", 0.0)
            if disk_lim > 0 and info.get("disk", 0.0) >= disk_lim:
                if state["disk_start_time"] == 0: state["disk_start_time"] = now
                elif (now - state["disk_start_time"]) > tolerance:
                    state["disk_start_time"] = 0
                    is_crit, script = self._check_emergency(state, cfg, "perf")
                    if is_crit: return "Alerta_Critico", "Sobrecarga Crítica de Disco.", script
                    return "Reiniciar", "Limite de Disco excedido.", None
            else: state["disk_start_time"] = 0

        # 6. MATRIZ DE ESTADOS (Ação Principal) - CORREÇÃO 4
        state_actions = cfg.get("state_actions", {})
        acao_configurada = state_actions.get(status, "Não Fazer Nada")

        if acao_configurada != "Não Fazer Nada":
            if acao_configurada == "Somente Alertar/Notificar":
                if state.get("notified_status") != status:
                    state["notified_status"] = status
                    return "Alertar_Notificar", f"Aviso (Matriz): O serviço encontra-se no estado '{status}'.", None
                return "Nada", "Alerta já enviado.", None
            
            # Se a ação não é apenas notificar, limpa o bloqueio do alerta
            state["notified_status"] = ""

            if (now - state["last_state_action"]) < 5:
                return "Nada", "Ação em Cooldown...", None

            is_crit, script = self._check_emergency(state, cfg, "state")
            if is_crit:
                return "Alerta_Critico", f"Status '{status}' persistente. Falhas críticas atingidas.", script

            return acao_configurada, f"Regra da Matriz: '{status}' -> {acao_configurada}", None

        # Se o serviço estiver bem, limpa qualquer alerta pendente
        state["notified_status"] = ""
        return "Nada", "Status Normal / Sem Ação Necessária", None