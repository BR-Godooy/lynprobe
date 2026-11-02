import argparse
import ipaddress
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import socket
import sys
import time
import textwrap

LOGO_ASCII = '  #     #   # #   # #####  ###  ####  #####\n  #     #   # ##  # #     #   # #   #   #  \n  #      # #  ##  # #     #   # #   #   #  \n  #       #   # # # ####  #   # ####    #  \n  #       #   #  ## #     #   # # #     #  \n  #       #   #  ## #     #   # #  #    #  \n  #####   #   #   # #      ###  #   #   #  '


# Seleção fixa do projeto; não é um ranking estatístico de portas.
PORTAS_COMUNS = (
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
    389, 443, 445, 465, 587, 636, 993, 995,
    1433, 1521, 3306, 3389, 5432, 5900, 6379,
    8000, 8080, 8443, 9200, 27017,
)

FILTROS_EXIBICAO = {
    "todas": None,
    "abertas": {"aberta"},
    "abertas-inconclusivas": {"aberta", "tempo_esgotado"},
}


class Terminal:
    """Apresentação no terminal; não modifica os resultados da verificação."""

    AMARELO = "1;38;2;255;214;0"
    AZUL = "38;2;143;181;224"
    BRANCO = "38;2;225;233;244"
    PAINEL = "1;38;2;255;214;0;48;2;13;25;46"

    def __init__(self, sem_cor=False):
        self.colorido = (
            sys.stdout.isatty() and not sem_cor
            and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb"
        )
        self.largura = max(20, min(96, shutil.get_terminal_size((100, 24)).columns - 2))

    def pintar(self, texto, estilo):
        return f"\033[{estilo}m{texto}\033[0m" if self.colorido else texto

    def texto(self, texto, estilo=None):
        for linha in textwrap.wrap(texto_seguro(str(texto), 4096), self.largura) or [""]:
            print(self.pintar(linha, estilo) if estilo else linha)

    def cabecalho(self):
        print()
        if self.largura >= 46:
            linhas = LOGO_ASCII.strip("\n").splitlines()
        else:
            linhas = ["  LYNFORT"]
        for linha in ["", *linhas, "", "  L Y N P R O B E", "  Scanner TCP | Lynfort", ""]:
            print(self.pintar(linha[:self.largura].ljust(self.largura), self.PAINEL))

    def secao(self, titulo):
        print()
        print(self.pintar("-" * self.largura, self.AZUL))
        self.texto(titulo, self.AMARELO)
        print()

    def campo(self, nome, valor):
        prefixo = f"  {nome}: "
        linhas = textwrap.wrap(texto_seguro(str(valor), 4096), max(10, self.largura - len(prefixo))) or [""]
        for indice, linha in enumerate(linhas):
            inicio = prefixo if indice == 0 else " " * len(prefixo)
            print(self.pintar(inicio + linha, self.BRANCO))

    def resultado(self, resultado):
        estado = resultado["estado"]
        rotulo = estado.replace("_", " ").upper()
        estilo = self.AMARELO if estado in {"aberta", "tempo_esgotado"} else self.AZUL
        self.texto(f"{resultado['porta']}/tcp — {rotulo}: {resultado['mensagem']}.", estilo)
        if "identificacao" in resultado:
            identificacao = resultado["identificacao"]
            self.campo("Serviço", identificacao["servico"] or "não identificado")
            self.campo("Software", identificacao["produto"] or "não informado")
            self.campo("Versão", identificacao["versao"] or "não informada")
        print()


def ler_intervalo(valor):
    """Valida um intervalo inclusivo, por exemplo 80-85."""
    partes = valor.split("-")
    if len(partes) != 2:
        raise argparse.ArgumentTypeError("Use INICIO-FIM. Exemplo: 80-85.")

    try:
        inicio, fim = (int(parte) for parte in partes)
    except ValueError:
        raise argparse.ArgumentTypeError("Os limites do intervalo devem ser inteiros.")

    if not 1 <= inicio <= fim <= 65535:
        raise argparse.ArgumentTypeError(
            "Use um intervalo crescente entre 1 e 65535."
        )

    return range(inicio, fim + 1)


def selecionar_portas(args, parser):
    """Escolhe um único modo e remove portas repetidas, mantendo a ordem."""
    tem_modo = args.comuns or args.todas or args.intervalo is not None
    if args.portas and tem_modo:
        parser.error("Use uma lista de portas OU uma das opções de seleção.")

    if args.comuns:
        portas, modo = PORTAS_COMUNS, "comuns"
    elif args.todas:
        portas, modo = range(1, 65536), "todas"
    elif args.intervalo is not None:
        portas, modo = args.intervalo, "intervalo"
    elif args.portas:
        portas, modo = args.portas, "lista"
    else:
        parser.error("Informe portas, --comuns, --intervalo INICIO-FIM ou --todas.")

    for porta in portas:
        if not 1 <= porta <= 65535:
            parser.error(f"Porta inválida: {porta}. Use valores de 1 a 65535.")

    return list(dict.fromkeys(portas)), modo


def formatar_duracao(segundos):
    horas, restante = divmod(math.ceil(segundos), 3600)
    minutos, segundos = divmod(restante, 60)
    return f"{horas}h {minutos}min {segundos}s"


def verificar_porta(alvo, porta, timeout):
    """Tenta uma conexão TCP e devolve seu resultado como um dicionário."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexao:
            conexao.settimeout(timeout)
            conexao.connect((alvo, porta))

        estado = "aberta"
        mensagem = "conexão aceita"

    except ConnectionRefusedError:
        estado = "recusada"
        mensagem = "conexão recusada"

    except TimeoutError:
        estado = "tempo_esgotado"
        mensagem = "sem resposta no prazo; resultado inconclusivo"

    except OSError as erro:
        estado = "erro"
        mensagem = str(erro)

    return {
        "porta": porta,
        "protocolo": "tcp",
        "estado": estado,
        "mensagem": mensagem,
    }


def texto_seguro(texto, limite=160):
    """Limita dados recebidos e remove controles antes de exibi-los."""
    return "".join(caractere if caractere.isprintable() else " "
                   for caractere in texto).strip()[:limite]


def separar_produto_versao(software):
    software = texto_seguro(software)
    encontrado = re.match(
        r"([A-Za-z][A-Za-z0-9.+-]*?)[/_ ](\d[0-9A-Za-z.+:~_-]*)",
        software,
    )
    if encontrado:
        return encontrado.group(1), encontrado.group(2)
    return (software.split()[0] if software else None), None


def identificacao_vazia(observacao):
    return {
        "servico": None,
        "produto": None,
        "versao": None,
        "metodo": "nao_identificado",
        "evidencia": None,
        "observacao": texto_seguro(observacao),
    }


def analisar_banner(dados, metodo="banner_tcp"):
    """Reconhece respostas explícitas, sem deduzir o serviço pela porta."""
    texto = dados.decode("utf-8", errors="replace")
    linhas = texto.splitlines()
    primeira = linhas[0] if linhas else ""
    if "\n" not in texto:
        return identificacao_vazia("Saudação incompleta ou sem assinatura reconhecida.")

    if re.match(r"^HTTP/1\.[01] [1-5][0-9]{2}(?:\s|$)", primeira):
        cabecalho = texto.split("\r\n\r\n", 1)[0] + "\r\n" if "\r\n\r\n" in texto else texto
        servidor = re.search(r"^Server:[ \t]*([^\r\n]*)\r?\n", cabecalho, re.I | re.M)
        software = servidor.group(1).strip() if servidor else ""
        produto, versao = separar_produto_versao(software)
        return {
            "servico": "HTTP",
            "produto": produto,
            "versao": versao,
            "metodo": metodo,
            "evidencia": texto_seguro(f"Server: {software}" if software else primeira),
            "observacao": "Informações declaradas pelo servidor; podem estar omitidas ou alteradas.",
        }

    ssh = re.search(r"^SSH-([0-9.]+)-([^\s]+)(?:[ \t][^\r\n]*)?\r?\n", texto, re.M)
    if ssh:
        produto, versao = separar_produto_versao(ssh.group(2))
        return {
            "servico": "SSH",
            "produto": produto,
            "versao": versao,
            "metodo": "banner_tcp",
            "evidencia": texto_seguro(ssh.group(0)),
            "observacao": "Versão do software declarada no banner; não é a versão do protocolo SSH.",
        }

    if primeira.startswith("220") and re.search(
        r"\bFTP\b|\bvsFTPd\b|\bProFTPD\b|\bPure-FTPd\b", primeira, re.I
    ):
        software = re.search(
            r"\b(vsFTPd|ProFTPD|Pure-FTPd)(?:[/ ]+(\d[0-9A-Za-z.+~_-]*))?",
            primeira, re.I,
        )
        return {
            "servico": "FTP",
            "produto": software.group(1) if software else None,
            "versao": software.group(2) if software else None,
            "metodo": "banner_tcp",
            "evidencia": texto_seguro(primeira),
            "observacao": "Identificação declarada no banner de boas-vindas.",
        }

    resultado = identificacao_vazia("Resposta sem assinatura suportada nesta versão.")
    resultado["evidencia"] = texto_seguro(primeira) or None
    return resultado


def receber_limitado(conexao, timeout, limite, terminador, inicial=b""):
    """Limita o tamanho e o tempo total de uma etapa de leitura."""
    dados = inicial[:limite]
    prazo = time.monotonic() + timeout
    while len(dados) < limite and terminador not in dados:
        restante = prazo - time.monotonic()
        if restante <= 0:
            break
        conexao.settimeout(restante)
        try:
            bloco = conexao.recv(min(4096, limite - len(dados)))
        except OSError:
            break
        if not bloco:
            break
        dados += bloco
    return dados


def identificar_servico(alvo, porta, timeout):
    """Abre uma conexão adicional para banner ou HEAD HTTP sem autenticação."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexao:
            conexao.settimeout(timeout)
            conexao.connect((alvo, porta))

            # Alguns serviços, como SSH e FTP, enviam uma saudação primeiro.
            banner = receber_limitado(conexao, min(timeout, 0.35), 4096, b"\n")
            if banner:
                if banner.startswith(b"HTTP/"):
                    banner = receber_limitado(
                        conexao, timeout, 8192, b"\r\n\r\n", inicial=banner
                    )
                return analisar_banner(banner)

            # Sem saudação, tenta obter somente os cabeçalhos HTTP.
            requisicao = (
                f"HEAD / HTTP/1.0\r\nHost: {alvo}:{porta}\r\n"
                "User-Agent: LynProbe\r\nConnection: close\r\n\r\n"
            )
            conexao.settimeout(timeout)
            conexao.sendall(requisicao.encode("ascii"))
            resposta = receber_limitado(conexao, timeout, 8192, b"\r\n\r\n")
            if resposta:
                return analisar_banner(resposta, metodo="http_head")
            return identificacao_vazia("Nenhuma resposta identificável foi recebida no prazo.")
    except OSError as erro:
        return identificacao_vazia(f"Não foi possível identificar o serviço: {erro}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="LynProbe — scanner de portas TCP."
    )
    parser.add_argument(
        "alvo", type=ipaddress.IPv4Address,
        help="Endereço IPv4 que será verificado."
    )
    parser.add_argument(
        "portas", type=int, nargs="*",
        help="Lista de portas TCP, de 1 a 65535. Exemplo: 80 81 443."
    )
    selecao = parser.add_mutually_exclusive_group()
    selecao.add_argument(
        "--comuns", action="store_true",
        help="Verifica as 30 portas TCP predefinidas no projeto."
    )
    selecao.add_argument(
        "--intervalo", type=ler_intervalo, metavar="INICIO-FIM",
        help="Verifica um intervalo inclusivo. Exemplo: 1-1024."
    )
    selecao.add_argument(
        "--todas", action="store_true",
        help="Verifica todas as portas TCP de 1 a 65535, sequencialmente."
    )
    parser.add_argument(
        "--timeout", type=float, default=2.0,
        help="Tempo limite por conexão, maior que zero e até 60 segundos. Padrão: 2."
    )
    parser.add_argument(
        "--saida", type=Path,
        help="Salva um relatório JSON em um arquivo novo. Exemplo: resultado-01.json"
    )
    parser.add_argument(
        "--mostrar", choices=tuple(FILTROS_EXIBICAO), default="todas",
        help=(
            "Filtra os resultados na tela. Padrão: todas. "
            "O JSON sempre mantém todos os resultados. "
            "Tempo esgotado é inconclusivo, sem confirmar filtragem."
        )
    )
    parser.add_argument(
        "--identificar", action="store_true",
        help="Tenta identificar HTTP, SSH e FTP nas portas abertas por respostas e banners."
    )
    parser.add_argument(
        "--sem-cor", action="store_true",
        help="Desativa as cores ANSI. NO_COLOR e saída redirecionada também as desativam."
    )
    args = parser.parse_args(argv)

    # Valida todos os parâmetros antes de iniciar as conexões.
    if not 0 < args.timeout <= 60:
        parser.error("O timeout deve ser maior que zero e no máximo 60 segundos.")

    portas, modo = selecionar_portas(args, parser)

    if args.saida is not None and args.saida.exists():
        parser.error("O arquivo de saída já existe. Escolha outro nome.")

    alvo = str(args.alvo)
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    resultados = []
    exibidos = 0
    estados_visiveis = FILTROS_EXIBICAO[args.mostrar]
    terminal = Terminal(sem_cor=args.sem_cor)
    terminal.cabecalho()
    terminal.secao("CONFIGURAÇÃO DA VERIFICAÇÃO")
    terminal.campo("Alvo", alvo)
    terminal.campo("Seleção", modo)
    terminal.campo("Portas", len(portas))
    terminal.campo("Timeout", f"{args.timeout:g}s por conexão")
    terminal.campo("Execução", "sequencial")
    terminal.campo("Exibição", args.mostrar)
    if args.identificar:
        terminal.campo("Identificação", "banners TCP e HTTP HEAD")
        terminal.texto("A identificação adiciona tempo nas portas abertas.", Terminal.AZUL)
    terminal.campo("Espera acumulada", f"{formatar_duracao(len(portas) * args.timeout)} + sobrecarga")
    terminal.texto("Cenário em que todas as conexões esgotam o prazo; não é uma previsão exata.", Terminal.AZUL)
    terminal.secao("RESULTADOS")

    # Verifica as portas sequencialmente e guarda cada resultado.
    try:
        for porta in portas:
            resultado = verificar_porta(alvo, porta, args.timeout)
            if args.identificar and resultado["estado"] == "aberta":
                resultado = dict(resultado)
                resultado["identificacao"] = identificar_servico(alvo, porta, args.timeout)
            resultados.append(resultado)
            if estados_visiveis is None or resultado["estado"] in estados_visiveis:
                terminal.resultado(resultado)
                exibidos += 1
    except KeyboardInterrupt:
        print("\nVerificação interrompida. Nenhum relatório JSON foi salvo.", file=sys.stderr)
        return 130

    terminal.secao("RESUMO")
    terminal.texto(f"Concluído: {len(resultados)} portas verificadas.", Terminal.AMARELO)
    terminal.texto(f"Resultados exibidos: {exibidos} | Omitidos na tela: {len(resultados) - exibidos}.")
    if exibidos == 0:
        print("Nenhum resultado corresponde ao filtro nesta seleção.")

    erros = sum(resultado["estado"] == "erro" for resultado in resultados)
    if erros and args.mostrar != "todas":
        print(
            f"Aviso: ocorreram {erros} erros de conexão. "
            "Use --mostrar todas para exibir os detalhes.",
            file=sys.stderr,
        )

    if args.saida is not None:
        relatorio = {
            "ferramenta": "LynProbe",
            "tipo_verificacao": "tcp_connect",
            "alvo": alvo,
            "timeout_segundos": args.timeout,
            "modo_portas": modo,
            "quantidade_portas": len(portas),
            "exibicao_terminal": args.mostrar,
            "identificacao_habilitada": args.identificar,
            "inicio_utc": inicio,
            "fim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "resultados": resultados,
        }

        try:
            # O modo "x" cria um arquivo novo sem sobrescrever um existente.
            with args.saida.open("x", encoding="utf-8") as arquivo:
                json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)
                arquivo.write("\n")
        except OSError as erro:
            print(f"Não foi possível salvar o relatório: {erro}", file=sys.stderr)
            return 1

        print()
        terminal.texto(f"Relatório salvo em: {args.saida}", Terminal.AMARELO)

    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
