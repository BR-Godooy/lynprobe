# Evidências do LynProbe

Capturas enviadas pelo autor durante o desenvolvimento no Kali, preservadas sem edição. Cada registro corresponde à versão e ao teste daquele momento. O desenvolvimento completo está em [NOTAS-DO-LAB.md](../NOTAS-DO-LAB.md).

| Arquivo | Registro |
| --- | --- |
| [01 — Conexão local](01-conexao-local-porta-80.png) | Primeiro teste: conexão aceita em 127.0.0.1:80. |
| [02 — Parâmetros](02-parametros-portas-80-e-81.png) | IP e porta no terminal: 80 aceita e 81 recusada. |
| [03 — Entradas inválidas](03-validacao-ip-e-porta.png) | Porta fora do intervalo e IPv4 inválido rejeitados. |
| [04 — Múltiplas portas](04-multiplas-portas.png) | Lista com 80, 81 e 443. |
| [05 — Timeout configurável](05-timeout-configuravel.png) | Uso do parâmetro de um segundo; sem ocorrência real de timeout na captura. |
| [06 — Exportação](06-exportacao-json.png) | Execução com mensagem de relatório salvo. |
| [07 — Leitura do JSON](07-conteudo-json-validado.png) | Documento exibido por json.tool, sem erro de parsing. |
| [08 — Preservação do relatório](08-preservacao-relatorio.png) | Nome existente rejeitado e hashes iguais antes/depois. |
| [09 — Portas comuns](09-portas-comuns.png) | 30 verificações: 80 aceita e as demais recusadas; mensagem de relatório salvo. |
| [10 — Identificação](10-identificacao-http-apache.png) | HTTP, Apache e versão declarada 2.4.69. |
| [11 — Cabeçalho anterior](11-cabecalho-terminal-kali.png) | Primeira apresentação com logo em caracteres, depois substituída a pedido do autor. |
| [12 — Cabeçalho final](12-visual-final-cabecalho.png) | Escrita LYNFORT em ASCII, cores e campos separados. |
| [13 — Resultado e resumo](13-visual-final-resultados-resumo.png) | Apresentação final: uma porta verificada e um resultado exibido. |

O [manifesto SHA-256](SHA256SUMS.txt) permite conferir a integridade dessas cópias. As prévias de design e os testes com dados simulados não estão nesta pasta.
