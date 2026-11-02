import ast
import contextlib
import importlib.util
import io
from pathlib import Path
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'lynprobe.py'
ast.parse(source.read_text(encoding='utf-8'))
spec = importlib.util.spec_from_file_location('lynprobe_ports', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def check_selection(arguments, expected):
    seen = []
    def fake_probe(alvo, porta, timeout):
        assert alvo == '127.0.0.1' and timeout == 2.0
        seen.append(porta)
        return {'porta':porta,'protocolo':'tcp','estado':'recusada','mensagem':'simulação de teste'}
    with patch.object(module,'verificar_porta',new=fake_probe), contextlib.redirect_stdout(io.StringIO()) as output:
        result = module.main(['127.0.0.1',*arguments])
    assert result == 0 and seen == expected
    assert f'Portas: {len(expected)}' in output.getvalue()
    assert f'Concluído: {len(expected)} portas verificadas.' in output.getvalue()
    return output.getvalue()

check_selection(['80','81','443'],[80,81,443])
check_selection(['80','80','81'],[80,81])
assert len(module.PORTAS_COMUNS) == 30
check_selection(['--comuns'],list(module.PORTAS_COMUNS))
check_selection(['--intervalo','80-83'],[80,81,82,83])
check_selection(['--intervalo','1-1'],[1])
check_selection(['--intervalo','65535-65535'],[65535])
full_output = check_selection(['--todas'],list(range(1,65536)))
assert '36h 24min 30s + sobrecarga' in full_output
assert module.formatar_duracao(65535) == '18h 12min 15s'

invalid = [[],['80','--comuns'],['80','--todas'],['80','--intervalo','81-83'],['--comuns','--todas'],['--todas','--intervalo','80-81'],['--intervalo','80'],['--intervalo','83-80'],['--intervalo','0-5'],['--intervalo','1-65536'],['--intervalo','a-b'],['--intervalo','80.5-81'],['0'],['65536']]
for arguments in invalid:
    with patch.object(module,'verificar_porta') as probe, contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()) as output:
        try:
            module.main(['127.0.0.1',*arguments])
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError('Invalid selection accepted: '+str(arguments))
        probe.assert_not_called()
        assert not output.getvalue()

with contextlib.redirect_stdout(io.StringIO()) as output:
    try:
        module.main(['--help'])
    except SystemExit as error:
        assert error.code == 0
for flag in ('--comuns','--intervalo','--todas','--timeout','--saida'):
    assert flag in output.getvalue()

print('OK: lista, duplicatas, 30 comuns, intervalos inclusivos, limites 1 e 65535, todas as 65535 portas, duracao, ajuda e 14 selecoes invalidas. Conexoes simuladas; sem varredura de rede real.')
