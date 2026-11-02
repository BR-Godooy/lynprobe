# LynProbe — registro de desenvolvimento

Projeto independente do analisador de logs Lynfort Sentinel. O registro abaixo é cronológico: observações sobre etapas pendentes descrevem aquele momento e são atualizadas nas seções seguintes. A versão atual inclui a interface final, treze capturas reais e testes reproduzíveis.

## Preparação para publicação

Os testes de regressão foram organizados em `tests/`, sem dependências externas e sem conexões reais. Os quatro grupos passaram na preparação do pacote. Referências a `.codex-build/` ao longo deste histórico identificam arquivos internos usados durante o desenvolvimento; essa pasta não faz parte da distribuição. As capturas originais tiveram seus hashes conferidos, e os links locais da documentação foram validados.

## Ambiente

- Usuário confirmado no print pelo comando `whoami`: `lynfort`.
- Nome da máquina no prompt: `kali`.
- Pasta do projeto na VM: `/home/lynfort/projetos/lynprobe`.
- Python 3.14.7 informado pelo autor; a consulta de versão não aparece nesta captura.
- O código inicial foi fornecido na conversa e digitado/executado pelo autor na VM. O arquivo fonte da VM ainda não foi recebido neste workspace.

## Primeiro resultado observado

Evidência: `evidencias/01-conexao-local-porta-80.png`, cópia sem edição da captura enviada pelo autor.

Comando: `python3 lynprobe.py`.

Saída visível:

```text
LynProbe | Verificando 127.0.0.1:80
ABERTA: conexão TCP aceita.
```

Conclusão limitada ao teste: uma conexão TCP à porta 80 do endereço de loopback foi aceita no ambiente do autor. Esse teste não identifica o software que respondeu, não verifica conteúdo HTTP nem confirma uma vulnerabilidade.

## Evolução: parâmetros no terminal

Após alterar a porta fixa para 81, o autor colou a saída do terminal informando conexão recusada em `127.0.0.1:81`.

Em seguida, foi fornecida uma segunda versão do código, com `argparse` para receber um IPv4 e uma porta, `ipaddress.IPv4Address` para validar o endereço e checagem de porta no intervalo 1–65535. O tempo limite permaneceu em dois segundos. O arquivo da VM ainda não foi recebido; a referência do código permanece a conversa.

Evidência: `evidencias/02-parametros-portas-80-e-81.png`, cópia sem edição da captura enviada pelo autor.

Resultados visíveis:

```text
python3 lynprobe.py 127.0.0.1 80
LynProbe | Verificando 127.0.0.1:80
ABERTA: conexão TCP aceita.

python3 lynprobe.py 127.0.0.1 81
LynProbe | Verificando 127.0.0.1:81
RECUSADA: a conexão foi recusada.
```

A captura confirma os dois resultados com os parâmetros fornecidos. Não houve identificação do serviço, teste HTTP ou confirmação de vulnerabilidade.

## Validação de entradas

Evidência: `evidencias/03-validacao-ip-e-porta.png`, cópia sem edição do print do autor.

- `python3 lynprobe.py 127.0.0.1 70000`: mensagem `A porta deve estar entre 1 e 65535.`
- `python3 lynprobe.py 999.1.1.1 80`: mensagem de argumento IPv4 inválido.
- Não aparece a mensagem `Verificando` em nenhum desses dois testes, em concordância com a validação anterior ao trecho de conexão no código fornecido.

## Verificação de múltiplas portas

O autor recebeu o código que aceita uma ou mais portas com `nargs="+"`, valida a lista antes das conexões e percorre as portas sequencialmente com `for`.

Evidência: `evidencias/04-multiplas-portas.png`, cópia sem edição do print do autor.

Comando: `python3 lynprobe.py 127.0.0.1 80 81 443`.

Resultados: 80/tcp com conexão aceita; 81/tcp e 443/tcp com conexão recusada. A evidência se limita a esses resultados TCP no loopback.

Ainda não há evidências de execução dos caminhos de tempo esgotado ou erro de conexão. A próxima evolução planejada é permitir configurar o tempo limite no terminal.

## Código completo com timeout configurável

O arquivo `lynprobe.py` deste workspace foi criado com a versão completa fornecida na conversa, incluindo `--timeout`, padrão de dois segundos e validação do intervalo maior que zero e até 60 segundos. O cabeçalho informa o timeout selecionado. Essa cópia não foi extraída da VM.

Evidência de execução pelo autor no Kali: `evidencias/05-timeout-configuravel.png`, cópia sem edição da captura enviada pelo autor.

Comando: `python3 lynprobe.py 127.0.0.1 80 81 443 --timeout 1`.

O cabeçalho mostra `Timeout: 1s`. A porta 80 aceitou a conexão; 81 e 443 recusaram. Esse teste verifica a aceitação do parâmetro e a preservação das classificações observadas; não demonstra o esgotamento real de uma conexão.

## Próxima versão: exportação JSON

O `lynprobe.py` do workspace agora contém a versão proposta com `--saida`, funções para separar a tentativa de conexão da execução da ferramenta e relatório JSON com alvo, timeout, horários UTC e resultados por porta. O modo de abertura `x` preserva arquivos de saída já existentes.

Verificações locais no Windows, usando Python 3.12 do ambiente de desenvolvimento: quatro classificações com sockets simulados, aplicação do timeout, gravação e leitura do JSON em UTF-8, preservação de relatório existente e rejeição de entradas inválidas antes das chamadas de conexão. Nenhuma conexão real foi feita nesses testes. O verificador fica em `.codex-build/lynprobe/check_report.py`, fora da pasta de evidências.

Evidência de execução do autor no Kali: `evidencias/06-exportacao-json.png`, cópia sem edição da captura enviada.

Comando visível: `python3 lynprobe.py 127.0.0.1 80 81 443 --timeout 1 --saida resultado-01.json`.

A porta 80 aceitou a conexão; 81 e 443 recusaram. O cabeçalho informa timeout de um segundo e a mensagem final é `Relatório salvo em: resultado-01.json`. Essa captura documenta a execução e a mensagem de gravação; o conteúdo do arquivo ainda não foi enviado ou validado no Kali nesta conversa.

Nenhum relatório simulado foi adicionado às evidências reais.

## Leitura do relatório no Kali

Evidência: `evidencias/07-conteudo-json-validado.png`, cópia sem edição do print do autor.

O comando `python3 -m json.tool resultado-01.json` exibiu o documento completo sem erro de parsing. Campos visíveis: ferramenta `LynProbe`, tipo `tcp_connect`, alvo `127.0.0.1`, timeout `1.0`, início e fim em `2026-11-02T17:50:15+00:00`, 80/tcp `aberta`, 81/tcp e 443/tcp `recusada`. Os horários são os declarados pelo ambiente do autor, sem conferência externa.

A imagem valida a leitura e os campos do JSON daquele teste. O arquivo JSON original não foi recebido no workspace e não foi reconstituído como se fosse um arquivo recebido.

O escape `\u00e3` nas mensagens exibidas corresponde ao caractere `ã`, decorrente da apresentação padrão do `json.tool`.

## Preservação de um relatório existente

Evidência: `evidencias/08-preservacao-relatorio.png`, cópia sem edição do print do autor.

O autor calculou o SHA-256 de `resultado-01.json`, repetiu a execução com o mesmo nome de saída e calculou novamente o hash. O programa exibiu `O arquivo de saída já existe. Escolha outro nome.` sem o cabeçalho de verificação. Os dois hashes visíveis são iguais, demonstrando que o conteúdo desse arquivo foi preservado durante o teste.

Essa etapa conclui a verificação manual do núcleo atual: IPv4 e porta inválidos rejeitados, conexões TCP aceitas/recusadas, lista de portas, parâmetro de timeout, gravação e leitura de JSON e preservação de saída existente. Tempo esgotado e outros erros de conexão têm testes locais com sockets simulados, sem evidência de ocorrência real no Kali. Sem teste de identificação de serviço, UDP ou IPv6, que não fazem parte do código atual.

## Próxima evolução: modos de seleção de portas

Por solicitação do autor, o código do workspace agora oferece `--comuns` (lista fixa de 30 portas), `--intervalo INICIO-FIM` (limites inclusivos) e `--todas` (1–65535). A lista manual continua aceita. Cada execução usa um único modo, com remoção de duplicatas e verificação sequencial. O relatório inclui o modo e a quantidade selecionada. O cabeçalho mostra a espera acumulada se cada tentativa consumir o prazo, acrescida da sobrecarga, sem prometer uma duração real.

Verificações de desenvolvimento ficam em `.codex-build/lynprobe/check_ports.py`, usando conexões simuladas, sem varredura real da rede.

Evidência: `evidencias/09-portas-comuns.png`, cópia sem edição do print do autor. O cabeçalho informa alvo `127.0.0.1`, timeout de um segundo, seleção `comuns` e 30 portas. A porta 80 aceitou conexão e as demais listadas recusaram. A execução concluiu 30 verificações e informou gravação de `comuns-01.json`. A imagem não inclui o comando executado ou o conteúdo desse arquivo. Não há evidência de teste de intervalo ou de todas as portas no Kali.

## Próxima evolução: filtro de exibição

O autor solicitou exibir apenas portas abertas ou filtradas. Como a conexão TCP com timeout não demonstra a causa da ausência de resposta, o filtro implementado é `--mostrar abertas-inconclusivas`: inclui `aberta` e `tempo_esgotado`, sem introduzir uma classificação confirmada de filtragem. Também estão disponíveis `--mostrar abertas` e `--mostrar todas` (padrão).

O filtro se aplica somente à saída dos resultados no terminal. Todas as portas selecionadas são verificadas e registradas no JSON, incluindo recusas e erros. O resumo conta os resultados exibidos/omitidos e um aviso aponta outros erros de conexão caso tenham sido omitidos da tela.

Testes locais com conexões simuladas ficam em `.codex-build/lynprobe/check_display.py`. Ainda não há print do autor executando a versão com filtro no Kali.

## Próxima evolução: identificação de serviço e versão

A pedido do autor, foi adicionada a opção `--identificar`, compatível com os filtros e com o JSON. Em portas abertas, ela abre uma conexão adicional, lê uma saudação ou envia HEAD HTTP. Reconhece HTTP, SSH e FTP quando as respostas correspondem às assinaturas implementadas. Não infere o serviço apenas pelo número da porta nem transforma a versão do protocolo em versão do software. Ausência de identificação ou versão é representada por valores nulos, sem alterar o estado TCP já observado.

Os verificadores `.codex-build/lynprobe/check_services.py` e `check_services_loopback.py` exercitaram dados simulados e servidores de teste temporários em 127.0.0.1 no Windows. Houve reconhecimento HTTP/SSH/FTP em portas efêmeras, controle de limites de leitura, cabeçalho ausente/parcial, sanitização da saída, manutenção dos filtros e registro no JSON. Os servidores de teste foram encerrados. Seus banners são dados de teste, sem evidência de serviços ou versões reais na VM.

Ainda não há evidência de execução de `--identificar` pelo autor no Kali. O próximo teste proposto utiliza o serviço da porta 80 do próprio Kali, antes de iniciar a etapa de design.

## Identificação HTTP observada no Kali

Evidência recebida posteriormente: `evidencias/10-identificacao-http-apache.png`, cópia sem edição do print do autor. A tela mostra alvo `127.0.0.1`, timeout de dois segundos, seleção de uma porta, exibição de abertas, identificação habilitada, 80/tcp aberta, serviço HTTP, software Apache e versão 2.4.69. A execução concluiu uma verificação e informou gravação de `servicos-01.json`. O comando e o conteúdo do arquivo não aparecem na imagem. Essa é a versão declarada pelo serviço, sem validação independente do binário instalado ou de vulnerabilidades.

## Apresentação Lynfort no terminal

A pedido do autor, a saída foi dividida em configuração, resultados e resumo, com quebras de linha, mais espaçamento e campos de serviço/software/versão separados. O logo foi derivado da imagem original da Lynfort em caracteres Unicode de terminal e incorporado ao script. Não houve modificação do PNG original nem uso de geração de imagens para representar uma execução.

O cabeçalho usa amarelo sobre azul-escuro. As cores respeitam TTY, NO_COLOR, TERM=dumb e `--sem-cor`; saída redirecionada permanece sem códigos ANSI. Há cabeçalho compacto para janelas estreitas. O JSON mantém o comportamento anterior.

As verificações locais de regressão passaram; `check_style.py` conferiu cores, modos sem cor, saída redirecionada e larguras de 40 e 96 colunas. A prévia `.codex-build/lynprobe/terminal-preview.png` foi renderizada localmente a partir de dados de teste e identifica isso na própria imagem. Não é evidência de execução da interface no Kali. Aguarda-se teste do autor com essa apresentação.

## Ajuste do logo para ASCII original

O print `evidencias/11-cabecalho-terminal-kali.png` foi recebido do autor, preservado sem edição, e mostra a apresentação anterior do cabeçalho no Kali, incluindo cores e logo em caracteres Unicode. A captura não mostra o resultado final da verificação.

O autor solicitou redesenhar o logo, em vez de reutilizar sua conversão de imagem. O cabeçalho foi substituído por arte original em ASCII simples: lince estilizado e LYNFORT em letras de caracteres. O desenho está embutido no mesmo `lynprobe.py`. O PNG original não foi editado. Esse ajuste altera apenas a constante do logo; a lógica de rede e o relatório permanecem iguais.

O verificador de apresentação passou novamente e a prévia de dados de teste foi atualizada fora das evidências. Ainda não há print do ASCII original sendo executado pelo autor no Kali.

## Ajuste final do cabeçalho: somente escrita

O autor solicitou retirar o lince e manter apenas a escrita. O cabeçalho atual exibe LYNFORT em letras ASCII, com amarelo e azul-escuro; a versão compacta também não inclui animal. Esse é um ajuste de apresentação. Não há nova evidência de execução no Kali após essa alteração.

## Registro da apresentação final no Kali

O autor enviou duas capturas da apresentação final, preservadas sem edição e com igualdade SHA-256 conferida em relação aos anexos recebidos:

- `evidencias/12-visual-final-cabecalho.png`: escrita LYNFORT em ASCII, LynProbe, cabeçalho amarelo sobre azul-escuro, configuração em blocos e resultado com serviço, software e versão em linhas distintas.
- `evidencias/13-visual-final-resultados-resumo.png`: configuração, resultado e resumo de uma porta verificada, com um resultado exibido e nenhum omitido.

Campos visíveis: alvo `127.0.0.1`, seleção `lista`, uma porta, timeout de dois segundos, execução sequencial, exibição `abertas`, identificação habilitada, 80/tcp aberta, HTTP, Apache e versão declarada 2.4.69. O comando completo e uma nova gravação de relatório não aparecem nessas duas capturas, portanto não são inferidos.

Agora existem 13 capturas reais de etapas do desenvolvimento. O manifesto `evidencias/SHA256SUMS.txt` identifica os arquivos preservados. As prévias renderizadas com dados de teste continuam fora dessa pasta.
