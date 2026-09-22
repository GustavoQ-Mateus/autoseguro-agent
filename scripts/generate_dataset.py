# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow"]
# ///
"""
Gera o dataset SINTETICO de conversas (lead <-> vendedor) para o desafio FDE.

Tudo aqui e ficticio e gerado proceduralmente: nenhum dado real de cliente.
Os dados pessoais (CPF, email, telefone, placa, CEP) sao plausiveis no formato,
mas inventados -- o candidato deve mascara-los na camada Silver.

Uso:
    uv run scripts/generate_dataset.py --n 2500 --seed 42 --out dataset/conversations.parquet
"""
from __future__ import annotations
import argparse, json, random, datetime as dt
from pathlib import Path

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Hugo",
         "Isabela", "Joao", "Karina", "Lucas", "Marina", "Nicolas", "Olivia", "Paulo",
         "Queila", "Rafael", "Sabrina", "Thiago", "Ursula", "Vinicius", "Wesley", "Yara"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Almeida",
              "Rodrigues", "Ferreira", "Gomes", "Martins", "Araujo", "Barbosa", "Ribeiro"]
VENDEDORES = ["Camila (Vendas)", "Rodrigo (Vendas)", "Patricia (Vendas)", "Marcos (Vendas)"]
MARCAS = {
    "Volkswagen": ["Gol", "Polo", "Virtus", "T-Cross", "Nivus"],
    "Chevrolet": ["Onix", "Onix Plus", "Tracker", "Spin"],
    "Fiat": ["Argo", "Mobi", "Cronos", "Pulse", "Toro"],
    "Hyundai": ["HB20", "Creta"],
    "Toyota": ["Corolla", "Yaris", "Corolla Cross"],
    "Honda": ["Civic", "City", "HR-V"],
    "Jeep": ["Renegade", "Compass"],
    "Renault": ["Kwid", "Sandero", "Duster"],
}
DDDS = ["11", "21", "31", "41", "47", "48", "51", "61", "62", "71", "81", "85"]
PROVEDORES = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com.br", "icloud.com", "bol.com.br"]
OUTCOMES = ["ganho", "perdido", "em_negociacao", "sem_resposta"]
OBJECOES = ["o preco ta salgado", "a franquia ta alta", "vi mais barato na concorrente",
            "preciso pensar", "vou ver com minha esposa", "achei caro pra esse carro"]
CONCORRENTES = ["Porto Seguro", "Azul Seguros", "Bradesco Auto", "SulAmerica", "Itau Auto"]


def cpf():
    n = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        s = sum((len(n) + 1 - i) * v for i, v in enumerate(n))
        d = (s * 10) % 11
        n.append(0 if d == 10 else d)
    return f"{n[0]}{n[1]}{n[2]}.{n[3]}{n[4]}{n[5]}.{n[6]}{n[7]}{n[8]}-{n[9]}{n[10]}"


def placa():
    L = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return f"{''.join(random.choice(L) for _ in range(3))}{random.randint(0,9)}{random.choice(L)}{random.randint(0,9)}{random.randint(0,9)}"


def telefone():
    return f"+55 {random.choice(DDDS)} 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"


def cep():
    pref = random.choice(["01", "04", "07", "08", "13", "20", "21", "26", "30", "41", "51", "59", "80", "88"])
    return f"{pref}{random.randint(100,999)}-{random.randint(100,999)}"


def email(nome, sobrenome):
    sep = random.choice([".", "_", ""])
    num = random.choice(["", "", str(random.randint(1, 99))])
    return f"{nome.lower()}{sep}{sobrenome.lower()}{num}@{random.choice(PROVEDORES)}"


def msg(conv_id, idx, sender, sender_name, body, mtype="text", base_ts=None):
    ts = base_ts + dt.timedelta(minutes=idx * random.randint(1, 9))
    return {
        "conversation_id": conv_id,
        "message_index": idx,
        "timestamp": ts.isoformat(),
        "sender_role": sender,          # "lead" | "vendedor"
        "sender_name": sender_name,
        "message_type": mtype,          # text | image | audio | document
        "message_body": body,
        "channel": "whatsapp",
    }


def gen_conversation(i, rng):
    random.seed(rng + i)
    nome, sobre = random.choice(NOMES), random.choice(SOBRENOMES)
    lead = f"{nome} {sobre}"
    vend = random.choice(VENDEDORES)
    marca = random.choice(list(MARCAS))
    modelo = random.choice(MARCAS[marca])
    ano = random.randint(2001, 2024)
    idade = random.randint(18, 82)
    base_ts = dt.datetime(2026, random.randint(1, 5), random.randint(1, 28),
                          random.randint(8, 21), random.randint(0, 59))
    cid = f"conv_{i:05d}"
    m, k = [], 0

    def add(role, name, body, mtype="text"):
        nonlocal k
        m.append(msg(cid, k, role, name, body, mtype, base_ts)); k += 1

    add("lead", lead, random.choice(["Oi, queria fazer um seguro pro meu carro", "Boa tarde, quero uma cotacao",
        "Ola! Vi o anuncio de voces, quanto fica o seguro?", "eae, tudo bem? to querendo segurar meu carro"]))
    add("vendedor", vend, f"Ola {nome}, tudo otimo! Claro, vou te ajudar. Qual o modelo e ano do veiculo?")
    add("lead", lead, random.choice([f"{marca} {modelo} {ano}", f"e um {modelo} {ano}", f"{modelo}, ano {ano}"]))
    add("vendedor", vend, "Perfeito. Pra cotar certinho preciso de alguns dados. Pode me passar seu CPF, idade e o CEP de onde o carro dorme?")

    # PII plantada (formato valido, conteudo ficticio)
    pii_bits = [f"CPF {cpf()}", f"tenho {idade} anos", f"CEP {cep()}"]
    random.shuffle(pii_bits)
    add("lead", lead, ", ".join(pii_bits).capitalize())
    if random.random() < 0.55:
        add("lead", lead, f"meu email é {email(nome, sobre)} e o whats é esse mesmo {telefone()}")
    if random.random() < 0.30:
        add("lead", lead, "[documento] CNH_frente.pdf", "document")
    if random.random() < 0.22:
        add("lead", lead, "[imagem] foto do veiculo na garagem", "image")
    if random.random() < 0.18:
        add("lead", lead, "[audio] mensagem de voz (18s)", "audio")
    add("lead", lead, random.choice([f"a placa é {placa()} se precisar", "qualquer coisa me chama", "to no aguardo"]))

    # cotacao do vendedor
    plano = random.choice(["Essencial", "Completo", "Premium"])
    preco = random.choice([129, 159, 189, 219, 259, 299, 349, 389])
    add("vendedor", vend, f"Show! Pelo perfil consigo o plano {plano} por R$ {preco},90/mes. Cobre colisao, roubo e furto. Te interessa?")

    outcome = random.choices(OUTCOMES, weights=[28, 22, 30, 20])[0]
    if outcome == "ganho":
        add("lead", lead, random.choice(["fechado!", "pode emitir entao", "vamos nessa, gostei"]))
        add("vendedor", vend, "Maravilha! Vou gerar o boleto e te mando a apolice. Bem-vindo!")
    elif outcome == "perdido":
        obj = random.choice(OBJECOES)
        add("lead", lead, f"{obj}... a {random.choice(CONCORRENTES)} me ofereceu menos")
        add("vendedor", vend, "Entendo! Consigo rever, posso te ligar?")
        add("lead", lead, random.choice(["nao precisa, obrigado", "deixa pra la por enquanto", "vou ficar com a outra"]))
    elif outcome == "em_negociacao":
        add("lead", lead, random.choice(OBJECOES))
        add("vendedor", vend, "Posso ajustar a franquia pra baixar a parcela. Te mando uma opcao amanha?")
        add("lead", lead, "pode mandar sim")
    else:  # sem_resposta
        add("vendedor", vend, random.choice(["Oi, conseguiu ver minha proposta?", f"{nome}, ainda tem interesse?"]))

    for row in m:
        row["conversation_outcome"] = outcome
        row["lead_idade_informada"] = idade
        row["veiculo_texto"] = f"{marca} {modelo} {ano}"
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="dataset/conversations.parquet")
    a = ap.parse_args()

    rows = []
    for i in range(a.n):
        rows.extend(gen_conversation(i, a.seed))

    import pandas as pd
    df = pd.DataFrame(rows)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    # amostra legivel pra inspecao rapida
    sample = df[df.conversation_id.isin(df.conversation_id.unique()[:3])].to_dict(orient="records")
    Path(out.parent / "sample.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in sample), encoding="utf-8")
    print(f"OK: {len(df)} mensagens em {df.conversation_id.nunique()} conversas -> {out}")
    print(f"colunas: {list(df.columns)}")
    print(f"outcomes: {df.drop_duplicates('conversation_id').conversation_outcome.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
