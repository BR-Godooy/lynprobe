import contextlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import tempfile
from unittest.mock import MagicMock, patch

source = Path(__file__).resolve().parents[1] / 'lynprobe.py'
spec = importlib.util.spec_from_file_location('lynprobe_services',source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

http = module.analisar_banner(b'HTTP/1.1 200 OK\r\nServer: Apache/2.4.69 (Debian)\r\n\r\n',metodo='http_head')
assert http['servico'] == 'HTTP' and http['produto'] == 'Apache' and http['versao'] == '2.4.69'
assert http['metodo'] == 'http_head' and http['evidencia'].startswith('Server: ')
for banner in [b'HTTP/1.0 403 Forbidden\r\nServer: nginx\r\n\r\n',b'HTTP/1.1 501 Not Implemented\r\n\r\n']:
    result = module.analisar_banner(banner)
    assert result['servico'] == 'HTTP' and result['versao'] is None
partial = module.analisar_banner(b'HTTP/1.1 200 OK\r\nServer: Apache/2.4.')
assert partial['servico'] == 'HTTP' and partial['versao'] is None
body_only = module.analisar_banner(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nServer: Fake/9.9\r\n')
assert body_only['servico'] == 'HTTP' and body_only['produto'] is None
ssh = module.analisar_banner(b'SSH-2.0-OpenSSH_9.9p2 Debian-example\r\n')
assert ssh['servico'] == 'SSH' and ssh['produto'] == 'OpenSSH' and ssh['versao'] == '9.9p2'
assert module.analisar_banner(b'SSH-2.0-OpenSSH_9.9')['servico'] is None
ftp = module.analisar_banner(b'220 (vsFTPd 3.0.5)\r\n')
assert ftp['servico'] == 'FTP' and ftp['versao'] == '3.0.5'
assert module.analisar_banner(b'220 Welcome to FTP\r\n')['versao'] is None
assert module.analisar_banner(b'220 mail.example ESMTP ready\r\n')['servico'] is None
assert module.analisar_banner(b'garbage\r\n')['servico'] is None
assert '\x1b' not in module.texto_seguro('\x1b[31mteste\n\x00')
assert len(module.texto_seguro('x'*1000)) == 160

# Resposta HEAD por socket simulado, incluindo conexão em porta não padrão.
connection = MagicMock()
connection.recv.side_effect = [socket.timeout(),b'HTTP/1.0 200 OK\r\nServer: LynProbeTest/1.2.3\r\n\r\n']
context = MagicMock()
context.__enter__.return_value = connection
with patch.object(module.socket,'socket',return_value=context):
    identified = module.identificar_servico('127.0.0.1',8123,1)
assert identified['servico'] == 'HTTP' and identified['versao'] == '1.2.3'
assert connection.sendall.call_args.args[0].startswith(b'HEAD / HTTP/1.0\r\n')
assert b'Host: 127.0.0.1:8123' in connection.sendall.call_args.args[0]
assert context.__exit__.call_count == 1

# Leitura lenta não pode ultrapassar o limite total da etapa nem o limite de bytes.
connection = MagicMock()
connection.recv.return_value = b'abc'
with patch.object(module.time,'monotonic',side_effect=[0,0.1,0.9,1.1]):
    received = module.receber_limitado(connection,1,100,b'\n')
assert received == b'abcabc' and connection.recv.call_count == 2
connection = MagicMock()
connection.recv.side_effect = lambda size: b'x'*size
received = module.receber_limitado(connection,1,8192,b'\r\n\r\n')
assert len(received) == 8192

base = Path(tempfile.gettempdir()).resolve()
with tempfile.TemporaryDirectory(prefix='services-check-',dir=base) as temp:
    assert Path(temp).resolve().parent == base
    destination = Path(temp) / 'resultado.json'
    records = [{'porta':80,'protocolo':'tcp','estado':'aberta','mensagem':'conexão aceita'}, {'porta':81,'protocolo':'tcp','estado':'recusada','mensagem':'conexão recusada'}]
    with patch.object(module,'verificar_porta',side_effect=records), patch.object(module,'identificar_servico',return_value=http) as identify, contextlib.redirect_stdout(io.StringIO()) as output:
        result = module.main(['127.0.0.1','80','81','--identificar','--mostrar','abertas','--saida',str(destination)])
    assert result == 0
    identify.assert_called_once_with('127.0.0.1',80,2.0)
    assert 'Serviço: HTTP' in output.getvalue()
    assert 'Software: Apache' in output.getvalue()
    assert 'Versão: 2.4.69' in output.getvalue()
    assert '81/tcp — ' not in output.getvalue()
    saved = json.loads(destination.read_text(encoding='utf-8'))
    assert saved['identificacao_habilitada'] is True and len(saved['resultados']) == 2
    assert saved['resultados'][0]['identificacao'] == http
    assert 'identificacao' not in saved['resultados'][1]

    # Falhar na identificação não transforma uma porta aberta em timeout/fechada.
    with patch.object(module,'verificar_porta',return_value=records[0]), patch.object(module,'identificar_servico',return_value=module.identificacao_vazia('Sem resposta')), contextlib.redirect_stdout(io.StringIO()) as output:
        result = module.main(['127.0.0.1','80','--identificar'])
    assert result == 0 and 'ABERTA' in output.getvalue()
    assert 'Serviço: não identificado' in output.getvalue()

    # Sem opção, não há sondagem adicional de serviço.
    with patch.object(module,'verificar_porta',return_value=records[0]), patch.object(module,'identificar_servico') as identify, contextlib.redirect_stdout(io.StringIO()):
        assert module.main(['127.0.0.1','80']) == 0
        identify.assert_not_called()

print('OK: HTTP/SSH/FTP por resposta, versoes ausentes ou parciais, limites de leitura, controles de terminal, identificacao so em abertas, filtros e JSON. Dados e sockets simulados, sem conexoes reais.')
