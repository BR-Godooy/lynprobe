import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

source = Path(__file__).resolve().parents[1] / 'lynprobe.py'
spec = importlib.util.spec_from_file_location('lynprobe_candidate', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Verifica classificações e aplicação do timeout sem conexões reais.
for error, expected in [(None,'aberta'),(ConnectionRefusedError(),'recusada'),(TimeoutError(),'tempo_esgotado'),(OSError('falha de rota de teste'),'erro')]:
    connection = MagicMock()
    connection.connect.side_effect = error
    context = MagicMock()
    context.__enter__.return_value = connection
    with patch.object(module.socket, 'socket', return_value=context):
        record = module.verificar_porta('127.0.0.1',80,0.5)
    assert record['estado'] == expected
    assert record['porta'] == 80 and record['protocolo'] == 'tcp'
    connection.settimeout.assert_called_once_with(0.5)
    connection.connect.assert_called_once_with(('127.0.0.1',80))
    assert context.__exit__.call_count == 1

test_base = Path(tempfile.gettempdir()).resolve()
with tempfile.TemporaryDirectory(prefix='lynprobe-check-', dir=test_base) as temp:
    assert Path(temp).resolve().parent == test_base
    destination = Path(temp) / 'resultado.json'
    records = [
        {'porta':80,'protocolo':'tcp','estado':'aberta','mensagem':'conexão aceita'},
        {'porta':81,'protocolo':'tcp','estado':'recusada','mensagem':'conexão recusada'},
    ]
    with patch.object(module, 'verificar_porta', side_effect=records) as probe, contextlib.redirect_stdout(io.StringIO()):
        result = module.main(['127.0.0.1','80','81','--timeout','1','--saida',str(destination)])
    assert result == 0 and probe.call_count == 2
    document = json.loads(destination.read_text(encoding='utf-8'))
    assert document['resultados'] == records and document['timeout_segundos'] == 1
    assert document['alvo'] == '127.0.0.1' and document['inicio_utc'].endswith('+00:00')
    preserved = destination.read_bytes()
    with patch.object(module, 'verificar_porta') as probe, contextlib.redirect_stderr(io.StringIO()):
        try:
            module.main(['127.0.0.1','80','--saida',str(destination)])
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError('Existing report was not rejected')
        probe.assert_not_called()
    assert destination.read_bytes() == preserved

    for arguments in [ ['999.1.1.1','80'],['127.0.0.1','80','70000'],['127.0.0.1','80','--timeout','nan'],['127.0.0.1','80','--timeout','0'] ]:
        with patch.object(module, 'verificar_porta') as probe, contextlib.redirect_stderr(io.StringIO()):
            try:
                module.main(arguments)
            except SystemExit as error:
                assert error.code == 2
            else:
                raise AssertionError('Invalid input accepted')
            probe.assert_not_called()

print('OK: 4 classificacoes com sockets simulados, timeout aplicado, JSON e UTF-8, arquivo existente preservado e entradas invalidas rejeitadas. Sem conexoes reais e sem execucao no Kali.')
