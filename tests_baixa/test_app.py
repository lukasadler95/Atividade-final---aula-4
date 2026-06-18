import pytest # type: ignore
from src_baixa.app import somar, dividir

def test_somar():
    assert somar(2, 3) == 5