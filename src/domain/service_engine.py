# src/domain/service_engine.py
import time
from datetime import datetime

class WatchdogServiceEngine:
    """Motor de regras focado exclusivamente na lógica de Serviços do Windows."""
    
    def __init__(self):
        self.service_states = {}
        # Para traduzir o dia da semana no Agendamento Inteligente
        self.dias_pt = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }

    def get_or_create_state(self, service_name):
        """Garante a memória de curto prazo para cada serviço."""
        if service_name not in self.service_states:
            self.service_states[service_name] = {
                "retry_count": 0, "perf_retry_count": 0, "hb_retry_count": 0,
                "last_state_action": 0, "last_perf_action": 0, "last_hb_action": 0,
                "script_executed": False, "last_schedule_run": "",
                "pending_status": "", "pending_start": 0,
                "perf_start_time": 0, "hb_start_time": 0
            }
        return self.service_states[service_name]

    def remove_state(self, service_name):
        if service_name in self.service_states:
            del self.service_states[service_name]

    def _verificar_reset_falhas(self, state, cfg):
        """Reseta os contadores se o tempo de 'reset_days' já tiver passado."""
        now = time.time()
        
        # Reset Emergência Principal
        em_reset = cfg.get("emergency", {}).get("reset_days", 0)
        if em_reset > 0 and state["last_state_action"] > 0:
            if (now - state["last_state_action"]) > (em_reset * 86400):
                state["retry_count"] = 0
                state["script_executed"] = False
                state["last_state_action"] = 0
                
        # Reset Performance
        perf_reset = cfg.get("perf_limits", {}).get("reset_days", 0)
        if perf_reset > 0 and state["last_perf_action"] > 0:
            if (now - state["last_perf_action"]) > (perf_reset * 86400):
                state["perf_retry_count"] = 0
                state["last_perf_action"] = 0
                
        # Reset Heartbeat
        hb_reset = cfg.get("heartbeat", {}).get("reset_days", 0)
        if hb_reset > 0 and state["last_hb_action"] > 0:
            if (now - state["last_hb_action"]) > (hb_reset * 86400):
                state["hb_retry_count"] = 0
                state["last_hb_action"] = 0

    def _check_emergency(self, state, cfg, fail_type):
        """
        Verifica se a quantidade de falhas excedeu o limite.
        Retorna (is_critical, script_to_run)
        """
        now = time.time()
        em_cfg = cfg.get("emergency", {})
        
        # Se a emergência global NÃO estiver habilitada e for uma falha da matriz (state),
        # apenas incrementa infinitamente, sem nunca travar.
        if fail_type == "state" and not em_cfg.get("enabled", False):
            state["retry_count"] += 1
            state["last_state_action"] = now
            return False, None

        # Definição dos limites dependendo do tipo da falha
        if fail_type == "state":
            max_retries = em_cfg.get("max_retries", 3)
            current_fails = state["retry_count"]
            script_path = em_cfg.get("run_script", "")
        elif fail_type == "perf":
            max_retries = cfg.get("perf_limits", {}).get("max_restarts", 3)
            current_fails = state["perf_retry_count"]
            script_path = "" # Scripts são reservados para falha crítica global
        elif fail_type == "hb":
            max_retries = cfg.get("heartbeat", {}).get("max_restarts", 3)
            current_fails = state["hb_retry_count"]
            script_path = ""

        # Atingiu o limite (FALHA CRÍTICA!)
        if current_fails >= max_retries:
            if fail_type == "state": state["last_state_action"] = now
            elif fail_type == "perf": state["last_perf_action"] = now
            elif fail_type == "hb": state["last_hb_action"] = now

            script_to_run = None
            # Executa o script apenas uma vez por falha global
            if fail_type == "state" and em_cfg.get("enabled", False) and script_path and not state["script_executed"]:
                state["script_executed"] = True
                script_to_run = script_path

            return True, script_to_run
        
        # Não atingiu o limite, apenas incrementa e continua tentando
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
        """
        Avalia as regras definidas pelo utilizador e retorna a ação necessária.
        Retorno: (Ação, Motivo, Alvo_Script_ou_Dependencia)
        """
        state = self.get_or_create_state(name)
        self._verificar_reset_falhas(state, cfg)
        
        status = info.get("status", "Ausente")
        now = time.time()

        # 1. VERIFICAÇÃO DE MANUTENÇÃO (SNOOZE)
        snooze = cfg.get("snooze", {})
        if snooze.get("active", False):
            until = snooze.get("until", 0)
            if until == -1 or until > now:
                return "Nada", "Modo Manutenção (Snooze) Ativo", None
            else:
                cfg["snooze"]["active"] = False # O tempo esgotou, desliga o Snooze

        # 2. AGENDAMENTO PREVENTIVO (SMART SCHEDULE)
        sched = cfg.get("schedule", {})
        if sched.get("enabled", False) and status == "running":
            hoje = datetime.now()
            dia_semana = self.dias_pt[hoje.weekday()]
            dia_cfg = sched.get("days", "Todos os Dias")
            
            if dia_cfg == "Todos os Dias" or dia_cfg == dia_semana:
                hora_cfg = sched.get("time", "03:00")
                hora_atual = hoje.strftime("%H:%M")
                data_hoje_str = hoje.strftime("%Y-%m-%d")
                
                if hora_atual == hora_cfg and state["last_schedule_run"] != data_hoje_str:
                    state["last_schedule_run"] = data_hoje_str
                    return "Reiniciar", f"Smart Schedule: Reinício preventivo agendado para {hora_cfg}.", None

        # 3. TRATAMENTO DE TRANSIÇÕES (DEADLOCKS)
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
                        return "Forcar_Encerramento", f"Deadlock: Travado em '{status}' por mais de {limit}s. Forçando Taskkill.", None
            return "Nada", f"Aguardando o Windows processar o status '{status}'...", None
        else:
            state["pending_status"] = ""
            state["pending_start"] = 0

        # 4. DEPENDÊNCIAS CUSTOMIZADAS (ÓRFÃOS)
        deps = cfg.get("custom_deps", {})
        dep_name = deps.get("services", "").strip()
        dep_behavior = deps.get("behavior", "Não Fazer Nada")

        if dep_name and dep_behavior != "Não Fazer Nada":
            dep_info = get_info_callback(dep_name)
            dep_status = dep_info.get("status", "Ausente")

            if dep_status != "running":
                if dep_behavior == "Ordem de Inicialização" and status in ["stopped", "paused"]:
                    return "Iniciar_Outro", f"Dependência '{dep_name}' parada. Iniciando ela primeiro.", dep_name
                elif dep_behavior == "Efeito Dominó (Queda)" and status == "running":
                    return "Parar", f"Efeito Dominó: Dependência '{dep_name}' caiu!", None

        # 5. HEARTBEAT & LIMITES DE DESEMPENHO (Apenas se estiver rodando)
        if status == "running":
            # 5.1 Heartbeat (Inatividade)
            hb_cfg = cfg.get("heartbeat", {})
            if hb_cfg.get("enabled", False):
                cpu_atual = info.get("cpu", 0.0) # Precisa do suporte do Adapter
                if cpu_atual == 0.0:
                    if state["hb_start_time"] == 0: state["hb_start_time"] = now
                    elif (now - state["hb_start_time"]) > (hb_cfg.get("timeout", 5) * 60):
                        state["hb_start_time"] = 0
                        is_crit, script = self._check_emergency(state, cfg, "hb")
                        if is_crit: return "Alerta_Critico", f"Heartbeat Falhou {state['hb_retry_count']}x. Automação Suspensa.", script
                        return "Reiniciar", "Heartbeat: CPU em 0% por tempo limite (Possível Travamento).", None
                else:
                    state["hb_start_time"] = 0

            # 5.2 Performance Limits
            perf = cfg.get("perf_limits", {})
            cpu_limit = perf.get("cpu", 0.0)
            ram_limit = perf.get("ram", 0.0)
            cpu_atual = info.get("cpu", 0.0)
            ram_atual = info.get("ram", 0.0)
            
            if (cpu_limit > 0 and cpu_atual >= cpu_limit) or (ram_limit > 0 and ram_atual >= ram_limit):
                if state["perf_start_time"] == 0: state["perf_start_time"] = now
                elif (now - state["perf_start_time"]) > perf.get("tolerance", 30):
                    state["perf_start_time"] = 0
                    is_crit, script = self._check_emergency(state, cfg, "perf")
                    if is_crit: return "Alerta_Critico", f"Sobrecarga excedeu {state['perf_retry_count']}x. Automação Suspensa.", script
                    return "Reiniciar", f"Limites de Desempenho Excedidos (CPU/RAM).", None
            else:
                state["perf_start_time"] = 0

        # 6. MATRIZ DE ESTADOS (Ação Principal)
        state_actions = cfg.get("state_actions", {})
        acao_configurada = state_actions.get(status, "Não Fazer Nada")

        if acao_configurada != "Não Fazer Nada":
            if acao_configurada == "Somente Alertar/Notificar":
                return "Log_Info", f"Aviso (Matriz): O serviço encontra-se '{status}'.", None

            # Cooldown manual para ações de matriz
            if (now - state["last_state_action"]) < 5:
                return "Nada", "Ação em Cooldown...", None

            # Verifica Emergência
            is_crit, script = self._check_emergency(state, cfg, "state")
            if is_crit:
                return "Alerta_Critico", f"Status '{status}' persistente. Falhas críticas atingidas.", script

            return acao_configurada, f"Regra da Matriz ativada: '{status}' -> {acao_configurada}", None

        return "Nada", "Status Normal / Sem Ação Necessária", None