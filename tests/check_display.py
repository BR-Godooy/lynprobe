import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'lynprobe.py'
spec = importlib.util.spec_from_file_location('lynprobe_display',source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
records = [
    {'porta':80,'protocolo':'tcp','estado':'aberta','mensagem':'conexão aceita'},
    {'porta':81,'protocolo':'tcp','estado':'recusada','mensagem':'conexão recusada'},
    {'porta':82,'protocolo':'tcp','estado':'tempo_esgotado','mensagem':'sem resposta no prazo; resultado inconclusivo'},
    {'porta':83,'protocolo':'tcp','estado':'erro','mensagem':'falha de rota simulada'},
]
base = Path(tempfile.gettempdir()).resolve()
with tempfile.TemporaryDirectory(prefix='display-check-',dir=base) as temp:
    assert Path(temp).resolve().parent == base
    for filtro, expected in [('todas',[80,81,82,83]),('abertas',[80]),('abertas-inconclusivas',[80,82])]:
        destination = Path(temp) / (filtro+'.json')
        with patch.object(module,'verificar_porta',side_effect=records) as probe, contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as errors:
            result = module.main(['127.0.0.1','80','81','82','83','--mostrar',filtro,'--saida',str(destination)])
        assert result == 0 and probe.call_count == 4
        lines = output.getvalue().splitlines()
        visible = [int(line.split('/tcp')[0]) for line in lines if '/tcp — ' in line]
        assert visible == expected
        assert f'Resultados exibidos: {len(expected)} | Omitidos na tela: {4-len(expected)}.' in output.getvalue()
        document = json.loads(destination.read_text(encoding='utf-8'))
        assert document['resultados'] == records
        assert document['exibicao_terminal'] == filtro and document['quantidade_portas'] == 4
        assert 'FILTRADA' not in output.getvalue()
        if filtro != 'todas': assert '1 erros de conexão' in errors.getvalue()

    with patch.object(module,'verificar_porta',return_value=records[1]), contextlib.redirect_stdout(io.StringIO()) as output:
        result = module.main(['127.0.0.1','81','--mostrar','abertas'])
    assert result == 0 and 'Nenhum resultado corresponde ao filtro nesta seleção.' in output.getvalue()
    assert '/tcp — ' not in output.getvalue()

    with patch.object(module,'verificar_porta') as probe, contextlib.redirect_stderr(io.StringIO()):
        try:
            module.main(['127.0.0.1','80','--mostrar','filtradas'])
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError('Invalid display filter accepted')
        probe.assert_not_called()

print('OK: filtros de tela, timeout inconclusivo, resumo, aviso de erros e JSON completo preservado em todos os modos. Sem conexoes reais.')
