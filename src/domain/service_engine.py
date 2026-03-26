# src/domain/service_engine.py
import time

class WatchdogServiceEngine:
    """Motor de regras focado exclusivamente na lógica de Serviços do Windows."""
    
    def __init__(self):
        self.service_states = {}

    def get_or_create_state(self, service_name):
        """Garante a memória de curto prazo (contadores de falha) para cada serviço."""
        if service_name not in self.service_states:
            self.service_states[service_name] = {
                "retry_count": 0, 
                "perf_retry_count": 0, 
                "script_executed": False,
                "last_action_time": 0
            }
        return self.service_states[service_name]

    def remove_state(self, service_name):
        if service_name in self.service_states:
            del self.service_states[service_name]

    def evaluate_service(self, name, info, cfg, get_info_callback):
        """
        Avalia as regras definidas pelo utilizador e retorna a ação necessária.
        Retorno: (Ação, Motivo, Alvo_Script_ou_Dependencia)
        """
        state = self.get_or_create_state(name)
        status = info.get("status", "Ausente")

        # 1. VERIFICAÇÃO DE MANUTENÇÃO (SNOOZE)
        snooze = cfg.get("snooze", {})
        if snooze.get("active", False):
            return "Nada", "Modo Manutenção Ativo (Snooze)", None

        # 2. VERIFICAÇÃO DE DEPENDÊNCIAS CUSTOMIZADAS
        deps = cfg.get("custom_deps", {})
        dep_name = deps.get("services", "").strip()
        dep_behavior = deps.get("behavior", "Não Fazer Nada")

        if dep_name and dep_behavior != "Não Fazer Nada":
            dep_info = get_info_callback(dep_name)
            dep_status = dep_info.get("status", "Ausente")

            if dep_status != "running":
                if dep_behavior == "Ordem de Inicialização" and status in ["stopped", "paused"]:
                    return "Iniciar_Outro", f"Dependência '{dep_name}' está parada. Iniciando primeiro.", dep_name
                elif dep_behavior == "Efeito Dominó (Queda)" and status == "running":
                    return "Parar", f"Dependência '{dep_name}' caiu! Aplicando Efeito Dominó.", None

        # 3. LIMITES DE DESEMPENHO (Se estiver em execução)
        if status == "running":
            perf = cfg.get("perf_limits", {})
            max_cpu = perf.get("cpu", 0.0)
            max_ram = perf.get("ram", 0.0)
            
            # Aqui poderíamos ler info["cpu"] se o psutil permitisse de forma leve para serviços, 
            # mas como os serviços rodam em svchost, a leitura isolada é complexa. 
            # O pilar principal será a Matriz de Estados abaixo.

        # 4. MATRIZ DE ESTADOS (Ação Principal)
        state_actions = cfg.get("state_actions", {})
        
        # Ignora estados de transição do Windows para não causar Deadlocks
        if "pending" in status.lower():
            return "Nada", f"Aguardando transição do Windows ({status})", None

        acao_configurada = state_actions.get(status, "Não Fazer Nada")

        if acao_configurada != "Não Fazer Nada":
            # Cooldown de 5 segundos para não spammar comandos no Windows
            agora = time.time()
            if (agora - state["last_action_time"]) < 5:
                return "Nada", "Em Cooldown", None
                
            state["last_action_time"] = agora
            return acao_configurada, f"Regra da Matriz: '{status}' -> {acao_configurada}", None

        return "Nada", "Status Normal / Sem Ação Necessária", None