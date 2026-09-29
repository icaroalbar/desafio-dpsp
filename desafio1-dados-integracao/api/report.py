"""
Gera o relatório .xlsx de retorno do lote: linhas rejeitadas + pendências,
com a coluna "motivo" e a célula do campo problemático destacada.
"""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

FUNDO_ERRO = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
FUNDO_AVISO = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
FONTE_CABECALHO = Font(bold=True, color="FFFFFF")
FUNDO_CABECALHO = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

COLUNAS = ["cpf", "nome", "email", "curso_id", "curso_nome",
           "data_inicio_desejada", "motivo"]

# motivo -> (coluna a destacar, é erro bloqueante ou só aviso informativo)
DESTAQUE_POR_MOTIVO = {
    "curso_inexistente": ("curso_id", True),
    "campo_obrigatorio_ausente:email": ("email", True),
    "duplicata_no_mesmo_lote": ("cpf", True),
    "nome_incompleto": ("nome", True),
    "ja_matriculado_no_curso": ("curso_id", False),
    "divergencia_cadastro:nome": ("nome", True),
    "divergencia_cadastro:email": ("email", True),
}


def _linha_de_rejeitada(motivo, linha_bruta):
    return {
        "cpf": linha_bruta.get("cpf", ""),
        "nome": linha_bruta.get("nome", ""),
        "email": linha_bruta.get("email", ""),
        "curso_id": linha_bruta.get("curso_id", ""),
        "curso_nome": linha_bruta.get("curso_nome", ""),
        "data_inicio_desejada": linha_bruta.get("data_inicio_desejada", ""),
        "motivo": motivo,
    }


def _linha_de_pendencia(cpf, nome, email, campo_divergente, valor_atual, valor_novo):
    # dado do aluno fica na coluna dele mesmo (o que já está cadastrado);
    # o motivo só descreve o que veio divergente na carga nova, não some com a linha
    return {
        "cpf": cpf,
        "nome": nome,
        "email": email,
        "curso_id": "",
        "curso_nome": "",
        "data_inicio_desejada": "",
        "motivo": f"divergencia_cadastro:{campo_divergente} (cadastro='{valor_atual}', carga nova='{valor_novo}')",
    }


def gerar_relatorio_xlsx(rejeitados: list, pendencias: list) -> bytes:
    """
    rejeitados: lista de tuplas (motivo, linha_bruta_dict) vindas de core.linha_rejeitada.
    pendencias: lista de tuplas (cpf, nome, email, campo_divergente, valor_atual, valor_novo)
                vindas de core.pendencia_cadastro JOIN core.alunos (nome/email atuais).
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Nao processados"

    ws.append(COLUNAS)
    for cel in ws[1]:
        cel.font = FONTE_CABECALHO
        cel.fill = FUNDO_CABECALHO
        cel.alignment = Alignment(horizontal="center")

    linhas = [_linha_de_rejeitada(motivo, lb) for motivo, lb in rejeitados]
    linhas += [_linha_de_pendencia(*p) for p in pendencias]

    # ordem alfabética por nome (linha sem nome, se houver, vai pro final)
    linhas.sort(key=lambda linha: (linha["nome"].strip() == "", linha["nome"].strip().lower()))

    for linha in linhas:
        ws.append([linha[c] for c in COLUNAS])
        row_idx = ws.max_row

        motivo_bruto = linha["motivo"]
        # tenta o motivo exato primeiro (ex: "campo_obrigatorio_ausente:email");
        # cai pro prefixo antes de ":"/" " pros motivos com detalhe variável
        # (ex: "divergencia_cadastro: nome atual=...")
        destaque = DESTAQUE_POR_MOTIVO.get(motivo_bruto)
        if destaque is None:
            prefixo = motivo_bruto.split(" ")[0]
            destaque = DESTAQUE_POR_MOTIVO.get(prefixo)
        if destaque:
            coluna_alvo, é_erro = destaque
            col_idx = COLUNAS.index(coluna_alvo) + 1
            ws.cell(row=row_idx, column=col_idx).fill = FUNDO_ERRO if é_erro else FUNDO_AVISO

    for col_cells in ws.columns:
        largura = max(len(str(c.value)) if c.value is not None else 0 for c in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(largura + 2, 12), 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
