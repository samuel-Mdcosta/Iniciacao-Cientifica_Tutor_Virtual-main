import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

import main
from App.Backend.config.instructions import Instructions
from App.Backend.engine.feedbackDesempenho import (
    formatar_nome_fonte,
    interpretar_json_llm,
    montar_consulta_area,
    montar_contexto_areas,
    sanitizar_feedback,
)


# ---------- dublês do Gemini e do RAG ----------

class ModelsFalso:
    def __init__(self, texto=None, erro=None):
        self.texto = texto
        self.erro = erro
        self.chamadas = []

    def generate_content(self, model, contents, config):
        self.chamadas.append({"model": model, "contents": contents, "config": config})
        if self.erro:
            raise self.erro
        uso = SimpleNamespace(prompt_token_count=900, candidates_token_count=300, total_token_count=1200)
        return SimpleNamespace(text=self.texto, usage_metadata=uso)


class RecuperacaoFalsa:
    def __init__(self, documentos_por_consulta=None, erro=None):
        self.documentos_por_consulta = documentos_por_consulta or {}
        self.erro = erro
        self.consultas = []

    def compare_vector(self, consulta):
        self.consultas.append(consulta)
        if self.erro:
            raise self.erro
        return {"documents": self.documentos_por_consulta.get(consulta, [])}


SEGREDO_TESTE = "segredo-de-teste"


@pytest.fixture
def cliente(monkeypatch):
    # Os endpoints do motor exigem o header X-API-Key igual ao SHARED_SECRET.
    monkeypatch.setenv("SHARED_SECRET", SEGREDO_TESTE)

    def configurar(texto_llm=None, erro_llm=None, documentos=None, erro_rag=None, chave=SEGREDO_TESTE):
        models = ModelsFalso(texto_llm, erro_llm)
        recuperacao = RecuperacaoFalsa(documentos, erro_rag)
        monkeypatch.setattr(main.sistema_tutor, "client", SimpleNamespace(models=models))
        monkeypatch.setattr(main.sistema_tutor, "recovery", recuperacao)
        headers = {"X-API-Key": chave} if chave else {}
        return TestClient(main.app, headers=headers), models, recuperacao

    return configurar


HIPOCAMPO = "Hipocampo e Sistema Límbico"
MEMORIA = "Memória e Aprendizagem"


def payload_padrao():
    return {
        "desempenho_por_tema": [
            {"tema": HIPOCAMPO, "tentativas": 2, "questoes": 20, "acertos": 8, "erros": 12,
             "taxa_acerto": 40.0, "taxa_recente": 40.0, "nivel": "critico", "tendencia": "estavel"},
            {"tema": "Linguagem, Leitura e Escrita", "tentativas": 1, "questoes": 10, "acertos": 9, "erros": 1,
             "taxa_acerto": 90.0, "taxa_recente": 90.0, "nivel": "bom", "tendencia": None},
        ],
        "areas_prioritarias": [
            {
                "tema": HIPOCAMPO,
                "questoes_erradas": [
                    {"pergunta": "Qual estrutura integra o circuito de Papez?", "subtema": "Circuito de Papez",
                     "resposta_escolhida": "Cerebelo", "resposta_correta": "Giro do cíngulo"},
                    {"pergunta": "Qual o papel do hipocampo na memória?", "subtema": "Consolidação da memória",
                     "resposta_escolhida": "Armazenamento definitivo", "resposta_correta": "Consolidação"},
                    {"pergunta": "Outra questão do circuito", "subtema": "circuito de papez",
                     "resposta_escolhida": "Ponte", "resposta_correta": "Fórnix"},
                ],
                "subtemas_acertados": ["Amígdala e emoção"],
            }
        ],
        "temas_nao_praticados": [MEMORIA],
    }


RESPOSTA_LLM = {
    "resumo_geral": "Você vai bem em Linguagem, mas o Hipocampo e Sistema Límbico precisa de atenção.",
    "areas_prioritarias": [
        {
            "tema": "hipocampo e sistema limbico",
            "diagnostico": "Você confunde as estruturas do circuito de Papez.",
            "o_que_estudar": ["Circuito de Papez", "Consolidação da memória"],
            "por_que_estudar": "O circuito de Papez integra emoção e memória.",
            "onde_estudar": ["Neurociencia Cognitiva", "Livro Que Nao Existe"],
        }
    ],
    "pontos_fortes": ["Linguagem, Leitura e Escrita"],
    "proximos_passos": ["Revisar o circuito de Papez", "Refazer a lista de Hipocampo e Sistema Límbico"],
}

CONSULTA_HIPOCAMPO = f"{HIPOCAMPO}: Circuito de Papez, Consolidação da memória"
DOCUMENTOS_HIPOCAMPO = {
    CONSULTA_HIPOCAMPO: [
        {"file_name": "Neurociencia_Cognitiva.pdf", "chunk": "O circuito de Papez conecta hipocampo e cíngulo."},
        {"file_name": "Principios_de_Neurociencia.pdf", "chunk": "O hipocampo consolida memórias declarativas."},
    ]
}


# ---------- prompts ----------

def test_prompts_formatam_sem_erro():
    instrucoes = Instructions()
    quiz = instrucoes.get_instructions("02").format(CONTEXT="trecho")
    feedback = instrucoes.get_instructions("03").format(CONTEXT="trecho")

    assert '"subtema"' in quiz
    assert '"areas_prioritarias"' in feedback
    assert "{CONTEXT}" not in feedback and "trecho" in feedback


# ---------- funções puras ----------

def test_formatar_nome_fonte():
    assert formatar_nome_fonte("Neurociencia_Cognitiva.pdf") == "Neurociencia Cognitiva"
    assert formatar_nome_fonte("  Kandel__cap_3.PDF ") == "Kandel cap 3"


def test_montar_consulta_area_remove_subtemas_repetidos():
    consulta = montar_consulta_area(HIPOCAMPO, ["Circuito de Papez", None, "circuito de papez", "Fórnix"])
    assert consulta == f"{HIPOCAMPO}: Circuito de Papez, Fórnix"
    assert montar_consulta_area(HIPOCAMPO, []) == HIPOCAMPO


def test_montar_contexto_areas_agrupa_por_area_sem_repetir_trecho():
    repetido = {"file_name": "A_B.pdf", "chunk": "trecho comum"}
    contexto, fontes = montar_contexto_areas({
        "Tema 1": [repetido, {"file_name": "C.pdf", "chunk": "outro"}],
        "Tema 2": [repetido],
    })

    assert contexto.count("trecho comum") == 1
    assert "### Área: Tema 1" in contexto and "[Fonte: A_B.pdf]" in contexto
    assert fontes == {"Tema 1": ["A B", "C"], "Tema 2": ["A B"]}


def test_sanitizar_remove_referencia_inventada_e_usa_nome_canonico():
    feedback = sanitizar_feedback(RESPOSTA_LLM, [HIPOCAMPO], {HIPOCAMPO: ["Neurociencia Cognitiva", "Principios de Neurociencia"]})

    area = feedback["areas_prioritarias"][0]
    assert area["tema"] == HIPOCAMPO
    assert area["onde_estudar"] == ["Neurociencia Cognitiva"]


def test_sanitizar_usa_fontes_recuperadas_quando_llm_nao_indica_nenhuma_valida():
    bruto = {"resumo_geral": "ok", "areas_prioritarias": [{"tema": HIPOCAMPO, "onde_estudar": ["Inventado"]}]}
    feedback = sanitizar_feedback(bruto, [HIPOCAMPO], {HIPOCAMPO: ["Neurociencia Cognitiva"]})
    assert feedback["areas_prioritarias"][0]["onde_estudar"] == ["Neurociencia Cognitiva"]


def test_sanitizar_mantem_ordem_do_sistema_e_descarta_area_nao_pedida():
    bruto = {
        "resumo_geral": "ok",
        "areas_prioritarias": [
            {"tema": "Tema Extra Inventado", "diagnostico": "x"},
            {"tema": MEMORIA, "diagnostico": "m"},
            {"tema": HIPOCAMPO, "diagnostico": "h"},
        ],
    }
    # A área "inventada" só é aproveitada se faltar alguma área pedida.
    feedback = sanitizar_feedback(bruto, [HIPOCAMPO, MEMORIA], {})
    assert [a["tema"] for a in feedback["areas_prioritarias"]] == [HIPOCAMPO, MEMORIA]
    assert [a["diagnostico"] for a in feedback["areas_prioritarias"]] == ["h", "m"]


def test_sanitizar_tolera_tipos_errados():
    feedback = sanitizar_feedback({"resumo_geral": 3, "areas_prioritarias": "x", "pontos_fortes": "Só um"}, [HIPOCAMPO], {})
    assert feedback == {"resumo_geral": "", "areas_prioritarias": [], "pontos_fortes": ["Só um"], "proximos_passos": []}


def test_interpretar_json_llm_tolera_cercas_e_texto_em_volta():
    texto = 'Segue o feedback:\n```json\n{"resumo_geral": "ok"}\n```\nBons estudos!'
    assert interpretar_json_llm(texto) == {"resumo_geral": "ok"}


# ---------- endpoint /feedback ----------

def test_feedback_fluxo_completo(cliente):
    client, models, recuperacao = cliente(
        texto_llm="```json\n" + json.dumps(RESPOSTA_LLM, ensure_ascii=False) + "\n```",
        documentos=DOCUMENTOS_HIPOCAMPO,
    )

    resposta = client.post("/feedback", json=payload_padrao())

    assert resposta.status_code == 200
    corpo = resposta.json()
    area = corpo["feedback"]["areas_prioritarias"][0]
    assert area["tema"] == HIPOCAMPO
    assert area["o_que_estudar"] == ["Circuito de Papez", "Consolidação da memória"]
    assert area["onde_estudar"] == ["Neurociencia Cognitiva"]
    assert corpo["feedback"]["proximos_passos"][0] == "Revisar o circuito de Papez"
    assert corpo["uso_tokens"] == {"entrada": 900, "saida": 300, "total": 1200}

    # RAG consultado com o tema + subtemas errados (sem repetição)
    assert recuperacao.consultas == [CONSULTA_HIPOCAMPO]

    # Contexto vai na instrução do sistema; os dados do aluno vão no turno do usuário
    chamada = models.chamadas[0]
    assert "### Área: Hipocampo e Sistema Límbico" in chamada["config"].system_instruction
    assert "[Fonte: Neurociencia_Cognitiva.pdf]" in chamada["config"].system_instruction
    dados_aluno = json.loads(chamada["contents"][0].parts[0].text)
    assert dados_aluno["areas_prioritarias"][0]["tema"] == HIPOCAMPO
    assert dados_aluno["temas_nao_praticados"] == [MEMORIA]


def test_feedback_sem_areas_prioritarias_nao_consulta_rag(cliente):
    client, models, recuperacao = cliente(texto_llm=json.dumps({
        "resumo_geral": "Excelente desempenho!", "areas_prioritarias": [], "pontos_fortes": ["Tudo"],
        "proximos_passos": ["Praticar Memória e Aprendizagem"],
    }))
    payload = payload_padrao()
    payload["areas_prioritarias"] = []

    resposta = client.post("/feedback", json=payload)

    assert resposta.status_code == 200
    assert resposta.json()["feedback"]["areas_prioritarias"] == []
    assert recuperacao.consultas == []
    assert "Nenhum trecho do material foi recuperado." in models.chamadas[0]["config"].system_instruction


def test_feedback_falha_no_rag_nao_derruba_o_feedback(cliente):
    client, _, _ = cliente(texto_llm=json.dumps(RESPOSTA_LLM), erro_rag=RuntimeError("mongo fora do ar"))

    resposta = client.post("/feedback", json=payload_padrao())

    assert resposta.status_code == 200
    assert resposta.json()["feedback"]["areas_prioritarias"][0]["onde_estudar"] == []


@pytest.mark.parametrize("texto_llm", ["isto não é json", '{"pontos_fortes": []}', None])
def test_feedback_resposta_invalida_ou_bloqueada_retorna_502(cliente, texto_llm):
    client, _, _ = cliente(texto_llm=texto_llm, documentos=DOCUMENTOS_HIPOCAMPO)
    resposta = client.post("/feedback", json=payload_padrao())
    assert resposta.status_code == 502
    assert "erro" in resposta.json()


def test_feedback_erro_da_api_do_gemini_retorna_502(cliente):
    erro = genai_errors.APIError(503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}})
    client, _, _ = cliente(erro_llm=erro, documentos=DOCUMENTOS_HIPOCAMPO)
    resposta = client.post("/feedback", json=payload_padrao())
    assert resposta.status_code == 502


@pytest.mark.parametrize("chave", [None, "chave-errada"])
def test_feedback_exige_chave_do_servico(cliente, chave):
    client, models, recuperacao = cliente(texto_llm=json.dumps(RESPOSTA_LLM), chave=chave)
    resposta = client.post("/feedback", json=payload_padrao())
    assert resposta.status_code == 401
    assert models.chamadas == [] and recuperacao.consultas == []


def test_feedback_valida_payload(cliente):
    client, models, _ = cliente(texto_llm=json.dumps(RESPOSTA_LLM))

    nivel_invalido = payload_padrao()
    nivel_invalido["desempenho_por_tema"][0]["nivel"] = "pessimo"
    areas_demais = payload_padrao()
    areas_demais["areas_prioritarias"] = areas_demais["areas_prioritarias"] * 4
    sem_desempenho = payload_padrao()
    sem_desempenho["desempenho_por_tema"] = []

    for payload in (nivel_invalido, areas_demais, sem_desempenho):
        assert client.post("/feedback", json=payload).status_code == 422
    assert models.chamadas == []
