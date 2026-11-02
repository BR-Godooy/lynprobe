"""Regressões do LynProbe: dados simulados, sem conexões de rede."""
import contextlib
import io
from pathlib import Path
import runpy
import unittest


class RegressaoLynProbe(unittest.TestCase):
    def executar(self, nome):
        # Os scripts usam assert; evitar execução com otimizações que os removem.
        self.assertTrue(__debug__, 'Execute os testes sem a opção -O.')
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(Path(__file__).with_name(f'check_{nome}.py')))

    def test_conexoes_relatorios_e_entradas(self):
        self.executar('report')

    def test_selecao_e_limites_de_portas(self):
        self.executar('ports')

    def test_filtros_e_relatorio_completo(self):
        self.executar('display')

    def test_identificacao_e_limites_de_leitura(self):
        self.executar('services')


if __name__ == '__main__':
    unittest.main()
