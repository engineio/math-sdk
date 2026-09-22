# Cash Cow 🎰🐄

**Cash Cow** é um jogo de caça-níquel estilo farm desenvolvido para a plataforma Stake Engine.  
Ele combina símbolos agrícolas com um modo bônus chamado **Golden Cow Hunt**, proporcionando uma jogabilidade divertida com um RTP alvo de ~95%.

## 🎯 Características

- **Grade:** 5x5
- **Linhas de pagamento:** 15
- **Símbolos:** Cenoura, Maçã, Uvas, Ovos, Balde de Leite, Fazendeira, Fazendeiro, Vaca Dourada, Wild
- **Bônus:** Golden Cow Hunt com coleta de multiplicadores
- **Max Win:** 12.500x

## 📂 Estrutura do Projeto

```
cash_cow/
├── __init__.py
├── game_config.py
├── run.py
├── README.md
└── meta.json
```

## ▶️ Como simular

Use o seguinte comando para rodar localmente:

```bash
PYTHONPATH="src" python3 games/cash_cow/run.py
```

## 🔄 RTP Alvo

O RTP foi ajustado e testado para ficar dentro de 94% a 96% ao longo de 100.000 simulações.

---

Desenvolvido para integração com [Stake Engine](https://stake-engine.com)
