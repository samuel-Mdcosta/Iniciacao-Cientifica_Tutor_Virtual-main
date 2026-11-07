"""Funções do feedback de desempenho do aluno (endpoint /feedback).

O sistema (backend Laravel) já entrega os números calculados e as áreas
prioritárias escolhidas; aqui só montamos o contexto RAG de cada área,
interpretamos a resposta do LLM e garantimos que ela não traga referências
que não vieram do material recuperado.
"""

import json
import logging
import unicodedata

logger = logging.getLogger(__name__)

MAX_SUBTEMAS_CONSULTA = 5
MAX_ITENS_LISTA = 5
MAX_CARACTERES_ITEM = 300
MAX_CARACTERES_TEXTO = 1500


def normalizar(texto):
    """Minúsculas, sem acentos e com espaços simples, para comparar nomes."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


def formatar_nome_fonte(file_name):
    """'Neurociencia_Cognitiva.pdf' -> 'Neurociencia Cognitiva' (mesmo padrão das "referencias")."""
    nome = (file_name or "").strip()
    if nome.lower().endswith(".pdf"):
        nome = nome[:-4]
    return " ".join(nome.replace("_", " ").split())


def montar_consulta_area(tema, subtemas):
    """Texto usado na busca vetorial de uma área: o tema e os subtemas em que o aluno errou."""
    unicos = []
    vistos = set()
    for subtema in subtemas:
        subtema = (subtema or "").strip()
        chave = normalizar(subtema)
        if chave and chave not in vistos:
            vistos.add(chave)
            unicos.append(subtema)

    if not unicos:
        return tema
    return f"{tema}: {', '.join(unicos[:MAX_SUBTEMAS_CONSULTA])}"


def recuperar_documentos(consultas_por_tema, recovery):
    """Busca os trechos do material de cada área. Uma falha na busca de uma área não derruba o feedback."""
    documentos_por_tema = {}
    for tema, consulta in consultas_por_tema.items():
        try:
            resultado = recovery.compare_vector(consulta)
        except Exception:
            # Embedding (Gemini) ou Vector Search (Mongo) indisponível: segue sem contexto para esta área.
            logger.warning("Falha ao recuperar contexto da área %r no /feedback", tema, exc_info=True)
            resultado = {}
        documentos_por_tema[tema] = resultado.get("documents") or []
    return documentos_por_tema


def montar_contexto_areas(documentos_por_tema):
    """Monta o {CONTEXT} agrupado por área e devolve os nomes das fontes recuperadas para cada área."""
    partes = []
    fontes_por_tema = {}
    trechos_usados = set()

    for tema, documentos in documentos_por_tema.items():
        fontes = []
        trechos = []
        for doc in documentos:
            file_name = doc.get("file_name") or ""
            chunk = doc.get("chunk") or ""
            if not chunk:
                continue

            nome = formatar_nome_fonte(file_name)
            if nome and nome not in fontes:
                fontes.append(nome)

            if (file_name, chunk) in trechos_usados:
                continue
            trechos_usados.add((file_name, chunk))
            trechos.append(f"[Fonte: {file_name}]\n{chunk}")

        fontes_por_tema[tema] = fontes
        if trechos:
            partes.append(f"### Área: {tema}\n" + "\n\n".join(trechos))

    return "\n\n".join(partes), fontes_por_tema


def montar_dados_aluno(dados):
    """Dados de desempenho enviados como turno do usuário (JSON), separados da instrução do sistema."""
    return json.dumps(dados, ensure_ascii=False)


def interpretar_json_llm(texto):
    """Extrai o objeto JSON da resposta do LLM (tolera cercas ```json e texto em volta)."""
    limpo = texto.replace("```json", "").replace("```", "").strip()
    inicio, fim = limpo.find("{"), limpo.rfind("}")
    if inicio != -1 and fim > inicio:
        limpo = limpo[inicio:fim + 1]
    return json.loads(limpo)


def _texto(valor, maximo=MAX_CARACTERES_TEXTO):
    if not isinstance(valor, str):
        return ""
    return valor.strip()[:maximo]


def _lista_textos(valor, maximo=MAX_ITENS_LISTA):
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        return []

    itens = []
    vistos = set()
    for item in valor:
        item = _texto(item, MAX_CARACTERES_ITEM)
        chave = normalizar(item)
        if chave and chave not in vistos:
            vistos.add(chave)
            itens.append(item)
    return itens[:maximo]


def _filtrar_fontes(sugeridas, disponiveis):
    """Mantém só as fontes que de fato vieram do RAG; se o LLM não indicar nenhuma válida, usa as recuperadas."""
    por_chave = {normalizar(fonte): fonte for fonte in disponiveis}
    escolhidas = []
    for sugestao in _lista_textos(sugeridas):
        fonte = por_chave.get(normalizar(formatar_nome_fonte(sugestao)))
        if fonte and fonte not in escolhidas:
            escolhidas.append(fonte)
    return escolhidas or list(disponiveis)[:MAX_ITENS_LISTA]


def sanitizar_feedback(bruto, temas_prioritarios, fontes_por_tema):
    """Normaliza a resposta do LLM para o contrato do front.

    - mantém as áreas na ordem decidida pelo sistema e com o nome canônico do tema;
    - descarta áreas que não foram pedidas;
    - "onde_estudar" só contém materiais recuperados pelo RAG (sem referências inventadas).
    """
    if not isinstance(bruto, dict):
        bruto = {}

    lista = bruto.get("areas_prioritarias")
    areas_brutas = [a for a in lista if isinstance(a, dict)] if isinstance(lista, list) else []

    chaves_pedidas = {normalizar(tema) for tema in temas_prioritarios}
    por_tema = {}
    sem_correspondencia = []
    for area in areas_brutas:
        chave = normalizar(_texto(area.get("tema")))
        if chave in chaves_pedidas:
            por_tema.setdefault(chave, area)
        else:
            sem_correspondencia.append(area)

    areas = []
    for tema in temas_prioritarios:
        area = por_tema.get(normalizar(tema))
        if area is None and sem_correspondencia:
            # O LLM pode ter reescrito o nome do tema; aproveita a próxima área sem correspondência, na ordem.
            area = sem_correspondencia.pop(0)
        if area is None:
            continue

        areas.append({
            "tema": tema,
            "diagnostico": _texto(area.get("diagnostico")),
            "o_que_estudar": _lista_textos(area.get("o_que_estudar")),
            "por_que_estudar": _texto(area.get("por_que_estudar")),
            "onde_estudar": _filtrar_fontes(area.get("onde_estudar"), fontes_por_tema.get(tema, [])),
        })

    return {
        "resumo_geral": _texto(bruto.get("resumo_geral")),
        "areas_prioritarias": areas,
        "pontos_fortes": _lista_textos(bruto.get("pontos_fortes")),
        "proximos_passos": _lista_textos(bruto.get("proximos_passos")),
    }
