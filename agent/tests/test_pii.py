from app.pii import mask_pii


def test_mask_cpf():
    assert mask_pii("meu cpf e 389.083.863-43") == "meu cpf e [CPF]"


def test_mask_email():
    assert mask_pii("meu email e ana.silva@gmail.com") == "meu email e [EMAIL]"


def test_mask_telefone():
    assert mask_pii("me chama no +55 21 98888-7777") == "me chama no [TELEFONE]"


def test_mask_placa_antiga():
    assert mask_pii("a placa e ABC1234") == "a placa e [PLACA]"


def test_mask_placa_mercosul():
    assert mask_pii("a placa e ABC1D23") == "a placa e [PLACA]"


def test_nao_mascara_idade_nem_ano():
    texto = "tenho 35 anos, meu carro e um Onix 2019"
    assert mask_pii(texto) == texto


def test_nao_mascara_cep():
    assert mask_pii("meu cep e 26703-384") == "meu cep e 26703-384"


def test_mascara_multiplos_no_mesmo_texto():
    texto = "cpf 389.083.863-43, email ana@gmail.com, placa ABC1234"
    assert mask_pii(texto) == "cpf [CPF], email [EMAIL], placa [PLACA]"
