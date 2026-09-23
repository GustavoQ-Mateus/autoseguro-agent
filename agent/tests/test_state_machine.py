from app import config
from app import state_machine as sm
from app.models import ConversationState, QuoteResult


def test_pedindo_humano_escala_mesmo_com_slots_vazios():
    state = ConversationState("c1")
    decision = sm.pre_quote_decision(state, "pedindo_humano", {})
    assert decision.action == "escalar"
    assert decision.motivo == "pedido_explicito"


def test_pede_dado_faltante():
    state = ConversationState("c1")
    decision = sm.pre_quote_decision(state, "fornecendo_dado", {"idade": 35})
    assert decision.action == "pedir_dado"
    assert decision.missing == ["veiculo_ano"]
    assert decision.slots["idade"] == 35


def test_slots_acumulam_entre_mensagens():
    state = ConversationState("c1", slots={"idade": 35})
    decision = sm.pre_quote_decision(state, "fornecendo_dado", {"veiculo_ano": 2019})
    assert decision.action == "cotar"
    assert decision.slots == {"idade": 35, "veiculo_ano": 2019}


def test_progresso_zera_contador_de_estagnacao():
    state = ConversationState("c1", stagnation_count=2)
    decision = sm.pre_quote_decision(state, "fornecendo_dado", {"idade": 35})
    assert decision.stagnation_count == 0


def test_sem_progresso_incrementa_estagnacao():
    state = ConversationState("c1", stagnation_count=1)
    decision = sm.pre_quote_decision(state, "duvida_generica", {})
    assert decision.action == "pedir_dado"
    assert decision.stagnation_count == 2


def test_estagnacao_atinge_limite_escala():
    state = ConversationState("c1", stagnation_count=2)
    decision = sm.pre_quote_decision(state, "duvida_generica", {})
    assert decision.action == "escalar"
    assert decision.motivo == "estagnacao_coleta"


def test_falha_tecnica_llm_incrementa_contador_dedicado_e_pede_reprocessar():
    state = ConversationState("c1", stagnation_count=1, llm_failure_count=1)
    decision = sm.pre_quote_decision(state, None, {}, llm_failed=True)
    assert decision.action == "reprocessar"
    assert decision.llm_failure_count == 2
    assert decision.stagnation_count == 1


def test_falha_tecnica_llm_nao_altera_slots_conhecidos():
    state = ConversationState("c1", slots={"idade": 35})
    decision = sm.pre_quote_decision(state, None, {"veiculo_ano": 2019}, llm_failed=True)
    assert decision.slots == {"idade": 35}


def test_falha_tecnica_llm_atinge_limite_escala():
    state = ConversationState("c1", llm_failure_count=config.LLM_FAILURE_LIMIT - 1)
    decision = sm.pre_quote_decision(state, None, {}, llm_failed=True)
    assert decision.action == "escalar"
    assert decision.motivo == "falha_tecnica_llm"
    assert decision.llm_failure_count == config.LLM_FAILURE_LIMIT


def test_extracao_com_sucesso_zera_contador_de_falha_tecnica_llm():
    state = ConversationState("c1", slots={"idade": 35}, llm_failure_count=2)
    decision = sm.pre_quote_decision(state, "fornecendo_dado", {"veiculo_ano": 2019})
    assert decision.action == "cotar"
    assert decision.llm_failure_count == 0


def test_post_decision_sucesso():
    result = QuoteResult(status="sucesso", data={"premio_mensal": 100})
    assert sm.post_quote_decision(result).action == "responder_cotacao"


def test_post_decision_recusada():
    result = QuoteResult(status="recusada", motivo="idade acima do limite")
    decision = sm.post_quote_decision(result)
    assert decision.action == "responder_recusa"
    assert decision.motivo == "idade acima do limite"


def test_post_decision_falha_tecnica_escala():
    result = QuoteResult(status="falha_tecnica", motivo="timeout")
    decision = sm.post_quote_decision(result)
    assert decision.action == "escalar"
    assert decision.motivo == "falha_tecnica_persistente"


def test_build_quote_payload_usa_default_de_plano():
    payload = sm.build_quote_payload({"idade": 35, "veiculo_ano": 2019})
    assert payload["plano_id"] == "essencial"
    assert "cep" not in payload
